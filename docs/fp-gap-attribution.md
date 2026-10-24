# Where the dual-issue core's floating-point cycles go (2026-10-24)

On hardware the dual-issue core (`rtl/ap68040_faster`, Quadra parameters,
`FPU_PIPE=0`) scores 0.744 on Speedometer 4.02's FPU suite against the
shipping core's 0.961, and PR Math 13.3 against 21.5; the 33/66 MHz scaling
puts the whole deficit inside the CPU.  This note attributes it by
instruction class from cycle-stamped instruction profiles of three
Speedometer-shaped kernels run on both cores in simulation.  Evidence,
sources, scripts and every table are under
[`docs/perf/fp_attribution_20261024/`](perf/fp_attribution_20261024/README.md).

## What was run

Both cores' standalone program benches on misterubuntu (Verilator 5.052, a
`git archive` of checkout `236b8c5`; no RTL in the checkout touched): the
dual core in its own `tb_ap68040` with the hardware parameters of
`rtl/quadra_cpu040.sv` (`FPU_PIPE=0 LOOP_PRED=0 EARLY_RES=0 DUAL=1 BTIC=1
S1_CLASSES=011 DIV_STEPS=2`, 8+8 KB caches), the shipping core (`ap040` +
the release macro set, through `wombat_cpu`) in the 2026-10-22 scratch
bench.  Same images on both: vbcc `-O=1023 -cpu=68040 -fpu=68040`, user
mode, copyback data.  Kernels: the bench's Whetstone (`whet.c`); a 20x20
double matrix multiply whose sum accumulates in the result element, so each
multiply-add is an FP load, two FP operations with memory sources and an FP
store; a radix-2 256-point complex FFT with every double volatile -- the
shape of code whose doubles live in memory, as Speedometer's do.  A 40x40
multiply and a 1024-point FFT (working sets past the 8 KB D-cache) and a
register-accumulator matmul were run as sensitivities.

The profile is the cycles between consecutive instruction completions,
charged to the completing instruction's address (`+pcprof` in the dual
bench; added to the old bench, dispatch to dispatch), two iteration counts
differenced so start-up and the result check cancel.  Both cores release
register-destination FP arithmetic to a background operation and make the
next FPU instruction wait for it; both benches count those waits separately
and the tables below charge them to the released operation, not the waiter
(the naive view is in the evidence directory).  The per-address sums agree
with the stamped loop times to 0.1 %.

## The tables

Cycles per iteration (one Whetstone loop; one 20x20 multiply; one forward +
inverse FFT), dual-issue core (D) against shipping core (S); clk/ins is
cycles per instruction of the class.

| class | Whet D | Whet S | clk/ins D/S | MatMul D | MatMul S | clk/ins D/S | FFT D | FFT S | clk/ins D/S |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FDIV / FSQRT | 46,652 (9.0 %) | 36,836 (8.2 %) | 24.6 / 19.4 | 0 | 0 | | 80 | 64 | |
| FADD/FSUB/FMUL/FCMP, other FP arithmetic | 212,304 (41.2 %) | 160,280 (35.9 %) | 8.6 / 6.5 | 139,054 (25.7 %) | 89,732 (19.0 %) | 8.7 / 5.6 | 276,069 (32.6 %) | 183,275 (28.3 %) | 10.7 / 7.1 |
| FMOVE register -> memory (FP store) | 31,977 (6.2 %) | 21,963 (4.9 %) | 11.0 / 7.3 | 88,013 (16.3 %) | 58,682 (12.4 %) | 11.0 / 7.3 | 276,848 (32.7 %) | 185,386 (28.6 %) | 11.0 / 7.4 |
| FMOVE memory -> register (FP load) | 37,032 (7.2 %) | 34,643 (7.8 %) | 9.0 / 8.4 | 131,042 (24.2 %) | 99,509 (21.1 %) | 8.2 / 6.2 | 202,348 (23.9 %) | 153,600 (23.7 %) | 8.0 / 6.1 |
| FBcc / FScc / FDBcc | 1,902 (0.4 %) | 1,768 (0.4 %) | 3.0 / 2.8 | 0 | 0 | | 189 | 293 | 3.0 / 4.7 |
| other FPU (FMOVEM, FMOVE control) | 101,894 (19.8 %) | 23,250 (5.2 %) | 30.3 / 6.5 | 10 | 0 | | 4,429 (0.5 %) | 546 (0.1 %) | 65 / 8 |
| integer loads / stores | 45,136 (8.7 %) | 101,738 (22.8 %) | 2.2 / 4.6 | 3,602 (0.7 %) | 2,865 (0.6 %) | | 11,905 (1.4 %) | 12,811 (2.0 %) | 3.0 / 3.2 |
| integer ALU | 27,706 (5.4 %) | 45,064 (10.1 %) | 1.8 / 2.5 | 170,629 (31.6 %) | 221,778 (46.9 %) | 2.3 / 2.7 | 69,394 (8.2 %) | 106,046 (16.4 %) | 1.8 / 2.4 |
| branches, JSR/RTS, DBcc, TRAP | 11,297 (2.2 %) | 20,965 (4.7 %) | 1.1 / 2.7 | 8,438 (1.6 %) | 12 | | 6,466 (0.8 %) | 5,572 (0.9 %) | 1.1 / 1.2 |
| **total** | **515,900** | **446,507** | 6.16 / 5.21 | **540,788** | **472,578** | 4.37 / 3.82 | **847,728** | **647,593** | 6.76 / 5.02 |
| dual / shipping | 1.155 | | | 1.144 | | | 1.309 | | |

(The shipping core's second integer pipeline folds compare-and-branch pairs
into one dispatch, so its branch row is near zero and its integer ALU row
carries them; the integer total is what to compare.)

Instruction by instruction in the hot loops, dual against shipping clocks:
FP load `fmove.d <mem>,fpN` 8.0-8.3 vs 6.0-6.3; arithmetic with a memory
source `fmul.d/fadd.d/fsub.d <mem>,fpN` 10.4-11.0 vs 7.0-7.5; register
arithmetic `fadd.x fpM,fpN` 6.0-6.6 vs 4.0; FP store `fmove.d fpN,<mem>`
11.0 flat vs 7.0-7.5; `fmovem.x` of two registers to `-(a7)` 79 vs 18 and
back 51-54 vs 11 (the dual core runs it as a slot-read and a store per long
word, 8-13 clocks each; `breakdown/ftrace_whet_p3_fmovem.txt` shows the
sequence); general `fdiv.d` 43 vs 31, `fdiv.x` 39 vs 26, `fsqrt.x` 39 vs 27,
while Whetstone's divides by `T2 = 2.0` terminate early on both (9 vs 11).

Sensitivities (cycles per iteration): 40x40 multiply 4,924,549 vs 4,114,782
(1.20x; FP loads 12.9 vs 7.4 clk once the arrays miss); 1024-point FFT
6,153,962 vs 3,858,285 (1.60x; loads 23.9 vs 11.1) -- but the two benches
have different memory models and neither is quadra800's SDRAM path, so the
cache-missing figures are not comparable, and the hardware scaling says the
suite does not miss.  Register-accumulator matmul 380,639 vs 365,775
(1.04x): keeping the sum in an FP register removes most of the gap, which is
why the memory-resident shape matters.  Dual core with `FPU_PIPE=1`:
Whetstone 460,004 (-10.8 %), matmul 484,164 (-10.6 %), FFT 752,496
(-11.2 %) -- arithmetic falls to 6.0-6.3 clk and loads to 6.0-6.8, but FP
stores rise from 11.0 to 14.0 because they wait for the pipeline to drain.

Against the hardware: the dual core's simulated speed relative to the
shipping core is Whetstone 0.865, matmul 0.874, FFT 0.764; on Speedometer
it is KWhetstones 0.76, Matrix 0.83, FFT 0.69.  The kernels reproduce the
order (FFT worst, matmul and Whetstone alike) with gaps about two thirds the
size of the hardware's.

## Conclusion

Every FP instruction the dual core executes costs more than on the shipping
core: 1.3x for loads, 1.4-1.5x for arithmetic with a memory source and for
stores, 1.6x for register arithmetic, 1.4-1.7x for the general divides and
square root, 4-5x for FMOVEM.  Its integer side is 19-50 % cheaper
(matmul, FFT, Whetstone), which is why the total gap (15-31 %) is smaller
than the FP gap.  Putting each
class at the shipping core's cost would recover, as a share of the dual
core's cycles:

| change | Whetstone | matmul | FFT |
|---|---:|---:|---:|
| FP arithmetic latency (FADD/FSUB/FMUL/FCMP, incl. memory-source forms) | 10.1 % | 9.1 % | 10.9 % |
| FP store path | 1.9 % | 5.4 % | 10.8 % |
| FP load path | 0.5 % | 5.8 % | 5.7 % |
| FMOVEM (register save/restore) | 15.2 % | 0 | 0.5 % |
| FDIV/FSQRT (the divider's 2 steps per clock) | 1.9 % | 0 | 0 |
| taken-FBcc prediction | 0.0 % | 0 | 0 |

So: **the divider is not the problem** -- Whetstone's divides are mostly by
2.0 and terminate early on both cores, the general ones are 1.4-1.7x slower
but add up to 1.9 % of Whetstone and nothing elsewhere; a 2 -> 3 step
divider would buy at most that.  **FBcc is not the problem** either: FP
compares are 0.4 % of Whetstone and absent from the kernels.  The two
levers that matter on every kernel are the sequential FPU's per-operation
latency (9-11 %) and the FP store path (2-11 %, equal to arithmetic in the
FFT, the kernel the hardware says is worst).  The `FPU_PIPE=1` sensitivity
recovers the arithmetic share in simulation (-11 % on all three) and on
hardware bought 0.7-1.2 % (`docs/fpu-pipe-experiment.md`); it also makes
every FP store 3 clocks slower.  Taken together, the one change that the
cycle numbers single out and that nothing has tried yet is **the FP
register-to-memory path** -- the 11-clock flat `fmove.d fpN,<ea>` and the
8-13 clocks per long word of FMOVEM -- which is the only large class the
pipeline leaves untouched or worsens, and whose weight grows with the
memory-resident style Speedometer compiles to.  FMOVEM alone is 15 % of
Whetstone here because vbcc saves FP registers in every callee prologue;
whether Speedometer's compiler did the same decides whether that 4-5x shows
on hardware.

## What the trace does not show

- Speedometer's own instruction stream.  These are vbcc kernels in the
  shape of Speedometer's tests, not its binary; sizes (20x20, 256 points)
  are guesses, and the compiler's choices (FMOVEM in prologues, memory-source
  arithmetic, no SANE) are vbcc's.  That the hardware gaps are larger than
  the simulated ones, and that `FPU_PIPE` helps the kernels 11 % but the
  suite 1 %, says Speedometer's code leans further towards the paths the
  pipeline does not help -- stores, FMOVEM, control-register moves -- and
  only a trace of the real binary on the full-machine sim can show how far.
- Mac OS: interrupts, the 60 Hz tick, Toolbox and trap overhead, the real
  cache state, and quadra800's SDRAM/ROM paths.  The benches run with
  zero-wait-state memory; the cache-missing variants are a different
  experiment on each bench and not a comparison.
- The attribution model: cycles between completions in an in-order
  machine, with FPU background waits moved to the released operation.  A
  stall is charged to the instruction at the head, which is right for a
  sequential FPU but hides overlap the pipeline would create; dual-issue
  companions retire at zero cost beside their partner; the old core's
  per-class split of integer work is approximate.
- How much of the FP store's 11 clocks is the FPU (extended -> double
  conversion, the `GET` uops) and how much the DMU store engine -- the
  per-stage trace of one store is the next step, not this one.
