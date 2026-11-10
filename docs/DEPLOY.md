#Deploy (GitHub Pages + local server)

## Paths

| Path | Page | Source |
|---|---|---|
| `/Business-Tracker/` | mockup | `index.html` |
| `/Business-Tracker/live/` | real dashboard | `live/index.html` |
| `/Business-Tracker/app/` | shared CSS / logo / icons | `app/` |

Locally `python server.py` serves the same layout:

- `http://127.0.0.1:8000/` → mockup
- `http://127.0.0.1:8000/live/` → live
- old links `/dashboard-live.html` and `/app/dashboard.html` redirect.

## GitHub Pages

Push `main`; Pages serves the repository root. Root and `/live/` both load statically, but **`live/` needs the Python API** for data (`/api/summary`, `/api/status`, …). GitHub Pages cannot run `server.py`.

To make `/live/` work on Pages:

1. Host `server.py` somewhere reachable over HTTPS (Render, Fly.io, a tunnel, a VPS).
2. In `live/index.html` set the API origin:

```html
<meta name="api-base" content="https://your-server.example.com" />
```

Rows are written by the adapter to Supabase; the browser never sees the service key.

3. Restrict CORS in the server env:

```
ALLOW_ORIGIN=https://ntp-md.github.io
```

The API has no login. Do not expose it publicly with `ALLOW_ORIGIN=*`; anyone could read/write the data through it.

## Mockup

`index.html` is static sample data and needs no backend. The live page keeps its own copy only through `live/index.html`; both load CSS from `app/`.
