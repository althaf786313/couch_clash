#!/usr/bin/env python3
"""
Couch Clash — game server + authoritative two-phone relay.

Pure Python stdlib + vendored `segno` (QR). No third-party services.

  POST /api/room            create room (host); optional {bestOf, roundSeconds}
  POST /api/join            join / reconnect with code + token
  GET  /api/events?...      Server-Sent Events stream
  POST /api/input           a phone sends its controls
  GET  /api/qr?text=...     scannable PNG invite code
  POST /api/pause           synced pause for both phones
  POST /api/options         host changes match settings
  POST /api/rematch         restart the match on both phones
  POST /api/leave           disconnect cleanly
  GET  /api/health          status
"""

import io
import json
import mimetypes
import os
import queue
import random
import string
import sys
import threading
import time
import urllib.parse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "vendor"))

import segno          # vendored, MIT/BSD-3-Clause; see vendor/SEGNO_LICENSE.txt
import engine

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0/O/1/I
ROOMS = {}
LOCK = threading.RLock()
FAVICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAB60lEQVR42u1bPUsEMRDdGxYEucorRARBRBsLweqqszksrf0R/hx/hLXlYaOVlWBho4hwIHLFddfYqFWOuGQv37lM9k217G4m8968TJJl09vqb/5WHTaqOm6dJ6B2bTi/Pc8OzOBiYt2mZ1MDcgTtSwaVCN4mXq0C2hwdXN5nB/r95sxaDSsJUIHPEbgJEW0ktBLQBM8BuI4IFQlGNYAjeNO4SZd9ruBV8auGNHGv9r6zA5UofRsc2AuUOvZNawEUAAJAAL4HJLOn1w/rNqdH+2UowAW8TzsMgZwI8M1iTBVQ7uBjk0AcwMckAdNgSGcPe9vL6/7dYzRVLcbDajSd5UOADFzYYjyMmjnRpy8RFAN8SvPtv07d+e71ifadz6tn6zhclYCFEFfph4qnTh2orbyxHQYBzL4HHL99La9fDney9+tMwGg6+1d45ACb93wCNvWLaXAdNUCwrsqSLouu2Vc991kOeysg1KZkXf1jFgjhZLBB1fz7Z+Vzl0yZ+MU6IJd1gMiGnLEQGYrlN9pCKGRwKfxiHQACQAAIAAEgQEw10q+kbT8eczUZj4wTCjBlrZTsawlwOXbCyZr4SPcSdxW0jX2rGsCVBJO4cWIEZ4YMj81xPEdgUtAppDNu4K0UwEER0U+OYjNUoP0BsJPLmlKPnuYAAAAASUVORK5CYII="

DT = 1.0 / 30.0
ALLOWED_BEST_OF = (3, 5)
ALLOWED_SECONDS = (45, 60, 90)
ALLOWED_CARS = ("silver84", "redfang", "goldrush", "bluecomet", "toxicwasp", "phantom07")
ALLOWED_LAYOUTS = tuple(engine.LAYOUT_SHAPES.keys())
_qr_cache = {}


def valid_car(value, fallback):
    return value if value in ALLOWED_CARS else fallback


def valid_layout(value, fallback="woven"):
    return value if value in ALLOWED_LAYOUTS else fallback


def sync_skins(room):
    """Push each phone's garage pick into the authoritative snapshot."""
    room.game.skins = room.skins()


def sync_layout(room):
    """Push the chosen couch outline into the authoritative simulation."""
    room.game.set_layout(room.layout)


def token(n=18):
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(n))


def code(n=4):
    return "".join(random.choice(ALPHABET) for _ in range(n))


def qr_png(text):
    text = (text or " ")[:300]
    if text in _qr_cache:
        return _qr_cache[text]
    q = segno.make(text, error="m")
    buf = io.BytesIO()
    q.save(buf, kind="png", scale=7, border=4,
           dark="#160d0a", light="#ffffff")
    data = buf.getvalue()
    if len(_qr_cache) > 80:
        _qr_cache.clear()
    _qr_cache[text] = data
    return data


class Client:
    def __init__(self, tok, role, car_id=None):
        self.token = tok
        self.role = role
        self.car_id = car_id or ("silver84" if role == "host" else "redfang")
        self.q = queue.Queue()
        self.connected = False
        self.conn_id = token(8)
        self.last_seen = time.time()
        self.input = dict(engine.ZERO)
        self.seq = 0

    def send(self, obj):
        self.q.put(json.dumps(obj, separators=(",", ":")))

    def kill_stream(self):
        try:
            self.q.put(None)
        except Exception:
            pass

    def drain(self):
        while True:
            try:
                self.q.get_nowait()
            except queue.Empty:
                break


class Room:
    def __init__(self, code_str, best_of=3, round_seconds=60,
                 host_car="silver84", layout="woven"):
        self.code = code_str
        self.layout = layout
        self.host = Client(token(), "host", host_car)
        self.guest = None
        self.started = False
        self.options = {"bestOf": best_of, "roundSeconds": round_seconds}
        self.game = engine.Game(best_of, round_seconds)
        self.last_snapshot = None
        self.last_active = time.time()
        self.created = time.time()

    def clients(self):
        return [c for c in (self.host, self.guest) if c is not None]

    def find(self, tok):
        for c in self.clients():
            if c.token == tok:
                return c
        return None

    def both(self):
        return self.host.connected and self.guest is not None and self.guest.connected

    def skins(self):
        return [self.host.car_id,
                self.guest.car_id if self.guest is not None else "redfang"]

    def peer_connected(self, c):
        other = self.guest if c.role == "host" else self.host
        return bool(other and other.connected)

    def broadcast(self, obj, exclude=None, only_connected=True):
        for c in self.clients():
            if c is exclude:
                continue
            if only_connected and not c.connected:
                continue
            c.send(obj)

    def peer_event(self, c):
        return {"type": "peer", "both": self.both(),
                "peerConnected": self.peer_connected(c), "role": c.role}

    def snapshot_payload(self, events=None):
        snap = self.game.snapshot()
        self.last_snapshot = snap
        return {"type": "snapshot", "snapshot": snap,
                "events": events if events is not None else []}


def get_room(code_str):
    return ROOMS.get((code_str or "").upper())


def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw or b"{}")
    except Exception:
        return {}


def ticker():
    """Single authoritative clock for every room: 30 Hz fixed step."""
    while True:
        time.sleep(DT)
        with LOCK:
            rooms = list(ROOMS.values())
        for room in rooms:
            with LOCK:
                if not room.started:
                    continue
                guest = room.guest
                # The match lives on the server: keep simulating as long as ANY
                # phone is connected. A backgrounded tab no longer freezes the duel.
                any_connected = room.host.connected or (guest is not None and guest.connected)
                active = any_connected and not room.game.paused
                if active:
                    room.game.step(DT, [room.host.input,
                                       guest.input if guest else dict(engine.ZERO)])
                sync_skins(room)
                sync_layout(room)
                events = room.game.drain_events()
                payload = room.snapshot_payload(events)
                for c in room.clients():
                    if c.connected:
                        c.send(payload)
                    else:
                        c.drain()
                if active:
                    room.last_active = time.time()


def janitor():
    while True:
        time.sleep(20)
        now = time.time()
        with LOCK:
            for c, room in list(ROOMS.items()):
                if not any(cl.connected for cl in room.clients()) and now - room.last_active > 180:
                    del ROOMS[c]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "CouchClash/5.3"

    def log_message(self, fmt, *args):
        p = getattr(self, "path", "")
        if any(x in p for x in ("/api/input", "/api/snapshot", "/api/events", "/api/qr")):
            return
        super().log_message(fmt, *args)

    # ------------------------------------------------------------------ helpers
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def json_response(self, status, obj):
        data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.cors()
        self.end_headers()
        self.wfile.write(data)

    def sse_write(self, obj):
        payload = obj if isinstance(obj, str) else json.dumps(obj, separators=(",", ":"))
        self.wfile.write(("data: " + payload + "\n\n").encode("utf-8"))
        self.wfile.flush()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.cors()
        self.end_headers()

    def do_HEAD(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("", "/"):
            path = "/index.html"
        rel = os.path.normpath(path).lstrip("/")
        full = os.path.join(ROOT, rel) if not rel.startswith("..") else ""
        if not full or not os.path.isfile(full):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.cors()
            self.end_headers()
            return
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(os.path.getsize(full)))
        # Never let a browser/proxy keep a STALE game page: an old cached copy
        # silently keeps the old relay logic and breaks CREATE ROOM.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.cors()
        self.end_headers()

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/health":
            self.json_response(200, {"ok": True, "rooms": len(ROOMS),
                                     "authoritative": True, "engine": True})
            return

        if path in ("/favicon.ico", "/favicon.png"):
            # Preview panels and mobile browsers probe this. A 404 here used to
            # show up as a broken resource in the live-preview console.
            try:
                data = base64.b64decode(FAVICON_B64)
            except Exception:
                self.send_response(204); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.cors()
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/api/qr":
            try:
                data = qr_png((query.get("text") or [""])[0])
            except Exception as exc:
                self.json_response(400, {"error": "qr failed: %s" % exc})
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=600")
            self.cors()
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/api/events":
            self.handle_events(query)
            return

        self.serve_static(path)

    def serve_static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        rel = os.path.normpath(path).lstrip("/")
        if rel.startswith(".."):
            self.json_response(403, {"error": "forbidden"})
            return
        full = os.path.join(ROOT, rel)
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        if not os.path.isfile(full):
            self.json_response(404, {"error": "not found"})
            return
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        try:
            with open(full, "rb") as f:
                data = f.read()
        except OSError:
            self.json_response(500, {"error": "read error"})
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        # Never let a browser/proxy keep a STALE game page: an old cached copy
        # silently keeps the old relay logic and breaks CREATE ROOM.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.cors()
        self.end_headers()
        self.wfile.write(data)

    def handle_events(self, query):
        room = get_room((query.get("code") or [""])[0])
        tok = (query.get("token") or [""])[0]
        if not room:
            self.json_response(404, {"error": "Room not found"})
            return
        client = room.find(tok)
        if not client:
            self.json_response(401, {"error": "Invalid session"})
            return

        with LOCK:
            if client.connected:
                client.kill_stream()   # retires the previous stream's queue
            client.q = queue.Queue()
            my_q = client.q           # this stream reads ONLY its own queue
            client.conn_id = token(8)
            my_id = client.conn_id
            client.connected = True
            client.last_seen = time.time()
            room.last_active = time.time()
            should_start = room.both() and not room.started
            if should_start:
                room.started = True
                room.game = engine.Game(room.options["bestOf"], room.options["roundSeconds"])
                room.game.reset_match()
            sync_skins(room)
            sync_layout(room)
            if should_start:
                room.last_snapshot = room.game.snapshot()
            hello = {
                "type": "hello", "code": room.code, "role": client.role,
                "both": room.both(), "peerConnected": room.peer_connected(client),
                "started": room.started, "options": room.options,
                "skins": room.skins(),
                "layout": room.layout,
            }
            if room.started:
                hello["sync"] = room.game.snapshot()
                room.last_snapshot = hello["sync"]
                hello["paused"] = room.game.paused
            others = [c for c in room.clients() if c is not client]

        # HTTP/1.0 + Connection: close is what makes an unbounded SSE body
        # stream through reverse proxies (Cloudflare Tunnel buffers HTTP/1.1
        # responses that have neither Content-Length nor a terminating chunk).
        self.protocol_version = "HTTP/1.0"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.cors()
        self.end_headers()

        # Some edge proxies (Cloudflare Tunnel included) hold back tiny
        # text/event-stream writes until their buffer fills. SSE comments are
        # ignored by EventSource, so a one-time padding burst safely forces the
        # first flush and makes hello/snapshot arrive immediately on phones.
        try:
            self.wfile.write(b": " + b"~" * 16384 + b"\n\n")
            self.wfile.flush()
        except OSError:
            return

        try:
            self.sse_write(hello)
            with LOCK:
                for c in others:
                    if c.connected:
                        c.send(room.peer_event(c))
                if should_start:
                    room.broadcast({"type": "start", "code": room.code,
                                    "options": room.options})
            while True:
                try:
                    item = my_q.get(timeout=2)   # fast drop detection
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                if item is None:
                    break
                self.sse_write(item)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with LOCK:
                if client.conn_id == my_id:
                    client.connected = False
                    client.input = dict(engine.ZERO)
                    room.last_active = time.time()
                    for c in room.clients():
                        if c is not client and c.connected:
                            c.send(room.peer_event(c))

    # ------------------------------------------------------------------ POST
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        body = read_json(self)

        if path == "/api/room":
            best_of = int(body.get("bestOf", 3))
            secs = int(body.get("roundSeconds", 60))
            host_car = valid_car(body.get("carId"), "silver84")
            layout = valid_layout(body.get("layoutId"))
            if best_of not in ALLOWED_BEST_OF:
                best_of = 3
            if secs not in ALLOWED_SECONDS:
                secs = 60
            with LOCK:
                c = code()
                while c in ROOMS:
                    c = code()
                room = Room(c, best_of, secs, host_car, layout)
                ROOMS[c] = room
                self.json_response(200, {"code": c, "token": room.host.token,
                                         "role": "host", "options": room.options,
                                         "carId": host_car, "layoutId": layout})
            return

        if path == "/api/join":
            room = get_room(body.get("code"))
            if not room:
                self.json_response(404, {"error": "Room not found. Check the code."})
                return
            with LOCK:
                tok = body.get("token")
                picked_car = valid_car(body.get("carId"), "redfang")
                # The host owns the room's couch outline; either driver can change
                # it later through /api/layout and both phones will be updated.
                matched = room.find(tok) if tok else None
                if matched:
                    if body.get("carId"):
                        matched.car_id = picked_car
                    self.json_response(200, {"code": room.code, "token": matched.token,
                                             "role": matched.role, "options": room.options,
                                             "carId": matched.car_id})
                elif room.guest is None:
                    room.guest = Client(token(), "guest", picked_car)
                    room.last_active = time.time()
                    self.json_response(200, {"code": room.code, "token": room.guest.token,
                                             "role": "guest", "options": room.options,
                                             "carId": picked_car})
                else:
                    # Reconnects must present their token; a stranger cannot steal a seat.
                    self.json_response(409, {"error": "That room already has two drivers."})
            return

        room = get_room(body.get("code"))
        tok = body.get("token")
        if not room:
            self.json_response(404, {"error": "Room not found"})
            return
        client = room.find(tok)
        if not client:
            self.json_response(401, {"error": "Invalid session"})
            return
        room.last_active = time.time()
        client.last_seen = time.time()

        if path == "/api/input":
            inp = body.get("input") or dict(engine.ZERO)
            client.input = {
                "throttle": max(-1.0, min(1.0, float(inp.get("throttle", 0)))),
                "steer": max(-1.0, min(1.0, float(inp.get("steer", 0)))),
                "boost": bool(inp.get("boost", False)),
            }
            client.seq = int(body.get("seq") or 0)
            self.json_response(200, {"ok": True})
            return

        if path == "/api/layout":
            picked = valid_layout(body.get("layoutId"), None)
            if not picked:
                self.json_response(400, {"error": "Unknown couch layout"})
                return
            with LOCK:
                room.layout = picked
                sync_layout(room)
                room.broadcast({"type": "layout", "layout": picked})
                room.last_snapshot = room.game.snapshot()
            self.json_response(200, {"ok": True, "layoutId": picked})
            return

        if path == "/api/car":
            picked = valid_car(body.get("carId"), None)
            if not picked:
                self.json_response(400, {"error": "Unknown car"})
                return
            with LOCK:
                client.car_id = picked
                sync_skins(room)
                room.broadcast({"type": "skins", "skins": room.skins()})
                room.last_snapshot = room.game.snapshot()
            self.json_response(200, {"ok": True, "carId": picked,
                                     "skins": room.skins()})
            return

        if path == "/api/pause":
            with LOCK:
                room.game.paused = bool(body.get("paused"))
                sync_skins(room)
                sync_layout(room)
                room.broadcast({"type": "pause", "paused": room.game.paused,
                                "by": client.role})
                room.last_snapshot = room.game.snapshot()
            self.json_response(200, {"ok": True, "paused": room.game.paused})
            return

        if path == "/api/options":
            if client.role != "host":
                self.json_response(403, {"error": "Only the host sets the rules"})
                return
            best_of = int(body.get("bestOf", room.options["bestOf"]))
            secs = int(body.get("roundSeconds", room.options["roundSeconds"]))
            if best_of not in ALLOWED_BEST_OF:
                best_of = 3
            if secs not in ALLOWED_SECONDS:
                secs = 60
            with LOCK:
                room.options = {"bestOf": best_of, "roundSeconds": secs}
                room.game.set_options(best_of, secs)
                room.broadcast({"type": "options", "options": room.options})
            self.json_response(200, {"ok": True, "options": room.options})
            return

        if path == "/api/rematch":
            with LOCK:
                room.game = engine.Game(room.options["bestOf"], room.options["roundSeconds"])
                room.game.reset_match()
                sync_skins(room)
                sync_layout(room)
                room.last_snapshot = room.game.snapshot()
                room.broadcast({"type": "rematch", "options": room.options})
            self.json_response(200, {"ok": True})
            return

        if path == "/api/leave":
            with LOCK:
                client.connected = False
                client.kill_stream()
                for c in room.clients():
                    if c is not client and c.connected:
                        c.send(room.peer_event(c))
            self.json_response(200, {"ok": True})
            return

        self.json_response(404, {"error": "unknown endpoint"})


if __name__ == "__main__":
    # One authoritative room store and ONE ticker, but listen on every port the
    # workspace exposes as a live preview. 20241 used to be occupied by the
    # cloudflared metrics server, so the "app preview" on that port showed a
    # 404 / Prometheus text instead of the game. Binding the real Handler here
    # fixes that while keeping both previews on the SAME room state (two-phone
    # rooms are shared, not duplicated).
    #   PORTS="8000,20241"  (default)   PORT="9000"  (single-port override)
    raw = os.environ.get("PORTS") or os.environ.get("PORT") or "8000,20241"
    ports = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if chunk:
            try:
                ports.append(int(chunk))
            except ValueError:
                print("Ignoring invalid port %r" % chunk, flush=True)
    if not ports:
        ports = [8000]

    threading.Thread(target=ticker, daemon=True).start()
    threading.Thread(target=janitor, daemon=True).start()

    servers = []
    for port in ports:
        try:
            httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        except OSError as exc:
            print("Could not bind 0.0.0.0:%d (%s) — skipping" % (port, exc), flush=True)
            continue
        httpd.daemon_threads = True
        httpd.allow_reuse_address = True
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        servers.append(httpd)
        print("Couch Clash authoritative relay on 0.0.0.0:%d" % port, flush=True)

    if not servers:
        raise SystemExit("No preview port could be bound")
    print("Serving %d port(s), single shared authoritative state" % len(servers), flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
