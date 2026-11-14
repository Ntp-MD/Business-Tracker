"""record_id backfill script: idempotent PATCHes, dry-run, and config failure."""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from scripts import backfill_record_ids  # noqa: E402

LINKS = [
    {"record_id": "rec-1", "item_id": "item-1"},
    {"record_id": "rec-2", "item_id": "item-2"},
]


class BackfillScriptTests(unittest.TestCase):
    def setUp(self):
        self.orig = {
            "request": backfill_record_ids.db._request,
            "configured": backfill_record_ids.db.configured,
            "user_id": backfill_record_ids.db.user_id,
        }
        self.patches = []
        backfill_record_ids.db.configured = lambda: True
        backfill_record_ids.db.user_id = lambda: "user-1"

    def tearDown(self):
        backfill_record_ids.db._request = self.orig["request"]
        backfill_record_ids.db.configured = self.orig["configured"]
        backfill_record_ids.db.user_id = self.orig["user_id"]

    def fake_request(self, method, path, payload=None, *args, **kwargs):
        if method == "GET":
            return LINKS
        self.patches.append((path, payload))
        return None

    def test_patches_only_null_record_ids(self):
        backfill_record_ids.db._request = self.fake_request
        with patch.object(sys, "stdout"):
            self.assertEqual(backfill_record_ids.main([]), 0)
        self.assertEqual(len(self.patches), 2)
        self.assertTrue(all("record_id=is.null" in path for path, _ in self.patches))
        self.assertEqual(self.patches[0][1], {"record_id": "rec-1"})

    def test_dry_run_does_not_patch(self):
        backfill_record_ids.db._request = self.fake_request
        with patch.object(sys, "stdout"):
            self.assertEqual(backfill_record_ids.main(["--dry-run"]), 0)
        self.assertEqual(self.patches, [])

    def test_missing_config_fails(self):
        backfill_record_ids.db.configured = lambda: False
        with patch.object(sys, "stderr"):
            self.assertEqual(backfill_record_ids.main([]), 1)


if __name__ == "__main__":
    unittest.main()
