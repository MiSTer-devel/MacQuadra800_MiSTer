# FP Store and FMOVEM Optimizations (2026-10-24)

This report details the implementation, verification, cycle measurements, benchmark speedups, and synthesis area impact for four stages of optimizations targeting floating-point stores and FMOVEM in the dual-issue 68040 core (`rtl/ap68040_faster`).

All work followed the guiding rule: **"make sure each change actually improves the speed enough to be worth any extra size increase."**

---

## 1. Summary of Optimizations

### Stage A (Changes 1 & 4)
- **Change 1 (Live Done Bypass):** In `ap68040_fpif.sv`, evaluate `live_done = go && f_done && !f_excreq && !f_unimp && !f_unsupp;` to release the store DISP uop immediately when the FPU reports a clean completion, eliminating the redundant 1-cycle `done_q` wait.
- **Change 4 (Drop GET Micro-ops):** Export `get_w1` (`get_q[63:32]`) and `get_w2` (`get_q[31:0]`) from `ap68040_fpif` directly to `ap68040_backend`. Select these words directly on `OP_MOV` stores when `cond == 1` or `cond == 2`. Drop `GET` micro-ops from `FPU_OUT8`, `FPU_OUT12`, `FPU_K_OUT8`, `FPU_K_OUT12`, and `FPU_MVS` in `ucode.py`.

### Stage B (Change 2)
- **Change 2 (Dispatch-Clock Store in `ap040_fpu.v`):** In `F_IDLE` when `op_class == 3'b011`:
  - **Extended precision (`src_fmt == 3'd2`):** Raw pass-through `{fr_src_s, fr_src_e, 16'd0, fr_src_m}` directly into `dout` with `done <= 1`, `fpu_used <= 1`, `r_op <= 7'h7F`, remaining in `F_IDLE`.
  - **Single & Double precision (`src_fmt == 3'd1 / 3'd5`):** For normal register values (`st_norm && st_sE >= min_exp && !sd_ov && !(sd_inx && fpcr[9])`), select `fr_src_*` into the shared rounder in `F_IDLE`, registering `dout <= sd_out`, `done <= 1`, `fpu_used <= 1`, and setting INEX in FPSR if needed, remaining in `F_IDLE`. Abnormal, denormal, overflow, and enabled-trap cases keep the full existing `F_SRC` / `F_SHR` / `F_STDONE` path.

### Stage C (FMOVEM Empty Slot Optimization)
- In `ap68040_fpif.sv`, when `!cur_on` (register not in the transfer mask), skip `mvr_wait = 1'b1` hold in `FC_MVR`. Empty slots complete `FC_MVR` in 1 cycle rather than stalling for an unused register-file read.

### Stage D (FMOVEM Dynamic Uop Bypass)
- In `ap68040_useq.sv`, when decoding static FMOVEM transfers (`!src.ext1[11]`), inspect the register mask at dispatch. If a slot is unselected, suppress micro-op emission (`wv = 0`) and advance `na` directly to the next active slot or exit sequence (`UA_FPU_MVS_EXIT` / `UA_FPU_MVL_EXIT`). On the last micro-op of each active slot, if no more registers remain in the mask, branch directly to the exit sequence.
- In `ap68040_fpif.sv`, bind `cur_slot = dynk` so slot-to-register decoding is direct and independent of skipped slots. Dynamic lists fall back cleanly to the unrolled path.

---

## 2. Micro-Benchmark Cycle Counts (`fpstore.s`)

Measured with cycle-accurate probes on the dual-issue pipeline parameters (`DUAL=1`, `DIV_STEPS=2`, `BTIC=1`, `FPU_PIPE=0`, `S1_CLASSES=3'b011`):

| Tag | Kernel | Baseline | Stage A | Stage B | Stage C | Stage D | Cumulative Delta | Speedup |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| `$2x` | `fmove.d fp0,(a0)+` | 10.99 | 8.99 | 7.99 | 7.99 | **7.99** | **-3.00 clk** | **+37.5%** |
| `$3x` | `fmove.d fp0,(a0)` | 10.99 | 8.99 | 7.99 | 7.99 | **7.99** | **-3.00 clk** | **+37.5%** |
| `$4x` | `fmove.d (a0)+ ; addq` | 11.99 | 9.99 | 8.99 | 8.99 | **8.99** | **-3.00 clk** | **+33.4%** |
| `$5x` | `fmove.d (a0) ; addq` | 11.99 | 9.99 | 8.99 | 8.99 | **8.99** | **-3.00 clk** | **+33.4%** |
| `$6x` | `fmove.s fp0,(a0)+` | 8.99 | 7.99 | 6.99 | 6.99 | **6.99** | **-2.00 clk** | **+28.6%** |
| `$7x` | `fmove.x fp0,(a0)+` | 12.99 | 9.99 | 8.99 | 8.99 | **8.99** | **-4.00 clk** | **+44.5%** |
| `$8x` | `fmove.x fp0,-(a7)` | 12.96 | 9.96 | 8.96 | 8.96 | **8.96** | **-4.00 clk** | **+44.6%** |
| `$9x` | `fmovem.x fp0-fp1,-(a7)` | 79.00 | 62.00 | 62.00 | 57.00 | **26.00** | **-53.00 clk** | **+203.8%** |
| `$Ax` | `fmovem.x (a7)+,fp0-fp1` | 55.00 | 55.00 | 55.00 | 55.00 | **25.00** | **-30.00 clk** | **+120.0%** |
| `$Bx` | `fmove.l fp0,(a0)+` | 10.99 | 9.99 | 9.99 | 9.99 | **9.99** | **-1.00 clk** | **+10.0%** |
| `$Cx` | `move.l d1,(a0)+` | 0.99 | 0.99 | 0.99 | 0.99 | **0.99** | 0.00 clk | 1.000x |
| `$Dx` | `fmove.d (a0)+,fp0` | 7.98 | 7.98 | 7.98 | 7.98 | **7.98** | 0.00 clk | 1.000x |
| `$Ex` | `fadd.x ; fmove.d` | 16.98 | 14.98 | 13.98 | 13.98 | **13.98** | **-3.00 clk** | **+21.5%** |
| `$Fx` | `fmove.d ; fmove.d ld` | 18.98 | 16.98 | 15.98 | 15.98 | **15.98** | **-3.00 clk** | **+18.8%** |

---

## 3. Macro-Benchmark Speedups (Cycle Accuracy)

Simulated across full multi-iteration C benchmark binaries on Verilator:

| Benchmark | Baseline (cyc/iter) | Stage A | Stage B | Stage C | Stage D | Total Savings | Total Speedup |
|:---|---:|---:|---:|---:|---:|---:|---:|
| **Whetstone** | 515,900 | 497,912 | 495,098 | 491,898 | **452,934** | **-62,966 cyc (-12.21%)** | **1.139x** |
| **MatMul 20x20** | 540,788 | 524,786 | 516,786 | 516,786 | **516,786** | **-24,002 cyc (-4.44%)** | **1.046x** |
| **FFT 256-pt** | 847,728 | 796,278 | 772,320 | 772,116 | **769,702** | **-78,026 cyc (-9.20%)** | **1.101x** |

#### Comparison to Shipping Quadra 800 Core (33 MHz):
* **Shipping Quadra 800 Whetstone:** **446,507 cycles**
* **Dual Core Stage D Whetstone:** **452,934 cycles**
* **Remaining Gap:** **6,427 cycles (only 1.4% away from parity!)**
  * *We have now closed **90.7%** of the original 69,393-cycle deficit on Whetstone.*

---

## 4. Verification Gates (All Passed Bit-for-Bit)

Every stage passed the three verification gates before any area or benchmark was recorded:

1. **CPU Regression Suite (`run_regress.sh`):**
   - 45 assembly programs across 5 bus timing configurations = **225 test cases**.
   - Result: **225 of 225 PASSED** on Stage A, Stage B, Stage C, and Stage D.
2. **Quadra Adapter Testbench (`run_adapter.sh`):**
   - 6 test configurations (1x and 2x clocks with normal, fast, and platform SDRAM controllers).
   - Result: **6 of 6 PASSED** on Stage A, Stage B, Stage C, and Stage D.
3. **Differential Random FPU/Store Verification (`run_fpdiff.sh`):**
   - 14 random seeds generating **21,000 instructions** with ~2,400 logged exceptions and random register/memory dumps.
   - Result: **`FPDIFF_ALL_SAME`** (100% bit-for-bit identical memory and exception state against baseline on all 14 seeds).

---

## 5. Synthesis Resource Utilization & Area Analysis

Quartus Prime 17.0 Lite Analysis & Synthesis (`MacQuadra800.map.rpt`) comparing Cyclone V resource usage:

| Hierarchy / Entity | Baseline ALUTs | Stage A | Stage B | Stage C | Stage D ALUTs | Stage D vs Base | Stage D vs C |
|:---|---:|---:|---:|---:|---:|---:|---:|
| `sys_top` (whole SoC) | 50,604 | 50,709 | 50,785 | 50,774 | **50,905** | **+301** | +131 |
| `emu` (emulator top) | 41,556 | 41,652 | 41,729 | 41,718 | **41,831** | **+275** | +113 |
| `ap68040` (whole CPU) | 29,679 | 29,765 | 29,859 | 29,858 | **29,924** | **+245 (+0.82%)** | **+66 (+0.22%)** |
| `ap68040_backend` | 16,297 | 16,338 | 16,601 | 16,547 | **16,558** | +261 | +11 |
| `ap68040_fpif` | 6,953 | 6,963 | 7,199 | 7,181 | **7,174** | +221 | -7 |
| `ap040_fpu` | 6,336 | 6,318 | 6,558 | 6,535 | **6,539** | +203 | +4 |
| `ap68040_useq` | 2,785 | 2,787 | 2,809 | 2,811 | **2,893** | +108 | +82 |
| `ap68040_dmu` | 5,253 | 5,263 | 5,257 | 5,238 | **5,238** | -15 | 0 |

### Dedicated Registers and DSP Blocks:
* **Registers:** Baseline 12,469 -> Stage D **12,510 (+41 regs, +0.33%)**
* **DSP Blocks:** Baseline 15 -> Stage D **15 (0 delta)**
* **Block Memory:** Baseline 3,722,339 bits -> Stage D **3,722,339 bits (0 delta)**

### ROI Evaluation against Rule:
- Total CPU ALUT increase for Stage D is **+66 ALUTs (+0.22%)** and **+9 registers**.
- Total CPU ALUT increase across ALL FOUR stages (A + B + C + D) is only **+245 ALUTs (+0.82%)**.
- Speedup achieved: **-67.1% on FMOVEM push**, **-54.5% on FMOVEM pop**, **-12.21% on Whetstone** (closing **90.7%** of the gap to shipping Quadra 800), **-9.20% on FFT**, **-4.44% on MatMul**.
- **Conclusion:** Outstanding ROI. The architectural compatibility remains 100% verified bit-for-bit, while Whetstone performance is now within 1.4% of the original Quadra 800 hardware core.
