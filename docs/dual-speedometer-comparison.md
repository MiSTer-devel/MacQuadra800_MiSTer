# Dual issue and previous Speedometer results — 2026-10-23

All values below are Speedometer 4.02 ratings; higher is better. Mix is a
separate workload from PR CPU. PR Math is not the separate FPU benchmark.
Current dual-issue runs use 32 MB, Ethernet Off, one iteration per test,
and a readback-verified disposable copy of the same Quad Squad image used
for earlier CPU66 trials. Baseline PRAM was restored before each new run.

| Build | CPU MHz | Mix | PR CPU | Graphics | Disk | Math | Overall PR |
|---|---:|---:|---:|---:|---:|---:|---:|
| Real Quadra 800 | 33 | 1.899 | 1.186 | 1.347 | 3.443 | 20.011 | 1.605 |
| Previous minimal | 33 | 1.611 | 1.716 | 0.855 | 2.273 | 13.218 | 1.472 |
| Previous original CPU66 | 66 | 3.162 | 3.468 | 1.463 | 2.413 | 26.633 | 2.456 |
| Previous timing 1 | 66 | 3.162 | 3.476 | 1.400 | 2.780 | 26.639 | 2.469 |
| Previous timing 2 | 66 | 3.162 | 3.474 | 1.397 | 2.787 | 26.636 | 2.467 |
| Previous timing 12 | 66 | 3.160 | 3.474 | 1.399 | — | 26.610 | — |
| Previous timing 24-small (last tested) | 66 | 3.159 | 3.475 | 1.397 | 2.515 | 26.642 | 2.420 |
| New dual issue R3 | 33 | **1.800** | **1.806** | **0.937** | **2.269** | **13.309** | **1.569** |
| New dual issue R3 | 66 | **3.614** | **3.637** | **1.579** | **2.807** | **26.824** | **2.667** |

The new 33 MHz Mix improves 11.7% over the previous minimal build and
reaches 94.8% of the photographed real machine. At 66 MHz, Mix improves
14.4% over timing24-small and reaches 190.3% of the real machine. Overall
PR improves 10.2% over timing24-small; graphics improves 13.0%, CPU 4.7%
and Math 0.7%. These are single observations, not repeated-run statistics.
Disk ratings vary with host/storage activity. Timing12's disk test did
not produce an accepted result, so its overall PR is deliberately absent.
The real machine had 120 MB RAM, and its disk/cache setup is unknown.

## Timing and fitted area

| Build | CPU MHz | Whole-core ALMs | FPGA ALMs used | CPU setup slack | CPU TNS |
|---|---:|---:|---:|---:|---:|
| Previous minimal | 33 | 33,200 | 79.22% | +1.324 ns | 0 ns |
| Previous original CPU66 | 66 | 34,213 | 81.63% | −2.391 ns | −1175.353 ns |
| Previous timing12 | 66 | 33,335 | 79.54% | −1.667 ns | −196.113 ns |
| Previous timing24-small | 66 | 33,328 | 79.52% | −1.539 ns | −147.124 ns |
| New dual issue R3 | 33 | 34,643 | 82.66% | +1.374 ns | 0 ns |
| New dual issue R3 | 66 | 35,346 | 84.34% | **−3.308 ns** | **−2114.552 ns** |

The new 66 MHz CPU timing is 1.769 ns worse than the last tested version.
It is also 0.917 ns worse than the original CPU66 fit. Other domains and
hold checks pass in both new fits. The new 33 MHz fit passes all clocks;
the previous minimal artifact had a separate −0.043 ns HDMI miss.
Both new fits use 497/553 M10Ks. The 66 MHz build adds 2,018 whole-core
ALMs (6.1%) over timing24-small; the 33 MHz build adds 1,443 (4.3%) over
minimal. The quoted approximately26k ALMs was not reproduced for the
complete Quadra core.

The [66 MHz path analysis](perf/dual_20261023/66mhz/r3/path-analysis.json)
finds 76 of the worst 100 reported paths ending in the D1 attribute ROM
address, with another six in MMU translation/cache-hit logic. Worst path:
fetch queue to attribute-ROM address, 14 logic levels, 18.416 ns data
delay, including 10.455 ns routing. The MMU path has 13 levels and
17.763 ns data delay. TimeQuest reports 54.17 MHz CPU Fmax. Hardware
benchmark completion does not establish safe operation across timing
corners. No timing exception was introduced to hide these paths.

## Evidence

- [Real Quadra photograph](perf/dual_20261023/reference/speedometerrealquadra.png), [transcription and provenance](perf/dual_20261023/reference/result.json).
- Previous minimal [Mix](perf/shutdown_20261022/min-mix-complete.png) and [full PR](perf/shutdown_20261022/min-pr-complete.png).
- Previous original CPU66 [results](cpu66-experiment.md).
- Previous [timing1](perf/cpu66_20261022/timing1/hardware/run.json), [timing2](perf/cpu66_20261022/timing2/hardware/run.json), [timing12](perf/cpu66_20261022/timing12/mac/result.json), and [timing24-small](perf/cpu66_20261022/timing24/small/mac/result.json).
- New dual issue [33 MHz](perf/dual_20261023/33mhz/mac/result.json) and [66 MHz](perf/dual_20261023/66mhz/mac/result.json); each directory contains completion screenshots.
- [Integration, compiler fixes and qualification](pipelined-040-dual.md).

This branch remains an experiment. A/UX and CD audio have not been
qualified on the new CPU, and 66 MHz CPU timing remains open.
