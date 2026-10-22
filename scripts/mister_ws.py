#!/usr/bin/env python3
"""Send kbd:* commands to the MiSTer Remote websocket.

Usage:
    python scripts/mister_ws.py up down confirm        # send each in order, with default delay
    python scripts/mister_ws.py --delay 0.6 osd        # custom delay before close
    python scripts/mister_ws.py --host my-mister.local osd
    python3 scripts/mister_ws.py --host my-mister.local --interactive

Interactive mode (POSIX) reads the same tokens from stdin, one per line, while keeping
one websocket open. This lets an operator verify screenshots between a mouse
press, drag and release. On exit it explicitly releases the left button.

Each positional argument is sent as "kbd:<arg>". Special forms:
    sleep:0.5     -> wait that many seconds
    mouse:3,0     -> mouseMove:3,0    relative mouse motion (dx,dy)
    mousebtn:1    -> mouseBtn:1       mouse button state
    raw:42        -> kbdRaw:42      press+release a RAW LINUX KEYCODE
    down:42       -> kbdRawDown:42  press and HOLD (no release)
    up:42         -> kbdRawUp:42    release a held key

Holding matters for Mac boot testing: classic Mac OS samples the shift key
while the System loads its extensions, so "Extensions Off" needs shift held
DOWN across the whole splash, which a tap can't do. Left shift is keycode 42:

    python scripts/mister_ws.py down:42 sleep:90 up:42

Careful: a held key stays held on the MiSTer until you send the matching
up:<code> (or reload the core), so always pair them.

Modifiers, as this core's ADB keyboard maps them (rtl/adb.sv, PS/2 set 2 ->
ADB):
    Command  Left Alt  56   (PS/2 0x11 -> ADB $37, adb.sv:530; Right Alt 100 too)
    Option   Left Meta 125  (PS/2 E0 1F -> ADB $3A, adb.sv:800)
    Control  Left Ctrl 29,  Shift  Left Shift 42
Command is 56, NOT 125: "cmd-W" sent with 125 holds Option instead and the W
lands in the Finder's type-select. Close the front window with

    python scripts/mister_ws.py down:56 raw:17 up:56

The default host/port come from the MISTER_HOST / MISTER_HTTP_PORT
environment variables (set those in scripts/local.env or your shell
profile). Falls back to MiSTer.local : 8182 if neither is set. The helper
scripts source scripts/local.env themselves; a bare call from a fresh shell
needs `. scripts/local.env` first, MISTER_HOST=<ip> in front of it, or --host.
"""
import asyncio, sys, os, argparse, json, signal
import websockets

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host",
                    default=os.environ.get("MISTER_HOST", "MiSTer.local"))
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("MISTER_HTTP_PORT", "8182")))
    ap.add_argument("--delay", type=float, default=0.35,
                    help="delay between key sends (seconds)")
    ap.add_argument("--interactive", action="store_true",
                    help="keep the websocket open and read one token per stdin line; release left mouse on exit")
    ap.add_argument("keys", nargs="*")
    args = ap.parse_args()
    if not args.keys and not args.interactive:
        ap.error("supply at least one command or --interactive")
    if args.interactive and os.name != "posix":
        ap.error("--interactive requires a POSIX terminal or pipe")

    url = f"ws://{args.host}:{args.port}/api/ws"
    async with websockets.connect(url) as ws:
        # drain a couple of initial server messages
        try:
            for _ in range(2):
                msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                print(f"<< {msg}")
        except asyncio.TimeoutError:
            pass

        async def send(k):
            if k.startswith("sleep:"):
                await asyncio.sleep(float(k.split(":", 1)[1]))
                return
            if k.startswith(("raw:", "down:", "up:")):
                pfx, code = k.split(":", 1)
                payload = {"raw": "kbdRaw", "down": "kbdRawDown",
                           "up": "kbdRawUp"}[pfx] + ":" + code
            elif k.startswith("mouse:"):
                payload = "mouseMove:" + k.split(":", 1)[1]
            elif k.startswith("mousebtn:"):
                payload = "mouseBtn:" + k.split(":", 1)[1]
            else:
                payload = f"kbd:{k}"
            print(f">> {payload}", flush=True)
            await ws.send(payload)
            await asyncio.sleep(args.delay)

        try:
            for k in args.keys:
                await send(k)
            if args.interactive:
                print("Ready: one command per line; EOF releases left mouse and exits.", flush=True)
                loop = asyncio.get_running_loop()
                reader = asyncio.StreamReader()
                transport, _ = await loop.connect_read_pipe(
                    lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
                task = asyncio.current_task()
                for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                    loop.add_signal_handler(sig, task.cancel)
                try:
                    while True:
                        line = await reader.readline()
                        if not line:
                            break
                        k = line.decode().strip()
                        if k and not k.startswith("#"):
                            await send(k)
                finally:
                    transport.close()
                    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                        loop.remove_signal_handler(sig)
        finally:
            if args.interactive:
                await ws.send("mouseBtn:left_up")

        # drain any final replies
        try:
            for _ in range(3):
                msg = await asyncio.wait_for(ws.recv(), timeout=0.3)
                print(f"<< {msg}")
        except asyncio.TimeoutError:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        sys.exit(130)
