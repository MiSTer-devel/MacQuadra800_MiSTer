#!/usr/bin/env python3
"""fp_attribution 2026-10-24: per-instruction-class cycle breakdown from the
two benches' +pcprof dumps.

Each bench charges, to every executed instruction address, the cycles
between consecutive instruction completions (the dual core: tb_ap68040
"PCPROF <pc> <count> <cycles>", retirement to retirement; the shipping
core: tb_wombat_prog, dispatch to dispatch, with the sequencer's waits for a
background FPU operation moved from the waiting instruction to the operation
-- "PCFPW" -- or left on the waiter, "PCFPWW", the naive view).  Two runs
with different iteration counts are differenced per address, so start-up,
the result check and cold caches cancel, and the remainder is divided by the
iteration difference.  The opcode words come from the linked binary; the
classifier below reads the 68040 opcode and the FPU extension word.

usage: fpattr.py --bin prog.bin --core new|old --iters A B runA.log runB.log
        [--view adjusted|naive] [--json out.json] [--top 30] [--label name]
"""
import argparse, json, re, sys

CLASSES = [
    ('fdiv',   'FDIV / FSQRT'),
    ('farith', 'FADD/FSUB/FMUL/FCMP and other FP arithmetic'),
    ('fstore', 'FMOVE register -> memory (FP store)'),
    ('fload',  'FMOVE memory -> register (FP load)'),
    ('fbcc',   'FBcc / FScc / FDBcc'),
    ('fother', 'other FPU (FMOVEM, FMOVE control, FNOP)'),
    ('ildst',  'integer loads / stores (any memory operand)'),
    ('ialu',   'integer ALU (register-only)'),
    ('branch', 'branches, JSR/JMP, RTS, DBcc, TRAP/RTE'),
    ('other',  'other'),
]

FPOPS = {
    0x00: 'fmove', 0x01: 'fint', 0x02: 'fsinh', 0x03: 'fintrz', 0x04: 'fsqrt', 0x06: 'flognp1',
    0x08: 'fetoxm1', 0x09: 'ftanh', 0x0a: 'fatan', 0x0c: 'fasin', 0x0d: 'fatanh', 0x0e: 'fsin',
    0x0f: 'ftan', 0x10: 'fetox', 0x11: 'ftwotox', 0x12: 'ftentox', 0x14: 'flogn', 0x15: 'flog10',
    0x16: 'flog2', 0x18: 'fabs', 0x19: 'fcosh', 0x1a: 'fneg', 0x1c: 'facos', 0x1d: 'fcos',
    0x1e: 'fgetexp', 0x1f: 'fgetman', 0x20: 'fdiv', 0x21: 'fmod', 0x22: 'fadd', 0x23: 'fmul',
    0x24: 'fsgldiv', 0x25: 'frem', 0x26: 'fscale', 0x27: 'fsglmul', 0x28: 'fsub',
    0x38: 'fcmp', 0x3a: 'ftst',
    0x40: 'fsmove', 0x44: 'fdmove', 0x41: 'fssqrt', 0x45: 'fdsqrt', 0x58: 'fsabs', 0x5c: 'fdabs',
    0x5a: 'fsneg', 0x5e: 'fdneg', 0x60: 'fsdiv', 0x64: 'fddiv', 0x62: 'fsadd', 0x66: 'fdadd',
    0x63: 'fsmul', 0x67: 'fdmul', 0x68: 'fssub', 0x6c: 'fdsub',
}
for _k in range(0x30, 0x38):
    FPOPS[_k] = 'fsincos'
FPFMT = ['l', 's', 'x', 'p', 'w', 'd', 'b', 'p']
DIVSQRT = {'fdiv', 'fsgldiv', 'fsdiv', 'fddiv', 'fsqrt', 'fssqrt', 'fdsqrt'}


def ea_is_mem(mode, reg):
    if mode in (0, 1):
        return False
    if mode == 7:
        return reg in (0, 1, 2, 3)
    return True


def ea_str(mode, reg):
    if mode == 0: return 'd%d' % reg
    if mode == 1: return 'a%d' % reg
    if mode == 2: return '(a%d)' % reg
    if mode == 3: return '(a%d)+' % reg
    if mode == 4: return '-(a%d)' % reg
    if mode == 5: return 'd16(a%d)' % reg
    if mode == 6: return 'd8(a%d,Xn)' % reg
    return ['abs.w', 'abs.l', 'd16(pc)', 'd8(pc,Xn)', '#imm', '?', '?', '?'][reg]


def classify(w, ext):
    """-> (class key, subclass key or '', mnemonic-ish text)"""
    hi = w >> 12
    mode = (w >> 3) & 7
    reg = w & 7
    mem = ea_is_mem(mode, reg)
    ea = ea_str(mode, reg)
    if hi == 0xF:
        cp = (w >> 9) & 7
        typ = (w >> 6) & 7
        if cp == 1:
            if typ == 0:
                t = (ext >> 13) & 7
                opmode = ext & 0x7F
                name = FPOPS.get(opmode, 'fop%02x' % opmode)
                dst = (ext >> 7) & 7
                if t == 0:
                    src = 'fp%d' % ((ext >> 10) & 7)
                    s = '%s.x %s,fp%d' % (name, src, dst)
                    if name in DIVSQRT: return ('fdiv', 'reg', s)
                    return ('farith', 'reg', s)
                if t == 2:
                    fmt = (ext >> 10) & 7
                    if mode == 7 and reg == 4 and fmt != 7:
                        s = '%s.%s #imm,fp%d' % (name, FPFMT[fmt], dst)
                        sub = 'imm'
                    elif fmt == 7:
                        return ('fother', '', 'fmovecr #%d,fp%d' % (ext & 0x7F, dst))
                    elif mode == 0:
                        # Dn source: an integer -> FP conversion, not a memory load
                        s = '%s.%s d%d,fp%d' % (name, FPFMT[fmt], reg, dst)
                        sub = 'dn'
                    else:
                        s = '%s.%s %s,fp%d' % (name, FPFMT[fmt], ea, dst)
                        sub = 'mem'
                    if name in ('fmove', 'fsmove', 'fdmove'):
                        return (('farith', 'dn', s) if sub == 'dn' else ('fload', sub, s))
                    if name in DIVSQRT: return ('fdiv', sub, s)
                    return ('farith', sub, s)
                if t == 3:
                    fmt = (ext >> 10) & 7
                    if mode == 0:
                        return ('farith', 'todn', 'fmove.%s fp%d,d%d' % (FPFMT[fmt], dst, reg))
                    return ('fstore', '', 'fmove.%s fp%d,%s' % (FPFMT[fmt], dst, ea))
                if t in (4, 5):
                    regs = []
                    if ext & 0x1000: regs.append('fpcr')
                    if ext & 0x0800: regs.append('fpsr')
                    if ext & 0x0400: regs.append('fpiar')
                    return ('fother', '', 'fmove%s.l %s %s' % ('m' if len(regs) > 1 else '', '/'.join(regs), 'to ' + ea if t == 5 else 'from ' + ea))
                return ('fother', '', 'fmovem.x %s %s' % ('->' if t == 7 else '<-', ea))
            if typ == 1:
                if mode == 1: return ('fbcc', 'fdbcc', 'fdbcc d%d' % reg)
                if mode == 7 and reg in (2, 3, 4): return ('fbcc', 'ftrapcc', 'ftrapcc')
                return ('fbcc', 'fscc', 'fscc %s' % ea)
            if typ in (2, 3):
                cond = w & 0x3F
                if cond == 0 and typ == 2 and ext == 0:
                    return ('fother', '', 'fnop')
                return ('fbcc', 'fbcc', 'fbcc.%s #%02x' % ('w' if typ == 2 else 'l', cond))
            if typ in (4, 5):
                return ('fother', '', 'fsave/frestore')
            return ('fother', '', 'f-line %04x' % w)
        if cp == 3 and (w & 0xFFE0) == 0xF620 or (w & 0xFFF8) in (0xF600, 0xF608, 0xF610, 0xF618):
            return ('ildst', 'move16', 'move16')
        return ('other', '', 'f-line %04x' % w)
    if hi == 6:
        cond = (w >> 8) & 0xF
        n = ['bra', 'bsr'][cond] if cond < 2 else 'bcc'
        return ('branch', n, '%s' % n)
    if hi == 7:
        return ('ialu', '', 'moveq')
    if hi in (1, 2, 3):
        dmode = (w >> 6) & 7
        dreg = (w >> 9) & 7
        dmem = ea_is_mem(dmode, dreg)
        sz = {1: 'b', 3: 'w', 2: 'l'}[hi]
        name = 'movea' if dmode == 1 else 'move'
        s = '%s.%s %s,%s' % (name, sz, ea, ea_str(dmode, dreg))
        if mem and dmem: return ('ildst', 'move m,m', s)
        if mem: return ('ildst', 'load', s)
        if dmem: return ('ildst', 'store', s)
        return ('ialu', '', s)
    if hi == 5:
        if (w & 0xF8) == 0xC8:
            return ('branch', 'dbcc', 'dbcc d%d' % reg)
        if ((w >> 6) & 3) == 3:
            if mode == 7 and reg in (2, 3, 4): return ('other', '', 'trapcc')
            return (('ildst', 'store', 'scc %s' % ea) if mem else ('ialu', '', 'scc d%d' % reg))
        n = 'subq' if w & 0x100 else 'addq'
        return (('ildst', 'rmw', '%s %s' % (n, ea)) if mem else ('ialu', '', '%s %s' % (n, ea)))
    if hi == 4:
        if w in (0x4E75, 0x4E74, 0x4E73, 0x4E77):
            return ('branch', 'rts', {0x4E75: 'rts', 0x4E74: 'rtd', 0x4E73: 'rte', 0x4E77: 'rtr'}[w])
        if 0x4E40 <= w <= 0x4E4F: return ('branch', 'trap', 'trap #%d' % (w & 15))
        if 0x4E50 <= w <= 0x4E57: return ('ildst', 'link', 'link a%d' % reg)
        if 0x4E58 <= w <= 0x4E5F: return ('ildst', 'unlk', 'unlk a%d' % reg)
        if 0x4E80 <= w <= 0x4EBF: return ('branch', 'jsr', 'jsr %s' % ea)
        if 0x4EC0 <= w <= 0x4EFF: return ('branch', 'jmp', 'jmp %s' % ea)
        if w == 0x4E71: return ('other', '', 'nop')
        if w in (0x4E7A, 0x4E7B): return ('other', '', 'movec')
        if 0x4E60 <= w <= 0x4E7F: return ('other', '', 'misc %04x' % w)
        if (w & 0xFB80) == 0x4880 and mode != 0:
            return ('ildst', 'movem', 'movem %s' % ('->mem' if not (w & 0x400) else '<-mem'))
        if (w & 0xFFF8) == 0x4840: return ('ialu', '', 'swap')
        if (w & 0xFFC0) == 0x4840: return ('ildst', 'pea', 'pea %s' % ea)
        if (w & 0xFFC0) == 0x4880 or (w & 0xFFC0) == 0x48C0 or (w & 0xFFC0) == 0x49C0:
            return ('ialu', '', 'ext')
        if (w & 0xF1C0) == 0x41C0: return ('ialu', '', 'lea %s' % ea)
        if (w & 0xF140) == 0x4100: return ('other', '', 'chk')
        if (w & 0xFF00) == 0x4A00:
            if (w & 0xC0) == 0xC0: return (('ildst', 'rmw', 'tas') if mem else ('ialu', '', 'tas'))
            return (('ildst', 'load', 'tst %s' % ea) if mem else ('ialu', '', 'tst %s' % ea))
        if (w & 0xFF80) == 0x4C00:
            n = 'mul.l' if not (w & 0x40) else 'div.l'
            return (('ildst', 'load', '%s %s' % (n, ea)) if mem else ('ialu', n, '%s %s' % (n, ea)))
        if (w & 0xFFC0) in (0x40C0, 0x42C0, 0x44C0, 0x46C0):
            return ('other', '', 'move sr/ccr')
        if (w & 0xF900) == 0x4000 and (w & 0xC0) != 0xC0:
            n = {0x4000: 'negx', 0x4200: 'clr', 0x4400: 'neg', 0x4600: 'not'}[w & 0xFF00]
            return (('ildst', 'store' if n == 'clr' else 'rmw', '%s %s' % (n, ea)) if mem else ('ialu', '', '%s %s' % (n, ea)))
        if (w & 0xFFC0) == 0x4800: return (('ildst', 'rmw', 'nbcd') if mem else ('ialu', '', 'nbcd'))
        return ('other', '', 'op %04x' % w)
    if hi == 0:
        if w & 0x100 or (w & 0xFF00) == 0x0800:
            n = 'btst/bchg/bclr/bset'
            if (w & 0x138) == 0x108: return ('ildst', 'movep', 'movep')
            return (('ildst', 'rmw', '%s %s' % (n, ea)) if mem else ('ialu', '', '%s %s' % (n, ea)))
        n = {0x0000: 'ori', 0x0200: 'andi', 0x0400: 'subi', 0x0600: 'addi', 0x0A00: 'eori', 0x0C00: 'cmpi',
             0x0E00: 'moves'}.get(w & 0x0F00, 'op0')
        if n in ('cmpi',) and mem: return ('ildst', 'load', '%s %s' % (n, ea))
        if (w & 0xC0) == 0xC0 and n in ('ori', 'andi', 'subi', 'addi', 'eori'):
            return ('ildst', 'cas/chk2', 'cas/chk2/cmp2')
        return (('ildst', 'rmw', '%s %s' % (n, ea)) if mem else ('ialu', '', '%s %s' % (n, ea)))
    if hi in (8, 9, 0xB, 0xC, 0xD):
        opmode = (w >> 6) & 7
        n = {8: 'or', 9: 'sub', 0xB: 'cmp/eor', 0xC: 'and', 0xD: 'add'}[hi]
        if hi == 8 and opmode in (3, 7): n = 'divu/divs.w'
        if hi == 0xC and opmode in (3, 7): n = 'mulu/muls.w'
        if hi in (9, 0xD) and opmode in (4, 5, 6) and mode in (0, 1):
            return ('ialu', '', n + 'x')
        if hi == 0xC and opmode in (5, 6) and mode in (0, 1):
            return ('ialu', '', 'exg')
        if hi == 0xB and opmode in (4, 5, 6):
            if mode == 1: return ('ildst', 'load', 'cmpm')
            return (('ildst', 'rmw', 'eor %s' % ea) if mem else ('ialu', '', 'eor %s' % ea))
        if opmode in (4, 5, 6):
            return (('ildst', 'rmw', '%s dn,%s' % (n, ea)) if mem else ('ialu', '', '%s dn,%s' % (n, ea)))
        return (('ildst', 'load', '%s %s,rn' % (n, ea)) if mem else ('ialu', '', '%s %s,rn' % (n, ea)))
    if hi == 0xE:
        if (w & 0xC0) == 0xC0:
            if w & 0x800:
                return (('ildst', 'load', 'bitfield %s' % ea) if mem else ('ialu', '', 'bitfield'))
            return ('ildst', 'rmw', 'shift %s' % ea)
        return ('ialu', '', 'shift/rot')
    if hi == 0xA:
        return ('other', '', 'a-line')
    return ('other', '', 'op %04x' % w)


def load_prof(path):
    n, cyc, fpw, fpww = {}, {}, {}, {}
    stamps = []
    for line in open(path, errors='replace'):
        if line.startswith('PCPROF '):
            _, pc, c, cy = line.split()
            n[int(pc, 16)] = int(c); cyc[int(pc, 16)] = int(cy)
        elif line.startswith('PCFPW '):
            _, pc, cy = line.split(); fpw[int(pc, 16)] = int(cy)
        elif line.startswith('PCFPWW '):
            _, pc, cy = line.split(); fpww[int(pc, 16)] = int(cy)
        elif line.startswith('STAMP'):
            m = re.search(r'cycles=(\d+)', line); stamps.append(int(m.group(1)))
        elif line.startswith('PASS'):
            pass
        elif line.startswith('FAIL'):
            sys.exit('run failed: %s: %s' % (path, line.strip()))
    return n, cyc, fpw, fpww, stamps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bin', required=True)
    ap.add_argument('--core', required=True, choices=['new', 'old'])
    ap.add_argument('--iters', nargs=2, type=float, required=True)
    ap.add_argument('--view', default='adjusted', choices=['adjusted', 'naive'])
    ap.add_argument('--json')
    ap.add_argument('--top', type=int, default=30)
    ap.add_argument('--label', default='')
    ap.add_argument('runA'); ap.add_argument('runB')
    a = ap.parse_args()
    code = open(a.bin, 'rb').read()

    def word(addr):
        if addr + 1 >= len(code): return 0
        return (code[addr] << 8) | code[addr + 1]

    nA, cA, fA, fwA, sA = load_prof(a.runA)
    nB, cB, fB, fwB, sB = load_prof(a.runB)
    di = a.iters[1] - a.iters[0]
    pcs = set(nA) | set(nB) | set(fA) | set(fB) | set(fwA) | set(fwB)
    rows = []
    for pc in pcs:
        dn = nB.get(pc, 0) - nA.get(pc, 0)
        dc = cB.get(pc, 0) - cA.get(pc, 0)
        # both benches move the FPU background waits off the waiter's gap and
        # report them twice: PCFPW on the released operation, PCFPWW on the waiter
        if a.view == 'adjusted':
            dc += fB.get(pc, 0) - fA.get(pc, 0)
        else:
            dc += fwB.get(pc, 0) - fwA.get(pc, 0)
        if dn == 0 and dc == 0:
            continue
        cls, sub, txt = classify(word(pc), word(pc + 2))
        rows.append((pc, dn / di, dc / di, cls, sub, txt))
    tot_c = sum(r[2] for r in rows)
    tot_n = sum(r[1] for r in rows)
    per = {k: {'count': 0.0, 'cycles': 0.0} for k, _ in CLASSES}
    sub = {}
    for pc, dn, dc, cls, sb, txt in rows:
        per[cls]['count'] += dn; per[cls]['cycles'] += dc
        key = cls + ('/' + sb if sb else '')
        s = sub.setdefault(key, {'count': 0.0, 'cycles': 0.0})
        s['count'] += dn; s['cycles'] += dc
    stamp_per_iter = None
    if len(sA) >= 2 and len(sB) >= 2:
        stamp_per_iter = (sB[1] - sA[1]) / di
    label = a.label or a.bin
    print('# %s  core=%s view=%s  iterations %g and %g' % (label, a.core, a.view, a.iters[0], a.iters[1]))
    print('# cycles/iteration: %.0f by the per-PC sum, %s by the stamps; %.0f instructions/iteration (%.2f clk/instr)'
          % (tot_c, '%.0f' % stamp_per_iter if stamp_per_iter is not None else 'n/a', tot_n, tot_c / tot_n if tot_n else 0))
    print('%-46s %12s %6s %12s %8s' % ('class', 'cycles/iter', '%', 'instr/iter', 'clk/ins'))
    for k, lab in CLASSES:
        p = per[k]
        if p['count'] == 0 and p['cycles'] == 0: continue
        print('%-46s %12.0f %6.1f %12.0f %8.2f' % (lab, p['cycles'], 100.0 * p['cycles'] / tot_c if tot_c else 0,
                                                 p['count'], p['cycles'] / p['count'] if p['count'] else 0))
    print('%-46s %12.0f %6.1f %12.0f %8.2f' % ('total', tot_c, 100.0, tot_n, tot_c / tot_n if tot_n else 0))
    print('# sub-classes')
    for key in sorted(sub, key=lambda k: -sub[k]['cycles']):
        s = sub[key]
        if s['cycles'] == 0 and s['count'] == 0: continue
        print('  %-30s %12.0f %6.1f %12.0f %8.2f' % (key, s['cycles'], 100.0 * s['cycles'] / tot_c if tot_c else 0,
                                                   s['count'], s['cycles'] / s['count'] if s['count'] else 0))
    print('# top %d addresses by cycles/iteration' % a.top)
    rows.sort(key=lambda r: -r[2])
    for pc, dn, dc, cls, sb, txt in rows[:a.top]:
        print('  %08x %-8s %-34s %10.0f %10.0f %7.2f' % (pc, cls, txt, dn, dc, dc / dn if dn else 0))
    if a.json:
        out = {
            'label': label, 'core': a.core, 'view': a.view, 'bin': a.bin,
            'iterations': a.iters, 'cycles_per_iter': tot_c, 'stamp_cycles_per_iter': stamp_per_iter,
            'instr_per_iter': tot_n,
            'classes': {k: {'label': lab, 'cycles': per[k]['cycles'], 'count': per[k]['count'],
                            'pct': 100.0 * per[k]['cycles'] / tot_c if tot_c else 0,
                            'clk_per_instr': per[k]['cycles'] / per[k]['count'] if per[k]['count'] else None}
                        for k, lab in CLASSES},
            'subclasses': sub,
            'top': [{'pc': '%08x' % pc, 'class': cls, 'sub': sb, 'text': txt, 'count': dn, 'cycles': dc}
                    for pc, dn, dc, cls, sb, txt in rows[:a.top]],
            'all': [{'pc': '%08x' % pc, 'class': cls, 'sub': sb, 'text': txt, 'count': dn, 'cycles': dc}
                    for pc, dn, dc, cls, sb, txt in sorted(rows)],
        }
        json.dump(out, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
