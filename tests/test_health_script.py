"""Health-check script behavior: endpoint failures fail, a stopped worker only warns."""

import contextlib
import io
import json
import pathlib
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from scripts import check_health  # noqa: E402

PROD = "https://trendrail.vercel.app/api/health"
LIVE = "https://trendrail-live.vercel.app/api/health"


def payload(ok=True, worker=None):
    return io.StringIO(json.dumps({"ok": ok, "items": {"active": 1}, "worker": worker}))


class HealthScriptTests(unittest.TestCase):
    def run_check(self, url, body):
        stream = io.StringIO()
        with (
            patch.object(check_health.urllib.request, "urlopen") as urlopen,
            contextlib.redirect_stdout(stream),
        ):
            urlopen.return_value.__enter__.return_value = body
            check_health.check(url)
        return stream.getvalue()

    def test_stale_worker_is_a_warning_not_a_failure(self):
        stale = {"lastSeen": "2026-11-14T11:48:19Z", "stale": True}
        out = self.run_check(PROD, payload(worker=stale))
        self.assertIn("warning", out)
        self.assertIn("worker stale", out)

    def test_missing_worker_on_prod_is_a_warning(self):
        out = self.run_check(PROD, payload(worker=None))
        self.assertIn("warning", out)

    def test_live_without_worker_is_fine(self):
        out = self.run_check(LIVE, payload(worker=None))
        self.assertNotIn("warning", out)

    def test_ok_false_still_fails(self):
        with (
            patch.object(check_health.urllib.request, "urlopen") as urlopen,
            self.assertRaises(RuntimeError),
        ):
            urlopen.return_value.__enter__.return_value = payload(ok=False)
            check_health.check(PROD)

    def test_main_fails_when_a_url_is_unreachable(self):
        with (
            patch.object(check_health.urllib.request, "urlopen") as urlopen,
            patch.dict("os.environ", {"HEALTH_URLS": PROD}, clear=False),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            urlopen.side_effect = HTTPError(PROD, 500, "server error", {}, None)
            self.assertEqual(check_health.main(), 1)


if __name__ == "__main__":
    unittest.main()
