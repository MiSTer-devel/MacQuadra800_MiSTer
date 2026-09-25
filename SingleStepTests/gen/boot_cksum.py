#!/usr/bin/env python3
"""Compute the boot block's expected 'C' row for a bench disk image.

Usage: boot_cksum.py <image> [image...]

Reads the image's own patched markers: PAYLDOFF (partition-relative
/Payload offset) and PAYLCKSZ (checksum window length), resolves the
HFS partition base (APM scan for .hda; 0 for floppies), and reproduces
the boot block's rotating 32-bit sum over the window. The printed value
must match the 'C' line the boot block paints, on every boot.
"""
import struct
import sys


def hfs_partition_base(data: bytes) -> int:
    if data[1024:1026] != b"BD" and data[512:514] == b"PM":
        n = struct.unpack(">I", data[516:520])[0]
        for i in range(n):
            e = 512 * (1 + i)
            if data[e:e + 2] != b"PM":
                break
            ptype = data[e + 48:e + 80].split(b"\x00")[0]
            if ptype == b"Apple_HFS":
                return struct.unpack(">I", data[e + 8:e + 12])[0] * 512
    return 0  # floppy / bare HFS volume


def cksum(image: str) -> str:
    with open(image, "rb") as f:
        data = f.read()
    base = hfs_partition_base(data)
    p = data.find(b"PAYLDOFF")
    c = data.find(b"PAYLCKSZ")
    if p < 0 or c < 0:
        return "no boot-stub markers"
    payload_off = struct.unpack(">I", data[p + 8:p + 12])[0]
    ck_len = struct.unpack(">I", data[c + 8:c + 12])[0]
    if payload_off == 0xDEADBEEF:
        return "PAYLDOFF unpatched"
    s = 0
    win = data[base + payload_off:base + payload_off + ck_len]
    for (v,) in struct.iter_unpack(">I", win):
        s = (s + v) & 0xFFFFFFFF
        s = ((s << 1) | (s >> 31)) & 0xFFFFFFFF
    return f"{s:08X}  (payload@0x{payload_off:X}+0x{base:X}, window 0x{ck_len:X})"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip())
    for img in sys.argv[1:]:
        print(f"{img}: {cksum(img)}")
