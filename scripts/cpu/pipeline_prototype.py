#!/usr/bin/env python3
"""Reproducible register-pipeline experiment; no FPGA or guest disk access."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "rtl/ap68040/rtl"
EXP = ROOT / "rtl/ap68040/experimental"


def workload():
    # The oracle operates on semantic tuples, independently of the RTL decoder.
    ops = []
    def emit(name, size=32, src=0, dst=0, imm=0):
        ops.append((name, size, src, dst, imm))
    for dst in range(8):
        emit("moveq", dst=dst, imm=127 if dst % 2 else -128)
    # Exercise sign overflow, carry, preserved X, and partial-register merges.
    for _ in range(26):
        for dst in range(8):
            emit("add", src=dst, dst=dst)
    for imm in range(-128, 128):
        for dst in range(8):
            emit("moveq", dst=dst, imm=imm)
    for name in ("move", "add", "sub", "cmp", "and", "or", "eor"):
        for size in (8, 16, 32):
            for src in range(8):
                for dst in range(8):
                    emit(name, size, src, dst)
    rng = random.Random(68040)
    for _ in range(5000):
        name = rng.choice(("moveq", "move", "add", "sub", "cmp", "and", "or", "eor", "nop"))
        emit(name, rng.choice((8, 16, 32)), rng.randrange(8), rng.randrange(8), rng.randrange(-128, 128))
    return ops


def encode(op):
    name, size, src, dst, imm = op
    if name == "nop": return 0x4e71
    if name == "moveq": return 0x7000 | dst << 9 | (imm & 255)
    if name == "move": return {8: 0x1000, 16: 0x3000, 32: 0x2000}[size] | dst << 9 | src
    sz = {8: 0, 16: 1, 32: 2}[size] << 6
    if name == "eor": return 0xb100 | src << 9 | sz | dst
    return {"add": 0xd000, "sub": 0x9000, "cmp": 0xb000, "and": 0xc000, "or": 0x8000}[name] | dst << 9 | sz | src


def expected(ops):
    regs, flags, rows = [0] * 8, 0, []
    for index, op in enumerate(ops):
        name, size, src, dst, imm = op
        if name != "nop":
            if name == "moveq": size = 32
            mask, sign = (1 << size) - 1, 1 << (size - 1)
            a = (imm if name == "moveq" else regs[src]) & mask
            b = regs[dst] & mask
            carry = overflow = 0
            x = (flags >> 4) & 1
            if name == "add":
                full = b + a
                result = full & mask
                carry = int(full > mask)
                overflow = int(bool((~(a ^ b) & (b ^ result)) & sign))
                x = carry
            elif name in ("sub", "cmp"):
                result = (b - a) & mask
                carry = int(b < a)
                overflow = int(bool(((a ^ b) & (b ^ result)) & sign))
                if name == "sub": x = carry
            elif name == "and": result = b & a
            elif name == "or": result = b | a
            elif name == "eor": result = b ^ a
            else: result = a
            flags = x << 4 | int(bool(result & sign)) << 3 | int(result == 0) << 2 | overflow << 1 | carry
            if name != "cmp": regs[dst] = (regs[dst] & ~mask) | result
        rows.append(f"{0x400 + index * 2:08x} {encode(op):04x} {flags:02x}" + "".join(f" {v:08x}" for v in regs))
    return rows


def run(args, log, cwd=None):
    with log.open("w") as output:
        result = subprocess.run([str(a) for a in args], cwd=cwd or ROOT, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {log}\n{log.read_text()[-3000:]}")
    return log.read_text()


def compare(path, oracle):
    rows = path.read_text().splitlines()
    if len(rows) != len(oracle):
        raise AssertionError(f"{path}: {len(rows)} retirements, expected {len(oracle)}")
    for i, (actual, wanted) in enumerate(zip(rows, oracle)):
        if actual != wanted:
            raise AssertionError(f"{path}: instruction {i}\nactual   {actual}\nexpected {wanted}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "scratch/pipeline_prototype")
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--pipeline-module", type=Path, default=EXP / "ap040_pipeline_integer.sv")
    args = parser.parse_args()
    out = args.out.resolve()
    pipeline = args.pipeline_module.resolve()
    out.mkdir(parents=True, exist_ok=True)
    import pipeline_address_oracle as address
    ops = workload() + (address.workload() if args.extended else [])
    encode_op = address.encode if args.extended else encode
    oracle = address.oracle(ops) if args.extended else expected(ops)
    words = [encode_op(op) for op in ops]
    registers = 16 if args.extended else 8
    supported = {encode(op) for op in workload()} | {address.encode(op) for op in address.workload()}
    (out / "supported.hex").write_text("".join(f"{int(opcode in supported)}\n" for opcode in range(65536)))
    (out / "instructions.hex").write_text("\n".join(f"{word:04x}" for word in words) + "\n")
    (out / "oracle.trace").write_text("\n".join(oracle) + "\n")
    # Reset vectors, straight-line payload, existing bench's pass mailbox.
    image = [0] * 32768
    image[0:4] = [0, 0 if args.extended else 0x3400, 0, 0x400]
    image[0x200:0x200 + len(words)] = words
    end = 0x200 + len(words)
    image[end:end + 7] = [0x33fc, 0x600d, 0, 0xf102, 0x4e72, 0x2700, 0x60fe]
    (out / "reference.hex").write_text("\n".join(f"{word:04x}" for word in image) + "\n")
    units = ("ap040_tg68k_compat", "ap040_core", "ap040_bus16_adapter", "ap040_bus_timeout",
             "ap040_regfile", "ap040_alu", "ap040_muldiv", "ap040_mmu", "ap040_cache",
             "ap040_fpu", "ap040_walker_cdc", "primitives/dpram")
    print("Compiling the current CPU reference and experimental pipeline", flush=True)
    run(["iverilog", "-g2012", "-I", RTL, "-s", "tb_ap040_program", "-s", "reference_trace",
         "-o", out / "reference.vvp", ROOT / "rtl/ap68040/tb/tb_ap040_program.v",
         EXP / "reference_trace.sv", *(RTL / (unit + ".v") for unit in units)], out / "compile_reference.log")
    log = run(["vvp", out / "reference.vvp", f"+prog={out / 'reference.hex'}", "+phase=0", "+prof",
               f"+trace={out / 'reference.trace'}", f"+count={len(words)}", f"+registers={registers}"], out / "reference.log")
    if "ALL TESTS PASSED" not in log or "FAIL:" in log:
        raise AssertionError(f"Reference failed: {out / 'reference.log'}")
    compare(out / "reference.trace", oracle)
    print(f"Current CPU: {len(words)} architectural snapshots match independent oracle", flush=True)
    run(["iverilog", "-g2012", "-I", RTL, "-s", "tb_pipeline_integer", "-o", out / "pipeline.vvp",
         EXP / "tb_pipeline_integer.sv", pipeline,
         RTL / "ap040_regfile.v", RTL / "ap040_alu.v"], out / "compile_pipeline.log")
    results = []
    for mode in range(6):
        trace = out / f"pipeline_{mode}.trace"
        log = run(["vvp", out / "pipeline.vvp", f"+program={out / 'instructions.hex'}",
                   f"+trace={trace}", f"+count={len(words)}", f"+registers={registers}", f"+mode={mode}", f"+supported={out / 'supported.hex'}"], out / f"pipeline_{mode}.log")
        compare(trace, oracle)
        summary = next(line for line in log.splitlines() if line.startswith("PIPELINE PASS"))
        results.append(summary)
        print(summary, flush=True)
    # Mutation control: disabling the WB data bypass must break the oracle
    # comparison. This proves the dependency workload exercises forwarding.
    poisoned = out / "no_forward.sv"
    poisoned.write_text(pipeline.read_text().replace(
        "wb_v && wb_we && wb_dst", "1'b0 && wb_we && wb_dst"))
    run(["iverilog", "-g2012", "-I", RTL, "-s", "tb_pipeline_integer", "-o", out / "no_forward.vvp",
         EXP / "tb_pipeline_integer.sv", poisoned, RTL / "ap040_regfile.v", RTL / "ap040_alu.v"],
        out / "compile_no_forward.log")
    trace = out / "no_forward.trace"
    run(["vvp", out / "no_forward.vvp", f"+program={out / 'instructions.hex'}",
         f"+trace={trace}", f"+count={len(words)}", f"+registers={registers}", "+mode=0", f"+supported={out / 'supported.hex'}"],
        out / "no_forward.log")
    try:
        compare(trace, oracle)
    except AssertionError as exc:
        (out / "negative_control.txt").write_text(str(exc) + "\n")
        print("PASS: disabled-forwarding mutation rejected", flush=True)
    else:
        raise AssertionError("Forwarding control unexpectedly passed")
    if args.extended:
        poisoned = out / "no_address_forward.sv"
        poisoned.write_text(pipeline.read_text().replace(
            "wb_v && wb_we && wb_dst", "wb_v && wb_we && !wb_dst[3] && wb_dst"))
        run(["iverilog", "-g2012", "-I", RTL, "-s", "tb_pipeline_integer", "-o", out / "no_address_forward.vvp",
             EXP / "tb_pipeline_integer.sv", poisoned, RTL / "ap040_regfile.v", RTL / "ap040_alu.v"],
            out / "compile_no_address_forward.log")
        trace = out / "no_address_forward.trace"
        run(["vvp", out / "no_address_forward.vvp", f"+program={out / 'instructions.hex'}",
             f"+trace={trace}", f"+count={len(words)}", "+registers=16", "+mode=0",
             f"+supported={out / 'supported.hex'}"], out / "no_address_forward.log")
        try:
            compare(trace, oracle)
        except AssertionError as exc:
            (out / "address_negative_control.txt").write_text(str(exc) + "\n")
            print("PASS: disabled An-only forwarding rejected", flush=True)
        else:
            raise AssertionError("Address forwarding control unexpectedly passed")
    identities = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in [RTL / "ap040_core.v", RTL / "ap040_regfile.v", RTL / "ap040_alu.v",
                               pipeline]}
    (out / "results.json").write_text(json.dumps({"instructions": len(words), "results": results,
                                                "sha256": identities}, indent=2) + "\n")
    print(f"PASS: prototype and current CPU agree with oracle; artifacts: {out}")


if __name__ == "__main__":
    main()
