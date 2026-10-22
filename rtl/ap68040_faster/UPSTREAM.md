# AP68040 in this repository

This directory is the AP68040 `faster` core, vendored from
`apolkosnik/AP68040` branch `main` at **1247b45** (2026-10-19, "Merge pull
request #10 from apolkosnik/dead-job-kill"), first taken at b388dfc
(2026-10-18, PR #8 `faster`) and brought up to main on 2026-10-19: that
adds PR #9 and PR #10 (this port's two fixes, below) and PR #11
(georgemog: an IPEND claim is made against the new mask on the clock an
SR write commits, `t_ipendsr`).  It is the pipelined
SystemVerilog core (`rtl/ap68040*.sv`, the FPU in `rtl/fpu/`) that
presents the real MC68040 external bus; the NeXT side talks to that bus
through `rtl/next/next_cpu040.sv`, documented in `docs/CPU_NEXT_PORT.md`.

## What was taken

| upstream | here |
|---|---|
| `rtl/`, including the generated `rtl/gen/*.svh` (tools/ucode.py output) | `rtl/` |
| `tb/` (the 33-program regression, cputest replay, benchmarks) | `tb/` |
| `tools/`, `syn/`, `doc/`, `README.md`, `LICENSE` | same |
| `rtl_old/`, `tb_old/` (the previous sequential core, kept upstream as a reference) | not taken: that lineage is this repository's history before this drop (`git log -- rtl/ap68040` up to cb30c12) |

## Local changes to the core

Listed in `docs/CPU_NEXT_PORT.md` ("CPU-side changes") and kept small so
that a newer drop can replace this directory and the list be re-applied:

1. `rtl/ap68040.sv`, `rtl/ap68040_backend.sv`: the `dbcc_floor[3:0]` input
   (a DBcc period floor for hosts calibrated on a real 68040's DBcc
   loops); `tb/tb_ap68040.sv` register `$F10C` and clock count `$F2EC`;
   `tb/asm/t_dbccfloor.s` in `tb/run_tests.sh`.
2. `rtl/ap68040_ram.sv`, `ap68040_sdp_be`: a module per 32-bit slice with
   every byte's write spelled out and the read in the same always block
   (Intel's template to the letter), so Quartus 17.0 infers one M10K per
   slice instead of one per byte (and does not fall back to flip-flops,
   which it does for a `for` loop over the bytes with variable enables).

Two more were made here and are upstream now (in the vendored main):
the table walk's tag compare wait state (`E_TW_DESCW2`, `t_nx8k`,
https://github.com/apolkosnik/AP68040/pull/9) and the DC2 job's kill
mark cleared in `E_IDLE` (`t_snkill`, the bench's `$F2F0` counter and
traffic bit 13, the `E_S_DONE` self-check,
https://github.com/apolkosnik/AP68040/pull/10); both found on the NeXT
on 2026-10-19 (`docs/CPU_NEXT_PORT.md`).

Both remaining changes are candidates for upstream.  `tb/asm/t_cbzero.s`
and `t_pushfill.s` are investigation programs from the panic hunt, not
in `run_tests.sh`.

## History

Until 2026-10-18 this directory held the sequential `ap040_*.v` core as
vendored in MacQuadra800_MiSTer (imported tree `8778213`, Alan
Steremberg's performance stack over Adam Polkosnik's base), with the NeXT
port's 32-bit beat adapter (`ap040_bus32_adapter.v`).  The old
`UPSTREAM.md` and `docs/CPU_NEXT_PORT.patch` describe that tree; both are
in git history.

## Tests

```bash
cd rtl/ap68040/tb && JOBS=12 WORK=/path/outside/tmpfs bash run_tests.sh   # Verilator 5, vasmm68k_mot
```

The default object directory is `rtl/ap68040/obj/` (ignored by git).
