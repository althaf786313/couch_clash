#!/usr/bin/env python3
"""Self-healing public relay.

Cloudflare quick tunnels are invalidated whenever the sandbox sleeps. cloudflared
then loops forever on `Unauthorized: Tunnel not found`. This supervisor restarts
it, and keeps PUBLIC-LINK.txt / PLAY-ON-PHONE.png / README.md pointing at the
CURRENT url. Run it as a long-lived process instead of raw cloudflared.
"""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "vendor"))

URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

CMD = ["/tmp/cloudflared", "tunnel",
       "--url", "http://127.0.0.1:8000",
       "--no-autoupdate", "--metrics", "[::1]:8000"]
if not os.path.exists("/tmp/cloudflared"):
    CMD[0] = "cloudflared"


def publish(url):
    """Keep every link artifact in sync with the live tunnel."""
    full = url.rstrip("/") + "/"
    with open(os.path.join(ROOT, "PUBLIC-LINK.txt"), "w") as f:
        f.write(full + "\n")
    try:
        import segno
        segno.make(full, error="m").save(
            os.path.join(ROOT, "PLAY-ON-PHONE.png"), scale=10, border=3,
            dark="#141414", light="#f5efe2")
    except Exception as exc:
        print("QR update failed:", exc, flush=True)
    plain = full.rstrip("/")
    for rel, pattern in (("README.md", r"\*\*https://[a-z0-9-]+\.trycloudflare\.com/\*\*"),
                         ("tests/public-relay.py", r"https://[a-z0-9-]+\.trycloudflare\.com")):
        try:
            p = os.path.join(ROOT, rel)
            text = open(p).read()
            repl = "**" + full + "**" if rel.endswith(".md") else plain
            open(p, "w").write(re.sub(pattern, repl, text))
        except Exception as exc:
            print(rel, "update failed:", exc, flush=True)
    print("=== CURRENT PUBLIC LINK: " + full + " ===", flush=True)


def run_once():
    proc = subprocess.Popen(CMD, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    seen = False
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if ("trycloudflare.com" in line or "ERR" in line
                    or "Registered tunnel" in line or "Metrics server" in line):
                print(line, flush=True)
            m = URL_RE.search(line)
            if m and not seen:
                seen = True
                publish(m.group(0))
            if "Tunnel not found" in line or "no more connections active" in line:
                print("Relay expired -> restarting cloudflared", flush=True)
                proc.terminate()
                break
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
    return


def main():
    while True:
        try:
            run_once()
        except Exception as exc:
            print("Supervisor error:", exc, flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
