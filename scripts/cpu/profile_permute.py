#!/usr/bin/env python3
"""Profile the unchanged Speedometer Permute routine through wombat_cpu.

The RAM model has controlled latency; this is not a MiSTer score prediction.
The original wrapper calls this n=7 routine 25 times; this fixture calls it once.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_SHA = "af67113bceb4eb906e973a9b747a0b1925b9d64c62f0f9a84bc6f0578839ca80"
KERNEL_SHA = "eedd72d43cf91c5c8035c2fd81ef9ef46b7dea5454106fede285e388c9b1c73c"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resource", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pipeline", action="store_true")
    parser.add_argument("--loads", action="store_true")
    parser.add_argument("--force-decode", action="store_true")
    parser.add_argument("--pea-entry-only", action="store_true", help="enter pipeline only at resident PEA")
    parser.add_argument("--selective", action="store_true", help="retain sequencer for isolated non-PEA entries")
    parser.add_argument("--pea", action="store_true", help="enable resident brief-index PEA")
    parser.add_argument("--stores", action="store_true", help="enable head-ordered pipeline stores")
    parser.add_argument("--xstore", action="store_true")
    parser.add_argument("--lea", action="store_true")
    parser.add_argument("--latencies", default="0,3,8")
    parser.add_argument("--verilator", default="/home/alans/verilator5/bin/verilator")
    parser.add_argument("--vasm", default="/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot")
    args = parser.parse_args()
    if args.pea_entry_only and not args.pea:
        parser.error("--pea-entry-only requires --pea")
    if (args.loads or args.stores or args.pea or args.selective or args.force_decode) and not args.pipeline:
        parser.error("--loads, --stores and --force-decode require --pipeline")
    resource = args.resource.read_bytes()
    assert hashlib.sha256(resource).hexdigest() == RESOURCE_SHA, "resource identity changed"
    # Verified AppleDouble offset: resource entry 82 + CODE 3 body 0x6250f.
    start = 82 + 0x6250f + 0x659c
    kernel = resource[start:start + 200]
    assert hashlib.sha256(kernel).hexdigest() == KERNEL_SHA, "kernel identity changed"
    out = args.out.resolve()
    (out / "build").mkdir(parents=True, exist_ok=True)
    (out / "build/exact_permute.bin").write_bytes(kernel)

    def run(command, log):
        with (out / log).open("w") as f:
            result = subprocess.run([str(x) for x in command], cwd=out,
                                    stdout=f, stderr=subprocess.STDOUT)
        text = (out / log).read_text()
        if result.returncode:
            raise RuntimeError(f"{log}: {text[-3000:]}")
        return text

    run([args.vasm, "-Fbin", "-m68040", "-no-opt", "-o", "program.bin",
         ROOT / "rtl/ap68040/tb/asm/bench_exact_permute.s"], "assemble.log")
    program = (out / "program.bin").read_bytes()
    assert program[0x659c:0x6664] == kernel, "original addresses/bytes changed"
    run(["python3", ROOT / "rtl/ap68040/tb/bin2hex.py", "program.bin", "program.hex"], "hex.log")
    rtl = ROOT / "rtl/ap68040/rtl"
    units = ("ap040_core", "ap040_bus_timeout", "ap040_regfile", "ap040_alu",
             "ap040_muldiv", "ap040_mmu", "ap040_cache", "ap040_fpu", "primitives/dpram")
    sources = [ROOT / "verilator/tb_cpu_permute.sv", ROOT / "rtl/wombat_cpu.sv",
               ROOT / "rtl/wombat_store_buffer.sv", *(rtl / (u + ".v") for u in units)]
    flags = []
    if args.force_decode:
        flags.append("-DAP040_PIPELINE_FORCE_DECODE")
    if args.pea_entry_only:
        flags.append("-DAP040_PIPELINE_PEA_ENTRY_ONLY")
    if args.selective:
        flags.append("-DAP040_PIPELINE_SELECTIVE")
    if args.pea:
        flags.append("-DAP040_EXPERIMENTAL_PIPELINE_PEA")
    if args.stores:
        flags.append("-DAP040_EXPERIMENTAL_PIPELINE_STORES")
    if args.loads:
        flags.append("-DAP040_EXPERIMENTAL_PIPELINE_LOADS")
    if args.lea:
        flags.append("-DAP040_EXPERIMENTAL_LEA")
    if args.xstore:
        flags.append("-DAP040_EXPERIMENTAL_XSTORE")
    if args.pipeline:
        flags.append("-DAP040_EXPERIMENTAL_PIPELINE")
        sources.append(ROOT / "rtl/ap68040/experimental/ap040_pipeline_integer.sv")
    identity = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    identity.update(resource_sha256=RESOURCE_SHA, kernel_sha256=KERNEL_SHA,
                    program_sha256=hashlib.sha256(program).hexdigest(),
                    experimental_pipeline=args.pipeline, experimental_xstore=args.xstore,
                    experimental_lea=args.lea, experimental_pipeline_loads=args.loads, experimental_pipeline_stores=args.stores, experimental_pipeline_pea=args.pea, selective_entry=args.selective, pea_entry_only=args.pea_entry_only,
                    force_decode=args.force_decode,
                    memory_model="controlled latency, no SDRAM or retained platform line")
    (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    run([args.verilator, "--binary", "--timing", "-Wno-fatal", "-Wno-BLKLOOPINIT",
         "-j", "8", "--top-module", "tb_cpu_permute", "--Mdir", out / "obj",
         "-I" + str(rtl), *flags, *sources], "compile.log")
    for latency in map(int, args.latencies.split(",")):
        assert latency >= 0
        text = run([out / "obj/Vtb_cpu_permute", "+prog=" + str(out / "program.hex"),
                    f"+latency={latency}"], f"latency{latency}.log")
        assert "KERNEL32 PASS" in text and "Fatal" not in text, text[-3000:]
        print("\n".join(line for line in text.splitlines()
                        if line.startswith(("KERNEL32", "LATENCY", "BUFFER_UPPER_BOUND", "PIPELINE"))), flush=True)


if __name__ == "__main__":
    main()
