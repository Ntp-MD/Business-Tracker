"""Core tests for server.py — stdlib unittest, no network."""

import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

import server


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        # Unit tests must never touch Supabase — force the local file adapter.
        self._db_configured = server.db.configured
        self._db_save = server.db.save
        server.db.configured = lambda: False
        server.db.save = lambda *args, **kwargs: False
        self.orig = {
            k: getattr(server, k)
            for k in (
                "ITEMS_FILE",
                "INDEX_FILE",
                "ANALYSIS_FILE",
                "ASSETS",
                "ARCHIVE_FILE",
                "TRASH_FILE",
                "SOURCE_LOG_FILE",
                "PROFILES_FILE",
            )
        }
        server.ITEMS_FILE = self.tmp / "items.json"
        server.INDEX_FILE = self.tmp / "index.json"
        server.ANALYSIS_FILE = self.tmp / "analysis.json"
        server.ARCHIVE_FILE = self.tmp / "archive.json"
        server.TRASH_FILE = self.tmp / "trash.json"
        server.SOURCE_LOG_FILE = self.tmp / "sources.json"
        server.PROFILES_FILE = self.tmp / "profiles.json"
        server.ASSETS = self.tmp / "assets"
        server.ASSETS.mkdir()

    def tearDown(self):
        for key, value in self.orig.items():
            setattr(server, key, value)
        server.db.configured = self._db_configured
        server.db.save = self._db_save
        shutil.rmtree(self.tmp, ignore_errors=True)

    def item(self, url, title, source="gnews", keyword="kw"):
        return {
            "url": url,
            "title": title,
            "body": "",
            "source": source,
            "keyword": keyword,
            "author": "",
            "score": 0,
            "created": "",
            "published": "",
            "created_at": server.now_iso(),
            "asset": None,
        }

    def test_canonical_url_variants(self):
        want = "https://www.youtube.com/watch?v=abc123"
        for url in (
            "https://youtu.be/abc123?t=30",
            "https://m.youtube.com/watch?v=abc123&utm_source=x",
            "https://www.youtube.com/shorts/abc123",
        ):
            self.assertEqual(server.canonical_url(url), want)
        self.assertEqual(
            server.canonical_url("https://www.facebook.com/ads/library/?active=1&id=99&fbclid=x"),
            "https://www.facebook.com/ads/library/?id=99",
        )
        self.assertEqual(
            server.canonical_url("https://www.tiktok.com/@u/video/7123?is_from_webapp=1"),
            "https://www.tiktok.com/video/7123",
        )

    def test_dedup_layers(self):
        added, skipped, _ = server.merge_items(
            [
                self.item("https://example.com/a?utm_source=x", "ข่าวเดียวกัน"),
                self.item("https://example.com/a", "ข่าวเดียวกัน"),
            ],
            "kw",
            0,
            fetch_thumbs=False,
        )
        self.assertEqual((added, skipped), (1, 1))

        added, skipped, _ = server.merge_items(
            [
                self.item(
                    "https://example.com/t1",
                    "โปรโมชั่นสินค้าใหม่ลดราคาพิเศษสำหรับลูกค้าทุกท่านวันนี้และพรุ่งนี้เท่านั้น",
                    "tiktok",
                ),
                self.item(
                    "https://example.com/t2",
                    "โปรโมชั่นสินค้าใหม่ลดราคาพิเศษสำหรับลูกค้าทุกท่านวันนี้และพรุ่งนี้เท่านั้นครับ",
                    "tiktok",
                ),
            ],
            "kw",
            0,
            fetch_thumbs=False,
        )
        self.assertEqual((added, skipped), (1, 1))

    def test_same_url_other_keyword_allowed(self):
        url = "https://example.com/same"
        server.merge_items(
            [self.item(url, "เรื่องเดียวกัน", keyword="one")], "one", 0, fetch_thumbs=False
        )
        added, skipped, _ = server.merge_items(
            [self.item(url, "เรื่องเดียวกัน", keyword="two")], "two", 0, fetch_thumbs=False
        )
        self.assertEqual((added, skipped), (1, 0))

    def test_import_roundtrip(self):
        server.merge_items(
            [self.item("https://example.com/i1", "นำเข้า")], "kw", 0, fetch_thumbs=False
        )
        payload = server.export_payload()
        self.assertEqual(payload["format"], server.EXPORT_FORMAT)
        self.assertEqual(payload["count"], 1)

        before = len(server.load_json(server.ITEMS_FILE, []))
        result, err = server.import_payload(payload)
        self.assertIsNone(err)
        self.assertEqual(result["added"], 0)
        self.assertEqual(result["duplicates"], 1)
        self.assertEqual(len(server.load_json(server.ITEMS_FILE, [])), before)

    def test_import_rejects_bad_format(self):
        result, err = server.import_payload({"items": []})
        self.assertEqual(result, {})
        self.assertTrue(err)

    def test_clear_keyword(self):
        server.merge_items([self.item("https://example.com/c1", "ลบ")], "kw", 0, fetch_thumbs=False)
        server.merge_items(
            [self.item("https://example.com/c2", "เก็บ", keyword="keep")],
            "keep",
            0,
            fetch_thumbs=False,
        )
        out = server.clear_keyword("kw")
        self.assertEqual(out["removed"], 1)
        left = server.load_json(server.ITEMS_FILE, [])
        self.assertEqual([i["keyword"] for i in left], ["keep"])

    def test_prune_old_dated_items(self):
        old = self.item("https://example.com/old", "เก่า")
        old["published"] = "2025-01-01T00:00:00+00:00"
        new = self.item("https://example.com/new", "ใหม่")
        new["published"] = server.now_iso()
        server.merge_items([old], "kw", 0, fetch_thumbs=False)
        server.merge_items([new], "kw", 0, fetch_thumbs=False)
        out = server.prune_old(90)
        self.assertEqual(out["removed"], 1)
        left = server.load_json(server.ITEMS_FILE, [])
        self.assertEqual([i["url"] for i in left], ["https://example.com/new"])

    def test_item_crud(self):
        payload = self.item("https://example.com/crud", "ชื่อเดิม")
        result, err = server.create_item(payload)
        self.assertIsNone(err)
        self.assertEqual(result["added"], 1)

        result, err = server.update_item(
            "kw", "https://example.com/crud", {"title": "ชื่อใหม่", "score": 42}
        )
        self.assertIsNone(err)
        self.assertEqual(result["item"]["title"], "ชื่อใหม่")
        self.assertEqual(result["item"]["score"], 42)

        result, err = server.delete_item("kw", "https://example.com/crud")
        self.assertIsNone(err)
        self.assertEqual(server.load_json(server.ITEMS_FILE, []), [])

    def test_archive_restore_and_bulk(self):
        server.merge_items(
            [
                self.item("https://example.com/ar1", "เก็บก่อน"),
                self.item("https://example.com/ar2", "ย้าย keyword"),
            ],
            "kw",
            0,
            fetch_thumbs=False,
        )
        keys = [{"keyword": "kw", "url": "https://example.com/ar1"}]
        out = server.archive_items(keys)
        self.assertEqual(out["archived"], 1)
        self.assertEqual(len(server.load_archive()), 1)
        self.assertEqual(len(server.load_json(server.ITEMS_FILE, [])), 1)

        out = server.restore_archived(keys)
        self.assertEqual(out["restored"], 1)
        self.assertEqual(len(server.load_json(server.ITEMS_FILE, [])), 2)
        self.assertEqual(len(server.load_archive()), 0)

        out, err = server.bulk_items(
            "move", [{"keyword": "kw", "url": "https://example.com/ar2"}], "moved"
        )
        self.assertIsNone(err)
        self.assertEqual(out["changed"], 1)
        keywords = [i["keyword"] for i in server.load_json(server.ITEMS_FILE, [])]
        self.assertIn("moved", keywords)

    def test_export_import_archive(self):
        server.merge_items(
            [self.item("https://example.com/ex1", "ส่งออก")], "kw", 0, fetch_thumbs=False
        )
        server.archive_items([{"keyword": "kw", "url": "https://example.com/ex1"}])
        payload = server.export_payload()
        self.assertEqual(len(payload["archive"]), 1)
        result, err = server.import_payload(payload)
        self.assertIsNone(err)
        self.assertEqual(result["archived_added"], 0)

    def test_clear_all_keeps_profiles(self):
        server.merge_items(
            [self.item("https://example.com/all", "ทั้งหมด")], "kw", 0, fetch_thumbs=False
        )
        result = server.clear_all_data()
        self.assertEqual(result["removed"], 1)
        self.assertEqual(server.load_json(server.ITEMS_FILE, []), [])
        self.assertEqual(server.load_json(server.INDEX_FILE, {}), {})
        self.assertEqual(server.load_json(server.ANALYSIS_FILE, {}), {})

    def test_trash_delete_restore(self):
        server.merge_items(
            [
                self.item("https://example.com/t1", "ลบชั่วคราว"),
                self.item("https://example.com/t2", "อยู่ต่อ"),
            ],
            "kw",
            0,
            fetch_thumbs=False,
        )
        out, err = server.bulk_items("delete", [{"keyword": "kw", "url": "https://example.com/t1"}])
        self.assertIsNone(err)
        self.assertEqual(out["trashed"], 1)
        self.assertEqual(len(server.load_json(server.ITEMS_FILE, [])), 1)
        self.assertEqual(len(server.load_trash()), 1)
        self.assertEqual(server.load_trash()[0]["url"], "https://example.com/t1")
        r = server.restore_trash([{"keyword": "kw", "url": "https://example.com/t1"}])
        self.assertEqual(r["restored"], 1)
        self.assertEqual(len(server.load_json(server.ITEMS_FILE, [])), 2)
        self.assertEqual(len(server.load_trash()), 0)

    def test_trash_restore_conflict_skipped(self):
        server.merge_items(
            [self.item("https://example.com/dup", "ซ้ำ")], "kw", 0, fetch_thumbs=False
        )
        server.bulk_items("delete", [{"keyword": "kw", "url": "https://example.com/dup"}])
        server.merge_items(
            [self.item("https://example.com/dup", "ซ้ำใหม่")], "kw", 0, fetch_thumbs=False
        )
        r = server.restore_trash([{"keyword": "kw", "url": "https://example.com/dup"}])
        self.assertEqual(r["restored"], 0)
        self.assertEqual(r["skipped"], 1)
        self.assertEqual(len(server.load_trash()), 0)

    def test_trash_purge_expired(self):
        server.merge_items(
            [self.item("https://example.com/old", "เก่า")], "kw", 0, fetch_thumbs=False
        )
        server.bulk_items("delete", [{"keyword": "kw", "url": "https://example.com/old"}])
        trash = server.load_trash()
        trash[0]["deleted_at"] = (
            server.datetime.now(server.timezone.utc)
            - server.timedelta(days=server.TRASH_RETENTION_DAYS + 1)
        ).isoformat()
        server.atomic_write(server.TRASH_FILE, trash)
        self.assertEqual(server.purge_trash(), 1)
        self.assertEqual(len(server.load_trash()), 0)

    def test_export_import_trash(self):
        server.merge_items(
            [self.item("https://example.com/ex2", "ส่งออก")], "kw", 0, fetch_thumbs=False
        )
        server.bulk_items("delete", [{"keyword": "kw", "url": "https://example.com/ex2"}])
        payload = server.export_payload()
        self.assertEqual(len(payload["trash"]), 1)
        result, err = server.import_payload(payload)
        self.assertIsNone(err)
        self.assertEqual(result["trash_added"], 0)

    def test_keyword_list(self):
        server.merge_items(
            [
                self.item("https://example.com/k1", "หนึ่ง", keyword="alpha"),
                self.item("https://example.com/k2", "สอง", keyword="beta"),
            ],
            "alpha",
            0,
            fetch_thumbs=False,
        )
        server.merge_items(
            [self.item("https://example.com/k3", "สาม", keyword="alpha")],
            "alpha",
            0,
            fetch_thumbs=False,
        )
        kws = {k["keyword"]: k for k in server.keyword_list()["keywords"]}
        self.assertEqual(kws["alpha"]["count"], 2)
        self.assertEqual(kws["beta"]["count"], 1)

    def test_refresh_stats_selected_filter(self):
        server.merge_items(
            [
                self.item("https://example.com/r1", "หนึ่ง", source="youtube", keyword="kw"),
                self.item("https://example.com/r2", "สอง", source="youtube", keyword="kw"),
            ],
            "kw",
            0,
            fetch_thumbs=False,
        )
        out = server.refresh_stats(
            "kw",
            ["youtube"],
            items=[{"keyword": "kw", "url": "https://example.com/nope"}],
        )
        self.assertEqual(out["total"], 0)

    def test_refresh_stats_all_without_keyword(self):
        server.merge_items(
            [
                self.item(
                    "https://www.youtube.com/watch?v=r3", "all", source="youtube", keyword="kw2"
                )
            ],
            "kw2",
            0,
            fetch_thumbs=False,
        )
        original = server.youtube_video_stats
        server.youtube_video_stats = lambda _vid: (321, None, None)
        try:
            out = server.refresh_stats("", ["youtube"])
        finally:
            server.youtube_video_stats = original
        self.assertEqual(out["updated"], 1)
        self.assertEqual(out["total"], 1)


if __name__ == "__main__":
    unittest.main()
