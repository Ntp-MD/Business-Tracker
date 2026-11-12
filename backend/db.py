"""Supabase (PostgREST) storage adapter.

The app's storage still speaks JSON files. When SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY are set, these two functions mirror the data into
Postgres through Supabase instead of touching data/*.json.

Env:
  SUPABASE_URL                 https://<ref>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY    service_role key (server only, never in the browser)
  SUPABASE_USER_ID             owner uuid of every row
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILES = (ROOT / ".env.local", ROOT.parent / ".env.local")
TIMEOUT = 30
PAGE = 1000

SOURCES = ("youtube", "gnews", "tiktok", "facebook", "fbads", "ttads", "manual")
METRICS = ("views", "plays", "likes")
CLASS_BY_FILE = {
    "items.json": "active",
    "archive.json": "archived",
    "trash.json": "trashed",
}
CLASS_FILTER = {
    "active": "deleted_at=is.null&archived_at=is.null",
    "archived": "deleted_at=is.null&archived_at=not.is.null",
    "trashed": "deleted_at=not.is.null",
}


def _load_env() -> None:
    for env_file in ENV_FILES:
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()


def base_url() -> str:
    return (os.environ.get("SUPABASE_URL") or "").rstrip("/")


def service_key() -> str:
    return os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""


def user_id() -> str:
    return os.environ.get("SUPABASE_USER_ID") or ""


def configured() -> bool:
    return bool(base_url() and service_key() and user_id())


def strict() -> bool:
    """Default on: a Supabase error is raised instead of silently using local files."""
    return (os.environ.get("SUPABASE_STRICT") or "1").strip() not in ("0", "false", "no")


def _request(
    method: str,
    path: str,
    payload=None,
    prefer: str = "",
    raw: bytes | None = None,
    root: str = "/rest/v1/",
    content_type: str = "application/json",
):
    url = f"{base_url()}{root}{path}"
    body = (
        raw
        if raw is not None
        else (None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    )
    headers = {
        "apikey": service_key(),
        "Authorization": f"Bearer {service_key()}",
        "Content-Type": content_type,
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else None


def _select(table: str, query: str = "", order: str = "") -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        q = f"{table}?select=*&limit={PAGE}&offset={offset}"
        if order:
            q += "&order=" + order
        if query:
            q += "&" + query
        page = _request("GET", q) or []
        rows.extend(page)
        if len(page) < PAGE:
            return rows
        offset += PAGE


_CREATED_LABEL: bool | None = None


def created_label_supported() -> bool:
    global _CREATED_LABEL
    if _CREATED_LABEL is None:
        try:
            _request("GET", "items?select=created_label&limit=1")
            _CREATED_LABEL = True
        except urllib.error.HTTPError as exc:
            if exc.code != 400:
                raise
            _CREATED_LABEL = False
    return _CREATED_LABEL


def _upsert(table: str, rows: list[dict], on_conflict: str) -> None:
    for start in range(0, len(rows), 200):
        chunk = rows[start : start + 200]
        _request(
            "POST",
            f"{table}?on_conflict={urllib.parse.quote(on_conflict)}",
            chunk,
            prefer="resolution=merge-duplicates,return=minimal",
        )


def _delete_missing(table: str, ids: list[str]) -> None:
    for start in range(0, len(ids), 100):
        chunk = ids[start : start + 100]
        joined = ",".join(chunk)
        _request(
            "DELETE",
            f"{table}?id=in.({urllib.parse.quote(joined, safe=',()')})",
            prefer="return=minimal",
        )


def upload_asset(filename: str, data: bytes) -> bool:
    """Copy one thumbnail to storage://thumbnails/<user_id>/<filename>."""
    key = f"{user_id()}/{filename}"
    _request(
        "POST",
        f"object/thumbnails/{urllib.parse.quote(key)}",
        raw=data,
        root="/storage/v1/",
        content_type="image/jpeg",
    )
    return True


def fetch_asset(filename: str) -> bytes | None:
    """Read a thumbnail straight from the storage bucket (None when missing)."""
    key = f"{user_id()}/{filename}"
    req = urllib.request.Request(
        f"{base_url()}/storage/v1/object/thumbnails/{urllib.parse.quote(key)}",
        headers={"apikey": service_key(), "Authorization": f"Bearer {service_key()}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _dt(value):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def _item_row(raw: dict, cls: str) -> dict | None:
    keyword = str(raw.get("keyword") or "").strip()
    url = str(raw.get("url") or "").strip()
    canonical = str(raw.get("canonical_url") or "").strip() or url
    if not keyword or not url or not canonical:
        return None
    source = str(raw.get("source") or "manual").strip()
    if source not in SOURCES:
        source = "manual"
    metric = raw.get("metric")
    if metric not in METRICS:
        metric = None

    def number(value):
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    def maybe_number(value):
        if value in (None, ""):
            return None
        return number(value)

    row = {
        "user_id": user_id(),
        "keyword": keyword,
        "source": source,
        "url": url,
        "canonical_url": canonical,
        "title": str(raw.get("title") or "")[:500],
        "body": str(raw.get("body") or "")[:2000],
        "author": str(raw.get("author") or "")[:200],
        "channel_url": str(raw.get("channel_url") or "")[:500],
        "score": number(raw.get("score")),
        "metric": metric,
        "views": maybe_number(raw.get("views")),
        "published": _dt(raw.get("published")),
        "asset_path": str(raw.get("asset") or raw.get("asset_path") or "") or None,
        "created_label": str(raw.get("created") or "")[:100] or None,
        "created_at": _dt(raw.get("created_at")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "archived_at": _dt(raw.get("archived_at")),
        "deleted_at": _dt(raw.get("deleted_at")),
    }
    if cls == "active":
        row["archived_at"] = None
        row["deleted_at"] = None
    elif cls == "archived":
        row["deleted_at"] = None
        row["archived_at"] = row["archived_at"] or datetime.now(timezone.utc).isoformat()
    else:
        row["deleted_at"] = row["deleted_at"] or datetime.now(timezone.utc).isoformat()
    if not row["created_at"]:
        row.pop("created_at")
    return row


def _item_dict(row: dict) -> dict:
    return {
        "url": row.get("url") or "",
        "title": row.get("title") or "",
        "body": row.get("body") or "",
        "source": row.get("source") or "",
        "keyword": row.get("keyword") or "",
        "author": row.get("author") or "",
        "score": row.get("score") or 0,
        "created": row.get("created_label") or row.get("created_at") or "",
        "created_at": row.get("created_at") or "",
        "asset": row.get("asset_path") or None,
        "canonical_url": row.get("canonical_url") or "",
        "metric": row.get("metric") or "none",
        "views": row.get("views"),
        "channel_url": row.get("channel_url") or "",
        "published": row.get("published") or "",
        "archived_at": row.get("archived_at") or "",
        "deleted_at": row.get("deleted_at") or "",
    }


def _save_items(cls: str, obj: list) -> bool:
    rows = [r for r in (_item_row(x, cls) for x in obj if isinstance(x, dict)) if r]
    if not created_label_supported():
        for row in rows:
            row.pop("created_label", None)
    _upsert("items", rows, "user_id,keyword,canonical_url")
    keep = {r["canonical_url"] + "\u0000" + r["keyword"] for r in rows}
    existing = _select("items", CLASS_FILTER[cls])
    stale = [
        r["id"] for r in existing if f"{r.get('canonical_url')}\u0000{r.get('keyword')}" not in keep
    ]
    if stale:
        _delete_missing("items", stale)
    return True


def load(path: Path, default):
    name = path.name
    try:
        if name in CLASS_BY_FILE:
            rows = _select("items", CLASS_FILTER[CLASS_BY_FILE[name]], "created_at.asc")
            return [_item_dict(r) for r in rows]
        if name == "profiles.json":
            rows = _select("profiles", order="created_at.asc")
            return [
                {
                    "id": r["id"],
                    "name": r.get("name") or "",
                    "keywords": r.get("keywords") or [],
                    "sources": r.get("sources") or [],
                    "created_at": r.get("created_at") or "",
                    "updated_at": r.get("updated_at") or "",
                }
                for r in rows
            ]
        if name == "sources.json":
            rows = _select("source_status")
            return {
                r["source"]: {
                    "at": r.get("checked_at") or "",
                    "ok": bool(r.get("ok")),
                    "count": r.get("count") or 0,
                    "error": r.get("error") or "",
                }
                for r in rows
            }
        if name in ("analysis.json", "index.json"):
            rows = _select("keyword_stats")
            out = {}
            for r in rows:
                base = {
                    "total": r.get("total") or 0,
                    "by_source": r.get("by_source") or {},
                    "hot": r.get("hot") or "",
                    "top_terms": r.get("top_terms") or [],
                }
                if name == "analysis.json":
                    base["keyword"] = r.get("keyword") or ""
                    base["suggestions"] = r.get("suggestions") or []
                out[r.get("keyword") or ""] = base
            return out
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        print(f"[db] load {name} failed: {exc}")
        if strict():
            raise
        print("[db] SUPABASE_STRICT=0: falling back to data/*.json")
        return None
    return None


def save(path: Path, obj) -> bool:
    if not configured():
        return False
    name = path.name
    try:
        if name in CLASS_BY_FILE:
            return _save_items(CLASS_BY_FILE[name], obj if isinstance(obj, list) else [])
        if name == "profiles.json":
            rows = []
            for p in obj if isinstance(obj, list) else []:
                if not isinstance(p, dict) or not p.get("name"):
                    continue
                pid = str(p.get("id") or "")
                try:
                    uuid.UUID(pid)
                except (ValueError, AttributeError):
                    pid = str(
                        uuid.uuid5(
                            uuid.NAMESPACE_URL, "social-tracker:profile:" + (p.get("name") or pid)
                        )
                    )
                rows.append(
                    {
                        "id": pid,
                        "user_id": user_id(),
                        "name": str(p["name"])[:200],
                        "keywords": p.get("keywords") or [],
                        "sources": p.get("sources") or [],
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            _upsert("profiles", rows, "id")
            keep = {r["name"] for r in rows}
            stale = [r["id"] for r in _select("profiles") if r.get("name") not in keep]
            if stale:
                _delete_missing("profiles", stale)
            return True
        if name == "sources.json":
            rows = []
            for source, value in (obj or {}).items():
                if source not in SOURCES or not isinstance(value, dict):
                    continue
                rows.append(
                    {
                        "user_id": user_id(),
                        "source": source,
                        "checked_at": _dt(value.get("at"))
                        or datetime.now(timezone.utc).isoformat(),
                        "ok": bool(value.get("ok")),
                        "count": int(value.get("count") or 0),
                        "error": str(value.get("error") or "")[:300] or None,
                    }
                )
            _upsert("source_status", rows, "user_id,source")
            keep = {r["source"] for r in rows}
            existing = _select("source_status")
            for source in [r["source"] for r in existing if r.get("source") not in keep]:
                _request(
                    "DELETE",
                    f"source_status?user_id=eq.{urllib.parse.quote(user_id())}&source=eq.{urllib.parse.quote(source)}",
                    prefer="return=minimal",
                )
            return True
        if name in ("analysis.json", "index.json"):
            rows = []
            for keyword, value in (obj or {}).items():
                if not keyword or not isinstance(value, dict):
                    continue
                rows.append(
                    {
                        "user_id": user_id(),
                        "keyword": keyword,
                        "total": int(value.get("total") or 0),
                        "by_source": value.get("by_source") or {},
                        "hot": value.get("hot") or None,
                        "top_terms": value.get("top_terms") or [],
                        "computed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                if name == "analysis.json":
                    rows[-1]["suggestions"] = value.get("suggestions") or []
            _upsert("keyword_stats", rows, "user_id,keyword")
            if name == "analysis.json":
                keep = {r["keyword"] for r in rows}
                existing = _select("keyword_stats")
                stale = [r["keyword"] for r in existing if r.get("keyword") not in keep]
                for keyword in stale:
                    _request(
                        "DELETE",
                        f"keyword_stats?user_id=eq.{urllib.parse.quote(user_id())}&keyword=eq.{urllib.parse.quote(keyword)}",
                        prefer="return=minimal",
                    )
            return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        print(f"[db] save {name} failed: {exc}")
        if strict():
            raise
        print("[db] SUPABASE_STRICT=0: keeping the disk copy")
        return False
    return False
