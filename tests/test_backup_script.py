"""Backup script: pagination, manifest, and checksums, with every Supabase call faked."""

import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from scripts import backup_supabase  # noqa: E402


class BackupScriptTests(unittest.TestCase):
    def setUp(self):
        self.orig = {
            "request": backup_supabase.db._request,
            "configured": backup_supabase.db.configured,
            "page": backup_supabase.PAGE,
        }
        backup_supabase.db.configured = lambda: True
        backup_supabase.PAGE = 2

    def tearDown(self):
        backup_supabase.db._request = self.orig["request"]
        backup_supabase.db.configured = self.orig["configured"]
        backup_supabase.PAGE = self.orig["page"]

    def fake_request(self, method, path, *args, **kwargs):
        table = path.split("?")[0]
        if table == "items":
            return [{"id": 1}, {"id": 2}] if "offset=0" in path else [{"id": 3}]
        if table == "profiles":
            return []
        return []

    def test_exports_rows_counts_and_checksum(self):
        backup_supabase.db._request = self.fake_request
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "stdout"):
                code = backup_supabase.main(["--dir", tmp])
            backups = list(pathlib.Path(tmp).iterdir())
            self.assertEqual(code, 0)
            self.assertEqual(len(backups), 1)
            manifest = json.loads((backups[0] / "manifest.json").read_text(encoding="utf-8"))
            items = json.loads((backups[0] / "items.json").read_text(encoding="utf-8"))
            self.assertEqual([row["id"] for row in items], [1, 2, 3])
            self.assertEqual(manifest["tables"]["items"]["rows"], 3)
            self.assertEqual(len(manifest["tables"]["items"]["sha256"]), 64)
            self.assertEqual(manifest["tables"]["profiles"]["rows"], 0)

    def test_missing_config_fails(self):
        backup_supabase.db.configured = lambda: False
        with patch.object(sys, "stderr"):
            self.assertEqual(backup_supabase.main([]), 1)

    def test_table_error_is_recorded_not_fatal(self):
        def boom(method, path, *args, **kwargs):
            if path.startswith("items"):
                raise RuntimeError("offline")
            return []

        backup_supabase.db._request = boom
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "stdout"), patch.object(sys, "stderr"):
                code = backup_supabase.main(["--dir", tmp])
            self.assertEqual(code, 0)
            backup = list(pathlib.Path(tmp).iterdir())[0]
            manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("error", manifest["tables"]["items"])


if __name__ == "__main__":
    unittest.main()
