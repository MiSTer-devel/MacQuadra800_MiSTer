# Hardware Benchmark Results: Stages A–F Optimizations

**Platform:** MiSTer FPGA (`10.0.2.192`), Mac OS 8.1, 32 MB RAM, QuadSquad8 SCSI disk image.  
**Bitstream:** `MacQuadra800_dual_small33_stgF_261025.rbf` (md5 `7e775471204d53217227c25d6ac7b1d3`).  
**Branch:** `pipelined-040-small33` (commit `b03911f`).  
**Timing:** Met on all clocks (+0.112 ns worst slack on 33 MHz system domain).  
**Area:** 30,168 ALUTs, 12,511 registers (+489 ALUTs / +1.65% total over dual-memory base).

---

## 1. Speedometer 4.02 — FPU Benchmarks

| Metric | Base Dual (33 MHz) | Stage D (33 MHz) | Stage E (33 MHz) | **Stage F (33 MHz)** | Total Delta vs Base | Shipping Core (20260930) |
|:---|---:|---:|---:|---:|---:|---:|
| **KWhetstones / sec** | 3,505.131 | 4,319.505 | 4,377.287 | **4,406.470** | **+25.72%** | 4,589.450 |
| **Matrix Mult (sec)** | 0.836 | 0.781 | 0.780 | **0.749** | **-10.41%** | 0.690 |
| **Fast Fourier (sec)** | 0.406 | 0.386 | 0.386 | **0.371** | **-8.62%** | 0.301 |
| **FPU Average Rating** | 0.741 | 0.826 | 0.830 | **0.855** | **+15.38%** | 0.953 |

*Note: Across Stages A–F, KWhetstones has climbed from 3,505 to **4,406.5 KWhetstones/sec** (+25.7%), closing **83.1%** of the performance gap to the shipping core with only +489 ALUTs (+1.65%) area overhead.*

---

## 2. Speedometer 4.02 — Benchmark Mix

| Test | Raw (sec / ops) | Quadra 605 Ratio | Real Quadra 800 HW Ratio | Dual vs. Real Quadra 800 HW |
|:---|---:|---:|---:|:---:|
| **KWhetstones / sec** | 1,527.732 | 5.194 | 6.727 | 77.2% |
| **Dhrystones / sec** | 24,706.767 | 1.430 | 1.447 | 98.8% |
| **Towers** | 0.350 s | 1.827 | 1.364 | **+34.0% faster** |
| **Quick Sort** | 0.432 s | 1.650 | 1.340 | **+23.1% faster** |
| **Bubble Sort** | 0.493 s | 1.542 | 1.343 | **+14.8% faster** |
| **Queens** | 0.327 s | 1.233 | 1.315 | 93.8% |
| **Puzzle** | 0.732 s | 1.493 | 1.367 | **+9.2% faster** |
| **Permutations** | 0.550 s | 1.478 | 1.315 | **+12.5% faster** |
| **Int. Matrix** | 0.444 s | 1.814 | 1.344 | **+35.0% faster** |
| **Sieve** | 0.819 s | 1.675 | 1.409 | **+18.9% faster** |
| **Benchmark Mix Average** | — | **1.934** | **1.897** | **+1.95% faster than Real Quadra 800!** |

---

## 3. Speedometer 4.02 — Performance Rating (PR)

| Test | Stage F Rating | Real Quadra 800 HW | Shipping Core | Dual vs. Real Quadra 800 HW |
|:---|---:|---:|---:|:---:|
| **CPU** | **1.806** | 1.184 | 0.798 | **+52.5% faster!** |
| **Graphics** | 0.954 | 1.310 | 1.179 | 72.8% (SDRAM arbitration) |
| **Disk** | 2.361 | 3.576 | 2.488 | 66.0% (SCSI image) |
| **Math** | **16.959** | 19.995 | 21.451 | 84.8% (up from 66% base!) |
| **Overall PR** | **1.596** | **1.593** | 1.267 | **Beats Real Quadra 800 HW!** |

---

## 4. Screenshots

Captured live on `10.0.2.192` via `/api/screenshots`:
- Stage F Speedometer 4.02 Suite: `20261026_003603-screen.png` (saved in `docs/perf/fp_store_changes_20261024/screen_stageF_speedometer.png`).
