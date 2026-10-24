# FP gap attribution, 2026-10-24: what is in this directory

The evidence behind [`docs/fp-gap-attribution.md`](../../fp-gap-attribution.md):
cycle-attributed instruction profiles of three Speedometer-shaped
floating-point kernels on the dual-issue core (`rtl/ap68040_faster`, the
hardware parameters of `rtl/quadra_cpu040.sv`) and on the shipping core
(`rtl/ap68040` through `wombat_cpu`), both in Verilator on misterubuntu,
checkout `236b8c5` (branch `pipelined-040-dual-memory`).  Nothing under
`rtl/` in the checkout was changed; the benches ran on a `git archive` copy
in `~/mister/q800_fpattr_20261024` on misterubuntu.

## Method

- **Images.** vbcc `-O=1023 -cpu=68040 -fpu=68040`, the bench's `crt0.s`
  with `-DCOPYBACK` (user mode, copyback data, both caches on), linked at 0
  (`rtl/ap68040_faster/tb/build_c.sh`).  Whetstone is the bench's own
  `tb/c/whet.c` at LOOPS 2 and 4; `kernels/fpmm.c` (N x N double matrix
  multiply, the sum accumulating in the result element through a volatile
  pointer) and `kernels/fft.c` (radix-2 complex FFT, every double volatile)
  at REPS 2 and 4.  `-DREGACC` builds the register-accumulator matmul.
- **Profiles.** Each bench charges the cycles between consecutive
  instruction completions to the completing instruction's address
  (`+pcprof`: the dual core's `tb_ap68040.sv` has it; `scripts/tb_wombat_prog.sv`
  adds it to the old core's scratch bench, dispatch to dispatch).  Both cores
  release register-destination FP arithmetic to a background FPU operation
  and make the *next* FPU instruction wait for it, so both benches count
  those wait cycles separately and the breakdown moves them onto the
  released operation (`PCFPW`; the "adjusted" view) -- the "naive" view
  (`*.naive.txt`) leaves them on the waiter.  `scripts/patch_tb_fpw.py` is
  the dual-core bench patch (applied to the scratch copy only).
- **Differencing.** Two iteration counts per kernel; the per-address
  profiles are subtracted, so start-up, the result check and cold caches
  cancel, and the remainder is divided by the iteration difference.  The
  per-address sum agrees with the stamped loop time to < 0.1 %.
- **Classes.** `scripts/fpattr.py` reads the opcode word and the FPU
  extension word from the linked binary: FDIV/FSQRT; FADD/FSUB/FMUL/FCMP and
  other FP arithmetic (sub-split by source: register, memory, immediate,
  Dn); FMOVE register -> memory (FP store); FMOVE memory -> register (FP
  load); FBcc/FScc/FDBcc; other FPU (FMOVEM, FMOVE control); integer
  loads/stores (any memory operand); integer ALU; branches/JSR/RTS/DBcc/TRAP;
  other.

## Files

- `kernels/fpmm.c`, `kernels/fft.c` -- the two new kernels (Whetstone is
  `rtl/ap68040_faster/tb/c/whet.c`).
- `scripts/build_sims.sh` -- verilates both benches (dual core: `FPU_PIPE=0
  LOOP_PRED=0 EARLY_RES=0 SKID=0 DC1_ATC=0 DUAL=1 BTIC=1 S1_CLASSES=3'b011`,
  `DIV_STEPS=2` the core default; old core: the release macro set).
  `scripts/run_kernels.sh` (first pass), `run2.sh` (REPS 2/4, patched dual
  bench), `run3.sh` (final dual-core pass), `run_pipe.sh` (the `FPU_PIPE=1`
  sensitivity) -- the build and run commands as executed.
- `scripts/fpattr.py` (breakdown), `merge_pc.py` (side-by-side per address),
  `make_csv.py` (the CSV), `patch_tb_fpw.py`, `tb_wombat_prog.sv`.
- `breakdown/<kernel>.<core>.txt` / `.json` -- the per-class table,
  sub-classes and top-30 addresses; `<core>` is `new` (dual), `old`
  (shipping), `newpipe` (dual with `FPU_PIPE=1`); `.naive` the other view.
  `fp_attribution.csv` is every class row of every kernel and core.
- `breakdown/hotloop_fpmm20.txt`, `hotloop_fft256.txt`, `hotspots_whet.txt`
  -- the hot loops instruction by instruction, both cores side by side.
- `breakdown/ftrace_whet_p3_fmovem.txt` -- the dual core's pipeline, one
  line a cycle, around a Whetstone P3 entry: the 79-clock `fmovem.x` of
  two registers.
- `listings/*.s` -- vbcc's assembly for each image.
- `raw_logs.tar.gz` -- every simulator log (`PCPROF`/`PCFPW` dumps, `STAMP`
  and `PROF` lines) and the patched `tb_ap68040.sv`.

## Kernels and iteration units

| kernel | one iteration | data |
|---|---|---|
| `whet` | one Whetstone loop (100,000 Whetstone instructions) | scalars and `E1[5]` |
| `fpmm20` | one 20x20 multiply (8,000 multiply-adds), doubles in memory | 3 x 3.2 KB |
| `fpmm20reg` | the same with the sum in an FP register | 3 x 3.2 KB |
| `fpmm40` | one 40x40 multiply (64,000 multiply-adds) | 3 x 12.8 KB (misses the 8 KB D-cache) |
| `fft256` | one forward + inverse 256-point FFT and the 1/N scaling | 2 x 2 KB |
| `fft1024` | the same at 1024 points | 2 x 8 KB (misses) |

A 50x50 image was tried first: its 60 KB of static arrays, linked from 0,
overlapped the dual-core bench's register page at `$F100-$F1FF` (a bus error
at `$F140`), so 40x40 stands in.  The cache-missing variants are not
comparable across the two benches -- each has its own memory model (the
dual core's `m68040_bus_slave` at zero wait states, the old core's
one-ack-per-transaction responder at latency 0), neither is quadra800's
SDRAM path -- and are reported only as a sensitivity.
