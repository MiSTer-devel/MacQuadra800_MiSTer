#!/usr/bin/env python3
"""Test opt-in pipeline ownership in the real core, with one shared register file."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from pipeline_prototype import ROOT, RTL, EXP, run, compare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "scratch/pipeline_p1")
    parser.add_argument("--vasm", default="/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot")
    parser.add_argument("--pipeline-module", type=Path, default=EXP / "ap040_pipeline_integer.sv")
    parser.add_argument("--core", type=Path, help="isolated candidate ap040_core.v")
    parser.add_argument("--cache", type=Path, help="isolated candidate ap040_cache.v")
    parser.add_argument("--only-irq", action="store_true")
    parser.add_argument("--force-decode", action="store_true", help="disable sequencer lookahead for full pipeline coverage")
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--memory-entry", action="store_true", help="enter at indexed memory/PEA, including resident lookahead")
    parser.add_argument("--p6", action="store_true", help="enable shifts, d16 LEA and brief indexed MOVE")
    parser.add_argument("--loads", action="store_true", help="enable head-ordered pipeline loads")
    parser.add_argument("--pea-entry-only", action="store_true", help="enter pipeline only at resident PEA")
    parser.add_argument("--selective", action="store_true", help="retain sequencer for isolated non-PEA entries")
    parser.add_argument("--pea", action="store_true", help="enable resident brief-index PEA")
    parser.add_argument("--stores", action="store_true", help="enable head-ordered pipeline stores")
    parser.add_argument("--xstore", action="store_true")
    parser.add_argument("--lea", action="store_true")
    parser.add_argument("--only-reference", action="store_true")
    parser.add_argument("--early-drain", action="store_true", help="handoff at final pipeline WB when younger slots are empty")
    parser.add_argument("--compare", action="store_true", help="indexed CMP/TST and register TST")
    args = parser.parse_args()
    if args.pea_entry_only and not args.pea:
        parser.error("--pea-entry-only requires --pea")
    if args.memory_entry and (not args.p6 or args.pea_entry_only or args.selective):
        parser.error("--memory-entry requires --p6 and excludes other entry policies")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    reference = out / ("prototype_extended" if args.extended else "prototype")
    if not (reference / "oracle.trace").exists():
        subprocess.run(["python3", str(ROOT / "scripts/cpu/pipeline_prototype.py"),
                        "--out", str(reference), *(["--extended"] if args.extended else [])], check=True)
    units = ("ap040_tg68k_compat", "ap040_core", "ap040_bus16_adapter", "ap040_bus_timeout",
             "ap040_regfile", "ap040_alu", "ap040_muldiv", "ap040_mmu", "ap040_cache",
             "ap040_fpu", "ap040_walker_cdc", "primitives/dpram")
    overrides = {"ap040_core": args.core, "ap040_cache": args.cache}
    source = [ROOT / "rtl/ap68040/tb/tb_ap040_program.v", args.pipeline_module.resolve(),
              EXP / "handoff_monitor.sv", *(overrides[u].resolve() if overrides.get(u) else RTL / (u + ".v") for u in units)]
    common = ["iverilog", "-g2012", "-DAP040_EXPERIMENTAL_PIPELINE", "-I", RTL,
              "-s", "tb_ap040_program", "-s", "handoff_monitor"]
    if args.compare:
        common.append("-DAP040_PIPELINE_COMPARE")
    if args.early_drain:
        common.append("-DAP040_PIPELINE_EARLY_DRAIN")
    if args.memory_entry:
        common.append("-DAP040_PIPELINE_MEMORY_ENTRY")
    if args.p6:
        common.append("-DAP040_EXPERIMENTAL_PIPELINE_P6")
    if args.xstore:
        common.append("-DAP040_EXPERIMENTAL_XSTORE")
    if args.lea:
        common.append("-DAP040_EXPERIMENTAL_LEA")
    if args.pea_entry_only:
        common.append("-DAP040_PIPELINE_PEA_ENTRY_ONLY")
    if args.selective:
        common.append("-DAP040_PIPELINE_SELECTIVE")
    if args.pea:
        common.append("-DAP040_EXPERIMENTAL_PIPELINE_PEA")
    if args.stores:
        common.append("-DAP040_EXPERIMENTAL_PIPELINE_STORES")
    if args.loads:
        common.append("-DAP040_EXPERIMENTAL_PIPELINE_LOADS")
    if args.force_decode:
        common.append("-DAP040_PIPELINE_FORCE_DECODE")
    (out / "identity.json").write_text(json.dumps({
        "sources": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source},
        "compile_args": [str(v) for v in common],
    }, indent=2) + "\n")
    if not args.only_irq:
        run([*common, "-s", "reference_trace", "-o", out / "trace.vvp",
             EXP / "reference_trace.sv", *source], out / "compile_trace.log")
        oracle = (reference / "oracle.trace").read_text().splitlines()
        log = run(["vvp", out / "trace.vvp", f"+prog={reference / 'reference.hex'}", "+phase=0",
                   f"+trace={out / 'handoff.trace'}", f"+count={len(oracle)}", f"+registers={16 if args.extended else 8}"], out / "trace.log")
        compare(out / "handoff.trace", oracle)
        match = re.search(r"HANDOFF entries=(\d+) commits=(\d+) paused=(\d+) cancelled=(\d+)", log)
        assert "ALL TESTS PASSED" in log and match and (args.pea_entry_only or args.memory_entry or int(match[1]) > 0) and int(match[1]) == int(match[2]), log[-2000:]
        if args.force_decode:
            assert int(match[1]) == len(oracle), log[-2000:]
        print(f"PASS {len(oracle)} shared-state snapshots; {match[0]}", flush=True)
        if args.only_reference:
            return
        run([*common, "-o", out / "program.vvp", *source], out / "compile_program.log")
        if args.loads or args.stores or args.pea:
            run([*common, "-DAP040_PIPELINE_FORCE_DECODE", "-o", out / "loads.vvp", *source],
                out / "compile_loads.log")
        tests = ("integer", "exceptions", "mmu", "bitfield_mmu", "bitfield_cache", "moves_fc",
                 "movem_restart", "atcprobe", "fpu_frames", "fpu_resume", "cache", "fpu",
                 "branch_early", "loops_irq")
        if args.loads:
            tests += ("pipeline_loads", "pipeline_load_fault")
        if args.stores:
            tests += ("pipeline_stores", "pipeline_store_fault")
        if args.pea:
            tests += ("pipeline_pea", "pipeline_pea_fault", "pipeline_pea_ext_fault", "pipeline_pea_trace")
        for name in tests:
            asm = ROOT / f"rtl/ap68040/tb/asm/t_{name}.s"
            run([args.vasm, "-Fbin", "-m68040", "-no-opt", "-o", out / f"{name}.bin", asm],
                out / f"{name}.asm.log", cwd=asm.parent.parent)
            run(["python3", ROOT / "rtl/ap68040/tb/bin2hex.py", out / f"{name}.bin",
                 out / f"{name}.hex"], out / f"{name}.hex.log")
            program = out / ("loads.vvp" if name.startswith(("pipeline_load", "pipeline_store", "pipeline_pea")) else "program.vvp")
            log = run(["vvp", program, f"+prog={out / (name + '.hex')}"], out / f"{name}.log")
            assert "ALL TESTS PASSED" in log and "FAIL:" not in log, f"{name}: {log[-2000:]}"
            match = re.search(r"HANDOFF entries=(\d+) commits=(\d+) paused=(\d+) cancelled=(\d+)", log)
            assert match and (args.pea_entry_only or args.memory_entry or int(match[1]) > 0) and int(match[1]) == int(match[2]) + int(match[4]), log[-1000:]
            print(f"PASS {name}: {match[0]}", flush=True)
    run([*common, *(["-DAP040_PIPELINE_FORCE_DECODE"] if (args.pea_entry_only or args.memory_entry) else []), "-s", "irq_overlap_monitor", "-o", out / "irq_overlap.vvp",
         EXP / "irq_overlap_monitor.sv", *source], out / "compile_irq_overlap.log")
    run([args.vasm, "-Fbin", "-m68040", "-no-opt", "-o", out / "irq_overlap.bin",
         EXP / "irq_overlap.s"], out / "irq_overlap.asm.log")
    run(["python3", ROOT / "rtl/ap68040/tb/bin2hex.py", out / "irq_overlap.bin",
         out / "irq_overlap.hex"], out / "irq_overlap.hex.log")
    log = run(["vvp", out / "irq_overlap.vvp", f"+prog={out / 'irq_overlap.hex'}"],
              out / "irq_overlap.log")
    match = re.search(r"IRQ OVERLAP injections=(\d+) killed=(\d+)", log)
    assert "ALL TESTS PASSED" in log and match and int(match[1]) >= 2 and int(match[2]) >= 2, log[-2000:]
    print(f"PASS precise interrupt and replay: {match[0]}", flush=True)
    if args.loads:
        run([*common, "-DAP040_PIPELINE_FORCE_DECODE", "-s", "irq_load_monitor",
             "-o", out / "irq_load.vvp", EXP / "irq_load_monitor.sv", *source],
            out / "compile_irq_load.log")
        run([args.vasm, "-Fbin", "-m68040", "-no-opt", "-o", out / "irq_load.bin",
             EXP / "irq_load.s"], out / "irq_load.asm.log")
        run(["python3", ROOT / "rtl/ap68040/tb/bin2hex.py", out / "irq_load.bin",
             out / "irq_load.hex"], out / "irq_load.hex.log")
        log = run(["vvp", out / "irq_load.vvp", f"+prog={out / 'irq_load.hex'}"], out / "irq_load.log")
        match = re.search(r"LOAD IRQ injections=(\d+) killed=(\d+)", log)
        assert "ALL TESTS PASSED" in log and match and int(match[1]) == 3 and int(match[2]) >= 3, log[-2000:]
        print(f"PASS load interrupt and replay: {match[0]}", flush=True)
    if args.stores:
        run([*common, "-DAP040_PIPELINE_FORCE_DECODE", "-s", "irq_store_monitor",
             "-o", out / "irq_store.vvp", EXP / "irq_store_monitor.sv", *source],
            out / "compile_irq_store.log")
        run([args.vasm, "-Fbin", "-m68040", "-no-opt", "-o", out / "irq_store.bin",
             EXP / "irq_store.s"], out / "irq_store.asm.log")
        run(["python3", ROOT / "rtl/ap68040/tb/bin2hex.py", out / "irq_store.bin",
             out / "irq_store.hex"], out / "irq_store.hex.log")
        log = run(["vvp", out / "irq_store.vvp", f"+prog={out / 'irq_store.hex'}"], out / "irq_store.log")
        match = re.search(r"STORE IRQ injections=(\d+) killed=(\d+) stores=(\d+)", log)
        assert "ALL TESTS PASSED" in log and match and int(match[1]) == 3 and int(match[2]) >= 3 and int(match[3]) == 3, log[-2000:]
        print(f"PASS store interrupt and replay: {match[0]}", flush=True)
    if args.pea:
        run([*common, "-DAP040_PIPELINE_FORCE_DECODE", "-s", "irq_pea_monitor",
             "-o", out / "irq_pea.vvp", EXP / "irq_pea_monitor.sv", *source],
            out / "compile_irq_pea.log")
        run([args.vasm, "-Fbin", "-m68040", "-no-opt", "-o", out / "irq_pea.bin",
             EXP / "irq_pea.s"], out / "irq_pea.asm.log")
        run(["python3", ROOT / "rtl/ap68040/tb/bin2hex.py", out / "irq_pea.bin",
             out / "irq_pea.hex"], out / "irq_pea.hex.log")
        log = run(["vvp", out / "irq_pea.vvp", f"+prog={out / 'irq_pea.hex'}"], out / "irq_pea.log")
        match = re.search(r"PEA IRQ injections=(\d+) killed=(\d+) stores=(\d+)", log)
        assert "ALL TESTS PASSED" in log and match and int(match[1]) == 3 and int(match[2]) >= 3 and int(match[3]) == 3, log[-2000:]
        print(f"PASS PEA interrupt and replay: {match[0]}", flush=True)
    print(f"PASS real-core pipeline ownership integration; artifacts: {out}")


if __name__ == "__main__":
    main()
