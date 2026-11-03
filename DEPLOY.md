# COUCH CLASH — one-click deploy

Two ways to ship it. **Take the file that matches what you want:**

| | `CouchClash-deploy.zip` | `CouchClash-static.html` |
|---|---|---|
| **Deploy action** | Push to GitHub → click **Deploy to Render** (or `docker compose up -d`) | **Drag the one file** into Netlify Drop |
| **Host type** | Any long-running container host | Any static host |
| **SOLO / ONE DEVICE** | ✅ | ✅ |
| **TWO PHONES** | ✅ same-origin relay, SSE, QR invites | ✅ via **⚙ RELAY** (paste a running server URL) |
| **Needs a server** | Yes (`server.py`) | No |
| **Stable public URL** | Yes — your own domain | Yes — host-provided domain |

> **Why two files?** Two-phone mode uses a long-lived `/api/events` SSE stream and
> keeps rooms in process memory. Static hosts can't **host** that relay and serverless
> functions (Vercel, Lambda) are request-scoped, so one always-on container is
> required as the relay. But a statically-hosted **client** can now point at that
> relay from anywhere (⚙ RELAY / `?relay=`), because the server sends
> `Access-Control-Allow-Origin: *`. `server.py` answers SSE with HTTP/1.0 +
> `Connection: close` so it streams through reverse proxies.

---

## ⚡ Fastest true one-click — `CouchClash-static.html`

1. Download **`CouchClash-static.html`**.
2. Go to **<https://app.netlify.com/drop>** and drag the file onto the page. You get a
   public HTTPS URL immediately. Done.
3. Alternatives: **Cloudflare Pages → Upload assets**, or a **GitHub repo → Settings →
   Pages**. For those two, rename the file to **`index.html`** first.

It is completely self-contained — no build, no CDN, no dependencies, no external
resources. SOLO and ONE DEVICE play offline. For **TWO PHONES**, tap **⚙ RELAY** in the
JOIN panel, paste the URL of a running Couch Clash server (e.g. the Docker/Render
deployment below, or `?relay=https://…` in the address bar) and hit **USE**. The relay
sends `Access-Control-Allow-Origin: *`, so cross-origin rooms, SSE, QR and invites all
work. If no relay is set, the panel opens by itself and explains exactly that — you no
longer get a silent *"Could not create a room"* toast.

---

## 🚀 Full game (TWO PHONES) — one click on Render

1. Unzip **`CouchClash-deploy.zip`**, then put the `couch-clash/` folder in a **public
   GitHub repo**:
   ```bash
   cd couch-clash
   git init && git add . && git commit -m "Couch Clash"
   git remote add origin https://github.com/YOU/REPO.git
   git push -u origin main
   ```
2. Click the deploy button (replace `YOUR_REPO_URL` with your repo URL):

   **[Deploy to Render](https://render.com/deploy?repo=YOUR_REPO_URL)**

   Or in the Render dashboard: **New → Blueprint → connect the repo**. Render reads
   `render.yaml` at the repo root automatically.

3. That's it. `render.yaml` sets `PORT=10000`, builds from `Dockerfile`, and health-checks
   `/api/health`. Invite links and the lobby QR are built from `location.origin`, so they
   automatically point at your real Render domain — share them with a friend on any
   network.

> Render's free tier spins down when idle. Rooms are in-memory anyway, so that just means
> a cold start. For always-on, use a paid Render plan or Fly.io (the included `fly.toml`
> sets `auto_stop_machines = false`).

---

## 🐳 Docker — one command

```bash
cd couch-clash
./deploy.sh                    # or: docker compose up -d --build
# -> http://localhost:8000/   health: /api/health
```

`deploy.sh` falls back to plain `python3 server.py` if Docker isn't installed.
To ship the image anywhere: `docker build -t couch-clash .`, push it, then run it with
`PORT` set and that port exposed. Works on **Cloud Run** (`gcloud run deploy --source .`),
**Railway** (`railway up`, reads `railway.toml`), **Fly.io** (`fly launch && fly deploy`,
change the `app` name in `fly.toml` first), **Heroku-style buildpacks** (`Procfile` +
`requirements.txt`), or any VPS.

No environment variables are needed beyond `PORT`. No database, no secrets, no API keys.

---

## ✅ Verify after deploying

```bash
curl https://YOUR_DOMAIN/api/health
# {"ok":true,"rooms":0,"authoritative":true,"engine":true}
curl -I https://YOUR_DOMAIN/          # 200, text/html
```

Then open the URL on two phones → **TWO PHONES → CREATE ROOM** → scan the lobby QR or
send the invite link. Both drivers should get the countdown and 30 Hz snapshots.

`tests/public-relay.py` runs the full two-client relay check against any deployed origin:
```bash
python3 tests/public-relay.py https://YOUR_DOMAIN/
# -> ALL PUBLIC RELAY CHECKS PASSED
```

---

## What's in `CouchClash-deploy.zip`

```
couch-clash/
├── index.html              game client (self-contained, photo embedded)
├── server.py               authoritative stdlib HTTP/SSE relay
├── engine.py               pure-Python physics
├── vendor/segno/           vendored QR generator + SEGNO_LICENSE.txt
├── CouchClash-static.html  one-file drag-and-drop build (solo)
├── Dockerfile              Python 3.12-slim, no pip install
├── docker-compose.yml      one-command local/VPS deploy
├── render.yaml             Render Blueprint (one-click)
├── fly.toml / railway.toml / Procfile / requirements.txt
├── deploy.sh               ./deploy.sh -> running game
├── DEPLOY.md               this file
├── README.md               game docs (controls, layouts, cars, rules)
└── tests/                  optional verification harnesses
```

---

## Notes / limits

- Rooms are **in-memory only** — restarting the container clears them. There is no DB,
  auth, matchmaking, or persistence.
- One process holds all rooms. Don't scale to multiple replicas for two-phone play
  unless you add shared state; a single small instance is plenty.
- SSE needs an origin that streams (not buffers). The server's HTTP/1.0 SSE framing
  handles Cloudflare Tunnel and most reverse proxies; if your proxy buffers, allow
  `text/event-stream` passthrough.
- Static hosts cannot serve `/api/*`. `CouchClash-static.html` detects that and
  lets you point at an external relay (⚙ RELAY or `?relay=`), rather than disabling
  TWO PHONES. Both phones must use the **same relay**, and it must be HTTPS.
