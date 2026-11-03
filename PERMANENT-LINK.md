# COUCH CLASH — the working link, and why it keeps expiring

## Right now

The **current** public link is always in **`PUBLIC-LINK.txt`** (one line), and the
phone QR is **`PLAY-ON-PHONE.png`**. Open that file in this workspace to copy the
live URL, or use the **port 8000 live preview** inside the Arena chat.

Do not bookmark a `*.trycloudflare.com` address. It **will** stop working.

---

## Why you saw `Error 1033 / Cloudflare Tunnel error`

The game server and the tunnel both run **inside this temporary sandbox**. When the
workspace sleeps or restarts, both processes are killed. Cloudflare still knows the
hostname but has nothing to connect to, so it answers 1033 ("unable to resolve it").
It is not a bug in the game — the whole host was gone.

`relay_watch.py` restarts the tunnel automatically after a normal disconnect and
rewrites `PUBLIC-LINK.txt`, `PLAY-ON-PHONE.png`, `README.md` and the relay test to
the new address. A full sandbox restart is different: nothing survives it, so the
link in this chat has to be refreshed. **That is why a quick-tunnel URL can never be
a permanent home for the game.**

I also tried to deploy it for you through the connected Vercel app; the token is
read-only (`Access denied … account lacks permission for this action or scope`), and
Vercel's request-scoped functions cannot hold the in-memory rooms + long-lived SSE
stream anyway. A real deployment needs your account, once.

---

## Permanent link — Render, about 5 minutes, no terminal needed

1. Download **`CouchClash-deploy.zip`** from this workspace and unzip it.
   Inside is a `couch-clash/` folder with `Dockerfile`, `render.yaml`, `server.py`,
   `engine.py`, `index.html` and everything else.
2. Go to **<https://github.com/new>**, create a **public** repo (name it anything,
   e.g. `couch-clash`), then on the repo's "Add file → Upload files" screen **drag
   the whole `couch-clash/` folder in** and commit. No Git commands needed.
3. Go to **<https://dashboard.render.com/select-repo?type=blueprint>** → **New
   Blueprint** → pick that repo → **Apply**. `render.yaml` is detected
   automatically; it builds the Dockerfile, sets `PORT=10000` and health-checks
   `/api/health`.

You get `https://couch-clash-xxxx.onrender.com` — **stable, phone-openable, and
never expires**. CREATE ROOM, the lobby QR and invite links all work same-origin.
Render's free tier sleeps after inactivity, so the *first* load after a long idle
may take ~30 s.

**Already comfortable with Docker?** `cd couch-clash && docker compose up -d` gives
you `http://localhost:8000` on your own machine; both phones on the same Wi-Fi can
open `http://<your-PC-LAN-IP>:8000` with no tunnel and no account at all.

---

## Fast static page (SOLO, or TWO PHONES with a relay)

Drag **`CouchClash-static-site.zip`** into **<https://app.netlify.com/drop>**. You get
a stable URL immediately. SOLO and ONE DEVICE work offline. For TWO PHONES, tap
**⚙ RELAY** in the JOIN panel and paste the URL of any running Couch Clash server
(the Render one above, or the current `PUBLIC-LINK.txt`), then **USE**. The server
sends `Access-Control-Allow-Origin: *`, so rooms, SSE, QR and invites all work
cross-origin.

> A static host can **serve** the game but cannot **be** the relay — two-phone mode
> needs one always-on process for `/api/events` and the in-memory rooms.

---

## How to tell which build you are on

Current build is **v5.5**: the JOIN panel shows **⚙ RELAY · v5.5** and the top badge
reads `● LIVE SERVER · v5.5 …`. If a page shows the old toast
*"Could not create a room. Are you on the live preview?"* or no ⚙ RELAY chip, it is
an old cached/deployed copy — hard-refresh or re-upload the static site. Static
responses now send `Cache-Control: no-store`, so a fresh load cannot be stale.
