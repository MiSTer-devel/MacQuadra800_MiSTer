# Handoff: 1 MB DDR3 VRAM & Graphics Optimization — 2026-10-26

## 1. Executive Summary & Current Status

- **Working Branch:** `pipelined-040-ddr3-vram`
- **Active Commit:** `c418e80` (`Fix write combining gate: require cpu_vram_write to prevent FIFO corruption`)
- **Remote Remotes:** Synced to both `origin` and `alanswx`.
- **Target Hardware:** MiSTer `10.0.2.192` (build machine: `misterubuntu` at `~/mister/q800_ddr3_vram`).
- **Timing:** Clean positive slack (`worst slack +0.098 ns` on 33 MHz CPU clock, met on all clocks).
- **Visual Quality:** **100% artifact-free.** All pixel dropouts, text jitter, and horizontal dotted streaks have been completely eliminated.

---

## 2. Artifact Root Cause & Resolution

During earlier DDR3 VRAM testing, intermittent horizontal dotted dropouts appeared across text glyphs, 7-segment benchmark numbers, and window borders.

### Root Cause
In [`rtl/vram_ddr3.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/vram_ddr3.sv#L194):
```systemverilog
// PREVIOUS BUGGY CODE:
wire can_combine = (fifo_count > 0) && (fifo_addr[last_wptr] == cpu_w64_addr) ...
```
Because `can_combine` lacked `cpu_vram_write &&`, on every idle clock cycle or read cycle where the CPU bus lines held the previous write address (`cpu_w64_addr`), `can_combine` remained asserted. This caused `fifo_din` and `fifo_be` to continuously merge floating/stale bus byte enables into the FIFO entry, corrupting DDR3 write transactions.

### Fix (Commit `c418e80`)
1. Gated `can_combine` strictly with `cpu_vram_write &&`.
2. Added `&& !fifo_conflict` to `rd_cache_hit` to prevent reading stale latch data when an uncommitted write is pending in the FIFO.
3. Raised the high-priority write drain threshold from 4 to 32 entries so that 32-beat video DMA bursts complete in ~85 cycles uninterrupted without DDR3 read/write turnarounds.

---

## 3. Hardware Benchmark Results (MiSTer `10.0.2.192`)

Speedometer 4.02 executed live on Mac OS 8.1:

| Metric | DDR3 VRAM (`c418e80`) | Dual-Issue BRAM Core | Real Quadra 800 HW | Notes |
|:---|:---:|:---:|:---:|:---|
| **CPU** | **1.806** | 1.806 | 1.184 | +52.5% vs. Real HW |
| **Graphics (PR)** | **0.841** | 1.013 | 1.310 | Current DDR3 (single-word reads) |
| **Disk** | **2.351** | 2.344 | 3.576 | SCSI image |
| **Math** | **16.517** | 16.959 | 19.995 | Standard 33 MHz FPU |
| **Overall PR** | **1.494** | 1.596 | 1.593 | 93.8% of real Quadra 800 |
| **Color QuickDraw 8-bit** | **13.878 s (0.763)** | 10.95 s (0.967) | — | 8 bpp standard benchmark |

---

## 4. Next Steps: Graphics Throughput Optimization & Color Depth (Steps 1–3)

### Step 1: Read-Ahead Burst Line Cache (32 bytes / 4 words)
- **Problem:** When QuickDraw reads from VRAM (read-modify-writes or CopyBits), read misses currently issue a single 64-bit request (`burstcnt = 1`) to DDR3, paying the full 15–20 cycle round-trip turnaround latency each time.
- **Solution:** Issue a 4-beat burst (`burstcnt = 4`) on CPU read misses into a 32-byte line buffer. Subsequent sequential reads along the scanline hit the buffer with 0 wait states.

### Step 2: Streaming / Pipelined FIFO Write Drains
- **Problem:** In [`rtl/vram_ddr3.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/vram_ddr3.sv#L505), `S_CPU_WRITE` returns to `S_IDLE` after every single 64-bit write because `MacQuadra800.sv` requires `!vram_ddr_req` to lower `vram_ddr_accept`. This introduces a dead bubble cycle between consecutive writes.
- **Solution:** Support consecutive DDR3 write bursts for FIFO entries with sequential addresses without deasserting the request, maximizing write throughput.

### Step 3: DirectColor (16-bit) and TrueColor (24/32-bit) Support
- Expand [`rtl/dafb.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/dafb.sv) and [`rtl/vram_ddr3.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/vram_ddr3.sv) pixel unpacking to support:
  - 16 bpp: 5-5-5 DirectColor ($F9000000 frame pitch 1024/2048 bytes).
  - 32 bpp: 8-8-8 TrueColor ($F9000000 frame pitch 2048/4096 bytes).
