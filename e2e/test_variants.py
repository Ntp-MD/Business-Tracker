"""E2E smoke tests for the three deployed Vercel variants.

Read-only tests run against the public URLs and are safe for CI. The prod write
test creates one disposable item (unique keyword/title/URL) and deletes it from
trash, so it only runs when E2E_PROD_EMAIL and E2E_PROD_PASSWORD are set.
"""

import os
import unittest
import uuid
from urllib.parse import quote, urlparse

from playwright.sync_api import expect, sync_playwright

MOCKUP_URL = os.environ.get("E2E_MOCKUP_URL", "https://trendrail-mockup.vercel.app").rstrip("/")
LIVE_URL = os.environ.get("E2E_LIVE_URL", "https://trendrail-live.vercel.app").rstrip("/")
PROD_URL = os.environ.get("E2E_PROD_URL", "https://trendrail.vercel.app").rstrip("/")
PROD_EMAIL = os.environ.get("E2E_PROD_EMAIL")
PROD_PASSWORD = os.environ.get("E2E_PROD_PASSWORD")


class BrowserCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._playwright = sync_playwright().start()
        cls.browser = cls._playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1400, "height": 900})
        self.page = self.context.new_page()
        self.page.set_default_timeout(30_000)

    def tearDown(self):
        self.context.close()

    def path(self):
        return urlparse(self.page.url).path


class ReadOnlyTests(BrowserCase):
    def test_mockup_root_and_live_redirect(self):
        requests = []
        self.page.on("request", lambda request: requests.append(request.url))
        response = self.page.goto(f"{MOCKUP_URL}/", wait_until="domcontentloaded")
        self.assertEqual(response.status, 200)
        expect(self.page.locator("body")).to_contain_text("sample data")
        self.assertFalse(
            [url for url in requests if "supabase.co" in url or "/api/" in url],
            "mockup must not call Supabase or the API",
        )

        self.page.goto(f"{MOCKUP_URL}/live", wait_until="domcontentloaded")
        self.assertEqual(self.path(), "/")

    def test_live_root_redirects_to_live(self):
        self.page.goto(f"{LIVE_URL}/", wait_until="domcontentloaded")
        self.assertEqual(self.path(), "/live")

    def test_live_pages_and_settings_redirect(self):
        response = self.page.goto(f"{LIVE_URL}/live", wait_until="domcontentloaded")
        self.assertEqual(response.status, 200)
        expect(self.page.locator("body")).to_contain_text("Top items")

        self.page.goto(f"{LIVE_URL}/live/settings", wait_until="domcontentloaded")
        self.assertEqual(self.path(), "/live")

    def test_live_rejects_post(self):
        response = self.context.request.post(
            f"{LIVE_URL}/live/items",
            form={"keyword": "e2e-read-only"},
        )
        self.assertEqual(response.status, 403)

    def test_prod_requires_login(self):
        self.page.goto(f"{PROD_URL}/live", wait_until="domcontentloaded")
        parsed = urlparse(self.page.url)
        self.assertEqual(parsed.path, "/login")
        self.assertEqual(parsed.query, "")

    def test_prod_deep_link_keeps_next(self):
        self.page.goto(f"{PROD_URL}/live/items?q=test", wait_until="domcontentloaded")
        parsed = urlparse(self.page.url)
        self.assertEqual(parsed.path, "/login")
        self.assertIn("next=%2Flive%2Fitems%3Fq%3Dtest", parsed.query)


@unittest.skipUnless(PROD_EMAIL and PROD_PASSWORD, "set E2E_PROD_EMAIL / E2E_PROD_PASSWORD")
class ProdWriteTests(BrowserCase):
    def login(self):
        self.page.goto(f"{PROD_URL}/login?password=1&next=%2Flive", wait_until="domcontentloaded")
        form = self.page.locator("form").filter(has=self.page.locator("input[name=password]"))
        form.locator("input[name=email]").fill(PROD_EMAIL)
        form.locator("input[name=password]").fill(PROD_PASSWORD)
        form.get_by_role("button", name="Sign in with password").click()
        self.page.wait_for_url("**/live", timeout=30_000)

    def test_filters_and_disposable_item_lifecycle(self):
        token = uuid.uuid4().hex[:10]
        title = f"E2E disposable {token}"
        url = f"https://example.com/e2e/{token}"
        self.login()

        self.page.goto(f"{PROD_URL}/live/items", wait_until="domcontentloaded")
        filters = self.page.locator("form.items-filters")
        filters.locator("input[name=q]").fill(f"no-match-{token}")
        filters.get_by_role("button", name="Filter").click()
        self.page.wait_for_load_state("domcontentloaded")
        expect(self.page.locator(".empty")).to_contain_text("No items match")

        try:
            self.page.goto(f"{PROD_URL}/live/items", wait_until="domcontentloaded")
            self.page.locator("summary", has_text="+ Add item").click()
            form = self.page.locator("details.add-item form")
            form.locator("input[name=keyword]").fill("__e2e__")
            form.locator("input[name=url]").fill(url)
            form.locator("input[name=title]").fill(title)
            form.locator("input[name=author]").fill("e2e")
            with self.page.expect_response(
                lambda response: (
                    response.request.method == "POST" and response.url.endswith("/live/items")
                )
            ):
                form.get_by_role("button", name="Save item").click()
            self.page.wait_for_url("**/live/items", timeout=30_000)

            self.page.goto(f"{PROD_URL}/live/items?q={quote(title)}", wait_until="domcontentloaded")
            row = self.page.locator("tr", has_text=title)
            expect(row).to_be_visible()
            row.get_by_role("button", name="Archive").click()
            expect(row).to_have_count(0)

            self.page.goto(
                f"{PROD_URL}/live/archive?q={quote(title)}", wait_until="domcontentloaded"
            )
            row = self.page.locator("tr", has_text=title)
            expect(row).to_be_visible()
            row.get_by_role("button", name="Delete").click()
            expect(row).to_have_count(0)

            self.page.goto(f"{PROD_URL}/live/trash", wait_until="domcontentloaded")
            row = self.page.locator("tr", has_text=title)
            expect(row).to_be_visible()
            row.get_by_role("button", name="Delete forever").click()
            expect(row).to_have_count(0)
        finally:
            self.cleanup(title)

    def cleanup(self, title):
        """Best-effort removal if the lifecycle test failed midway."""
        try:
            self.page.goto(f"{PROD_URL}/live/items?q={quote(title)}")
            row = self.page.locator("tr", has_text=title)
            if row.count():
                row.get_by_role("button", name="Delete").click()
                row.wait_for(state="detached", timeout=10_000)
            self.page.goto(f"{PROD_URL}/live/archive?q={quote(title)}")
            row = self.page.locator("tr", has_text=title)
            if row.count():
                row.get_by_role("button", name="Delete").click()
                row.wait_for(state="detached", timeout=10_000)
            self.page.goto(f"{PROD_URL}/live/trash")
            row = self.page.locator("tr", has_text=title)
            if row.count():
                row.get_by_role("button", name="Delete forever").click()
                row.wait_for(state="detached", timeout=10_000)
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
