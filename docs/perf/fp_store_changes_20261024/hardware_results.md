# Hardware Benchmark Results: Stage A–E Optimizations

**Platform:** MiSTer FPGA (`10.0.2.192`), Mac OS 8.1, 32 MB RAM, QuadSquad8 SCSI disk image.  
**Bitstream:** `MacQuadra800_dual_small33_stgE_261025.rbf` (md5 `0c820914bc3bdca185cab56a57f4811b`).  
**Branch:** `pipelined-040-small33` (commit `55f12e3`).  
**Timing:** Met on all clocks (+0.163 ns worst slack on 33 MHz system domain).  
**Area:** 29,988 ALUTs, 12,510 registers (+309 ALUTs / +1.03% total over dual-memory base).

---

## 1. Speedometer 4.02 — FPU Benchmarks

| Metric | Base Dual-Memory (33 MHz) | Stage A–D Small (33 MHz) | Stage A–E Small (33 MHz) | Total Delta vs Base | Shipping Core (20260930) |
|:---|---:|---:|---:|---:|---:|
| **KWhetstones / sec** | 3,505.131 | 4,319.505 | **4,377.287** | **+24.88%** | 4,589.450 |
| **Matrix Mult (sec)** | 0.836 | 0.781 | **0.780** | **-6.70%** | 0.690 |
| **Fast Fourier (sec)** | 0.406 | 0.386 | **0.386** | **-4.93%** | 0.301 |
| **FPU Average Rating** | 0.741 | 0.826 | **0.830** | **+12.01%** | 0.953 |

*Note: Whetstone performance improved by **+24.9%** (from 3,505 to 4,377.3 KWhetstones/sec), closing **80.4%** of the performance gap between the dual core and the shipping core on real hardware with only +309 ALUTs area overhead.*

---

## 2. Speedometer 4.02 — Benchmark Mix

| Test | Raw (sec / ops) | Quadra 605 Ratio | Base Dual-Memory Ratio |
|:---|---:|---:|---:|
| **KWhetstones / sec** | 1,527.655 | 5.194 | — |
| **Dhrystones / sec** | 24,699.261 | 1.430 | 1.043 |
| **Towers** | 0.350 s | 1.826 | 1.348 |
| **Quick Sort** | 0.432 s | 1.649 | 1.322 |
| **Bubble Sort** | 0.493 s | 1.542 | 1.261 |
| **Queens** | 0.328 s | 1.232 | 1.117 |
| **Puzzle** | 0.732 s | 1.493 | 1.400 |
| **Permutations** | 0.550 s | 1.478 | 1.146 |
| **Int. Matrix** | 0.444 s | 1.813 | 1.683 |
| **Sieve** | 0.820 s | 1.673 | 1.626 |
| **Benchmark Mix Average** | — | **1.933** | **1.791** |

---

## 3. Speedometer 4.02 — Performance Rating (PR)

| Test | Rating (Quadra 605 = 1.0) |
|:---|---:|
| **CPU** | 1.806 |
| **Graphics** | 0.967 |
| **Disk** | 2.280 |
| **Math** | **16.940** (up from 13.317 in Base!) |

---

## 4. Screenshots

Captured live on `10.0.2.192` via `/api/screenshots`:
- Stage E Speedometer Run (Benchmark Mix, FPU Benchmarks, PR): `20261025_161352-screen.png` (saved in `docs/perf/fp_store_changes_20261024/screen_stageE_speedometer.png`).
