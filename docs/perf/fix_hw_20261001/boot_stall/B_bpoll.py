#!/usr/bin/env python3
"""Brief B boot watcher -- runs ON the MiSTer (copied to /tmp/B_bpoll.py).
Read-only toward the guest (gdump.py / pcsample.py only).

usage: python3 -u /tmp/B_bpoll.py CYCLE RBF

  Writes `load_core RBF` to /dev/MiSTer_cmd; T0 = the box clock at that write.
  From T0+40 s, every 5 s: Ticks ($16A, gdump 16A 4) and Main's write_bytes.
  Stall = Ticks seen above $40, then unchanged on 4 consecutive reads (20 s):
    pcsample 3 12 and /proc/tty/driver/serial once; ~60 s into the stall the
    small serial-driver reads (each <= $200 bytes, RAM only) into
    /tmp/B_stall_CYCLE.txt with Ticks before/after; otherwise watch only.
  Ends with a line `END <status>`:
    BOOT_DONE  the host touched /tmp/B_finder (a screenshot showed the Finder)
               and the last 5 reads advance at 50..70 ticks/s (20 s)
    HUNG       a stall not over 8 min after detection (second pcsample taken)
    TIMEOUT    no BOOT_DONE within 480 s (no stall) / stall-detect + 510 s
"""
import os
import subprocess
import sys
import time

CYC, RBF = sys.argv[1], sys.argv[2]
FLAG = "/tmp/B_finder"
STALLF = "/tmp/B_stall_%s.txt" % CYC
BASE_MAX = 480.0
HUNG_AFTER = 480.0
RAM_END = 0x08000000          # 128 MB (CFG $50): never DMA-read outside RAM
PLAUSIBLE = 0x00100000        # Ticks below this are real (RAM test leaves b6db6db6/6db6db6d)
T0 = 0.0


def now():
    return time.time()


def out(s):
    t = now()
    for line in str(s).rstrip("\n").split("\n"):
        print("%s t+%6.1f %s" % (time.strftime("%H:%M:%S", time.localtime(t)), t - T0, line), flush=True)


def sh(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return r.returncode, r.stdout.decode("latin-1")
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT after %ss" % timeout


def wb():
    try:
        pid = subprocess.check_output(["pidof", "MiSTer"]).split()[0].decode()
        for line in open("/proc/%s/io" % pid):
            if line.startswith("write_bytes"):
                return int(line.split()[1])
    except Exception:
        pass
    return -1


def gread(addr, n, path="/tmp/B_g.bin"):
    rc, o = sh("python3 /tmp/gdump.py %X %X %s" % (addr, n, path), timeout=10)
    if rc != 0:
        o = o.strip()
        return None, (o.splitlines()[-1] if o else "rc=%d" % rc)
    with open(path, "rb") as f:
        return f.read(), None


def ticks():
    d, e = gread(0x16A, 4, "/tmp/B_t.bin")
    if d is None or len(d) < 4:
        return None, e or "short read"
    return int.from_bytes(d[:4], "big"), None


def fmt(v):
    return "--------" if v is None else "%08x" % v


def be32(d, o):
    return int.from_bytes(d[o:o + 4], "big")


def be16(d, o):
    return int.from_bytes(d[o:o + 2], "big")


def capture():
    """The coordinator's serial-driver reads, small and RAM-only."""
    lines = []
    L = lines.append
    tb, _ = ticks()
    out("CAPTURE begin, Ticks before = %s" % fmt(tb))
    L("# B_stall %s  %s  t+%.1f  Ticks before = %s" % (CYC, time.strftime("%H:%M:%S"), now() - T0, fmt(tb)))

    def rd(label, addr, n):
        if addr <= 0 or n > 0x200 or addr + n > RAM_END:
            L("## %s  %08X+%X  SKIPPED (outside RAM or too large)" % (label, addr, n))
            return None
        d, e = gread(addr, n, "/tmp/B_x.bin")
        if d is None:
            L("## %s  %08X+%X  ERR %s" % (label, addr, n, e))
            return None
        L("## %s  %08X+%X" % (label, addr, n))
        _, o = sh("xxd -o 0x%X /tmp/B_x.bin" % addr)
        lines.extend(o.rstrip().splitlines())
        return d

    low = rd("1 low memory $100-$2FF", 0x100, 0x200)
    if low:
        P = be32(low, 0x2D0 - 0x100)
        U = be32(low, 0x11C - 0x100)
        L("# SerialVars($2D0) P=%08X  UTableBase($11C) U=%08X  PortAUse($290)=%02X  Lvl2DT($1B2)=%08X  ExtStsDT($2BE)=%08X"
          % (P, U, low[0x190], be32(low, 0xB2), be32(low, 0x1BE)))
        rd("2 port A driver variables (P)", P, 0x100)
        ut = rd("3 unit table U+$10", U + 0x10, 0x10)
        if ut:
            for name, off in ((".AIn", 4), (".AOut", 8)):
                H = be32(ut, off)
                L("# %s handle H=%08X" % (name, H))
                if H == 0:
                    continue
                hd = rd("3 %s handle (master pointer)" % name, H, 4)
                if not hd:
                    continue
                D = be32(hd, 0)
                dce = rd("3 %s DCE (D=%08X)" % (name, D), D, 0x40)
                if not dce:
                    continue
                Q = be32(dce, 8)
                L("# %s dCtlQHdr qFlags=%04X qHead=%08X qTail=%08X" % (name, be16(dce, 6), Q, be32(dce, 0xC)))
                if Q == 0:
                    continue
                pb = rd("4 %s qHead param block (Q=%08X)" % (name, Q), Q, 0x50)
                if not pb:
                    continue
                buf, req, act = be32(pb, 0x20), be32(pb, 0x24), be32(pb, 0x28)
                L("# %s ioCompletion=%08X ioResult=%04X ioRefNum=%04X ioBuffer=%08X ioReqCount=%08X ioActCount=%08X"
                  % (name, be32(pb, 0xC), be16(pb, 0x10), be16(pb, 0x18), buf, req, act))
                if buf:
                    rd("4 %s ioBuffer" % name, buf, 0x100)
                    if act > 0x100:
                        rd("4 %s ioBuffer+(ioActCount&~$FF)" % name, buf + (act & ~0xFF), 0x100)
    ta, _ = ticks()
    L("# Ticks after = %s  (%s)" % (fmt(ta), time.strftime("%H:%M:%S")))
    with open(STALLF, "w") as f:
        f.write("\n".join(lines) + "\n")
    out("CAPTURE end, Ticks before = %s after = %s -> %s" % (fmt(tb), fmt(ta), STALLF))


def main():
    global T0
    for f in (FLAG, STALLF):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    with open("/dev/MiSTer_cmd", "w") as f:
        T0 = now()
        f.write("load_core %s\n" % RBF)
    out("T0 %.3f T0MS=%d load_core %s" % (T0, int(T0 * 1000), RBF))

    k = 0
    reads = []            # (t, v) plausible reads
    wbh = []              # (t, write_bytes)
    prev = prev_t = None
    val_since = None      # t of the first read showing the current value
    last_diff_t = None    # t of the last read before that (a different value)
    same = 0
    seen40 = False
    first = None
    finder_t = None
    stall = None
    stalls = []
    max_t = BASE_MAX
    status = None
    while True:
        el = now() - T0
        target = 40 + 5 * k
        if target < el - 2.5:                     # fell behind: next slot
            k = int((el - 40) // 5) + 1
            target = 40 + 5 * k
        d = T0 + target - now()
        if d > 0:
            time.sleep(d)
        k += 1
        t = now() - T0
        v, err = ticks()
        w = wb()
        wbh.append((t, w))
        fl = os.path.exists(FLAG)
        if fl and finder_t is None:
            finder_t = t
            out("FINDER flag seen")
        if v is None:
            out("Ticks ERR %s wb=%d" % (err, w))
        else:
            pl = v < PLAUSIBLE
            extra = ""
            if pl and prev is not None and prev < PLAUSIBLE and prev_t is not None:
                extra = " d=%+d rate=%.1f/s" % (v - prev, (v - prev) / (t - prev_t))
            if pl:
                if first is None:
                    first = (t, v)
                    extra += " FIRST plausible Ticks (counting since ~t+%.1f)" % (t - v / 60.15)
                if v > 0x40:
                    seen40 = True
                reads.append((t, v))
            if prev is not None and v == prev:
                same += 1 if pl else 0
            else:
                same = 0
                last_diff_t = prev_t
                val_since = t
            prev, prev_t = v, t
            out("Ticks=%08x%s wb=%d F=%d" % (v, extra, w, int(fl)))

            if stall is not None and stall["end_t"] is None and v == stall["v"]:
                stall["last_frozen_t"] = t
            if (stall is None or stall["end_t"] is not None) and seen40 and pl and same >= 4:
                stall = {"v": v, "first_t": val_since, "before_t": last_diff_t, "detect_t": t,
                         "last_frozen_t": t, "captured": False, "end_t": None, "after_v": None, "finder": fl}
                stalls.append(stall)
                out("STALL detected: Ticks=%08x unchanged since t+%.1f (last different read t+%s), Finder flag %d"
                    % (v, val_since, "%.1f" % last_diff_t if last_diff_t is not None else "?", int(fl)))
                _, o = sh("python3 /tmp/pcsample.py 3 60", timeout=30)
                out("\n".join("PCS1 " + x for x in o.rstrip().splitlines()))
                _, o = sh("cat /proc/tty/driver/serial")
                out("\n".join("SERIAL-STALL " + x for x in o.rstrip().splitlines()))
                max_t = t + HUNG_AFTER + 30
            elif stall is not None and stall["end_t"] is None and v != stall["v"]:
                stall["end_t"] = t
                stall["after_v"] = v
                est = t - (v - stall["v"]) / 60.15 if pl else t
                out("STALL END: Ticks moved %08x -> %08x; last frozen read t+%.1f, this read t+%.1f; "
                    "resumed ~t+%.1f by extrapolation; first frozen read t+%.1f"
                    % (stall["v"], v, stall["last_frozen_t"], t, est, stall["first_t"]))
            if (stall is not None and stall["end_t"] is None and not stall["captured"]
                    and t >= stall["first_t"] + 60):
                stall["captured"] = True
                capture()
            if stall is not None and stall["end_t"] is None and t >= stall["detect_t"] + HUNG_AFTER:
                _, o = sh("python3 /tmp/pcsample.py 3 60", timeout=30)
                out("\n".join("PCS2 " + x for x in o.rstrip().splitlines()))
                rec = [x for x in wbh if x[0] >= t - 31]
                out("HUNG: no recovery %.0f s after detection; write_bytes over the last ~30 s: %s"
                    % (HUNG_AFTER, " ".join("t+%.0f:%d" % x for x in rec)))
                status = "HUNG"
                break
        active = stall is not None and stall["end_t"] is None
        if fl and not active and len(reads) >= 5:
            last5 = reads[-5:]
            ok = all(0 < last5[i + 1][0] - last5[i][0] < 8.0 and
                     50.0 <= (last5[i + 1][1] - last5[i][1]) / (last5[i + 1][0] - last5[i][0]) <= 70.0
                     for i in range(4))
            if ok:
                status = "BOOT_DONE"
                break
        if now() - T0 > max_t:
            status = "TIMEOUT"
            break

    out("SUMMARY status=%s first_plausible=%s finder_flag=%s stalls=%s" % (
        status,
        "t+%.1f:%08x(counting since ~t+%.1f)" % (first[0], first[1], first[0] - first[1] / 60.15) if first else "none",
        "t+%.1f" % finder_t if finder_t is not None else "none",
        ";".join("v=%08x first_t=%.1f before_t=%s detect_t=%.1f end_t=%s after_v=%s finder=%d" % (
            s["v"], s["first_t"], "%.1f" % s["before_t"] if s["before_t"] is not None else "?", s["detect_t"],
            "%.1f" % s["end_t"] if s["end_t"] is not None else "none", fmt(s["after_v"]), int(s["finder"]))
            for s in stalls) or "none"))
    out("END %s" % status)


if __name__ == "__main__":
    main()
