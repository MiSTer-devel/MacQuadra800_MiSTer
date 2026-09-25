#!/usr/bin/env python3
"""Compare a device MMU /Results.jsonl (safe OR full run) against the
MAME baseline — an ADJUDICATION REPORT, not a pass/fail scorer: MAME's
harness state and known 040 quirks pervade the corpus expectations
(finding 22), so divergences are classified, and only vec errors and
unexplained live-row data bytes count as REAL. The pass/fail golden
contract for RTL runs is gen/score_vs_oracle.py against the hardware
captures.

Live rows (device full runs): the runner relocates the corpus world
(finding 24), so descriptor ADDRESS bytes differ by construction; this
checks what is comparable: descriptor FLAG bytes, stored data, vec, and
MMUSR presence. Labeled classes:
  - atc: MAME models no ATC (silicon/QEMU hold stale entries; silicon
    adjudicated, finding 26).
  - vecbase: the capture ran vectors at VA 0; the bench's VBR lives in
    the payload.

Safe rows (device safe AND full runs) — the finding-13/22 treatment,
environment split from CPU behavior:
  - the row's TARGET register (MOVEC <reg>) is compared; a mismatch is
    labeled `mask` (MAME's writable masks are known over-wide — the
    device value is the silicon adjudication).
  - other MMU registers are `env` (platform handoff state: the Quadra
    ROM hands off with TTRs programmed, MAME's harness does not).
  - d/a register mismatches are `dreg`/`areg` (harness state; a-regs
    are compared through the device's reloc header first).

Usage: mmu_live_check.py <mame_baseline.json> <device_results.jsonl> [--verbose]
"""
import json, re, sys

DATA_BASE, DATA_SIZE = 0x1800, 0x40
MMU_TARGET = re.compile(r'MOVEC (TC|ITT0|ITT1|DTT0|DTT1|URP|SRP|MMUSR)\b')

def load_device(path):
    out, reloc = {}, {}
    raw = open(path, 'rb').read().decode('latin1').replace('\0', '')
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if 'reloc' in r:
            reloc = r['reloc']
        if 'name' in r:
            out[r['name']] = r
    return out, reloc

def winbyte(row, addr):
    for w in row.get('windows', []):
        b = w['base']
        if b <= addr < b + len(w['bytes']):
            return w['bytes'][addr - b]
    return None

def classify(name, addr):
    if 'ATC stale' in name:
        return 'atc'
    if addr == 0x3403:
        return 'vecbase'
    return None

def score_safe_rows(base, dev, reloc, verbose):
    """The 14 hw-safe rows: vec is the REAL signal; register mismatches
    against the MAME model are classified, not failed (finding 22)."""
    delta = reloc.get('data', DATA_BASE) - DATA_BASE
    n_ok = n_vec = 0
    labels = {}

    def label(kind, msg):
        labels[kind] = labels.get(kind, 0) + 1
        if verbose:
            print(f"{kind:8s} {msg}")

    for name, b in base.items():
        m = dev.get(name)
        if not m or b['flags'].get('mmu_live') or m.get('skipped'):
            continue
        if m.get('vec', 0) != 0:
            n_vec += 1
            print(f"VEC safe {name[:52]}: device took vector {m.get('vec')}")
            continue
        clean = True
        tgt = MMU_TARGET.search(name)
        tgt = tgt.group(1).lower() if tgt else None
        bm, cm = m.get('final', {}).get('mmu', {}), b['final']['mmu']
        for k in sorted(set(cm) & set(bm)):
            if bm[k] == cm[k]:
                continue
            clean = False
            if k == tgt:
                label('mask', f"{name[:44]} mmu.{k}: device {bm[k]:#x} vs "
                              f"MAME model {cm[k]:#x} (silicon adjudicates)")
            else:
                label('env', f"{name[:44]} mmu.{k}: {bm[k]:#x} vs {cm[k]:#x}")
        bd, cd = m.get('final', {}).get('d', []), b['final']['d']
        for i, (dv, cv) in enumerate(zip(bd, cd)):
            if dv != cv:
                clean = False
                label('dreg', f"{name[:44]} d{i}: device {dv:#x} vs {cv:#x}")
        ba, ca = m.get('final', {}).get('a', []), b['final']['a']
        for i, (dv, cv) in enumerate(zip(ba, ca)):
            reloc_cv = cv + delta if DATA_BASE <= cv < DATA_BASE + DATA_SIZE else cv
            if dv not in (cv, reloc_cv):
                clean = False
                label('areg', f"{name[:44]} a{i}: device {dv:#x} vs {cv:#x}")
        n_ok += clean
    cl = ', '.join(f"{k} {v}" for k, v in sorted(labels.items()))
    print(f"safe rows: {n_ok} clean, {n_vec} VEC ERRORS"
          + (f"; classified: {cl}" if cl else ""))
    return n_vec


def main():
    verbose = '--verbose' in sys.argv
    base_path, dev_path = sys.argv[1], sys.argv[2]
    base = {r['name']: r for r in
            (json.loads(l) for l in open(base_path) if l.strip())}
    dev, reloc = load_device(dev_path)

    ran = sum(1 for r in dev.values() if not r.get('skipped'))
    print(f"device rows: {len(dev)} ({ran} ran)")

    vec_errs = score_safe_rows(base, dev, reloc, verbose)

    ok = diff = labeled = 0
    for name, b in base.items():
        m = dev.get(name)
        if not m or not b['flags'].get('mmu_live') or m.get('skipped'):
            continue
        exp_vec = 2 if b['flags'].get('raises_exception') else 0
        if m.get('vec') != exp_vec:
            print(f"VEC {name[:52]}: device {m.get('vec')} vs baseline-model {exp_vec}"
                  f"  (hardware adjudication if PTEST/supervisor row)")
        for addr, val in b['final']['ram']:
            if 0x3FF00 <= addr < 0x40000:
                continue                     # fault frames differ by design
            if 0x3000 <= addr < 0x3500 and (addr & 3) != 3:
                continue                     # descriptor address bytes relocated
            mv = winbyte(m, addr)
            if mv is None:
                continue
            tag = classify(name, addr)
            if mv == val:
                ok += 1
            elif tag:
                labeled += 1
                print(f"{tag:8s} {name[:44]} @{addr:#x}: base {val:#04x} dev {mv:#04x}")
            else:
                diff += 1
                print(f"DIFF     {name[:44]} @{addr:#x}: base {val:#04x} dev {mv:#04x}")
        mm = m.get('final', {}).get('mmu', {})
        if 'PTEST' in name:
            print(f"MMUSR    {name[:44]}: {mm.get('mmusr', 0):#010x} (hw-adjudicated)")
    print(f"\nflag/data bytes: {ok} match, {labeled} known-artifact, {diff} REAL diffs")
    return 1 if (diff or vec_errs) else 0

if __name__ == '__main__':
    sys.exit(main())
