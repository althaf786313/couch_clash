#!/usr/bin/env python3
"""
Couch Clash — authoritative game simulation (two-phone mode).

Pure Python port of the browser physics so the SERVER owns the match state.
Both phones become thin renderers: they send input and draw snapshots.
Formulas mirror index.html exactly; keep them in sync when tuning gameplay.
"""

import math
import random

W, H = 1000.0, 640.0
R = 27.0
TAU = math.pi * 2
BASE_ARENA = {"x": 76.0, "y": 70.0, "w": 848.0, "h": 500.0, "r": 70.0}
ZERO = {"throttle": 0.0, "steer": 0.0, "boost": False}

# Mirrors LAYOUTS in index.html so the ring-out edge is identical everywhere.
LAYOUT_SHAPES = {
    "woven": ("roundrect", 70.0),
    "quilt": ("pill", 250.0),
    "check": ("diamond", 70.0),
    "neon": ("octagon", 70.0),
}


def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def arena_rect(scale, shape="roundrect", corner=70.0):
    w = BASE_ARENA["w"] * scale
    h = BASE_ARENA["h"] * scale
    r = h / 2 if shape == "pill" else corner * scale
    return {"x": W / 2 - w / 2, "y": H / 2 - h / 2, "w": w, "h": h,
            "r": r, "shape": shape, "cx": W / 2, "cy": H / 2}


def sd_arena(px, py, B):
    """Signed distance to the chosen couch outline (negative = inside)."""
    shape = B.get("shape", "roundrect")
    cx, cy = B["x"] + B["w"] / 2, B["y"] + B["h"] / 2
    hx, hy = B["w"] / 2, B["h"] / 2
    dx, dy = abs(px - cx), abs(py - cy)
    if shape == "diamond":
        return (dx / hx + dy / hy - 1.0) * min(hx, hy) * 0.72
    if shape == "octagon":
        cut = min(hx, hy) * 0.42
        return max(dx - hx, dy - hy,
                   (dx + dy - (hx + hy - cut)) / math.sqrt(2.0))
    r = min(B["r"], hx, hy)
    qx, qy = dx - (hx - r), dy - (hy - r)
    return (math.hypot(max(qx, 0.0), max(qy, 0.0))
            + min(max(qx, qy), 0.0) - r)


def _car(i):
    return {
        "i": i, "type": i, "x": 0.0, "y": 0.0, "angle": 0.0,
        "vx": 0.0, "vy": 0.0, "hp": 100.0, "turbo": 100.0,
        "boosting": False, "prevBoost": False, "dash": 0.0,
        "flash": 0.0, "alive": True, "fallT": 0.0, "skidT": 0.0,
    }


class Game:
    def __init__(self, best_of=3, round_seconds=60):
        self.best_of = int(best_of)
        self.round_seconds = int(round_seconds)
        self.wins_needed = 2 if self.best_of == 3 else 3
        self.state = "countdown"
        self.paused = False
        self.skins = ["silver84", "redfang"]   # set by the relay from each phone's garage pick
        self.layout = "woven"
        self.shape, self.corner = LAYOUT_SHAPES["woven"]
        self.cars = [_car(0), _car(1)]
        self.scores = [0, 0]
        self.round = 1
        self.timer = float(self.round_seconds)
        self.countdown = 3.4
        self.sudden = False
        self.arena_scale = 1.0
        self.round_over_t = 0.0
        self.hit_cd = 0.0
        self.spawn_t = 5.5
        self.pickups = []
        self.match_winner = -1
        self.time = 0.0
        self.events = []
        self.last_count_label = ""
        self._place_cars()

    # ------------------------------------------------------------------ setup
    def _place_cars(self):
        start = [
            (352.0, 338.0, -0.10),
            (648.0, 302.0, math.pi + 0.10),
        ]
        for i, (x, y, a) in enumerate(start):
            self.cars[i].update(x=x, y=y, angle=a, vx=0.0, vy=0.0,
                                hp=100.0, turbo=100.0, boosting=False,
                                prevBoost=False, dash=0.0, flash=0.0,
                                alive=True, fallT=0.0, skidT=0.0)

    def reset_match(self):
        self.scores = [0, 0]
        self.round = 1
        self.match_winner = -1
        self.events = []
        self._start_round()

    def _start_round(self):
        self._place_cars()
        self.pickups = []
        self.timer = float(self.round_seconds)
        self.countdown = 3.4
        self.sudden = False
        self.arena_scale = 1.0
        self.round_over_t = 0.0
        self.hit_cd = 0.0
        self.spawn_t = 5.5
        self.state = "countdown"
        self.last_count_label = ""
        self.emit({"t": "roundStart", "round": self.round})

    def set_options(self, best_of, round_seconds):
        self.best_of = int(best_of)
        self.round_seconds = int(round_seconds)
        self.wins_needed = 2 if self.best_of == 3 else 3
        self.timer = min(self.timer, float(self.round_seconds))

    def set_layout(self, layout):
        self.layout = layout if layout in LAYOUT_SHAPES else "woven"
        self.shape, self.corner = LAYOUT_SHAPES[self.layout]

    def emit(self, e):
        self.events.append(e)

    # ------------------------------------------------------------------ tick
    def step(self, dt, inputs):
        self.time += dt
        self.hit_cd = max(0.0, self.hit_cd - dt)
        if self.paused or self.state == "matchover":
            return

        live = self.state == "live"
        ctl = inputs if live else [ZERO, ZERO]
        for i in (0, 1):
            self._step_car(self.cars[i], ctl[i], dt, live)
        self._resolve(live)

        if self.state == "countdown":
            label = ("3" if self.countdown > 2.3 else
                     "2" if self.countdown > 1.3 else
                     "1" if self.countdown > 0.3 else "GO")
            if label != self.last_count_label:
                self.last_count_label = label
                if label != "GO":
                    self.emit({"t": "count", "label": label})
            self.countdown -= dt
            if self.countdown <= 0:
                self.last_count_label = ""
                self.state = "live"
                self.emit({"t": "go"})

        elif self.state == "live":
            self.timer -= dt
            if self.timer <= 0:
                if not self.sudden:
                    self.sudden = True
                    self.emit({"t": "sudden"})
                elapsed = -self.timer
                self.arena_scale = max(0.70, 1.0 - elapsed / 20.0 * 0.30)
                for c in self.cars:
                    if c["alive"]:
                        c["hp"] = clamp(c["hp"] - 4.0 * dt, 0.0, 100.0)
            self._update_pickups(dt)
            self._check_round_end()

        elif self.state == "roundover":
            self.round_over_t -= dt
            if self.round_over_t <= 0:
                if (self.scores[0] >= self.wins_needed or
                        self.scores[1] >= self.wins_needed):
                    self._finish_match()
                else:
                    self.round += 1
                    self._start_round()

    # ------------------------------------------------------------------ physics
    def _step_car(self, c, ctl, dt, allow_boost):
        if not c["alive"]:
            c["fallT"] += dt
            return
        fx, fy = math.cos(c["angle"]), math.sin(c["angle"])
        vf = c["vx"] * fx + c["vy"] * fy
        vl = -c["vx"] * fy + c["vy"] * fx

        speed_factor = min(1.0, abs(vf) / 150.0)
        turn_rate = (0.9 + 1.75 * speed_factor) * (0.84 if c["boosting"] else 1.0)
        c["angle"] += ctl["steer"] * turn_rate * (-1.0 if vf < -12 else 1.0) * dt
        fx, fy = math.cos(c["angle"]), math.sin(c["angle"])

        want = allow_boost and bool(ctl["boost"]) and c["turbo"] > 3
        if want and not c["prevBoost"] and c["turbo"] > 22:
            c["turbo"] -= 16.0
            c["dash"] = 0.4
            c["vx"] += fx * 175.0
            c["vy"] += fy * 175.0
            self.emit({"t": "boost", "x": c["x"], "y": c["y"], "car": c["i"]})
        c["prevBoost"] = want
        c["boosting"] = want
        if want:
            c["turbo"] = max(0.0, c["turbo"] - 31.0 * dt)
        else:
            c["turbo"] = min(100.0, c["turbo"] + 11.0 * dt)
        c["dash"] = max(0.0, c["dash"] - dt)
        c["flash"] = max(0.0, c["flash"] - dt)

        accel = 0.0
        if ctl["throttle"] > 0:
            accel = 470.0 * ctl["throttle"]
        elif ctl["throttle"] < 0:
            accel = 300.0 * ctl["throttle"]
        if want and ctl["throttle"] >= 0:
            accel += 560.0
        vf += accel * dt
        vf *= math.exp(-(2.0 if ctl["throttle"] == 0 else 0.75) * dt)
        vf = clamp(vf, -190.0, 540.0 if want else 340.0)
        vl *= math.exp(-(3.4 if want else 7.5) * dt)

        c["vx"] = fx * vf - fy * vl
        c["vy"] = fy * vf + fx * vl
        c["x"] += c["vx"] * dt
        c["y"] += c["vy"] * dt

        c["skidT"] -= dt
        if (c["skidT"] <= 0 and (abs(vl) > 62 or want)
                and math.hypot(c["vx"], c["vy"]) > 110):
            c["skidT"] = 0.035

    def _resolve(self, do_damage):
        a, b = self.cars
        if not a["alive"] or not b["alive"]:
            return
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        d = math.hypot(dx, dy)
        if d < 0.001:
            dx, dy, d = 1.0, 0.0, 1.0
        min_d = R * 2
        if d >= min_d:
            return
        nx, ny = dx / d, dy / d
        overlap = min_d - d
        a["x"] -= nx * overlap / 2
        a["y"] -= ny * overlap / 2
        b["x"] += nx * overlap / 2
        b["y"] += ny * overlap / 2

        closing = -((b["vx"] - a["vx"]) * nx + (b["vy"] - a["vy"]) * ny)
        if closing <= 0:
            return
        j = 0.72 * closing
        a["vx"] -= nx * j
        a["vy"] -= ny * j
        b["vx"] += nx * j
        b["vy"] += ny * j
        if not do_damage or self.hit_cd > 0 or closing < 90:
            return
        self.hit_cd = 0.32

        afx, afy = math.cos(a["angle"]), math.sin(a["angle"])
        bfx, bfy = math.cos(b["angle"]), math.sin(b["angle"])
        aF = afx * nx + afy * ny
        bF = bfx * nx + bfy * ny
        atkA = (0.35 + 0.95 * max(0.0, aF)
                + (0.45 if a["dash"] > 0 else 0.0)
                + (0.2 if a["boosting"] else 0.0))
        atkB = (0.35 + 0.95 * max(0.0, -bF)
                + (0.45 if b["dash"] > 0 else 0.0)
                + (0.2 if b["boosting"] else 0.0))
        vulB = max(0.45, 0.70 + 0.75 * max(0.0, bF)
                   + 0.35 * (1 - abs(bF)) - 0.20 * max(0.0, -bF))
        vulA = max(0.45, 0.70 + 0.75 * max(0.0, -aF)
                   + 0.35 * (1 - abs(aF)) - 0.20 * max(0.0, aF))
        base = (closing - 75) * 0.095
        dB = base * atkA * vulB
        dA = base * atkB * vulA
        a["hp"] = clamp(a["hp"] - dA, 0.0, 100.0)
        b["hp"] = clamp(b["hp"] - dB, 0.0, 100.0)
        a["flash"] = 0.17
        b["flash"] = 0.17
        hx, hy = (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2
        self.emit({"t": "hit", "x": hx, "y": hy, "power": closing,
                   "dA": dA, "dB": dB})

    def _fall(self, c):
        c["alive"] = False
        c["fallT"] = 0.0
        self.emit({"t": "fall", "x": c["x"], "y": c["y"], "car": c["i"]})

    def _check_round_end(self):
        if self.state != "live":
            return
        B = arena_rect(self.arena_scale, self.shape, self.corner)
        outA = self.cars[0]["alive"] and sd_arena(self.cars[0]["x"], self.cars[0]["y"], B) > -1
        outB = self.cars[1]["alive"] and sd_arena(self.cars[1]["x"], self.cars[1]["y"], B) > -1
        if outA or outB:
            if outA:
                self._fall(self.cars[0])
            if outB:
                self._fall(self.cars[1])
            win = ((0 if self.cars[0]["hp"] >= self.cars[1]["hp"] else 1)
                   if (outA and outB) else (1 if outA else 0))
            self._end_round(win, "DOUBLE RING-OUT!" if (outA and outB) else "RING-OUT!")
            return
        if self.cars[0]["hp"] <= 0 or self.cars[1]["hp"] <= 0:
            if self.cars[0]["hp"] <= 0 and self.cars[1]["hp"] <= 0:
                win = 0 if self.cars[0]["hp"] >= self.cars[1]["hp"] else 1
            else:
                win = 1 if self.cars[0]["hp"] <= 0 else 0
            self._end_round(win, "KNOCKOUT!")

    def _end_round(self, win, reason):
        self.scores[win] += 1
        self.round_over_t = 2.9
        self.state = "roundover"
        self.emit({"t": "roundEnd", "win": win, "reason": reason,
                   "round": self.round, "scores": list(self.scores)})

    def _finish_match(self):
        self.match_winner = 0 if self.scores[0] > self.scores[1] else 1
        self.state = "matchover"
        self.emit({"t": "matchEnd", "win": self.match_winner,
                   "scores": list(self.scores)})

    # ------------------------------------------------------------------ pickups
    def _spawn_pickup(self):
        B = arena_rect(self.arena_scale, self.shape, self.corner)
        for _ in range(40):
            x = B["x"] + 70 + random.random() * (B["w"] - 140)
            y = B["y"] + 70 + random.random() * (B["h"] - 140)
            if (sd_arena(x, y, B) < -80
                    and all(math.hypot(c["x"] - x, c["y"] - y) > 130 for c in self.cars)):
                self.pickups.append({"x": x, "y": y,
                                     "t": random.random() * 6, "life": 14.0})
                return

    def _update_pickups(self, dt):
        self.spawn_t -= dt
        if self.spawn_t <= 0 and len(self.pickups) < 2:
            self._spawn_pickup()
            self.spawn_t = 8 + random.random() * 4
        for p in self.pickups:
            p["t"] += dt
            p["life"] -= dt
            for c in self.cars:
                if not c["alive"]:
                    continue
                if math.hypot(c["x"] - p["x"], c["y"] - p["y"]) < 34:
                    c["turbo"] = min(100.0, c["turbo"] + 45.0)
                    c["hp"] = min(100.0, c["hp"] + 8.0)
                    self.emit({"t": "pickup", "x": p["x"], "y": p["y"], "car": c["i"]})
                    p["life"] = -1
                    break
        self.pickups = [p for p in self.pickups if p["life"] > 0]

    # ------------------------------------------------------------------ output
    def snapshot(self):
        return {
            "state": self.state,
            "paused": self.paused,
            "bestOf": self.best_of,
            "roundSeconds": self.round_seconds,
            "winsNeeded": self.wins_needed,
            "cars": [{
                "i": c["i"], "type": c["type"], "x": c["x"], "y": c["y"],
                "angle": c["angle"], "vx": c["vx"], "vy": c["vy"],
                "hp": c["hp"], "turbo": c["turbo"], "boosting": c["boosting"],
                "prevBoost": c["prevBoost"], "dash": c["dash"], "flash": c["flash"],
                "alive": c["alive"], "fallT": c["fallT"], "skidT": c["skidT"],
            } for c in self.cars],
            "pickups": [dict(p) for p in self.pickups],
            "timer": self.timer,
            "countdown": self.countdown,
            "sudden": self.sudden,
            "arenaScale": self.arena_scale,
            "scores": list(self.scores),
            "round": self.round,
            "matchWinner": self.match_winner,
            "roundOverT": self.round_over_t,
            "skins": list(self.skins),
            "layout": self.layout,
            "shape": self.shape,
            "corner": self.corner,
            "hitCd": self.hit_cd,
            "spawnT": self.spawn_t,
        }

    def drain_events(self):
        e = self.events
        self.events = []
        return e
