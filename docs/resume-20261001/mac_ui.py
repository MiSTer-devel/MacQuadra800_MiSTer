#!/usr/bin/env python3
"""Tiny absolute-position mouse/keyboard driver over the mrext websocket.

    python mac_ui.py goto X Y            # home to (0,0), then step to X,Y
    python mac_ui.py click X Y | dbl X Y
    python mac_ui.py rel DX DY
    python mac_ui.py keys raw:28 ...      # passthrough of mister_ws forms
    python mac_ui.py release              # mousebtn:left_up

Moves go in steps of <= 8 px with a short gap so Mac OS applies no
acceleration.  Every invocation ends with an explicit left_up.
"""
import asyncio, os, sys
import websockets

HOST = os.environ.get("MISTER_HOST", "192.168.99.143")
PORT = int(os.environ.get("MISTER_HTTP_PORT", "8182"))
STEP = 40


async def run(cmds):
    async with websockets.connect(f"ws://{HOST}:{PORT}/api/ws") as ws:
        async def send(p, d=0.012):
            await ws.send(p)
            await asyncio.sleep(d)

        async def move(dx, dy):
            while dx or dy:
                sx = max(-STEP, min(STEP, dx))
                sy = max(-STEP, min(STEP, dy))
                await send(f"mouseMove:{sx},{sy}", 0.05)
                dx -= sx
                dy -= sy

        async def home():
            for _ in range(24):
                await send("mouseMove:-40,-40", 0.05)
            await asyncio.sleep(0.15)

        try:
            for c in cmds:
                op = c[0]
                if op == "goto":
                    await home(); await move(int(c[1]), int(c[2]))
                elif op == "rel":
                    await move(int(c[1]), int(c[2]))
                elif op in ("click", "dbl"):
                    await home(); await move(int(c[1]), int(c[2]))
                    await asyncio.sleep(0.2)
                    n = 2 if op == "dbl" else 1
                    for _ in range(n):
                        await send("mouseBtn:left_down", 0.07)
                        await send("mouseBtn:left_up", 0.10)
                elif op == "down":
                    await send("mouseBtn:left_down", 0.2)
                elif op == "up":
                    await send("mouseBtn:left_up", 0.2)
                elif op == "key":
                    for k in c[1:]:
                        pfx, code = k.split(":", 1)
                        if pfx == "sleep":
                            await asyncio.sleep(float(code)); continue
                        await send({"raw": "kbdRaw", "down": "kbdRawDown",
                                    "up": "kbdRawUp"}[pfx] + ":" + code, 0.12)
                elif op == "sleep":
                    await asyncio.sleep(float(c[1]))
                elif op == "release":
                    pass
        finally:
            await ws.send("mouseBtn:left_up")
            await asyncio.sleep(0.1)


def parse(argv):
    cmds, cur = [], []
    for a in argv:
        if a == "--":
            if cur: cmds.append(cur)
            cur = []
        else:
            cur.append(a)
    if cur: cmds.append(cur)
    return cmds


if __name__ == "__main__":
    asyncio.run(run(parse(sys.argv[1:])))
