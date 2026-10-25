# Hardware Benchmark Results: Stage A–D Optimizations

**Platform:** MiSTer FPGA (`10.0.2.192`), Mac OS 8.1, 32 MB RAM, QuadSquad8 SCSI disk image.  
**Bitstream:** `MacQuadra800_dual_small33_stgD_261025.rbf` (md5 `a7f98399ec0a506f19881f435fde0d3b`).  
**Branch:** `pipelined-040-small33` (commit `dc0a345`).  
**Timing:** Met on all clocks (+0.094 ns worst slack on 33 MHz system domain).  
**Area:** 29,924 ALUTs, 12,510 registers (+245 ALUTs / +0.82% over dual-memory base).

---

## 1. Speedometer 4.02 — FPU Benchmarks

| Metric | Base Dual-Memory (33 MHz) | Stage A–D Small (33 MHz) | Delta | Shipping Core (20260930) |
|:---|---:|---:|---:|---:|
| **KWhetstones / sec** | 3,505.131 | **4,319.505** | **+23.23%** | 4,589.450 |
| **Matrix Mult (sec)** | 0.836 | **0.781** | **-6.58%** | 0.690 |
| **Fast Fourier (sec)** | 0.406 | **0.386** | **-4.93%** | 0.301 |
| **FPU Average Rating** | 0.741 | **0.826** | **+11.47%** | 0.953 |

*Note: Whetstone performance improved by +23.2% (from 3,505 to 4,320 KWhetstones/sec), closing ~75% of the performance gap between the dual core and the shipping core on real hardware with only +245 ALUTs area overhead.*

---

## 2. Speedometer 4.02 — Benchmark Mix

| Test | Raw (sec / ops) | Quadra 605 Ratio | Base Dual-Memory Ratio |
|:---|---:|---:|---:|
| **KWhetstones / sec** | 1,453.987 | 4.944 | — |
| **Dhrystones / sec** | 29,817.617 | 1.726 | 1.043 |
| **Towers** | 0.349 s | 1.830 | 1.348 |
| **Quick Sort** | 0.437 s | 1.631 | 1.322 |
| **Bubble Sort** | 0.496 s | 1.534 | 1.261 |
| **Queens** | 0.329 s | 1.227 | 1.117 |
| **Puzzle** | 0.783 s | 1.395 | 1.400 |
| **Permutations** | 0.577 s | 1.411 | 1.146 |
| **Int. Matrix** | 0.548 s | 1.468 | 1.683 |
| **Sieve** | 0.822 s | 1.669 | 1.626 |
| **Benchmark Mix Average** | — | **1.883** | **1.791** |

---

## 3. Screenshots

Captured live on `10.0.2.192` via `/api/screenshots`:
- Both Benchmark Mix and FPU Benchmarks complete: `20261025_152153-screen.png` (saved in `scratch/screen_sp_both_final.png`).
