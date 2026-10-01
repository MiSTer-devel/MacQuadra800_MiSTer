#!/usr/bin/env python3
"""Closed-loop pointer placement for the Mac guest.

    python pointer.py find  [png]       # print the arrow's hotspot
    python pointer.py goto X Y          # move until the hotspot is within 2 px
    python pointer.py click X Y         # goto, then one click
    python pointer.py dbl X Y           # goto, then double-click

Finds the standard arrow cursor (CURS 0, hotspot 1,1) by its black data
pixels and white mask-only pixels, then corrects with small relative moves
(Mac OS accelerates large ones).  Ends every call with mousebtn:left_up.
"""
import asyncio, os, subprocess, sys, time
import numpy as np
from PIL import Image
import websockets

HOST = os.environ.get("MISTER_HOST", "192.168.99.143")
PORT = int(os.environ.get("MISTER_HTTP_PORT", "8182"))
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, "..", ".."))

DATA = [0x0000, 0x4000, 0x6000, 0x7000, 0x7800, 0x7C00, 0x7E00, 0x7F00,
        0x7F80, 0x7C00, 0x6C00, 0x4600, 0x0600, 0x0300, 0x0300, 0x0000]
MASK = [0xC000, 0xE000, 0xF000, 0xF800, 0xFC00, 0xFE00, 0xFF00, 0xFF80,
        0xFFC0, 0xFFE0, 0xFE00, 0xEF00, 0xCF00, 0x8780, 0x0780, 0x0380]
BLK = [(r, c) for r in range(16) for c in range(16) if DATA[r] >> (15 - c) & 1]
WHT = [(r, c) for r in range(16) for c in range(16)
       if (MASK[r] >> (15 - c) & 1) and not (DATA[r] >> (15 - c) & 1)]


def grab(path):
    rel = os.path.relpath(path, REPO).replace(os.sep, "/")
    subprocess.run(["C:/Program Files/Git/bin/bash.exe", "scripts/grab.sh", rel], cwd=REPO,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path


def _match(black, white):
    h, w = black.shape
    H, W = h - 16, w - 16
    cand = np.ones((H, W), bool)
    for r, c in BLK:
        cand &= black[r:r + H, c:c + W]
        if not cand.any():
            return None
    sc = np.zeros((H, W), int)
    for r, c in WHT:
        sc += white[r:r + H, c:c + W]
    sc = np.where(cand, sc, -1)
    y, x = np.unravel_index(np.argmax(sc), sc.shape)
    if sc[y, x] >= len(WHT) - 6:
        return (x + 1, y + 1)
    return None


def find(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    s = a.sum(axis=2)
    black = s < 60
    white = s > 700
    return _match(black, white) or _match(white, black)


async def ws_do(msgs):
    async with websockets.connect(f"ws://{HOST}:{PORT}/api/ws") as ws:
        try:
            for m, d in msgs:
                await ws.send(m)
                await asyncio.sleep(d)
        finally:
            await ws.send("mouseBtn:left_up")
            await asyncio.sleep(0.1)


def nudge(dx, dy):
    msgs = []
    while dx or dy:
        sx = max(-2, min(2, dx)); sy = max(-2, min(2, dy))
        msgs.append((f"mouseMove:{sx},{sy}", 0.05))
        dx -= sx; dy -= sy
    asyncio.run(ws_do(msgs))


def goto(x, y, tries=20):
    tmp = os.path.join(REPO, "scratch", "_ptr.png")
    for _ in range(tries):
        p = find(grab(tmp))
        if p is None:
            nudge(-20, 20)
            continue
        dx, dy = x - p[0], y - p[1]
        print('  seen', p, 'delta', dx, dy, flush=True)
        if abs(dx) <= 2 and abs(dy) <= 2:
            return p
        # big distances: a fraction, so acceleration cannot overshoot
        k = 0.5 if max(abs(dx), abs(dy)) > 4 else 0.7
        nudge(int(dx * k), int(dy * k))
    return find(grab(tmp))


if __name__ == "__main__":
    op = sys.argv[1]
    if op == "find":
        print(find(sys.argv[2] if len(sys.argv) > 2 else grab(os.path.join(REPO, "scratch", "_ptr.png"))))
    elif op in ("goto", "click", "dbl"):
        x, y = int(sys.argv[2]), int(sys.argv[3])
        p = goto(x, y)
        print("at", p)
        if op != "goto":
            n = 2 if op == "dbl" else 1
            msgs = []
            for _ in range(n):
                msgs += [("mouseBtn:left_down", 0.07), ("mouseBtn:left_up", 0.10)]
            asyncio.run(ws_do(msgs))
