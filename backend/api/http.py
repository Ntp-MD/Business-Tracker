from __future__ import annotations

import json
import os
from pathlib import Path

CTYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".json": "application/json; charset=utf-8",
}


def _write(handler, data: bytes) -> None:
    try:
        handler.wfile.write(data)
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        pass  # client cancelled/closed the tab


def ALLOW_ORIGIN() -> str:
    return (os.environ.get("ALLOW_ORIGIN") or "").strip()


def _cors(handler) -> None:
    origin = ALLOW_ORIGIN()
    if origin:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")


def _send(handler, path: Path, ctype: str | None = None) -> None:
    if not path.is_file():
        _send_json(handler, {"error": "not found"}, 404)
        return
    data = path.read_bytes()
    handler.send_response(200)
    _cors(handler)
    handler.send_header(
        "Content-Type", ctype or CTYPES.get(path.suffix, "application/octet-stream")
    )
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    _write(handler, data)


def _send_bytes(handler, data: bytes, ctype: str) -> None:
    handler.send_response(200)
    _cors(handler)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    _write(handler, data)


def _redirect(handler, to: str) -> None:
    handler.send_response(302)
    _cors(handler)
    handler.send_header("Location", to)
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def _send_json(handler, obj, status: int = 200) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    _cors(handler)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    _write(handler, data)


def _send_download(handler, data: bytes, ctype: str, filename: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    _write(handler, data)


def _resolve(base: Path, rel: str) -> Path | None:
    path = (base / rel).resolve()
    try:
        path.relative_to(base.resolve())
    except ValueError:
        return None
    return path
