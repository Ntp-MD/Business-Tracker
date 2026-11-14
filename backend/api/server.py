from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import db
import runtime
from collectors import dry_run as collector_dry_run
from collectors.job import validate_collect_payload
from collectors.store import job_cancel_check, job_progress
from runtime import APP, HOST, LIVE, PORT, STATIC, atomic_write, ensure_data, now_iso
from services.items import (
    analyze,
    archive_items,
    bulk_items,
    cleanup_orphan_assets,
    clear_all_data,
    clear_keyword,
    create_item,
    delete_archived,
    delete_item,
    export_payload,
    export_zip,
    import_payload,
    import_zip,
    load_archive,
    load_trash,
    merge_items,
    migrate_items,
    prune_old,
    purge_trash,
    refresh_stats,
    restore_archived,
    restore_trash,
    update_item,
)
from services.profiles import fetch_profile, load_profiles, validate_profile
from services.sources import COLLECTORS
from services.status import keyword_list, log_source, status_payload

from api.http import _cors, _redirect, _resolve, _send, _send_bytes, _send_download, _send_json


class Handler(BaseHTTPRequestHandler):
    request_id = "-"

    def handle_one_request(self) -> None:
        self.request_id = uuid.uuid4().hex[:12]
        super().handle_one_request()

    def log_message(self, fmt: str, *args) -> None:
        print(
            json.dumps(
                {
                    "level": "info",
                    "event": "http",
                    "request_id": self.request_id,
                    "client": self.client_address[0],
                    "message": fmt % args,
                }
            ),
            flush=True,
        )

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        _cors(self)
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if path in ("/", "/index.html"):
            _send(self, STATIC / "index.html")
        elif path in ("/live", "/live/", "/live/index.html"):
            _send(self, LIVE / "index.html")
        elif path in ("/dashboard-live.html", "/dashboard.html"):
            _redirect(self, "/live/")
        elif path == "/app/dashboard.html":
            _redirect(self, "/")
        elif path == "/api/summary":
            q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            _send_json(self, analyze(q, write=False))
        elif path == "/api/profiles":
            _send_json(self, load_profiles())
        elif path == "/api/progress":
            _send_json(self, runtime.progress_get())
        elif path == "/api/status":
            _send_json(self, status_payload())
        elif path == "/api/archive":
            _send_json(self, load_archive())
        elif path == "/api/trash":
            _send_json(self, load_trash())
        elif path == "/api/keywords":
            _send_json(self, keyword_list())
        elif path in ("/api/export", "/api/export.zip"):
            q = (urllib.parse.parse_qs(parsed.query).get("q", [""])[0] or "").strip()
            payload = export_payload(q)
            stamp = datetime.now().strftime("%Y%m%d")
            if path.endswith(".zip"):
                data = export_zip(payload)
                _send_download(self, data, "application/zip", f"social-tracker-{stamp}.zip")
            else:
                data = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
                _send_download(
                    self,
                    data,
                    "application/json; charset=utf-8",
                    f"social-tracker-{stamp}.json",
                )
        elif path.startswith("/fonts/"):
            rel = path[len("/fonts/") :]
            found = _resolve(runtime.ASSETS / "fonts", rel)
            _send(self, found) if found else _send_json(self, {"error": "not found"}, 404)
        elif path.startswith("/assets/"):
            rel = path[len("/assets/") :]
            name = Path(rel).name
            if db.configured() and "/" not in rel and name.lower().endswith(".jpg"):
                try:
                    data = db.fetch_asset(name)
                except Exception as exc:  # noqa: BLE001 - served below from the disk cache
                    print(f"[db] asset {name} failed: {exc}")
                    data = None
                if data:
                    _send_bytes(self, data, "image/jpeg")
                    return
                if db.strict():
                    _send_json(self, {"error": "not found"}, 404)
                    return
            found = _resolve(runtime.ASSETS, rel)
            _send(self, found) if found else _send_json(self, {"error": "not found"}, 404)
        elif path.startswith("/app/"):
            found = _resolve(APP, path[len("/app/") :])
            _send(self, found) if found else _send_json(self, {"error": "not found"}, 404)
        else:
            found = _resolve(STATIC, path.lstrip("/"))
            if found is not None and found.is_file():
                _send(self, found)
            else:
                _send_json(self, {"error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw_body.decode("utf-8") or "{}")
        except Exception:
            body = {}
        q = str(body.get("q") or "").strip()
        try:
            max_age_days = int(body.get("max_age_days") or 0)
        except (TypeError, ValueError):
            _send_json(self, {"error": "bad max_age_days"}, 400)
            return
        if max_age_days < 0 or max_age_days > 3650:
            _send_json(self, {"error": "bad max_age_days"}, 400)
            return
        if parsed.path == "/api/import":
            try:
                result, err = (
                    import_zip(raw_body) if raw_body[:2] == b"PK" else import_payload(body)
                )
            except Exception as e:  # noqa: BLE001 - always answer the client
                _send_json(self, {"error": f"import failed: {e}"}, 500)
                return
            if err:
                _send_json(self, {"error": err}, 400)
                return
            _send_json(self, result)
        elif parsed.path == "/api/cancel":
            runtime.cancel_fetch()
            runtime.progress_stage("cancel requested")
            _send_json(self, {"cancelled": True})
        elif parsed.path == "/api/refresh-stats":
            raw_sources = body.get("sources")
            sources = (
                [str(s).strip().lower() for s in raw_sources if str(s).strip()]
                if isinstance(raw_sources, list)
                else ["youtube", "tiktok", "ttads"]
            )
            cancel = runtime.new_fetch_cancel()
            runtime.progress_set(
                active=True,
                keyword=q or "all",
                source="",
                stage="refresh stats",
                done=0,
                total=len(sources),
                started=time.time(),
                updated=time.time(),
            )
            try:
                out = refresh_stats(q, sources, cancel, body.get("items"))
                out["keyword"] = q or "all"
                _send_json(self, out)
            except Exception as e:  # noqa: BLE001
                _send_json(self, {"error": f"refresh failed: {e}"}, 500)
            finally:
                runtime.progress_set(active=False, stage="done")
        elif parsed.path == "/api/trash/restore":
            raw = body.get("items")
            if not isinstance(raw, list) or not raw:
                _send_json(self, {"error": "missing items"}, 400)
                return
            _send_json(self, restore_trash(raw))
        elif parsed.path == "/api/items":
            result, err = create_item(
                body.get("item") if isinstance(body.get("item"), dict) else body
            )
            if err:
                _send_json(self, {"error": err}, 400)
                return
            _send_json(self, result, 201)
        elif parsed.path == "/api/items/bulk":
            action = str(body.get("action") or "").strip().lower()
            if action not in ("delete", "move"):
                _send_json(self, {"error": "bad action"}, 400)
                return
            result, err = bulk_items(action, body.get("items"), str(body.get("to_keyword") or ""))
            if err:
                _send_json(self, {"error": err}, 400)
                return
            _send_json(self, result)
        elif parsed.path == "/api/archive":
            raw = body.get("items")
            if not isinstance(raw, list) or not raw:
                _send_json(self, {"error": "missing items"}, 400)
                return
            _send_json(self, archive_items(raw))
        elif parsed.path == "/api/archive/restore":
            raw = body.get("items")
            if not isinstance(raw, list) or not raw:
                _send_json(self, {"error": "missing items"}, 400)
                return
            _send_json(self, restore_archived(raw))
        elif parsed.path == "/api/clear-all":
            _send_json(self, clear_all_data())
        elif parsed.path == "/api/clear":
            if not q:
                _send_json(self, {"error": "missing q"}, 400)
                return
            _send_json(self, clear_keyword(q))
        elif parsed.path == "/api/collect":
            try:
                payload = validate_collect_payload(body)
                job_id = payload.get("job_id")
                cancel_check = job_cancel_check(job_id) if job_id else None
                progress = job_progress(job_id) if job_id else None
                result = collector_dry_run.run(
                    payload["connector_id"],
                    payload["scope"]["keyword"],
                    payload["max_records"],
                    collector_dry_run.DEFAULT_REPORT_DIR,
                    0,
                    write=not payload["dry_run"],
                    cancel_check=cancel_check,
                    progress=progress,
                )
            except (ValueError, RuntimeError, SystemExit, urllib.error.HTTPError) as exc:
                _send_json(self, {"error": str(exc)}, 400)
                return
            _send_json(self, result)
        elif parsed.path == "/api/prune":
            try:
                days = int(body.get("days") or 0)
            except (TypeError, ValueError):
                days = 0
            if days <= 0:
                _send_json(self, {"error": "bad days"}, 400)
                return
            _send_json(self, prune_old(days))
        elif parsed.path == "/api/profiles":
            prof, err = validate_profile(
                body.get("name"), body.get("keywords"), body.get("sources")
            )
            if err:
                _send_json(self, {"error": err}, 400)
                return
            prof.update(
                {
                    "id": str(uuid.uuid4()),
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                }
            )
            profiles = load_profiles()
            profiles.append(prof)
            atomic_write(runtime.PROFILES_FILE, profiles)
            _send_json(self, prof, 201)
        elif parsed.path == "/api/fetch" and str(body.get("profile_id") or "").strip():
            pid = str(body["profile_id"]).strip()
            prof = next((p for p in load_profiles() if p.get("id") == pid), None)
            if not prof:
                _send_json(self, {"error": "profile not found"}, 404)
                return
            mode = str(body.get("mode") or "public").strip().lower()
            if mode not in ("public", "session"):
                _send_json(self, {"error": "bad mode (public|session)"}, 400)
                return
            cancel = runtime.new_fetch_cancel()
            runtime.progress_set(
                active=True,
                keyword=prof["keywords"][0],
                source="",
                stage="queue",
                done=0,
                total=len(prof["keywords"]),
                started=time.time(),
                updated=time.time(),
            )
            try:
                out = fetch_profile(prof, mode, max_age_days, cancel)
                kw0 = prof["keywords"][0]
                runtime.progress_set(source="analysis", stage="scoring items")
                out.update(analyze(kw0, write=False))
                out["per_keyword"] = out.get("per_keyword", [])
                out["mode"] = mode
                _send_json(self, out)
            finally:
                runtime.progress_set(active=False, stage="done")
        elif parsed.path == "/api/fetch":
            if not q:
                _send_json(self, {"error": "missing q"}, 400)
                return
            raw_sources = body.get("sources")
            if raw_sources is None:
                sources = ["youtube"]
            else:
                sources = [str(s).strip().lower() for s in raw_sources if str(s).strip()]
            if not sources:
                _send_json(self, {"error": "no source selected"}, 400)
                return
            mode = str(body.get("mode") or "public").strip().lower()
            if mode not in ("public", "session"):
                _send_json(self, {"error": "bad mode (public|session)"}, 400)
                return
            new_items, errors = [], []
            cancel = runtime.new_fetch_cancel()
            cancelled = False
            runtime.progress_set(
                active=True,
                keyword=q,
                source="",
                stage="queue",
                done=0,
                total=len(sources),
                started=time.time(),
                updated=time.time(),
            )
            try:
                for i, src in enumerate(sources):
                    if cancel.is_set():
                        cancelled = True
                        break
                    fn = COLLECTORS.get(src)
                    if fn is None:
                        errors.append(f"{src}: not implemented yet")
                        continue
                    runtime.progress_set(source=src, stage="starting", done=i, total=len(sources))
                    if src == "tiktok":
                        items, errs = fn(q, mode, max_age_days)
                    else:
                        items, errs = fn(q, max_age_days)
                    log_source(src, not errs, len(items), "; ".join(errs))
                    new_items += items
                    errors += errs
                runtime.progress_set(source="disk", stage="saving items")
                added, skipped, thumb_errors = merge_items(new_items, q, max_age_days)
                errors += thumb_errors
                runtime.progress_set(source="analysis", stage="scoring items")
                out = analyze(q, write=True)
                out.update(
                    {
                        "added": added,
                        "duplicates": skipped,
                        "errors": errors,
                        "fetched_at": now_iso(),
                        "mode": mode,
                        "max_age_days": max_age_days,
                        "cancelled": cancelled,
                    }
                )
                _send_json(self, out)
            finally:
                runtime.progress_set(active=False, stage="done")
        elif parsed.path == "/api/analyze":
            if not q:
                _send_json(self, {"error": "missing q"}, 400)
                return
            _send_json(self, {"analysis": analyze(q, write=True), "fetched_at": now_iso()})
        else:
            _send_json(self, {"error": "not found"}, 404)

    def do_PUT(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception:
            body = {}
        if parsed.path == "/api/items":
            result, err = update_item(
                str(body.get("keyword") or ""),
                str(body.get("url") or ""),
                body.get("patch") if isinstance(body.get("patch"), dict) else body,
            )
            if err:
                _send_json(self, {"error": err}, 400)
                return
            _send_json(self, result)
            return
        if parsed.path != "/api/profiles":
            _send_json(self, {"error": "not found"}, 404)
            return
        profiles = load_profiles()
        pid = str(body.get("id") or "").strip()
        idx = next((i for i, p in enumerate(profiles) if p.get("id") == pid), None)
        if idx is None:
            _send_json(self, {"error": "profile not found"}, 404)
            return
        cur = profiles[idx]
        prof, err = validate_profile(
            body.get("name", cur["name"]),
            body.get("keywords", cur["keywords"]),
            body.get("sources", cur["sources"]),
        )
        if err:
            _send_json(self, {"error": err}, 400)
            return
        prof.update(
            {
                "id": pid,
                "created_at": cur.get("created_at", now_iso()),
                "updated_at": now_iso(),
            }
        )
        profiles[idx] = prof
        atomic_write(runtime.PROFILES_FILE, profiles)
        _send_json(self, prof)

    def do_DELETE(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception:
            body = {}
        if parsed.path == "/api/items":
            result, err = delete_item(str(body.get("keyword") or ""), str(body.get("url") or ""))
            if err:
                _send_json(self, {"error": err}, 404 if "not found" in err else 400)
                return
            _send_json(self, result)
            return
        if parsed.path == "/api/archive":
            result = delete_archived(body.get("items") or [])
            _send_json(self, result)
            return
        if parsed.path == "/api/trash":
            # 2.5 manual purge all trash
            trash = load_trash()
            atomic_write(runtime.TRASH_FILE, [])
            cleanup_orphan_assets()
            _send_json(self, {"purged": len(trash)})
            return
        if parsed.path != "/api/profiles":
            _send_json(self, {"error": "not found"}, 404)
            return
        pid = str(body.get("id") or "").strip()
        profiles = load_profiles()
        kept = [p for p in profiles if p.get("id") != pid]
        if len(kept) == len(profiles):
            _send_json(self, {"error": "profile not found"}, 404)
            return
        atomic_write(runtime.PROFILES_FILE, kept)
        _send_json(self, {"ok": True})


def main() -> None:
    ensure_data()
    migrate_items()
    purge_trash()  # 2.5 auto-purge expired trash on server start
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"social-tracker on http://{HOST}:{PORT}  (mock: /, live: /live/)")
    server.serve_forever()
