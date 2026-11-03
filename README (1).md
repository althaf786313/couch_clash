# Verification harnesses

Optional — none of these are needed to play or deploy.

```bash
# Browser-level DOM / input checks (install jsdom locally first)
cd tests && npm install jsdom --no-save
node touch-v53.js       # direct element touch, click pulse, portrait, fullscreen
node static-check.js    # single-file static build starts with NO server
node relay-v54.js       # no-relay diagnosis, ?relay=, USE button, CORS routing

# Real two-phone relay against ANY deployed origin
python3 public-relay.py https://YOUR_DOMAIN/
# -> ALL PUBLIC RELAY CHECKS PASSED
```

`touch-v53.js` deliberately makes `document.elementFromPoint()` throw, proving the
wheel/pedals use direct element Touch Events. It also covers the plain `click` pulse,
pointer path, portrait match, fullscreen, four couches and six cars.

`static-check.js` stubs `fetch()` to reject (simulating a static host with no `/api/*`)
and asserts the single-file build starts clean, auto-opens the ⚙ RELAY panel, keeps
TWO PHONES available and plays a SOLO match with working controls.

`relay-v54.js` covers the same-origin build (no regression), a static page with no
relay (panel auto-opens, actionable error, old vague toast gone), `?relay=` override
(room POST / EventSource / QR / invite all use the external origin) and repairing a
broken page live with the USE button.

`public-relay.py` opens BOTH host and guest SSE streams and waits for the couch layout
change to propagate into a snapshot on each, then asserts `hello`, `start`, `snapshot`,
`layout` and `peer` events, QR PNG generation and 30 Hz snapshots.
