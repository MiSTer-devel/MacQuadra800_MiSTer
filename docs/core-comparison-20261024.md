# CPU core comparison: real Quadra 800, shipping core, pipelined and dual-issue experiments (2026-10-24)

One table for the question the pipelined-040 work set out to answer: how
the apolkosnik/Ranzbak pipelined 68040 compares with the ap040 this core
ships, in size, timing and what Speedometer 4.02 sees on Mac OS 8.1. Every
number here is copied from an existing record (listed under Provenance);
nothing was re-run for this page.

How to read it:

- **Mix** is the Benchmark Mix average (Quadra 605 = 1); **PR** is the
  Performance Rating and its four parts; the **FPU suite** is Speedometer's
  separate FPU Benchmarks (Quadra 650 = 1). PR Math is not the FPU suite.
- **Shipping 20260930** values are medians of five PR runs on the old
  wired box (`10.3.164.251`, Main `75e00b65`, Ethernet On, 32 MB). Every
  pipelined/dual value is **one iteration** on `mister192` (Ethernet Off,
  32 MB, disposable image). The two shipping-core rows show how much box,
  Main and seed move PR CPU for the same RTL (0.896 vs 0.798); treat
  differences under ~5 % as noise until the medians-of-five sweep in
  `RESUME-20261024-dual-memory-and-fpu.md` has been run.
- Disk depends on host/storage activity and is reported, not compared.
- ALMs are whole-core fitted ALMs out of the 5CSEBA6's 41,910. CPU slack
  is worst setup slack on the CPU clock; negative means the fit missed.
- The real Quadra 800 is a photograph of a 120 MB machine with unknown disk;
  it is the scale, not a controlled baseline.

## Speedometer, area and timing

| Build (source, seed) | CPU MHz | Whole-core ALMs | CPU setup slack | Mix | PR | PR CPU | Graphics | Disk | Math |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Real Quadra 800** (photograph, 120 MB) | 33 | -- | -- | 1.899 | 1.605 | 1.186 | 1.347 | 3.443 | 20.011 |
| **Shipping 20260930** (`6ce38c8`, seed 24; medians of 5) | 33 | 39,300 (94 %) | +0.507 | 1.808 | 1.267 | 0.896 | 1.166 | 2.488 | 21.451 |
| Shipping 20261002 (`8c223c8`, seed 38; same CPU + three bug fixes) | 33 | 39,030 (93 %) | +0.118 | not measured | | | | | |
| Shipping master, stamp 261021 (seed 40; on mister192) | 33 | 38,899 (93 %) | +0.198 | 1.790 | 1.195 | 0.798 | 1.176 | 2.660 | 20.910 |
| Scalar pipelined, minimal (RTL `6e1b795`, two fits / two runs) | 33 | 33,200 / 33,333 (79-80 %) | +1.324 / +1.249 | 1.611 / 1.612 | 1.472 / 1.473 | 1.716 / 1.717 | 0.855 / 0.846 | 2.273 / 2.385 | 13.218 / 13.223 |
| Scalar + CM 10 write buffer (`d811095`, seed 40) | 33 | 33,470 (80 %) | met | 1.647 | 1.530 | 1.700 | 0.924 | -- | -- |
| Scalar + write buffer + FPU_PIPE/LOOP_PRED/EARLY_RES (seed 40) | 33 | 35,648 (85 %) | +0.289 | 1.727 | 1.543 | 1.715 | 0.927 | 2.376 | 13.508 |
| Scalar CPU66, original | 66 | 34,213 (82 %) | **-2.391** | 3.162 | 2.456 | 3.468 | 1.463 | 2.413 | 26.633 |
| Scalar CPU66, timing24-small (best 66 MHz fit so far) | 66 | 33,328 (80 %) | **-1.539** | 3.159 | 2.420 | 3.475 | 1.397 | 2.515 | 26.642 |
| Dual issue R3 (`43a5280`, seed 38) | 33 | 34,643 (83 %) | +1.374 | 1.800 | 1.569 | 1.806 | 0.937 | 2.269 | 13.309 |
| Dual issue R3 (`43a5280`, seed 38) | 66 | 35,346 (84 %) | **-3.308** | 3.614 | 2.667 | 3.637 | 1.579 | 2.807 | 26.824 |
| **Dual + VRAM retirement** (`6bfd9c0`, seed 38; two runs) | 33 | 34,554 (82 %) | +1.245 | 1.801 / 1.802 | 1.617 / 1.604 | 1.807 | 0.982 / 0.985 | 2.381 / 2.228 | 13.313 |
| Dual + VRAM retirement + FPU_PIPE (`0bcf3b4`, seed 38) | 33 | 35,631 (85 %) | +0.964 | 1.806 | 1.623 | 1.806 | 0.985 | 2.417 | 13.313 |

M10K / DSP: shipping core 468 / 36; scalar pipelined 487 / 38; every dual
fit 497 / 38 (of 553 M10K). The dual core's extra block RAM is its register
file banks, ATCs, caches, BTB and BTIC.

## Separate FPU suite, Dhrystone and Whetstone

| Build | CPU MHz | FPU suite average | KWhet/s (FPU suite) | Matrix s | FFT s | Dhrystones/s (in Mix) | KWhet/s (in Mix) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Real Quadra 800 | 33 | 1.011 | 5,456.6 | 0.713 | 0.288 | -- | -- |
| Shipping 20260930 | 33 | 0.953 cold; 0.961, 0.968 warm | 4,589-4,621 | 0.690-0.723 | 0.280-0.301 | 19,388 | 1,851 |
| Shipping master, stamp 261021 | 33 | -- | -- | -- | -- | 18,010 | 1,755 |
| Scalar pipelined, minimal | 33 | -- | -- | -- | -- | 28,391 | 1,158 |
| Scalar + write buffer + FPU_PIPE/LOOP_PRED/EARLY_RES | 33 | 0.728 | -- | -- | -- | 24,896 then 30,221 on one boot | 1,219 |
| Dual issue R3 | 33 | 0.741 first; 0.744 warm | 3,504-3,505 | 0.828-0.836 | 0.406 | -- | -- |
| Dual issue R3 | 66 | 1.484 first; 1.492 warm | 7,054-7,061 | 0.417-0.422 | 0.201-0.202 | -- | -- |
| Dual + VRAM retirement | 33 | 0.741; 0.744 | 3,505-3,509 | 0.829-0.836 | 0.406 | -- | -- |
| Dual + VRAM retirement + FPU_PIPE | 33 | 0.750; 0.749 | 3,573-3,635 | 0.827-0.835 | 0.406 | -- | -- |

The dual runs' Mix sub-tests (Dhrystone, Whetstone, Towers, ...) were not
transcribed into their result records; only the averages were. The
medians-of-five sweep should record the full Mix table for every row.

Standalone, in simulation (vbcc `-O=1023 -cpu=68040 -fpu=68040`, same
images on both cores, copyback data, 2026-10-22, the scalar import before
dual issue -- the dual core has no standalone figure yet):

| Core | Dhrystone cycles / iteration | = Dhrystones/s at 33 MHz | Whetstone cycles / loop |
|---|---:|---:|---:|
| Pipelined, Quadra parameters (FPU_PIPE/LOOP_PRED/EARLY_RES = 0) | 1,009 | 32,706 | 518,038 |
| Pipelined, bench defaults (all three on) | 957 | 34,483 | 461,890 |
| Shipping ap040, release macros | 1,608 | 20,522 | **446,509** |

## What the shipping core has that the dual core has not, and vice versa

The clock costs are the 2026-10-22 microbenchmarks on the scalar import
(`docs/pipelined-040-compare.md` on branch `pipelined-040`); the dual
branch imports a newer upstream (`eed15a0`), so re-measure before
relying on an exact figure.

| Mechanism | Shipping core (`rtl/ap68040`: ap040 + the 2026-09 performance stack) | Dual-issue core (`rtl/ap68040_faster`: apolkosnik `faster` + Ranzbak dual) |
|---|---|---|
| Integer issue | In-order sequencer plus the second integer pipeline (`AP040_EXPERIMENTAL_PIPELINE`, `_LOADS`, `_STORES`, `_PEA`, `_P6`, `LEA`, `XSTORE`, `PIPELINE_MEMORY_ENTRY`, `_COMPARE`, `_EARLY_DRAIN`) | Pipelined core with dual issue (`DUAL=1`, `S1_CLASSES=011`: Dn/An companion ops; second-slot loads **off** after upstream Minimig corruption), BTB + BTIC |
| Caches | 8+8 KB write-through (`SETW=7`) | 8+8 KB copyback (128 sets); Mac OS maps RAM copyback, so RAM writes leave as 4-beat line pushes |
| Store that cannot complete in the cache (VRAM, device) | 3.0 clk, posted through the two-entry `wombat_store_buffer` | 11.2 clk, a DMU engine job each; since `6bfd9c0` an eligible VRAM store retires early (`PA_VRAM_POST=1`), engine still held until the bus completes |
| Uncached / device read (CM 10 treated like CM 11) | 5.2 clk | 14.1 clk, waits for every older instruction |
| Line fill from SDRAM / ROM | 15 / 9 clk, plus the retained-line sideband (`sdram_beat32`) answering a second miss in the same 16-byte line | 15 / 9 clk, fills through its own bus, no sideband |
| FPU | Same `ap040_fpu` lineage, area-compacted (one state frame, one rounding unit, tree LZC; P263); FDIV/FSQRT **3 restoring bits per clock** (`rtl/ap68040/rtl/ap040_fpu.v:2157`), ~27 / 17.6 clk | Upstream `ap040_fpu`, FDIV/FSQRT **2 steps per clock** (`rtl/ap68040_faster/rtl/fpu/ap040_fpu.v:798`; measured 39 / 24.4 clk on the earlier 1-step import); FADD/FMUL 6.05 clk (3.3 with `FPU_PIPE=1`, +1,077 ALMs); FP store 11.2 clk. `DIV_STEPS=2` is the *integer* divider |
| Taken FBcc | 3.7 clk | 10.7 clk (always mispredicted) |
| A-line trap + RTE / JSR + RTS | 64 / 14 clk | 83 / 25-30 clk |
| Cached loads, EAs, LEA, MULS.L | -- | 1.5-3x faster |
| SONIC D-cache snoop (Ethernet) | Yes | No -- Ethernet must stay Off |
| MMU table walker port into quadra800 | Yes | Walks through its own bus |
| CPU entity | 25,773 ALMs, 13 DSP | ~20,090 ALMs + 82 M10K, 15 DSP (scalar); dual issue about +1,400 |

## What the tables say

- At 33 MHz the dual core equals the shipping core on Mix (1.80 vs
  1.79-1.81) with **4,500-4,750 fewer whole-core ALMs** (34,554 vs
  39,030-39,300, about -12 %) and twice the PR CPU (1.807 vs 0.80-0.90).
- It is behind on Graphics (0.985 vs 1.166-1.176, -16 %), Math (13.3 vs
  20.9-21.5, -37 %) and the FPU suite (0.744 vs 0.961, -23 %). Against the
  real machine: dual core Mix 95 %, FPU 74 %, Graphics 73 %, Math 67 %;
  shipping core Mix 95 %, FPU 95 %, Graphics 87 %, Math 107 %.
- The two configuration experiments on the dual core bought almost
  nothing for their area: FPU_PIPE +1,077 ALMs for +0.7-1.2 % FPU; the
  VRAM retirement is the exception (+4.8 % Graphics for -89 ALMs).
- At 66 MHz the dual core's Mix is 3.614, 1.9x the real Quadra and 2.0x
  its own 33 MHz figure -- but with CPU slack -3.308 ns (Fmax 54 MHz).
  No 66 MHz fit of either pipelined core has closed timing; the best is the
  scalar timing24-small at -1.539 ns. The miss is now in the D1
  attribute-ROM address path (76 of the worst 100), not where the scalar
  timing work was.
- The shipping core is at 93-94 % of the device and its fits are a seed
  lottery; the dual core at 82 % fits every seed tried at 33 MHz.

## Is the slowdown memory? (added 2026-10-24)

The memory map as built -- the header comment at the top of
`MacQuadra800.sv` ("RAM and ROM live in DDR3") is stale; the read mux at
`MacQuadra800.sv:1007` is the truth:

| Region | Where | Path and cost |
|---|---|---|
| RAM, 32/128 MB | **SDRAM** (16-bit, 99 MHz, open page, BL8) via `sdram_beat32` | first data 5 clk_sys (hardware-measured), a 16-byte line fill **15 clk_sys**; one retained line; 8-entry posted write FIFO |
| ROM, 1 MB | **DDR3** (f2h bridge, 64-bit, `DDRAM_CLK = clk_sys`) | one 2-beat burst per 16-byte line, **9 clk_sys**; one retained line (`rom_line`) |
| VRAM, 320 KB (advertised 512 KB by row compaction) | **on-chip**, 4 byte lanes x 82,016 = **324 M10Ks, 59 % of the 553** | CPU write acked in 1 clk, read in 3; DAFB scanout at 640x480, 1/2/4/8 bpp, registered 1-cycle port |
| Ethernet mailbox | DDR3 | SONIC doorbell ring, not latency-sensitive |

The decisive measurement is the dual R3 pair: the same bitstream family at
33 and 66 MHz CPU with the **bus fixed at 33 MHz** in both. If a test
waited on memory, doubling only the CPU clock could not double its score.

| Score | 33 MHz | 66 MHz | Scaling |
|---|---:|---:|---:|
| Mix | 1.800 | 3.614 | 2.008x |
| PR CPU | 1.806 | 3.637 | 2.014x |
| PR Math | 13.309 | 26.824 | 2.015x |
| FPU suite (after Mix) | 0.744 | 1.492 | 2.005x |
| PR Graphics | 0.937 | 1.579 | 1.685x |
| PR Disk | 2.269 | 2.807 | 1.237x |

So Mix, CPU, Math and the FPU suite are **0 % memory-bound** on this core:
their working sets sit in the 8 KB caches and the deficits against the
shipping core (Math -37 %, FPU -23 %) are inside the CPU (FP store path,
divider steps, FP op latency). Graphics is the one test with a bus
component: solving a + b = 1, a/2 + b = 1/1.685 gives b = 0.19, so about a
fifth of the Graphics test's time at 33 MHz is bus waits. The `+fillprobe`
run (`rtl/quadra800.sv:639-646`) says what that fifth is: QuickDraw runs
from ROM, misses the 8 KB I-cache hard, and in the 8-bit Color test **ROM
fill beats outnumber VRAM beats several times** -- each a 9-clk DDR3 trip;
the VRAM accesses themselves are acked in 1-3 clocks and the cost there is
the CPU's 11-14 clk handling of an uncached access, not the memory. Faster
memory therefore cannot move Mix/CPU/Math/FPU at all and can move Graphics
by at most ~19 %, mostly through ROM fetch.

Against the shipping core the memory path is identical (both 15/9 clk), so
none of the dual core's deficit is memory. Against the real Quadra 800 the
gap is partly memory: a real 68040 line burst at 33 MHz is on the order of
10-12 bus clocks where ours is 15, and the real ROM is a zero-wait-state
burst device where ours is a DDR3 round trip.

**BlockMove.** Measured per byte (2026-10-22 microbenchmarks): MOVE16 2.40
clk (shipping) vs 2.7 (pipelined); a `move.l (a0)+,(a1)+` loop 1.66 vs
4.4. The 040 BlockMove uses MOVE16 for aligned bulk, so the common path is
near parity; the plain-loop loss is copyback write-allocate (a destination
line costs a 15-clk fill plus a 7-clk push where the write-through core
posted four stores), which is authentic 68040 behaviour and is avoided only
by MOVE16. Speeding up bulk copies on either core means a shorter SDRAM
line fill; the floor is about 5 (first data) + 3 (eight 16-bit beats at
99 MHz) + CPU/bus overhead, so ~10-11 clk is the realistic target, ~25 %
per miss, felt in large copies and cache-missing code, not in Speedometer.

**VRAM in DDR3 -- what it would look like.** It is an enabler, not a
speedup: it frees ~320 M10Ks (room for 16+16 or 32+32 KB caches, a larger
BTB/ATC) and allows a real 1 MB VRAM (16-bit 640x480, 832x624 at 8 bpp)
if the DAFB model grows to match. The parts: (1) CPU stores post into a
write FIFO with a byte/word combiner into 64-bit beats (the rejected
external queue returns here; `PA_VRAM_POST` retirement stays); (2) CPU
reads go through a small VRAM line cache (a handful of 64-byte lines,
updated by the write path) because a DDR3 read is ~9 clk against 3 today
and QuickDraw reads ~1 word per 2 it writes -- without the cache Graphics
gets *worse*; (3) scanout prefetches a whole scanline into an M10K buffer
(up to 1,280 bytes at 16 bpp, 2-3 M10Ks) so DDR3 arbitration jitter under
the scaler never reaches the pixel clock; bandwidth is trivial (37 MB/s at
640x480x16x60). `MISTER_FB` is not a shortcut: the framework's framebuffer
reads 8/16/24/32 bpp only, and the Mac's 1/2/4 bpp modes would need
expansion on write and a shadow for read-back. Cost estimate +700-1,000
ALMs and a week-scale effort; the full-machine sim instantiates
`quadra800`, not `emu`, so a DDR3 bridge model with randomised latency
must come first. SDRAM is the wrong home (the one 16-bit port already
carries every CPU fill, scanout would take ~20 % of it with page misses,
and the 128 MB RAM option fills the module). The user has asked for this to
be discussed before any architectural change.

Ranked by speed per ALM, the memory-side items are: a **ROM next-line
prefetch** (a second retained line, speculative DDR3 burst for line+1;
~200 ALMs; attacks the Graphics bus share directly, both cores, measurable
with `+fillprobe`); the **SDRAM fill 15 -> ~11 clk** (both cores, every
miss); then **DDR3 VRAM** as the way to afford bigger caches.

## Provenance

- Real Quadra 800: `docs/perf/dual_20261023/reference/result.json` (photograph transcription).
- Shipping 20260930: `docs/perf/dual_20261023/reference/shipping-20260930-report.md` (the P263 release gate, medians of 5) and the `.qsf` seed ledger; 20261002 and master fits from the `.qsf` ledger.
- Shipping master at 261021 and the scalar pipelined rows: `docs/pipelined-040-compare.md` on branch `pipelined-040` (`git show pipelined-040:docs/pipelined-040-compare.md`), including the microbenchmarks and the standalone Dhrystone/Whetstone.
- `pipelined-040-min`: `docs/dual-speedometer-comparison.md`, `docs/perf/shutdown_20261022/`, `.qsf` ledger.
- Scalar CPU66 rows: `docs/cpu66-experiment.md`, `docs/perf/cpu66_20261022/`.
- Dual R3 at 33 and 66: `docs/pipelined-040-dual.md`, `docs/perf/dual_20261023/`.
- Dual + VRAM retirement: `docs/dual-memory-performance.md`, `docs/perf/dual_memory_20261023/`, `test-builds/pipelined-040-dual-memory-20261023/33mhz/`.
- FPU_PIPE trial: `docs/fpu-pipe-experiment.md`; evidence on tag `pipelined-040-dual-fpu-pipe-20261024`.
- FPU suite rows: `docs/dual-fpu-comparison.md`.
