#!/usr/bin/env python3
# vk_probe.py -- on a load with the scaler fault, where did the header burst go?
# The scaler writes its 16-byte header (type 01, fmt 01, ..., w, h) as beat 0 of
# the burst at offset 0 of each of its three 8 MB buffers.  When the HPS port's
# write data runs k beats (16 bytes each) ahead of its commands, that beat lands
# in the tail of the burst written just before it in time -- the last burst of
# the previous frame, at 0x100 + 479*0x800 + 7*0x100 = 0xF0000 for 640x480x24 --
# at byte offset (16-k)*16.  Print k for each buffer.  Read-only.
import mmap, os, sys
fd = os.open('/dev/mem', os.O_RDONLY | os.O_SYNC)
m = mmap.mmap(fd, 0x1800000, mmap.MAP_SHARED, mmap.PROT_READ, offset=0x20000000)
def hdr(b):
    return b[0] == 1 and b[1] == 1 and (b[6] << 8 | b[7]) == 640 and (b[8] << 8 | b[9]) == 480
for buf in range(3):
    base = buf * 0x800000
    h = m[base:base + 16]
    line = 'buf%d header slot: %s  %s' % (buf, h.hex(), 'VALID' if hdr(h) else 'invalid')
    found = []
    # the whole last line and the slot itself, in 16-byte beats
    for off in list(range(0xF0000 - 0x800, 0xF0100, 16)) + list(range(0, 0x100, 16)):
        if hdr(m[base + off:base + off + 16]):
            found.append(off)
    for off in found:
        if off >= 0xF0000:
            line += '  header beat at 0x%X -> k = %d beats (%d bytes) early' % (off, 16 - (off - 0xF0000) // 16, (16 - (off - 0xF0000) // 16) * 16)
        elif off:
            line += '  header beat at 0x%X' % off
    if not found:
        line += '  header beat not found near the frame tail'
    print(line)
