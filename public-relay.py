"""End-to-end two-phone relay check over the PUBLIC Cloudflare URL."""
import json, urllib.request, urllib.parse, threading, time, sys

U = sys.argv[1] if len(sys.argv) > 1 else 'https://thee-mat-strings-structures.trycloudflare.com'

def post(path, payload):
    req = urllib.request.Request(U + path, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, json.loads(r.read().decode())

def get(path):
    with urllib.request.urlopen(U + path, timeout=20) as r:
        return r.status, r.read()

def sse(code, tok, role, out, ready, stop):
    q = urllib.parse.urlencode({'code': code, 'token': tok, 'role': role})
    req = urllib.request.Request(U + '/api/events?' + q,
                                 headers={'Accept': 'text/event-stream'})
    with urllib.request.urlopen(req, timeout=30) as r:
        ready.set()
        for raw in r:
            line = raw.decode().strip()
            if line.startswith('data:'):
                try: out.append(json.loads(line[5:].strip()))
                except Exception: pass
            if stop.is_set(): return

print('TARGET', U)
st, h = post('/api/room', {'mode': 'online', 'carId': 'silver84', 'layoutId': 'woven'})
assert st == 200, h
code, htok = h['code'], h['token']
print('PUBLIC ROOM OK', code)

st, g = post('/api/join', {'code': code, 'carId': 'redfang'})
assert st == 200, g
gtok = g['token']
print('PUBLIC JOIN OK', g['role'])

hout, gout, stop = [], [], threading.Event()
hr, gr = threading.Event(), threading.Event()
th = threading.Thread(target=sse, args=(code, htok, 'host', hout, hr, stop), daemon=True)
tg = threading.Thread(target=sse, args=(code, gtok, 'guest', gout, gr, stop), daemon=True)
th.start(); tg.start()
assert hr.wait(12) and gr.wait(12), 'SSE streams never connected'
print('PUBLIC BOTH SSE CONNECTED OK')
time.sleep(0.6)

st, _ = post('/api/input', {'code': code, 'token': htok,
                            'input': {'throttle': 1, 'steer': 0.5, 'boost': True}, 'seq': 1})
assert st == 200
print('PUBLIC INPUT OK')

st, _ = post('/api/layout', {'code': code, 'token': gtok, 'layoutId': 'neon'})
assert st == 200
print('PUBLIC LAYOUT OK')

st, png = get('/api/qr?text=' + urllib.parse.quote(U + '/?room=' + code))
assert st == 200 and png[:8] == b'\x89PNG\r\n\x1a\n', (st, png[:20])
print('PUBLIC QR OK', len(png), 'bytes')

# Wait for the layout change to PROPAGATE into a snapshot on both streams,
# not merely for the first snapshot / layout event (those can predate the POST).
deadline = time.time() + 10
while time.time() < deadline:
    hl = [o['snapshot'].get('layout') for o in hout if o.get('type') == 'snapshot']
    gl = [o['snapshot'].get('layout') for o in gout if o.get('type') == 'snapshot']
    if 'neon' in hl and 'neon' in gl and any(o.get('type') == 'layout' for o in hout):
        break
    time.sleep(0.2)

ht = [o.get('type') for o in hout]
gt = [o.get('type') for o in gout]
print('HOST EVENTS  ', sorted(set(ht)), 'count', len(ht))
print('GUEST EVENTS ', sorted(set(gt)), 'count', len(gt))
assert 'hello' in ht and 'hello' in gt, (ht, gt)
assert 'snapshot' in ht and 'snapshot' in gt, (ht, gt)
assert 'layout' in ht and 'layout' in gt, (ht, gt)
layouts = [o['snapshot'].get('layout') for o in hout if o.get('type') == 'snapshot']
assert 'neon' in layouts, layouts[:5]
print('PUBLIC SNAPSHOTS OK, layout synced =', layouts[-1])

stop.set()
post('/api/leave', {'code': code, 'token': htok})
print('ALL PUBLIC RELAY CHECKS PASSED')
