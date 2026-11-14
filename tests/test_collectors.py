"""Collector quality-gate tests: fixtures only, no network, no database."""

import contextlib
import hashlib
import io
import json
import os
import pathlib
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from collectors import dry_run, gdelt, store
from collectors.contract import QUALITY_RULES_VERSION, CancelledRun, RawRecord
from collectors.dry_run import write_report
from collectors.http import TransportError
from collectors.job import validate_collect_payload
from collectors.quality import canonicalize_url, gate
from collectors.registry import Connector, get_connector

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
TEST_CONNECTOR = Connector(
    connector_id="test_search",
    source="example",
    scope="keyword",
    record_kind="content",
    enabled=True,
    dry_run=True,
    rights="test",
)


def raw(**overrides):
    values = {
        "source": "example",
        "connector_id": "test_search",
        "source_item_id": "1001",
        "url": "https://example.com/story",
        "title": "Thailand startup ecosystem update",
        "author_id": "pg",
        "author_display": "pg",
        "published_at": "2026-11-11T00:00:00Z",
        "engagement": {"views": 10, "comments": 2},
        "numeric_signal": 10,
        "signal_unit": "views",
    }
    values.update(overrides)
    return RawRecord(**values)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.connector = TEST_CONNECTOR

    def gate_one(self, record):
        return gate([record], self.connector, now=NOW)

    def test_accepts_valid_record(self):
        outcome = self.gate_one(raw())
        self.assertEqual(len(outcome.accepted), 1)
        self.assertEqual(outcome.rejected, [])
        self.assertEqual(outcome.accepted[0].language, "en")

    def test_rejects_missing_title(self):
        self.assertEqual(self.gate_one(raw(title="")).rejected[0].reason, "malformed")

    def test_rejects_bad_url(self):
        self.assertEqual(
            self.gate_one(raw(url="javascript:alert(1)")).rejected[0].reason, "bad_url"
        )

    def test_strips_html_and_tracking_params(self):
        outcome = self.gate_one(
            raw(
                title="<b>Thailand</b> startup ecosystem update",
                url="https://example.com/a?utm_source=x",
            )
        )
        record = outcome.accepted[0]
        self.assertEqual(record.title, "Thailand startup ecosystem update")
        self.assertEqual(record.canonical_url, "https://example.com/a")

    def test_rejects_wrong_language(self):
        outcome = self.gate_one(raw(title="泰国创业公司生态更新消息"))
        self.assertEqual(outcome.rejected[0].reason, "unsupported_language")

    def test_rejects_spam(self):
        outcome = self.gate_one(raw(title="Casino bonus crypto giveaway today"))
        self.assertEqual(outcome.rejected[0].reason, "spam")

    def test_rejects_future_date(self):
        outcome = self.gate_one(raw(published_at="2026-11-20T00:00:00Z"))
        self.assertEqual(outcome.rejected[0].reason, "out_of_window")

    def test_rejects_metric_anomaly(self):
        outcome = self.gate_one(raw(numeric_signal=-5))
        self.assertEqual(outcome.rejected[0].reason, "metric_invalid")

    def test_duplicate_source_id_counts_once(self):
        outcome = gate([raw(), raw()], self.connector, now=NOW)
        self.assertEqual(len(outcome.accepted), 1)
        self.assertEqual(outcome.duplicates, 1)

    def test_short_title_is_quarantined(self):
        outcome = self.gate_one(raw(title="Hi"))
        self.assertEqual(outcome.accepted, [])
        self.assertEqual(len(outcome.quarantined), 1)

    def test_canonicalize_rejects_private_host(self):
        with self.assertRaises(ValueError):
            canonicalize_url("http://127.0.0.1/private")


class GdeltAdapterTests(unittest.TestCase):
    connector = get_connector("gdelt_doc")

    def fetch(self, articles, limit=10):
        with patch("collectors.gdelt.fetch_json", return_value={"articles": articles}) as fake:
            records = gdelt.fetch("Thailand", limit, self.connector)
        return records, fake.call_args[0][0]

    def test_maps_articles_to_raw_records(self):
        records, url = self.fetch(
            [
                {
                    "url": "https://example.com/a?utm=1",
                    "title": "Thailand startup raises fund",
                    "seendate": "20261111T004500Z",
                    "domain": "example.com",
                    "language": "English",
                    "sourcecountry": "Thailand",
                },
                {"title": "missing url"},
            ]
        )
        self.assertIn("query=Thailand", url)
        self.assertIn("maxrecords=10", url)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.source, "gdelt")
        self.assertEqual(
            record.source_item_id, hashlib.sha256(b"https://example.com/a?utm=1").hexdigest()
        )
        self.assertEqual(record.published_at, "2026-11-11T00:45:00+00:00")
        self.assertEqual(record.author_display, "example.com")

    def test_bad_seendate_is_none(self):
        records, _ = self.fetch(
            [{"url": "https://example.com/b", "title": "A story", "seendate": "bad"}]
        )
        self.assertIsNone(records[0].published_at)

    def test_caps_max_records(self):
        _, url = self.fetch([], limit=500)
        self.assertIn("maxrecords=250", url)

    def test_gate_accepts_adapter_output(self):
        records, _ = self.fetch(
            [
                {
                    "url": "https://example.com/a",
                    "title": "Thailand startup raises fund",
                    "seendate": "20261111T004500Z",
                    "domain": "example.com",
                }
            ]
        )
        outcome = gate(records, self.connector, now=NOW)
        self.assertEqual(len(outcome.accepted), 1)
        self.assertEqual(outcome.accepted[0].language, "en")

    def test_retries_a_throttle_once(self):
        with (
            patch(
                "collectors.gdelt.fetch_json",
                side_effect=[TransportError("HTTP Error 429: Too Many Requests"), {"articles": []}],
            ) as fake,
            patch("collectors.gdelt.time.sleep") as sleep,
        ):
            records = gdelt.fetch("x", 1, self.connector)
        self.assertEqual(records, [])
        self.assertEqual(fake.call_count, 2)
        sleep.assert_called_once()


class ReportTests(unittest.TestCase):
    def test_report_contains_hashes_not_titles(self):
        connector = TEST_CONNECTOR
        outcome = gate([raw(title="Secret title that should not be stored")], connector, now=NOW)
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "report.jsonl"
            write_report(path, outcome)
            text = path.read_text(encoding="utf-8")
        self.assertNotIn("Secret title", text)
        expected = hashlib.sha256(b"https://example.com/story").hexdigest()
        self.assertIn(expected, text)
        line = json.loads(text.splitlines()[0])
        self.assertEqual(line["status"], "accepted")
        self.assertNotIn("title", line)

    def test_second_run_appends_to_report(self):
        outcome = gate([raw()], TEST_CONNECTOR, now=NOW)
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "report.jsonl"
            write_report(path, outcome)
            write_report(path, outcome)
            lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)


class JobPayloadTests(unittest.TestCase):
    def validate(self, payload):
        return validate_collect_payload(payload, lambda _: TEST_CONNECTOR)

    def test_valid_payload(self):
        payload = self.validate(
            {
                "connector_id": "test_search",
                "scope": {"keyword": "Thailand"},
                "mode": "manual",
                "dry_run": True,
                "max_records": 50,
            }
        )
        self.assertEqual(payload["scope"]["keyword"], "Thailand")
        self.assertTrue(payload["dry_run"])

    def test_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            self.validate({"connector_id": "test_search", "scope": {"keyword": "x"}, "surprise": 1})

    def test_rejects_disabled_connector(self):
        with self.assertRaises(ValueError):
            validate_collect_payload(
                {"connector_id": "google_trends_th", "scope": {"keyword": "x"}, "dry_run": True}
            )

    def test_rejects_writes(self):
        with patch.dict(os.environ, {"COLLECTOR_WRITE_ENABLED": "0"}):
            with self.assertRaises(ValueError):
                self.validate(
                    {"connector_id": "test_search", "scope": {"keyword": "x"}, "dry_run": False}
                )

    def test_allows_writes_when_enabled(self):
        with patch.dict(os.environ, {"COLLECTOR_WRITE_ENABLED": "1"}):
            payload = self.validate(
                {"connector_id": "test_search", "scope": {"keyword": "x"}, "dry_run": False}
            )
        self.assertFalse(payload["dry_run"])

    def test_rejects_bad_limits_and_modes(self):
        for payload in (
            {"connector_id": "test_search", "scope": {"keyword": "x"}, "max_records": 0},
            {"connector_id": "test_search", "scope": {"keyword": "x"}, "max_records": 101},
            {"connector_id": "test_search", "scope": {"keyword": "x"}, "mode": "cron"},
            {"connector_id": "test_search", "scope": {}},
        ):
            with self.assertRaises(ValueError):
                self.validate(payload)

    def test_quality_rules_version_must_match(self):
        payload = {"connector_id": "test_search", "scope": {"keyword": "x"}}
        self.assertEqual(
            self.validate({**payload, "quality_rules_version": QUALITY_RULES_VERSION})[
                "quality_rules_version"
            ],
            QUALITY_RULES_VERSION,
        )
        with self.assertRaises(ValueError):
            self.validate({**payload, "quality_rules_version": "2026-01-01.1"})

    def test_accepts_positive_job_id(self):
        payload = self.validate(
            {"connector_id": "test_search", "scope": {"keyword": "x"}, "job_id": 42}
        )
        self.assertEqual(payload["job_id"], 42)

    def test_rejects_bad_job_id(self):
        base = {"connector_id": "test_search", "scope": {"keyword": "x"}}
        for value in (0, -1, "42", True, 1.5):
            with self.assertRaises(ValueError):
                self.validate({**base, "job_id": value})

    def test_job_id_is_optional(self):
        payload = self.validate({"connector_id": "test_search", "scope": {"keyword": "x"}})
        self.assertNotIn("job_id", payload)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.orig = {
            "env": os.environ.get(store.WRITE_ENV),
            "configured": store.db.configured,
            "user_id": store.db.user_id,
            "request": store.db._request,
        }
        self.calls = []
        self.existing_records = []
        self.existing_items = []
        self.fail_on = set()
        self.job_row = None
        os.environ[store.WRITE_ENV] = "1"
        store.db.configured = lambda: True
        store.db.user_id = lambda: "user-1"
        store.db._request = self.fake_request

    def tearDown(self):
        if self.orig["env"] is None:
            os.environ.pop(store.WRITE_ENV, None)
        else:
            os.environ[store.WRITE_ENV] = self.orig["env"]
        store.db.configured = self.orig["configured"]
        store.db.user_id = self.orig["user_id"]
        store.db._request = self.orig["request"]

    def fake_request(self, method, path, payload=None, prefer="", **kwargs):
        self.calls.append((method, path, payload, prefer))
        table = path.split("?")[0]
        if method == "POST" and table in self.fail_on:
            raise RuntimeError(f"boom: {table}")
        if method == "GET":
            if table == "jobs":
                return [self.job_row] if self.job_row else []
            if table == "collector_records":
                return self.existing_records
            if table == "items":
                return self.existing_items
            return []
        if table == "collector_records":
            return [
                {"id": f"rec-{row['source_item_id']}", "source_item_id": row["source_item_id"]}
                for row in payload
            ]
        if table == "items":
            return [
                {"id": f"item-{row['canonical_url']}", "canonical_url": row["canonical_url"]}
                for row in payload
            ]
        return None

    def save(self, cancel_check=None):
        outcome = gate([raw()], TEST_CONNECTOR, now=NOW)
        return store.save_accepted(
            TEST_CONNECTOR,
            "Thailand",
            outcome.accepted,
            outcome.counters(1),
            cancel_check=cancel_check,
        )

    def posts(self, table, resolution=""):
        return [
            payload
            for method, path, payload, prefer in self.calls
            if method == "POST" and path.startswith(table) and resolution in prefer
        ]

    def test_writes_disabled_by_default(self):
        os.environ.pop(store.WRITE_ENV, None)
        with self.assertRaises(RuntimeError):
            store.save_accepted(TEST_CONNECTOR, "Thailand", [], {})

    def test_save_upserts_records_items_links_state(self):
        result = self.save()

        paths = [call[1].split("?")[0] for call in self.calls]
        self.assertIn("collector_records", paths)
        self.assertIn("items", paths)
        self.assertIn("collector_item_links", paths)
        self.assertIn("collector_state", paths)
        self.assertFalse(any(call[0] == "DELETE" for call in self.calls))

        item_call = next(
            call for call in self.calls if call[0] == "POST" and call[1].startswith("items?")
        )
        self.assertEqual(item_call[2][0]["metric"], "views")
        self.assertEqual(item_call[2][0]["body"], "")
        self.assertEqual(item_call[2][0]["score"], 10)
        self.assertEqual(result["written"], 1)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 0)

    def test_uses_two_batched_reads_per_run(self):
        self.save()
        gets = [path for method, path, _, _ in self.calls if method == "GET"]
        self.assertEqual(len(gets), 2)
        self.assertTrue(gets[0].startswith("collector_records?"))
        self.assertTrue(gets[1].startswith("items?"))

    def test_repeat_run_merges_keywords(self):
        self.existing_records = [{"source_item_id": "1001", "keywords_matched": ["old"]}]

        result = self.save()

        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 1)
        record = self.posts("collector_records")[0][0]
        self.assertEqual(record["keywords_matched"], ["old", "Thailand"])

    def test_existing_item_refreshes_metric_columns_only(self):
        self.existing_items = [
            {"id": "item-x", "canonical_url": "https://example.com/story", "deleted_at": None}
        ]

        self.save()

        self.assertEqual(self.posts("items", "ignore-duplicates"), [])
        projection = self.posts("items", "merge-duplicates")[0][0]
        self.assertEqual(
            set(projection), {"user_id", "keyword", "canonical_url", "score", "metric"}
        )
        self.assertEqual(projection["score"], 10)
        self.assertEqual(projection["metric"], "views")

    def test_trashed_item_is_not_relinked_or_refreshed(self):
        self.existing_items = [
            {
                "id": "item-x",
                "canonical_url": "https://example.com/story",
                "deleted_at": "2026-11-01T00:00:00Z",
            }
        ]

        self.save()

        self.assertEqual(self.posts("collector_item_links"), [])
        self.assertEqual(self.posts("items"), [])

    def test_success_updates_source_status(self):
        self.save()
        status = self.posts("source_status")[0][0]
        self.assertEqual(status["source"], "example")
        self.assertTrue(status["ok"])
        self.assertEqual(status["count"], 1)

    def test_failed_write_records_error_state_and_reraises(self):
        self.fail_on = {"collector_records"}

        with self.assertRaises(RuntimeError):
            self.save()

        state = self.posts("collector_state")[-1][0]
        self.assertEqual(state["last_status"], "error")
        self.assertNotIn("cursor", state)
        self.assertNotIn("counters", state)

    @staticmethod
    def cancel_after(allowed):
        calls = {"count": 0}

        def check():
            calls["count"] += 1
            return calls["count"] > allowed

        return check

    def test_cancel_before_persist_writes_nothing(self):
        with self.assertRaises(CancelledRun) as raised:
            self.save(cancel_check=lambda: True)

        self.assertEqual([call for call in self.calls if call[0] == "POST"], [])
        self.assertEqual(raised.exception.counters["written"], 0)

    def test_cancel_after_records_stops_before_items(self):
        with self.assertRaises(CancelledRun) as raised:
            self.save(cancel_check=self.cancel_after(1))

        paths = [call[1].split("?")[0] for call in self.calls if call[0] == "POST"]
        self.assertEqual(paths, ["collector_records"])
        self.assertEqual(raised.exception.counters["written"], 1)

    def test_cancel_after_all_writes_skips_health_state(self):
        with self.assertRaises(CancelledRun):
            self.save(cancel_check=self.cancel_after(4))

        paths = [call[1].split("?")[0] for call in self.calls if call[0] == "POST"]
        self.assertIn("collector_item_links", paths)
        self.assertNotIn("collector_state", paths)
        self.assertNotIn("source_status", paths)

    def test_job_cancel_check_reads_owner_scoped_row(self):
        self.job_row = {"cancel_requested": True}

        self.assertTrue(store.job_cancel_check(7, interval=0)())

        path = next(call[1] for call in self.calls if call[1].startswith("jobs?"))
        self.assertIn("id=eq.7", path)
        self.assertIn("user_id=eq.user-1", path)

    def test_job_cancel_check_throttles_and_survives_failures(self):
        self.job_row = {"cancel_requested": False}
        check = store.job_cancel_check(7)
        self.assertFalse(check())
        self.job_row = {"cancel_requested": True}
        self.assertFalse(check())
        self.assertEqual(len([call for call in self.calls if call[1].startswith("jobs?")]), 1)

        def boom(*_args, **_kwargs):
            raise RuntimeError("offline")

        store.db._request = boom
        self.assertFalse(store.job_cancel_check(7, interval=0)())


class DryRunCancellationTests(unittest.TestCase):
    def setUp(self):
        self.fetched = []
        self.orig_adapters = dry_run.ADAPTERS
        self.orig_connector = dry_run.get_connector
        dry_run.ADAPTERS = {"test_search": types.SimpleNamespace(fetch=self.fetch)}
        dry_run.get_connector = lambda _connector_id: TEST_CONNECTOR

    def tearDown(self):
        dry_run.ADAPTERS = self.orig_adapters
        dry_run.get_connector = self.orig_connector

    def fetch(self, keyword, _limit, _connector):
        self.fetched.append(keyword)
        return [raw()]

    def run_dry(self, cancel_check, directory):
        with contextlib.redirect_stdout(io.StringIO()):
            return dry_run.run(
                "test_search",
                "Thailand",
                5,
                pathlib.Path(directory),
                0,
                cancel_check=cancel_check,
            )

    def test_cancel_before_fetch_skips_provider_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self.run_dry(lambda: True, tmp)
            files = list(pathlib.Path(tmp).iterdir())

        self.assertTrue(summary["cancelled"])
        self.assertEqual(self.fetched, [])
        self.assertEqual(summary["counters"]["fetched"], 0)
        self.assertEqual(files, [])

    def test_cancel_after_gate_keeps_counters_and_report(self):
        checks = iter([False, True])

        with tempfile.TemporaryDirectory() as tmp:
            summary = self.run_dry(lambda: next(checks), tmp)
            files = list(pathlib.Path(tmp).iterdir())
            report_lines = len(files[0].read_text(encoding="utf-8").splitlines()) if files else 0

        self.assertTrue(summary["cancelled"])
        self.assertEqual(self.fetched, ["Thailand"])
        self.assertEqual(summary["counters"]["accepted"], 1)
        self.assertEqual(len(files), 1)
        self.assertEqual(report_lines, 1)

    def test_no_cancel_returns_normal_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self.run_dry(lambda: False, tmp)

        self.assertFalse(summary["cancelled"])
        self.assertEqual(summary["counters"]["accepted"], 1)


if __name__ == "__main__":
    unittest.main()
