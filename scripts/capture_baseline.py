"""Baseline/parity screenshots for the legacy UI.

Usage: python scripts/capture_baseline.py [--base http://127.0.0.1:8000] [--out baseline-shots]
Requires the local server (`python backend/server.py`) and Playwright chromium.
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGES = ["overview", "sources", "terms", "ideas", "items", "archive", "ads", "settings"]
VIEWPORTS = [(1440, 900), (390, 844)]


def click_page(page, name):
    for sel in (f'.nav a[data-page="{name}"]', f'.mobile-nav a[data-page="{name}"]'):
        loc = page.locator(sel)
        if loc.count() and loc.first.is_visible():
            loc.first.click()
            return True
    return False


def capture(page, url, shot_prefix, out, errors):
    page.goto(url, wait_until="load")
    page.wait_for_timeout(2000)
    for name in PAGES:
        if name != "overview" and not click_page(page, name):
            errors.append(f"{shot_prefix}: nav {name} not clickable")
        page.wait_for_timeout(900)
        page.screenshot(path=str(out / f"{shot_prefix}-{name}.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="baseline-shots")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in VIEWPORTS:
            ctx = browser.new_context(viewport={"width": w, "height": h})
            page = ctx.new_page()
            page.on("console", lambda m: errors.append(f"{w}: {m.text[:120]}") if m.type == "error" else None)
            capture(page, args.base + "/", f"mock-{w}", out, errors)
            capture(page, args.base + "/live/", f"live-{w}", out, errors)
            ctx.close()
        browser.close()

    print(f"shots={len(list(out.glob('*.png')))} dir={out}")
    print(f"errors={errors}")


if __name__ == "__main__":
    main()
