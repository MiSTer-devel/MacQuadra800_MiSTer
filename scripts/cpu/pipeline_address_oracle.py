#!/usr/bin/env python3
"""Prepare/verify the next pipeline workload against the real core and an independent oracle.

This does not claim that the experimental pipeline supports these operations yet.
It establishes semantics for all 16 integer registers, quick arithmetic, and
word sign extension before changing that engine.
"""
import argparse
import json
from pathlib import Path
import random
from pipeline_prototype import ROOT, RTL, EXP, run, compare


def workload():
    ops = [("moveq", 32, 0, d, -128 if d % 2 else 127) for d in range(8)]
    # Create values whose high words matter for partial writes and sign extension.
    for _ in range(19):
        ops += [("add", 32, d, d, 0) for d in range(8)]
    # Adjacent address-register RAW chains exercise pipeline forwarding,
    # not just the register file's delayed-write bypass two clocks later.
    for dst in range(8, 16):
        other = 8 + ((dst - 8 + 1) % 8)
        ops += [("moveq", 32, 0, 0, -1), ("move", 32, 0, dst, 0),
                ("addq", 16, 0, dst, 1), ("subq", 32, 0, dst, 8),
                ("move", 16, dst, other, 0), ("move", 16, other, 0, 0),
                ("adda", 16, 0, dst, 0), ("cmpa", 16, dst, other, 0)]
    pool = []
    for size in (8, 16, 32):
        for src in range(16):
            for dst in range(16):
                if size != 8 or (src < 8 and dst < 8):
                    pool.append(("move", size, src, dst, 0))
            for dst in range(8):
                if size != 8 or src < 8:
                    for name in ("add", "sub", "cmp"):
                        pool.append((name, size, src, dst, 0))
        for dst in range(16):
            if size != 8 or dst < 8:
                for quick in range(1, 9):
                    for name in ("addq", "subq"):
                        pool.append((name, size, 0, dst, quick))
    for size in (16, 32):
        for src in range(16):
            for dst in range(8, 16):
                for name in ("adda", "suba", "cmpa"):
                    pool.append((name, size, src, dst, 0))
    # Randomize exhaustive combinations so address values and flags don't settle
    # into a trivial all-zero stream. Mix fresh MOVEQ values into dependencies.
    rng = random.Random(6804016)
    rng.shuffle(pool)
    for op in pool:
        ops.append(("moveq", 32, 0, rng.randrange(8), rng.randrange(-128, 128)))
        ops.append(op)
    return ops


def encode(op):
    name, size, src, dst, imm = op
    ea = (8 if src >= 8 else 0) | (src & 7)
    sz = {8: 0, 16: 1, 32: 2}[size] << 6
    if name == "nop": return 0x4e71
    if name == "eor": return 0xb100 | src << 9 | sz | dst
    if name == "moveq":
        return 0x7000 | dst << 9 | (imm & 255)
    if name == "move":
        return {8: 0x1000, 16: 0x3000, 32: 0x2000}[size] | (dst & 7) << 9 | (64 if dst >= 8 else 0) | ea
    if name in ("addq", "subq"):
        return 0x5000 | (imm & 7) << 9 | (256 if name == "subq" else 0) | sz | (8 if dst >= 8 else 0) | (dst & 7)
    if name in ("adda", "suba", "cmpa"):
        return {"adda": 0xd0c0, "suba": 0x90c0, "cmpa": 0xb0c0}[name] | (dst & 7) << 9 | (256 if size == 32 else 0) | ea
    return {"add": 0xd000, "sub": 0x9000, "cmp": 0xb000, "and": 0xc000, "or": 0x8000}[name] | dst << 9 | sz | ea


def oracle(ops):
    regs, flags, result = [0] * 16, 0, []
    for index, op in enumerate(ops):
        name, size, src, dst, imm = op
        if name == "nop":
            result.append(f"{0x400 + index * 2:08x} {encode(op):04x} {flags:02x}" + "".join(f" {r:08x}" for r in regs))
            continue
        if name == "moveq": size = 32
        a = imm if name in ("moveq", "addq", "subq") else regs[src]
        address = dst >= 8
        if address:
            if size == 16 and name not in ("addq", "subq"):
                a = (a & 65535) - (65536 if a & 32768 else 0)
            size = 32
        mask, sign = (1 << size) - 1, 1 << (size - 1)
        a &= mask
        b = regs[dst] & mask
        carry = overflow = 0
        x = (flags >> 4) & 1
        if name in ("add", "adda", "addq"):
            value = (b + a) & mask
            carry = int(b + a > mask)
            overflow = int(bool((~(a ^ b) & (value ^ b)) & sign))
            x = carry
        elif name in ("sub", "suba", "subq", "cmp", "cmpa"):
            value = (b - a) & mask
            carry = int(b < a)
            overflow = int(bool(((a ^ b) & (value ^ b)) & sign))
            if name not in ("cmp", "cmpa"):
                x = carry
        elif name == "and": value = b & a
        elif name == "or": value = b | a
        elif name == "eor": value = b ^ a
        else:
            value = a
        if not address or name == "cmpa":
            flags = x << 4 | int(bool(value & sign)) << 3 | int(value == 0) << 2 | overflow << 1 | carry
        if name not in ("cmp", "cmpa"):
            regs[dst] = ((regs[dst] & ~mask) | value) & 0xffffffff
        result.append(f"{0x400 + index * 2:08x} {encode(op):04x} {flags:02x}" + "".join(f" {r:08x}" for r in regs))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "scratch/pipeline_address_oracle")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ops = workload()
    expected = oracle(ops)
    words = [encode(op) for op in ops]
    assert 0x400 + 2 * len(words) < 0xf000
    image = [0] * 32768
    # Use zero as initial ISP to match the prototype's reset register state.
    image[:4] = [0, 0, 0, 0x400]
    image[0x200:0x200 + len(words)] = words
    end = 0x200 + len(words)
    image[end:end + 7] = [0x33fc, 0x600d, 0, 0xf102, 0x4e72, 0x2700, 0x60fe]
    (out / "program.hex").write_text("".join(f"{word:04x}\n" for word in image))
    (out / "instructions.hex").write_text("".join(f"{word:04x}\n" for word in words))
    (out / "oracle.trace").write_text("\n".join(expected) + "\n")
    (out / "operations.json").write_text(json.dumps(ops) + "\n")
    units = ("ap040_tg68k_compat", "ap040_core", "ap040_bus16_adapter", "ap040_bus_timeout",
             "ap040_regfile", "ap040_alu", "ap040_muldiv", "ap040_mmu", "ap040_cache",
             "ap040_fpu", "ap040_walker_cdc", "primitives/dpram")
    run(["iverilog", "-g2012", "-I", RTL, "-s", "tb_ap040_program", "-s", "reference_trace",
         "-o", out / "reference.vvp", ROOT / "rtl/ap68040/tb/tb_ap040_program.v",
         EXP / "reference_trace.sv", *(RTL / (u + ".v") for u in units)], out / "compile.log")
    log = run(["vvp", out / "reference.vvp", f"+prog={out / 'program.hex'}", "+phase=0",
               f"+trace={out / 'reference.trace'}", f"+count={len(ops)}", "+registers=16"], out / "reference.log")
    assert "ALL TESTS PASSED" in log, log[-2000:]
    compare(out / "reference.trace", expected)
    print(f"PASS {len(ops)} independent 16-register snapshots; next-stage fixture: {out}")


if __name__ == "__main__":
    main()
