#!/usr/bin/env python3
"""Import data/*.json + thumbnails into Supabase.

    python scripts/import_to_supabase.py [--dry-run] [--skip-thumbnails]
        [--user-id UUID] [--create-user EMAIL] [--password PASS]

Reads SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY from env or .env.local.
Idempotent: items/profiles/stats use upsert on their natural keys.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import db  # noqa: E402  (loads .env.local on import)

DATA = ROOT / "data"
ASSETS = ROOT / "assets"
STORAGE_BUCKET = "thumbnails"


def api(method: str, path: str, payload=None, raw: bytes | None = None, headers: dict | None = None):
    url = db.base_url() + path
    h = {
        "apikey": db.service_key(),
        "Authorization": "Bearer " + db.service_key(),
    }
    body = raw
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    return json.loads(data) if data else None


def read_json(name: str, default):
    path = DATA / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def resolve_user(args) -> str:
    if args.user_id:
        return args.user_id
    if db.user_id():
        return db.user_id()

    users = api("GET", "/auth/v1/admin/users?per_page=200") or []
    if isinstance(users, dict):
        users = users.get("users") or []
    if len(users) == 1:
        return users[0]["id"]

    if args.create_user:
        created = api(
            "POST",
            "/auth/v1/admin/users",
            {"email": args.create_user, "password": args.password, "email_confirm": True},
        )
        return created["id"]

    if not users:
        raise SystemExit(
            "no auth user in the project. Re-run with --create-user you@example.com --password '...'"
        )
    listing = "\n".join(f"  {u['id']}  {u.get('email', '')}" for u in users[:20])
    raise SystemExit("several auth users found; pass --user-id UUID:\n" + listing)


def upload_thumbnail(user_id: str, asset: str, dry: bool) -> bool:
    if not asset.startswith("assets/"):
        return False
    path = ASSETS / Path(asset).name
    if not path.is_file():
        return False
    key = f"{user_id}/{path.name}"
    if dry:
        return True
    headers = {"Content-Type": "image/jpeg", "x-upsert": "true"}
    api("POST", f"/storage/v1/object/{STORAGE_BUCKET}/{key}", raw=path.read_bytes(), headers=headers)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-thumbnails", action="store_true")
    ap.add_argument("--user-id")
    ap.add_argument("--create-user", metavar="EMAIL")
    ap.add_argument("--password", default="changeme-1234")
    args = ap.parse_args()

    if not db.base_url() or not db.service_key():
        raise SystemExit("set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local")

    uid = resolve_user(args)
    os.environ["SUPABASE_USER_ID"] = uid
    print(f"project {db.base_url()}  user {uid}  dry-run={args.dry_run}")

    files = {
        "items.json": read_json("items.json", []),
        "archive.json": read_json("archive.json", []),
        "trash.json": read_json("trash.json", []),
        "profiles.json": read_json("profiles.json", []),
        "analysis.json": read_json("analysis.json", {}),
        "index.json": read_json("index.json", {}),
        "sources.json": read_json("sources.json", {}),
    }
    for name, value in files.items():
        count = len(value)
        print(f"{name:<15} {count}")

    if args.dry_run:
        print("dry run: nothing written")
        return 0

    for name, value in files.items():
        ok = db.save(DATA / name, value)
        print(("saved " if ok else "FAILED ") + name)

    if not args.skip_thumbnails:
        assets = set()
        for key in ("items.json", "archive.json", "trash.json"):
            for item in files[key]:
                asset = str((item or {}).get("asset") or "")
                if asset:
                    assets.add(asset)
        uploaded = sum(upload_thumbnail(uid, asset, False) for asset in sorted(assets))
        print(f"thumbnails uploaded {uploaded}/{len(assets)}")

    print("done")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        print("HTTP", exc.code, exc.read().decode("utf-8", "replace")[:500], file=sys.stderr)
        raise SystemExit(1)
    except urllib.error.URLError as exc:
        print("network error:", exc, file=sys.stderr)
        raise SystemExit(1)
