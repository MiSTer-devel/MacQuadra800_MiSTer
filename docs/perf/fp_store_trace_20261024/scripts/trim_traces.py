#!/usr/bin/env python3
# fp_store_trace 2026-10-24: cut each per-cycle trace to a steady-state window.
# The trace starts in the stamp's TRAP handler; the window begins when the
# kernel's third instruction (by distinct address in EX / dispatched pc)
# appears and ends when the (3 + N)th does, N instructions later.
# usage: trim_traces.py <out dir with *_trace_0x??.log> <dest dir>
import os, re, sys
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
# kernel: (tag, name, instructions to keep, instruction index to start at)
K = [("0x20", "fmove_d_a0inc", 3, 3), ("0x30", "fmove_d_a0", 3, 3), ("0x40", "fmove_d_a0inc_addq", 4, 4),
     ("0x50", "fmove_d_a0_addq", 4, 4), ("0x60", "fmove_s_a0inc", 3, 3), ("0x70", "fmove_x_a0inc", 3, 3),
     ("0x80", "fmove_x_predec_a7", 3, 3), ("0x90", "fmovem_x_push2", 2, 2), ("0xA0", "fmovem_x_pop2", 2, 2),
     ("0xB0", "fmove_l_a0inc", 3, 3), ("0xC0", "move_l_a0inc", 6, 3), ("0xD0", "fmove_d_load", 3, 3),
     ("0xE0", "fadd_x_fmove_d", 4, 4), ("0xF0", "fmove_d_store_load", 4, 4)]
new_ex = re.compile(r"\| EX ([0-9a-f]{4}) ")
old_pc = re.compile(r"pc=0000([0-9a-f]{4}) ")
def cut(lines, pat, keep, start_idx):
    seen, first = [], {}
    for i, l in enumerate(lines):
        m = pat.search(l)
        if not m: continue
        pc = m.group(1)
        if pc not in first:
            first[pc] = i; seen.append(pc)
    # the kernel's instructions are the addresses after the handler's (RTE at
    # 0x20xx): the first address below 0x2000 that is followed by others
    kern = [p for p in seen if int(p, 16) < 0x2000]
    if len(kern) < start_idx + keep + 1:
        return lines[-80:]
    a = first[kern[start_idx - 1]]
    b = first[kern[start_idx - 1 + keep]]
    return lines[a:b + 1]
for tag, name, keep, start in K:
    for core, pat in (("new", new_ex), ("old", old_pc)):
        p = os.path.join(src, f"{core}_trace_{tag}.log")
        if not os.path.exists(p): continue
        lines = [l.rstrip("\n") for l in open(p) if re.match(r"\s*\d+ ", l) and "STAMP" not in l]
        w = cut(lines, pat, keep, start)
        out = os.path.join(dst, f"{core}_{tag}_{name}.txt")
        with open(out, "w") as f:
            f.write(f"# {core} core, kernel {tag} {name}: {len(w)} cycles, steady state ({keep} instructions)\n")
            f.write("\n".join(w) + "\n")
        print(f"{out}: {len(w)} lines")
