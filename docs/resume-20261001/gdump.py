#!/usr/bin/env python3
# Read guest RAM through the SONIC mailbox's DMA engine (dir 0: guest -> XFER).
# Never writes guest memory.  Needs OSD Ethernet = On and Main's Q8 service up.
#   gdump.py ADDR LEN OUTFILE        (hex ADDR/LEN; LEN may exceed 16 KiB)
import mmap, os, struct, sys, time
BASE = 0x1FF00000
CTL = 0x4000
W = lambda i: i * 8                      # 64-bit word index -> byte offset
OFF_MAGIC, OFF_CMD, OFF_STAT, OFF_OPS = W(0x800), W(0x817), W(0x818), W(0x820)
CHUNK = 0x3F00

addr = int(sys.argv[1], 16); total = int(sys.argv[2], 16); out = sys.argv[3]
fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
m = mmap.mmap(fd, 0x5000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=BASE)
assert m[OFF_MAGIC:OFF_MAGIC + 8] == struct.pack("<Q", 0x4D63513845544834), "no mailbox"
# Main's own seq: the cmd byte, unless it is one this tool wrote last time
LOG = "/tmp/gdump.seq"
try: mine_last, main_seq = [int(x, 16) for x in open(LOG).read().split()]
except Exception: mine_last, main_seq = -1, None
if m[OFF_CMD] != mine_last: main_seq = m[OFF_CMD]
seq = (m[OFF_CMD] + 1) & 0xFF   # never the seq the FPGA last completed
buf = bytearray()
a = addr & ~3
end = (addr + total + 3) & ~3
while a < end:
    n = min(CHUNK, end - a)
    if m[OFF_STAT] != m[OFF_CMD]:
        time.sleep(0.05)                 # Main's own DMA in flight: let it finish
        continue
    op = (a << 32) | (n << 16) | 0      # dir 0: guest -> XFER
    m[OFF_OPS:OFF_OPS + 8] = struct.pack("<Q", op)
    assert m[OFF_OPS:OFF_OPS + 8] == struct.pack("<Q", op)
    while seq == 0 or seq == m[OFF_STAT] or ((seq - main_seq) & 0xFF) <= 16:
        seq = (seq + 1) & 0xFF
    m[OFF_CMD + 1:OFF_CMD + 8] = struct.pack("<Q", 1 << 8)[1:]   # count first
    m[OFF_CMD] = seq                                              # seq last
    t0 = time.time()
    while m[OFF_STAT] != seq:
        if time.time() - t0 > 1.0:
            sys.exit("timeout at %08x (stat %02x cmd %02x)" % (a, m[OFF_STAT], m[OFF_CMD]))
    buf += m[0:n]
    a += n
    seq = (seq + 1) & 0xFF or 1
open(LOG, "w").write("%x %x" % ((seq - 1) & 0xFF or 0xFF, main_seq))
open(out, "wb").write(bytes(buf[addr - (addr & ~3):][:total]))
print("dumped %08x+%x -> %s (main seq %02x, last mine %02x)" % (addr, total, out, main_seq, (seq - 1) & 0xFF))
