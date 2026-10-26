# Architecture Plan: 1 MB DDR3 VRAM & Scanline Cache for MacQuadra800

**Branch:** `pipelined-040-ddr3-vram`  
**Base Commit:** `8212246` (Stages A–F dual-issue core with all FPU optimizations)  
**Target:** Enable full Quadra 800 video capabilities (1 MB / 2 MB VRAM, 16-bit / 24-bit TrueColor, 832×624, 1152×870) by migrating VRAM from on-chip M10K BRAM to DDR3 with an ultra-low-jitter scanline cache.

---

## 1. Background & Motivation

### Current Limitations of M10K BRAM VRAM
- On-chip FPGA M10K memory is scarce (Cyclone V 5CSEBA6 has ~553 M10K blocks total = 707 KB).
- To fit within FPGA BRAM, the current core implements **320 KB of VRAM** via row-stride compaction (storing 640 bytes per 1024-byte pitch, sharing a scratch tail for row padding).
- **Consequences:**
  1. Consumes **~260 M10K blocks** (nearly half of the entire FPGA's block RAM!).
  2. Artificially caps the Quadra 800 to **8 bpp at 640×480** (cannot support 16 bpp DirectColor or 24 bpp TrueColor).
  3. Cannot support larger Quadra monitor resolutions (832×624 16" RGB, 1152×870 21" Two-Page Display).

### Opportunity: Idle DDR3 Memory
- System RAM (32 MB) runs on the 16-bit 99 MHz SDRAM daughterboard.
- The 64-bit DDR3 memory interface on MiSTer is currently used only for ROM (1 MB) and Ethernet buffers. During display execution, DDR3 is nearly 100% idle.
- DDR3 bandwidth at 33 MHz (64-bit wide) provides **264 MB/s** burst bandwidth—far exceeding the peak scanout requirement of 640×480@24bpp (75 MB/s) or 832×624@8bpp (57 MB/s).

---

## 2. Architecture Design

```
+-------------------------------------------------------------+
|                     68040 CPU / DMU                         |
+-------------------------------------------------------------+
                              |
                     VRAM Beat Port ($F9000000)
                              |
                              v
                +----------------------------+
                |    VRAM CPU Write Buffer   |
                |   (Coalescing 64-bit/Burst)|
                +----------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     DDR3 Memory Controller                  |
|               (1 MB / 2 MB VRAM Framebuffer)                |
+-------------------------------------------------------------+
                              |
                     Burst Read DMA
                              |
                              v
+-------------------------------------------------------------+
|               Ping-Pong Scanline Cache (BRAM)               |
|   Line Buffer A (Active Scanout) <-> Line Buffer B (Pre-fetch)|
|               (Total Size: ~8 to 16 M10K blocks)             |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                  DAFB Pixel Generator & VGA                 |
|               (1/2/4/8 bpp CLUT, 16/24 bpp Direct)          |
+-------------------------------------------------------------+
```

### Component Details

#### 1. DDR3 Framebuffer Allocation
- Allocate 1 MB or 2 MB in DDR3 address space:
  - `DDR_VRAM_BASE = 29'h0500_0000` (byte `0x2800_0000 >> 3`).
- Flat, standard linear address mapping: `address = row * stride + column`. No compaction or aliasing needed.

#### 2. Ping-Pong Scanline Cache in `dafb.sv`
- **Structure:** Two line buffers instantiated as dual-port BRAM:
  - Width: 64-bit or 32-bit.
  - Depth: 1024 or 2048 words (accommodates up to 1152 pixels at 24bpp / 32bpp).
  - Total BRAM footprint: Only **8 to 16 M10K blocks** (saving ~245 M10K blocks vs. current design!).
- **Operation:**
  - When `vcnt` advances to scanline $N$, scanout reads from `Buffer A` using `clk_vid`.
  - Concurrently, during HBLANK and early line time, a burst read DMA requests the pixels for line $N+1$ from DDR3 into `Buffer B` using `clk_sys`.
  - At each HSYNC / line start, the buffers swap.

#### 3. CPU Write Path & Coherency
- CPU writes to `$F9000000 - $F91FFFFF`:
  - QuickDraw primarily performs longword writes.
  - Writes are queued and written to DDR3.
  - If a CPU write targets the line currently residing in the prefetch scanline buffer, the scanline buffer is either write-through updated or re-fetched.

#### 4. DAFB TrueColor Video Expansion
- In [`rtl/dafb.sv`](../rtl/dafb.sv):
  - Add 16 bpp (5-5-5 RGB) and 24 bpp (8-8-8 RGB) unpackers to the pixel generation pipeline.
  - Update DAFB register decoding to advertise 1 MB VRAM and accept 16/24-bit pixel modes.

---

## 3. Implementation Steps

1. **Phase 1: DDR3 VRAM Framebuffer & DMA Controller**
   - Implement `vram_ddr3_dma` module: handles DDR3 scanline burst requests and CPU write arbitration.
   - Hook into `MacQuadra800.sv` DDR3 interface alongside the ROM bridge.
2. **Phase 2: Ping-Pong Line Buffer in `dafb.sv`**
   - Replace the single-cycle `vid_rdata` random-access port with the continuous streaming scanline buffer.
   - Verify 640×480 8 bpp scanout bit-for-bit matches existing display output.
3. **Phase 3: TrueColor (16/24 bpp) and Resolution Expansion**
   - Implement 16bpp and 24bpp pixel unpackers in `dafb.sv`.
   - Update monitor sense and VRAM size probe response (1 MB).
4. **Phase 4: Hardware Verification on MiSTer**
   - Deploy to `10.0.2.192`.
   - Verify Mac OS 8.1 Monitors & Sound control panel offers "Thousands" and "Millions" of colors.
   - Measure Speedometer graphics and mix benchmarks.
