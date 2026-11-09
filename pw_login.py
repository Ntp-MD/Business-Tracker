#!/usr/bin/env python3
"""One-time headed login for TikTok / Facebook Playwright sessions.

Usage: python pw_login.py tiktok | facebook
A browser window opens — log in once, then close the window.
Session persists under sessions/<platform>/ (gitignored, machine-local only).
"""
import sys

from server import PW_SESSIONS, UA


def main() -> None:
    kind = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if kind not in ("tiktok", "facebook"):
        print(__doc__)
        sys.exit(2)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed — run: python -m pip install playwright && python -m playwright install chromium")
        sys.exit(1)
    home = {"tiktok": "https://www.tiktok.com/foryou",
            "facebook": "https://www.facebook.com/"}[kind]
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PW_SESSIONS / kind), headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            user_agent=UA, locale="th-TH", timezone_id="Asia/Bangkok")
        page = ctx.new_page()
        page.goto(home, timeout=60000)
        print(f"Log in to {kind} in the opened browser window, then press Enter here to save + close.")
        input()
        try:
            page.wait_for_timeout(1500)
        except Exception:
            pass
        ctx.close()
    print(f"saved sessions/{kind}/ — now Fetch with {kind} in the dashboard.")


if __name__ == "__main__":
    main()
