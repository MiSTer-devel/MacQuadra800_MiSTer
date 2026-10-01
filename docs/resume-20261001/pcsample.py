#!/usr/bin/env python3
# Sample the guest CPU's {SR, PC} from the SONIC mailbox's SAMPLE word
# (DDR3 window 0x1FF00000, 64-bit word $81A; needs OSD Ethernet = On).
# Read-only.  usage: pcsample.py [seconds] [top-N]
import mmap, os, struct, sys, time, collections
secs = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
topn = int(sys.argv[2]) if len(sys.argv) > 2 else 40
fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
m = mmap.mmap(fd, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ, offset=0x1FF04000)
assert m[0:8] == struct.pack("<Q", 0x4D63513845544834), "no mailbox magic (Ethernet off?)"
off = 0x81A * 8 - 0x4000
h = collections.Counter()
sr = collections.Counter()
last = None; n = 0; changes = 0
t_end = time.time() + secs
while time.time() < t_end:
    lo, hi = struct.unpack_from("<II", m, off)
    pc = lo; s = hi & 0xFFFF
    n += 1
    if (pc, s) != last:
        changes += 1
        h[pc] += 1
        sr[s] += 1
        last = (pc, s)
print("reads %d, distinct-sample updates %d" % (n, changes))
print("SR:", ", ".join("%04x:%d" % kv for kv in sr.most_common(8)))
for pc, c in h.most_common(topn):
    print("%08x %6d" % (pc, c))
