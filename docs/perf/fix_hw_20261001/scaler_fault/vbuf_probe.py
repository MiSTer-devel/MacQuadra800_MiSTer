#!/usr/bin/env python3
# vbuf_probe.py <seconds> -- is the scaler's DDR3 write port alive?
# Writes a marker word into each of ascal's three frame buffers (line 0 and
# line 256 of a 640x480 24-bit frame: offset 0x100 + n*0x800) and checks
# 0.25 s later whether the scaler has overwritten it.  The scaler rewrites
# every buffer every third frame (~50 ms), so a live port clears all six.
# Also prints the header's type byte and frame counter.  Run on the MiSTer.
import mmap, os, sys, time, struct
secs = int(sys.argv[1]) if len(sys.argv) > 1 else 30
fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
m = mmap.mmap(fd, 0x1800000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=0x20000000)
MARK = 0x5A5AA5A5
offs = [b * 0x800000 + o for b in range(3) for o in (0x100, 0x100 + 256 * 0x800)]
t0 = time.time()
while time.time() - t0 < secs:
    for o in offs:
        m[o:o+4] = struct.pack('<I', MARK)
    time.sleep(0.25)
    left = sum(1 for o in offs if struct.unpack('<I', m[o:o+4])[0] == MARK)
    hdr = m[0:16]
    print('%5.1fs markers left %d/6  hdr type=%02x fmt=%02x attr=%02x%02x w=%d h=%d' % (
        time.time() - t0, left, hdr[0], hdr[1], hdr[4], hdr[5],
        hdr[6] << 8 | hdr[7], hdr[8] << 8 | hdr[9]), flush=True)
    time.sleep(0.75)
