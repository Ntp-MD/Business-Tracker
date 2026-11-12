"""Collector quality-gate tests: fixtures only, no network, no database."""

import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from collectors import store
from collectors.contract import RawRecord
from collectors.dry_run import write_report
from collectors.hn import parse_hits
from collectors.job import validate_collect_payload
from collectors.quality import canonicalize_url, gate
from collectors.registry import get_connector

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def raw(**overrides):
    values = {
        "source": "hackernews",
        "connector_id": "hn_search",
        "source_item_id": "1001",
        "url": "https://example.com/story",
        "title": "Thailand startup ecosystem update",
        "author_id": "pg",
        "author_display": "pg",
        "published_at": "2026-11-11T00:00:00Z",
        "engagement": {"points": 10, "comments": 2},
        "numeric_signal": 10,
        "signal_unit": "points",
    }
    values.update(overrides)
    return RawRecord(**values)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.connector = get_connector("hn_search")

    def gate_one(self, record):
        return gate([record], self.connector, now=NOW)

    def test_accepts_valid_hn_story(self):
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


class HackerNewsTests(unittest.TestCase):
    def test_parse_hits_keeps_metadata_only(self):
        connector = get_connector("hn_search")
        payload = {
            "hits": [
                {
                    "objectID": "42",
                    "title": "Thailand startup ecosystem update",
                    "url": "https://example.com/story?utm_medium=hn",
                    "author": "pg",
                    "points": 12,
                    "num_comments": 3,
                    "created_at": "2026-11-11T00:00:00Z",
                }
            ]
        }
        records = parse_hits(payload, connector)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].source_item_id, "42")
        self.assertEqual(records[0].signal_unit, "points")
        self.assertNotIn("title", records[0].raw_source_ref)

    def test_parse_hits_rejects_bad_payload(self):
        from collectors.http import TransportError

        with self.assertRaises(TransportError):
            parse_hits({"hits": "nope"}, get_connector("hn_search"))

    def test_canonicalize_rejects_private_host(self):
        with self.assertRaises(ValueError):
            canonicalize_url("http://127.0.0.1/private")


class ReportTests(unittest.TestCase):
    def test_report_contains_hashes_not_titles(self):
        connector = get_connector("hn_search")
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


class JobPayloadTests(unittest.TestCase):
    def test_valid_payload(self):
        payload = validate_collect_payload(
            {
                "connector_id": "hn_search",
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
            validate_collect_payload(
                {"connector_id": "hn_search", "scope": {"keyword": "x"}, "surprise": 1}
            )

    def test_rejects_disabled_connector(self):
        with self.assertRaises(ValueError):
            validate_collect_payload(
                {"connector_id": "google_trends_th", "scope": {"keyword": "x"}, "dry_run": True}
            )

    def test_rejects_writes(self):
        with self.assertRaises(ValueError):
            validate_collect_payload(
                {"connector_id": "hn_search", "scope": {"keyword": "x"}, "dry_run": False}
            )

    def test_rejects_bad_limits_and_modes(self):
        for payload in (
            {"connector_id": "hn_search", "scope": {"keyword": "x"}, "max_records": 0},
            {"connector_id": "hn_search", "scope": {"keyword": "x"}, "max_records": 101},
            {"connector_id": "hn_search", "scope": {"keyword": "x"}, "mode": "cron"},
            {"connector_id": "hn_search", "scope": {}},
        ):
            with self.assertRaises(ValueError):
                validate_collect_payload(payload)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.orig = {
            "env": os.environ.get(store.WRITE_ENV),
            "configured": store.db.configured,
            "user_id": store.db.user_id,
            "request": store.db._request,
        }
        self.calls = []

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
        if method == "GET":
            return []
        if path.startswith("collector_records"):
            return [
                {"id": f"rec-{row['source_item_id']}", "source_item_id": row["source_item_id"]}
                for row in payload
            ]
        if path.startswith("items"):
            return [
                {"id": f"item-{row['canonical_url']}", "canonical_url": row["canonical_url"]}
                for row in payload
            ]
        return None

    def test_writes_disabled_by_default(self):
        os.environ.pop(store.WRITE_ENV, None)
        with self.assertRaises(RuntimeError):
            store.save_accepted(get_connector("hn_search"), "Thailand", [], {})

    def test_save_upserts_records_items_links_state(self):
        os.environ[store.WRITE_ENV] = "1"
        store.db.configured = lambda: True
        store.db.user_id = lambda: "user-1"
        store.db._request = self.fake_request
        connector = get_connector("hn_search")
        outcome = gate([raw()], connector, now=NOW)
        counters = outcome.counters(1)

        result = store.save_accepted(connector, "Thailand", outcome.accepted, counters)

        paths = [call[1].split("?")[0] for call in self.calls]
        self.assertIn("collector_records", paths)
        self.assertIn("items", paths)
        self.assertIn("collector_item_links", paths)
        self.assertIn("collector_state", paths)
        self.assertFalse(any(call[0] == "DELETE" for call in self.calls))

        item_call = next(
            call for call in self.calls if call[0] == "POST" and call[1].startswith("items?")
        )
        self.assertEqual(item_call[2][0]["metric"], "points")
        self.assertEqual(item_call[2][0]["body"], "")
        self.assertEqual(item_call[2][0]["score"], 10)
        self.assertEqual(result["written"], 1)


if __name__ == "__main__":
    unittest.main()
