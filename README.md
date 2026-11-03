# COUCH CLASH — Diecast Duel (v5.3)

A tiny top-down sumo duel built from the photo in `../uploads/IMG_20261102_181202.jpg`:
two customised diecast racers, nose-to-nose on a brown woven cushion. Ram your rival,
shove them off the fabric, or drain their health before sudden death shrinks the arena.

Runs entirely in the workspace: **no CDN, no build step, no account, no install.**

**Deploying it?** See **`DEPLOY.md`** — `CouchClash-deploy.zip` is the one-click Render / Docker bundle for the **full two-phone game**, and `CouchClash-static.html` is a drag-and-drop single file for SOLO / ONE DEVICE.

---

## ▶ PLAY ON YOUR PHONE — open this exact link

**https://thee-mat-strings-structures.trycloudflare.com/**

This is a **public HTTPS link** to the real `server.py`, not a file preview. Open it
directly in Chrome/Safari on any phone — no Arena login, no preview token. The invite
link and QR in the **TWO PHONES** lobby are built from this same origin, so a friend on
another network can join. A scannable copy is in `PLAY-ON-PHONE.png`.

> The link is a Cloudflare **quick tunnel**, so it is temporary: if the sandbox or the
> tunnel restarts, the subdomain changes. Ask for a fresh link if it ever stops loading.
> `start_public.sh` recreates it (prints the new URL to the process log).

### v5.5 — no more stale copies

Two follow-ups after a screenshot showed the *old* toast and no ⚙ RELAY chip:

- **Version stamp.** The relay chip, the relay status and the corner badge all read
  `v5.5`. A screenshot now identifies the build instantly — if you don't see
  `⚙ RELAY · v5.5`, you are looking at an old/cached/deployed copy, not this server.
- **`Cache-Control: no-store, must-revalidate` + `Pragma: no-cache`** on every static
  response, so a browser cannot silently hold an old game page with dead relay logic.
- **`relay_watch.py`** supervises the Cloudflare quick tunnel: when Cloudflare
  invalidates it after a sandbox sleep (`Unauthorized: Tunnel not found`), it restarts
  `cloudflared` and rewrites `PUBLIC-LINK.txt`, `PLAY-ON-PHONE.png`, `README.md` and
  the relay-test default to the new URL. **The current link is always in
  `PUBLIC-LINK.txt`.**

### v5.4 — "Could not create a room" is now impossible to get stuck on

`CREATE ROOM` used to `fetch('/api/room')` against the page's own origin. On a
**static copy** (workspace file viewer, Netlify, Cloudflare Pages) that returns an
HTML 404, `r.json()` throws, and the only feedback was a vague
*"Are you on the live preview?"* toast. Now:

- **One shared relay probe** at startup drives both the corner badge and a
  **⚙ RELAY** panel. If there is no server, the panel **opens automatically** with
  `● NO RELAY — TWO PHONES NEEDS A SERVER` and a plain-English explanation.
- **Paste any running Couch Clash server URL** into the panel and hit **USE** — or
  **OPEN** to go straight to that server page. `?relay=https://…` does the same and
  is remembered. Every `/api/*` call, the `EventSource`, the QR image and the health
  check route through that origin. The relay sends `Access-Control-Allow-Origin: *`,
  so a static page can drive the full two-phone game.
- **Invite links** with an external relay send your friend to the relay's own page
  (`https://relay/?room=XXXX`), so they never need to configure anything.
- Failures now report the real reason (`HTTP 404`, `Failed to fetch`, …) instead of
  guessing, and keep the fix visible rather than a 2.6-second toast.

On the normal server build the panel stays collapsed — the accepted look is unchanged.

### App previews — ports 8000 and 20241

`server.py` now binds **both `0.0.0.0:8000` and `0.0.0.0:20241` in one process**, so
both live previews show the same game and share **one** authoritative room store
(`PORTS=8000,20241`, or a single `PORT=9000` override). Previously 20241 was
cloudflared's **metrics** endpoint (404 on `/`, Prometheus text on `/metrics`), so
that "app preview" never showed the game. cloudflared now binds its metrics to
`[::1]:20241` (IPv6 loopback), which coexists with the game's IPv4 bind without
stealing the port or creating a second, dead preview panel. The public tunnel now points
at `http://127.0.0.1:8000` (the primary preview) and its metrics server is bound to
`[::1]:8000` — IPv6 loopback on the same port number, so it does not create a second,
dead preview panel. `/favicon.ico` now returns a real 548-byte PNG instead of a 404,
so preview-browser probes no longer log a broken resource (seen in the server log as
`GET /favicon.ico 404`).

A room created through port 8000 can be joined from port 20241 (verified), so
TWO PHONES works no matter which preview each driver opens.

**Why the old links failed:** `https://8000-<sandbox-id>.e2b.app/` is token-gated by the
Arena preview gateway — outside the in-app preview it returns
`403 Sandbox is secured with traffic access token`. A `*.arena.site` page showing
**"Preview Unavailable / Previews open inside Arena"** is just that gate, not the game.
Neither surface can receive touches. The quick tunnel above bypasses both.

---

## Run it

```bash
cd couch-clash
python3 server.py          # 0.0.0.0:8000 + 0.0.0.0:20241 (both live previews)
PORTS=9000,9001 python3 server.py   # custom ports; PORT=9000 for just one
```

Open the **public link at the top of this file** (or the in-app live preview).
`server.py` binds `0.0.0.0:8000` and accepts any Host/Origin, so no config is needed.
`index.html` also works in the workspace file viewer for SOLO / ONE DEVICE — but
TWO PHONES needs `server.py` because it calls `/api/*`. Python 3.8+ only; the QR
generator (`vendor/segno`) is vendored.

For SSE to stream through a reverse proxy (Cloudflare Tunnel buffers HTTP/1.1
responses with neither `Content-Length` nor a terminating chunk), `/api/events`
answers with HTTP/1.0 + `Connection: close` and a one-time 16 KB SSE comment burst.
`EventSource` ignores the comment; it simply forces the first flush.

> **Which preview?** The **"Preview project"** button opens a *static* file preview —
> it says "Static projects run locally" and has **no server**, so TWO PHONES cannot work
> there. Use the **live preview link** (`https://8000-<sandbox-id>.e2b.app/`) that comes
> from the running `server.py`. The file viewer is fine for SOLO / ONE DEVICE only.
>
> **Blank / unresponsive preview?** The file viewer uses a sandboxed iframe with an
> opaque origin, where `localStorage` is blocked. The game falls back to in-memory
> storage and shows a visible error banner if anything else fails, so it works in both.

---

## Three ways to play

| Mode | What it is |
| --- | --- |
| **SOLO** | You vs CPU (chill / normal / spicy). |
| **ONE DEVICE** | Two drivers sharing one screen — P1 wheel/pedals or `W A S D`, P2 `↑ ← ↓ →` + `Enter`. |
| **TWO PHONES** | One driver per phone, over the relay. Create a room → share the **4-letter code**, the **invite link**, or the **QR code** in the lobby. |

### Two-phone flow
1. Tap **TWO PHONES → CREATE ROOM**. Pick **BEST OF 3 / 5** and **45s / 60s / 90s** first (the host sets the rules), and choose the **couch** in the **COUCH** screen first.
2. On the lobby, point your friend's camera at the **QR code**, or hit **INVITE** / **COPY**.
   The link contains `?room=XXXX`, so it auto-joins on their phone.
3. Both phones show the countdown. **Your car wears a pulsing gold ring and arrow.**
4. The match is synced. Either driver can hit the **pause button** — both phones freeze together.
5. **REMATCH** resyncs both phones. If a tab is backgrounded, the duel keeps running on the server
   and the returning phone gets a fresh snapshot on reconnect.

---

## Controls (v5 — actually reliable)

The old controls were hidden on non-touch devices, the wheel snapped back to zero the
instant you released it, and a pedal could stay stuck after a cancelled pointer. v5
fixes all of that:

- **On-screen controls are shown in every mode while playing** (SOLO, ONE DEVICE and
  TWO PHONES), for **touch and mouse alike** — unless you explicitly pick `⌨ KEYBOARD`.
- Every button uses **Pointer Events** with pointer capture, `pointercancel` and
  `lostpointercapture` cleanup, plus a per-pointer watchdog. Each held button remembers
  *which finger* pressed it, so tapping NITRO with a second finger no longer releases
  GAS. `touch-action:none` prevents the browser from panning/zooming mid-drag.
- **Wheel drag** gives analog steering; a **tap on either side** now gives a short
  steering impulse that decays smoothly instead of doing nothing.
- **v5.1 input rewrite:** the whole control strip is now hit-testable (`pointer-events:auto`
  instead of the old `none`), and **no control depends on `setPointerCapture` any more**. Every
  sequence is tracked on `window`, so a cancelled capture, an iframe, a fullscreen transition or
  a webview that never delivers `pointermove` cannot leave a pedal stuck or make the wheel dead.
  Pointer Events are primary; Touch + Mouse fallbacks take over when they are missing, and a
  `click` fallback guarantees tap-to-steer. The wheel also has a live **STEER · LEFT/RIGHT %**
  readout and a pair of backup **◀ LEFT / RIGHT ▶** buttons — so steering works even in a
  browser that mishandles drag events.
- Three interchangeable schemes, chosen from the menu and persisted:

| Chip | What you get |
| --- | --- |
| 🏎 **RACE WHEEL** (default) | Drag/tap wheel on the left, `GAS` / `BRAKE` / `NITRO` pedals on the right — the standard mobile-racing layout. |
| ◀▶ **ARCADE** | Big `LEFT` / `RIGHT` buttons plus the same three pedals. Simplest on a small phone. |
| ⌨ **KEYBOARD** | Hides the overlay; `W A S D` + `Space` (P1), arrows + `Enter` (P2). |

| Action | Keyboard | Touch |
| --- | --- | --- |
| Steer | `A` `D` / `←` `→` | drag/tap the wheel, or LEFT / RIGHT |
| Gas | `W` / `↑` | **GAS** pedal |
| Brake / reverse | `S` / `↓` | **BRAKE** pedal |
| Nitro dash | `Space` / `Enter` | **NITRO** pedal |
| Pause | `P` or `Esc` | ⏸ in HUD (synced online) |

---

## Your choice of view

The v4 landscape-only gate is gone. In portrait, a **CHOOSE YOUR VIEW** panel offers:

- **↻ ROTATE TO LANDSCAPE** — keeps the wide horizontal arena; on Android/Chrome the
  game also asks the browser to lock landscape.
- **⛶ FULL SCREEN** — requests the Fullscreen API and **rotates the couch 90°** so the
  arena fills the tall screen instead of being squeezed into a thin strip. If the browser
  or a sandboxed iframe blocks fullscreen, the arena still expands to fit with no cropping
  of the ring-out edge.

`LANDSCAPE` / `FULL SCREEN` chips in the menu and a ⛶ button in the HUD let you switch
at any time. The choice is saved (`cc_view`). Compact HUD and smaller pedals handle
short/wide screens; safe-area insets keep the controls clear of the notch and home bar.

**v5.1 fullscreen fixes:** the old version only set a CSS class — if the browser or a
sandboxed iframe blocked the Fullscreen API, nothing actually expanded. Now
`.fullscreen-view #app` becomes `position:fixed; inset:0; width/height:100%` as a
**CSS fullscreen fallback** that works everywhere, while the real API is still attempted.
`resize()` re-runs on `fullscreenchange` / `orientationchange` (plus delayed passes) and
guards against a momentary `0×0` canvas rect, which could blank the game mid-transition.
Exiting fullscreen no longer silently flips you back to LANDSCAPE.

The 90° arena rotation is now **switchable** and **OFF by default**, because in a tall
portrait view it changes which way is "forward" and made the car feel unresponsive.
The **↻ ARENA TURN · ON/OFF** chip in the menu and the **↻** button in the HUD toggle it
live (saved as `cc_arena_turn`). Turn it ON only if you want the couch to fill a tall
screen. Controls work identically in every combination of fullscreen + rotation.

### v5.2 — no more stuck UI
Two things could make the game look completely frozen:

- **The frame loop had no error handling.** `requestAnimationFrame(frame)` was the last
  line of `frame()`, so a single exception in `update()`/`render()` stopped the loop
  forever — the countdown never ended and nothing moved. Worse, the global error trap
  then showed a **full-screen** `#fatal` overlay (`z-index:99`) over everything. Now
  `frame()` uses `try/catch/finally` so every frame re-schedules the next one, a
  generation-guarded watchdog restarts the loop if rAF is throttled or lost, and runtime
  errors appear in a small dismissible **error chip** instead of covering the game. Only a
  genuine startup failure shows the full-screen banner.
- **The portrait view chooser was a full-screen modal** (`inset:0; z-index:60`). In a
  short/narrow preview iframe its buttons could be clipped by `overflow:hidden`, leaving
  no way to dismiss it — and it could reappear over a running match after a `resize`.
  It is now a **compact, non-blocking top card** with an explicit **✕**, `pointer-events:none`
  on the container, scrollable overflow, and it is hidden automatically as soon as a match
  starts. `#touch` was raised to `z-index:45` so the controls are never under an overlay.

Result: in portrait you can simply tap **✕** (or ignore the card entirely) and press
**START ENGINE**; the match runs and the controls respond. Verified that the round timer
counts down from 60 to 54 over 600 frames in a 400×820 portrait viewport with the chooser
still unanswered.

### v5.3 — touches that actually reach the game
The screenshot that came back was not the game at all: it was Arena's
**"Preview Unavailable"** gate on `*.arena.site`, so no control could ever respond.
v5.3 fixes both halves — access and input.

- **Access:** a public Cloudflare quick tunnel serves the real server, including
  `/api/*` and SSE, so two-phone play works across networks (see the link above).
- **Three independent input paths.** Pointer Events are still the primary path, but
  the old Touch fallback used `document.elementFromPoint()` on a window capture
  listener — fragile in embedded webviews. Now every pedal and the wheel have
  **direct element-level `touchstart` / `touchmove` / `touchend`** listeners. Touch
  targets stay pinned to the element where the gesture began, so dragging a finger
  off the wheel keeps steering. No pointer capture and no `elementFromPoint`.
- **A plain `click` pulse.** If both Pointer and Touch events are suppressed, a tap
  still produces a real 320 ms press (visible `ACTIVE` state, real throttle/steer
  payload). De-dup is **per element**, so tapping GAS never swallows a wheel tap.
- **Frame-loop, gate, and error-chip fixes from v5.2 are still in place.**

Verified with a jsdom harness that **throws if `elementFromPoint` is called**:
direct `touchstart` on GAS presses and releases it, a `touchstart` on the wheel's
inner ring followed by a `touchmove` outside the wheel steers `-1.00` → `+1.00`,
plain clicks give GAS and steering pulses, and the pointer path / portrait match /
fullscreen / four couches / six cars all still work.

---
---

## Choose your couch (4 layouts)

Open **COUCH** from the menu. Every layout changes **both the fabric and the outline of
the arena** — the stitched edge, the minimap, the ring-out collision and the pickup spawn
all follow the new shape.

| # | Layout | Fabric | Shape |
| --- | --- | --- | --- |
| 01 | **WOVEN CUSHION** | The brown woven cushion from your photo, with storybook + knitted throw | Rounded rectangle |
| 02 | **QUILTED LEATHER** | Oxblood leather, diamond stitching | Pill / stadium |
| 03 | **PICNIC CHECK** | Red-and-cream gingham | Diamond |
| 04 | **NEON GRID** | Dark slate with a cyan grid | Octagon |

Each card draws a small canvas preview of its own fabric and outline. The pick is saved
(`cc_layout`). Open COUCH from the **menu**, the **online lobby**, or the **pause panel** —
BACK returns you to where you came from. In TWO PHONES the **host's room layout wins**
(the guest gets a toast), but **either driver can change it** from the lobby or a synced
pause: that POSTs `/api/layout`, broadcasts to both phones, and switches the authoritative
Python physics too. Pause and rematch preserve the layout.

---

## Rules

- **Best of 3** (first to 2) or **Best of 5** (first to 3), **45 / 60 / 90 second** rounds.
- Win a round by **ring-out**, **knockout**, or having more health when the timer hits zero.
- Nose-to-side / nose-to-rear hits do far more damage. A turbo dash costs 16% charge
  and adds a burst of speed plus damage. Spark-plug pickups restore turbo and health.
- **Sudden death:** the cushion shrinks and both cars bleed health until someone falls.
- Win/loss and current **win streak** are tracked locally (solo + two-phone) and shown
  on the menu and result screen. A first-match coach overlay explains the controls once.

---

## The garage (6 cars)

Open **GARAGE** from the menu. Six diecast racers, all unlocked:

| # | Car | Look |
| --- | --- | --- |
| 01 | **SILVER BOLT 84** | Photo original — silver chevrons, red `84`, red hood burst |
| 02 | **RED FANG** | Photo original — angular red shards, red roof grid |
| 03 | **GOLD RUSH** | Champagne gold, twin black racing stripes |
| 04 | **BLUE COMET** | Deep blue, white centre stripe, ice-blue chevrons |
| 05 | **TOXIC WASP** | Acid green, diagonal hazard bars |
| 06 | **PHANTOM 07** | Matte black/violet, magenta neon piping |

Pick **DRIVER 1** and **DRIVER 2 / CPU** separately (in TWO PHONES each phone picks
its own). Selections persist locally, are sent with `/api/room`, `/api/join` or
`/api/car`, and are echoed in every authoritative snapshot, so both phones always
draw the right liveries and show the right nameplates. Wins are counted **per car**
and shown in the garage. All cars share identical balanced handling — the duel
stays fair, the livery is yours.

---

## Architecture (v5 — fair networking)

```
index.html   renderer + input + UI       (both phones are identical thin clients)
   |  POST /api/input  (20 Hz)              ^  SSE /api/events (30 Hz snapshots)
   v                                        |
server.py    stdlib HTTP/SSE relay + authoritative 30 Hz ticker
   |
engine.py    pure-Python port of the game physics (the single source of truth)
   |
vendor/segno  QR PNG generator (BSD-3-Clause, vendored)
```

**Neither phone simulates physics.** Both POST their controls and draw the same
server snapshot stream, so there is no host advantage, no drift, and a backgrounded
tab cannot stall the match. Inputs from a disconnected phone are zeroed server-side,
and a reconnect is resynchronised from the cached snapshot. `LAYOUT_SHAPES` in
`engine.py` mirrors `LAYOUTS` in `index.html`, so the ring-out edge is identical on
both phones and in the browser's local SOLO mode.

### Endpoints
| Path | Purpose |
| --- | --- |
| `POST /api/room` | create room, optional `{bestOf, roundSeconds, carId, layoutId}` |
| `POST /api/join` | join / reconnect with `{code, token, carId, layoutId}` (a stranger gets 409) |
| `GET  /api/events` | SSE: `hello`, `peer`, `start`, `snapshot`, `skins`, `layout`, `pause`, `options`, `rematch` |
| `POST /api/input` | a phone's `{throttle, steer, boost}` |
| `POST /api/car` | change that seat's livery; broadcasts `skins` |
| `POST /api/layout` | change the room's couch; broadcasts `layout` and updates physics (400 on unknown id) |
| `GET  /api/qr?text=` | scannable PNG of the invite URL |
| `POST /api/pause` | synced pause / resume |
| `POST /api/options` | host changes match rules |
| `POST /api/rematch` | restart on both phones |
| `POST /api/leave` | clean disconnect |
| `GET  /api/health` | `{ok, rooms, authoritative, engine}` |

`hello` and every `snapshot` carry `layout`, `shape` and `corner` alongside `skins`.
Room codes use `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (no ambiguous 0/O/1/I). Each seat
gets an 18-character token stored in `localStorage` so a reload rejoins the same seat.
Idle rooms with no connected clients are reaped after 180 seconds. SSE heartbeats
fire every 2 seconds for fast drop detection.

---

## Photo → game

The photo is embedded as a base64 JPEG inside `index.html` and shown via **VIEW THE PHOTO**.
The woven cushion is redrawn as a procedural fabric pattern, and both liveries are
recreated in canvas: Silver Bolt 84 (black, red `84`, grey chevrons/spoiler) and
Red Fang (angular red graphics, red windshield and rear wing). The original JPEG has
EXIF orientation `6`; re-apply `ImageOps.exif_transpose` before any further processing.

## Notes / limits

- Local SOLO / ONE DEVICE logic still runs in the browser; only TWO PHONES is server-authoritative.
  Both use the same shape-aware signed-distance function.
- Two-phone play assumes both phones can reach the same `server.py` origin. To play across
  the internet, expose this preview host (or deploy `server.py` behind HTTPS).
- Fullscreen API calls can be blocked by iOS Safari or a sandboxed iframe; the game falls
  back to a fit-to-screen rotated arena and a toast rather than failing.
- Rooms are in-memory only — restarting the server clears them. There is no auth,
  matchmaking, persistence, or anti-cheat beyond the seat token.
- Deliberately deferred for now: extra power-ups and additional game modes.
- Verification (v5.3): `node --check` on the extracted script, `py_compile` on both Python
  files, a jsdom harness in normal **and** opaque-origin sandboxed contexts covering
  direct element Touch Events and click pulses with `elementFromPoint` rigged to throw,
  a **public two-phone SSE relay** (both streams deliver `hello`/`start`/`snapshot`/
  `layout`/`peer` at 30 Hz, QR PNG, layout sync) over the Cloudflare tunnel, and
  a portrait 400×820 match started with the chooser unanswered (chooser hidden, controls
  visible, timer counting down, wheel + GAS working), `resize`/`fullscreenchange`/
  `orientationchange` during play, a synthetic runtime error (no fatal banner, loop still
  scheduled), rotation default OFF + toggles, and fullscreen controls. Earlier coverage:
  wheel drag delivered on `window` (no capture), touch/mouse/click fallbacks, the backup
  LEFT/RIGHT buttons, the live STEER readout, local-physics steering decay, controls while
  fullscreen + rotated, the ↻ rotation toggle, `fullscreenchange`/`resize`, and a `0×0`
  canvas rect; plus a regression pass over couches, garage, schemes, views and online sync.
  Also: `node --check`/`py_compile` and a real two-client SSE relay test. Earlier v5 coverage:
  startup with no fatal banner, GAS/BRAKE/NITRO press+release payloads, two-finger
  multitouch, stuck-pointer cleanup, wheel tap impulse, ARCADE taps, local CPU-mode
  physics (NITRO drains turbo), the four couch cards, layout selection, portrait view
  choice with rotation, and `layoutId`/`carId` on room creation; plus a real two-client
  SSE relay test for `hello`/snapshot `shape`, `/api/layout` broadcast, invalid ids,
  shape-dependent ring-outs, skins, pause and rematch. No real-browser visual check
  has been run.
