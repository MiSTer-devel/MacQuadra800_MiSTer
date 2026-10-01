#!/usr/bin/env python3
"""Blind button press for a hidden cursor: home to (0,0), step (nx, ny) 2-px
reports, press, and only release on the target if its rectangle lights up.
    probe_click.py X0 Y0 X1 Y1 [gain]
"""
import asyncio, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pointer as P

x0, y0, x1, y1 = [int(v) for v in sys.argv[1:5]]
g = float(sys.argv[5]) if len(sys.argv) > 5 else 1.6
cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
img = os.path.join(P.REPO, "scratch", "_probe.png")


def bright():
    a = np.asarray(Image.open(P.grab(img)).convert("L")).astype(int)
    return a[y0 + 3:y1 - 3, x0 + 6:x1 - 6].mean()


async def ws(msgs, release=True):
    import websockets
    async with websockets.connect(f"ws://{P.HOST}:{P.PORT}/api/ws") as w:
        for m, d in msgs:
            await w.send(m); await asyncio.sleep(d)
        if release:
            await w.send("mouseBtn:left_up"); await asyncio.sleep(0.1)


def go(nx, ny):
    msgs = [("mouseMove:-40,-40", 0.05)] * 24 + [("mouseMove:0,0", 0.2)]
    for i in range(max(nx, ny)):
        msgs.append((f"mouseMove:{2 if i < nx else 0},{2 if i < ny else 0}", 0.05))
    asyncio.run(ws(msgs, release=False))


base = bright()
print("button brightness at rest %.1f" % base)
cands = []
for gg in (g, g * 0.9, g * 1.1, g * 0.8, g * 1.2, g * 0.7, g * 1.3):
    cands.append((round(cx / (2 * gg)), round(cy / (2 * gg))))
for nx, ny in cands:
    go(nx, ny)
    asyncio.run(ws([("mouseBtn:left_down", 0.4)], release=False))
    b = bright()
    hit = b > base + 40
    print("probe nx=%d ny=%d brightness %.1f %s" % (nx, ny, b, "HIT" if hit else ""))
    if hit:
        asyncio.run(ws([("mouseBtn:left_up", 0.3)]))
        sys.exit(0)
    # not on the target: slide to the screen corner before releasing
    asyncio.run(ws([("mouseMove:-40,-40", 0.05)] * 20 + [("mouseBtn:left_up", 0.2)]))
sys.exit("no hit")
