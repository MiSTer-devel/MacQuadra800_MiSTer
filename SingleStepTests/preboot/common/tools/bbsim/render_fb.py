#!/usr/bin/env python3
"""render_fb.py — turn bbsim's fb_dump.bin into a PNG you can look at.

The boot block and the payload entry shim paint straight into the
framebuffer, so the only honest check that a paint change is correct is
to look at the pixels. bbsim writes the simulated framebuffer to
fb_dump.bin; this renders it.

    ./render_fb.py fb_dump.bin out.png --stride 1024 --bpp 8
    ./render_fb.py fb_dump.bin out.png --stride 80   --bpp 1

Polarity matches display_1bpp.c: 8 bpp index 0 = white stroke, 0xFF =
black background; 1 bpp 0-bits = white stroke.
"""
import argparse, struct, zlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump"); ap.add_argument("out")
    ap.add_argument("--stride", type=int, default=1024)
    ap.add_argument("--bpp", type=int, choices=(1, 8), default=8)
    ap.add_argument("--rows", type=int, default=72)
    ap.add_argument("--width", type=int, default=480, help="pixels to show")
    ap.add_argument("--scale", type=int, default=2)
    a = ap.parse_args()

    fb = open(a.dump, "rb").read()
    lines = []
    for r in range(a.rows):
        row = fb[r * a.stride:(r + 1) * a.stride]
        if a.bpp == 8:
            px = [255 - b for b in row[:a.width]]
        else:
            px = []
            for b in row[:(a.width + 7) // 8]:
                px += [0 if (b >> (7 - i)) & 1 else 255 for i in range(8)]
            px = px[:a.width]
        line = bytes(v for p in px for v in (p,) * a.scale)
        lines += [line] * a.scale

    w, h = len(lines[0]), len(lines)
    raw = b"".join(b"\x00" + ln for ln in lines)

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    open(a.out, "wb").write(png)
    print(f"wrote {a.out} ({w}x{h})")


if __name__ == "__main__":
    main()
