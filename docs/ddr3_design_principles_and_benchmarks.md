# DDR3 SDRAM Architecture, Limitations, Best Practices, and Reference Implementations

**Author:** Antigravity / Pair Programming  
**Branch:** `pipelined-040-ddr3-vram`  
**Date:** October 26, 2026  
**Target:** MiSTer FPGA (Cyclone V SoC 5CSEBA6U23I7)

---

## 1. Executive Summary & Problem Statement

In the MacQuadra800 core, moving the 1 MB Video RAM (VRAM) from on-chip FPGA Block RAM (M10K BRAM) to external DDR3 SDRAM reclaimed **6,043 ALMs and 80 M10K blocks**, freeing critical FPGA resources for the pipelined 68040 CPU and FPU. However, initial benchmarks in Speedometer 4.02 revealed a performance degradation in the Graphics PR score:

* **Real Quadra 800 HW (33 MHz 68040):** **1.310** (Color QuickDraw 8-bit: **8.07 s**)
* **Dual-Issue BRAM Core (On-Chip VRAM):** **1.013** (Color QuickDraw 8-bit: **10.45 s**)
* **Initial DDR3 VRAM Core (Seed 38 / `da138b8`):** **0.851** (Color QuickDraw 8-bit: **12.65 – 13.21 s**)

The current DDR3 VRAM core runs at **65.0% of real hardware speed** and **84.0% of the internal BRAM core**. 

This document analyzes the fundamental physical characteristics and limitations of DDR3 on the Cyclone V SoC, examines how high-performance MiSTer cores (`ascal` and `Vectrex_MiSTer`) maximize DDR3 throughput, identifies the exact bottlenecks in the current core, and details the new architecture to bring graphics performance towards **1.2 – 1.3 PR**.

---

## 2. DDR3 Physical Architecture & Cyclone V Limitations

### 2.1 Hardware Topology on MiSTer (DE10-Nano)
On the MiSTer DE10-Nano board, DDR3 SDRAM is connected directly to the **Hard Processor System (HPS)** memory controller, operating at **400 MHz (800 MT/s DDR)** with a 32-bit physical bus. The FPGA logic communicates with this hard controller via the **FPGA-to-SDRAM (F2SDRAM) Multiport Front End (MPFE)** over Avalon-MM buses clocked at 100 MHz:

```
┌────────────────────────────────────────────────────────┐
│               Cyclone V FPGA Fabric                    │
│                                                        │
│   MacQuadra800 Core (ram1)       HDMI Scaler (vbuf)    │
│    64-bit @ 99.75 MHz clk_sys     128-bit @ 100 MHz    │
└──────────────┬────────────────────────────┬────────────┘
               │ Avalon-MM                  │ Avalon-MM
┌──────────────▼────────────────────────────▼────────────┐
│         F2SDRAM Multi-Port Front End (MPFE)            │
│               Hard Memory Controller                   │
│          DDR3 PHY (400 MHz Clock / 800 MT/s)           │
└──────────────────────────────┬─────────────────────────┘
                               │ 32-bit DDR3 Bus
┌──────────────────────────────▼─────────────────────────┐
│        1 GB DDR3 SDRAM Chip (MT41K256M16 / 48B)        │
└────────────────────────────────────────────────────────┘
```

### 2.2 Physical Limitations of DDR3 SDRAM
DDR3 SDRAM is organized internally into 8 banks of rows and columns. While peak sequential streaming throughput is enormous (3.2 GB/s physical, ~800 MB/s per 64-bit 100 MHz Avalon port), **random single-word access is severely latency-limited**:

1. **Row Cycle Overhead ($t_{RC}$, $t_{RCD}$, $t_{RP}$)**:
   * Accessing a new row in a bank requires a Precharge ($t_{RP} \approx 13.75\text{ ns}$), followed by Row Activation ($t_{RCD} \approx 13.75\text{ ns}$).
   * Opening a new page takes **~30 to 40 ns** before data can be addressed.
2. **CAS Latency ($CL$) & Round-Trip Bus Latency**:
   * Once a column read is issued, CAS latency is $CL \approx 13.75\text{ ns}$.
   * Across the Avalon-MM interface, FIFO bridges, and synchronizers, a single cold read round trip takes **15 to 22 clock cycles (150–220 ns)**.
3. **Read/Write Bus Turnaround ($t_{WTR}$, $t_{RTW}$)**:
   * Switching between write and read commands incurs bus turnaround dead cycles to allow I/O buffers to tristate and settle.
4. **The "Single-Beat Penalty"**:
   * If a system issues single 64-bit reads or writes (`burstcount = 1`), it incurs the full row/CAS/handshake latency on every single word.
   * **Single-beat write throughput**: 8 bytes / 80–100 ns = **~80 to 100 MB/s (10–12% efficiency)**.
   * **Burst write throughput (16 beats)**: 128 bytes / 160 ns = **~800 MB/s (100% efficiency)**.

---

## 3. Best Practices & Reference Implementations on MiSTer

High-throughput cores on MiSTer overcome DDR3 latency using two architectural pillars:
1. **Never perform unbuffered, single-beat writes to DDR.**
2. **Decouple the client execution engine with on-chip BRAM buffers and stream multi-beat bursts.**

### 3.1 Reference 1: `ascal.vhd` (MiSTer Advanced Video Scaler)
In [`sys/ascal.vhd`](file:///Users/alans/dev2/MacQuadra800_MiSTer/sys/ascal.vhd#L1760-L1812), the video scaler buffers incoming raster data into an internal Dual-Port RAM (`i_dpram`). When a burst boundary is reached, it initiates an Avalon write transaction:

```vhdl
WHEN sWRITE =>
    avl_write_i <= '1';
    IF avl_write_i = '1' AND avl_waitrequest = '0' THEN
        IF (avl_rad MOD BLEN) = BLEN - 1 THEN
            avl_write_i <= '0';
            avl_state   <= sIDLE;
        END IF;
    END IF;
...
avl_burstcount <= std_logic_vector(to_unsigned(BLEN, 8));
avl_rad_c      <= (avl_rad + 1) MOD (2 * BLEN)
                  WHEN avl_write_i = '1' AND avl_waitrequest = '0' ELSE avl_rad;
```

#### Key Architecture Principles in `ascal`:
* **Continuous Streaming**: `avl_write` is held asserted across all beats.
* **1 Beat per Clock Cycle**: On every clock cycle where `avl_waitrequest == '0'`, exactly one 128-bit beat is absorbed by the memory controller, and `avl_rad` immediately increments to supply the next beat.
* **Zero Inter-Beat Handshake**: No request/acknowledge handshakes occur between individual beats; the entire burst of `BLEN` beats completes back-to-back at the full bus clock rate.

---

### 3.2 Reference 2: `Vectrex_MiSTer` (`vfb_ddr_arbiter.sv` & `vfb_tile_cache_manager.sv`)
The Vectrex MiSTer core implements an emulated vector display with full raster CRT persistence and artwork overlay compositing. It uses a custom framebuffer pipeline in [`rtl/videodr0me_fb/`](file:///Users/alans/dev2/Vectrex_MiSTer/rtl/videodr0me_fb/).

#### Key Architecture Principles in Vectrex:
1. **Single-Cycle Advance Strobe (`write_beat`)**:
   In [`vfb_ddr_arbiter.sv`](file:///Users/alans/dev2/Vectrex_MiSTer/rtl/videodr0me_fb/vfb_ddr_arbiter.sv#L214-L236):
   ```systemverilog
   assign DDRAM_WE   = internal_we && !discard_q;
   wire   write_beat = discard_q || (DDRAM_WE && !DDRAM_BUSY);
   assign flush_advance = (arb_state == ARB_FLUSH) && write_beat;

   always_ff @(posedge clk_sys) begin
       case (arb_state)
       ARB_FLUSH: begin
           if (flush_advance) begin
               burst_counter <= burst_counter + 1'b1;
               if (burst_counter == burst_target - 1) begin
                   internal_we <= 0;
                   flush_done  <= 1;
                   arb_state   <= ARB_IDLE;
               end
           end
       end
   ```
   * As long as `!DDRAM_BUSY`, every single clock cycle is a valid write beat.
   * Data (`flush_din`) shifts to the next word on `flush_advance` with zero bubble cycles.
2. **Associative BRAM Tile Cache Decoupling**:
   * The vector drawing engine operates exclusively on an associative BRAM tile cache (`vfb_tile_cache_manager.sv`).
   * When drawing lines or points, vector writes hit in BRAM in **1 cycle (0 wait states)**.
   * Evictions and fills are batched into **16-beat (128-byte) DDR3 bursts**.

---

## 4. Bottleneck Diagnosis of the Prior MacQuadra800 Implementation

Why did our previous DDR3 VRAM core score **0.851** when the BRAM core achieved **1.013**?

### Bottleneck A: The Single-Beat Write Stop-and-Wait Loop
In [`rtl/vram_ddr3.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/vram_ddr3.sv#L442-L451), every write from the FIFO to DDR3 was issued as a single beat:
```systemverilog
vram_ddr_burstcnt <= 8'd1;
vram_ddr_we       <= 1'b1;
state             <= S_CPU_WRITE;
```
In [`MacQuadra800.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/MacQuadra800.sv#L1167-L1241):
```systemverilog
if (!vram_ddr_req) vram_ddr_accept <= 0;
...
else if (vram_ddr_req && !vram_ddr_accept) begin
    ddram_we        <= 1;
    vram_ddr_accept <= 1;
    vram_ddr_ack    <= 1;
end
```
* Once `vram_ddr_accept <= 1` was set, `MacQuadra800.sv` deasserted `ddram_we` after 1 cycle and refused to accept any subsequent write until `vram_ddr_req` dropped low to 0.
* In `vram_ddr3.sv`, after seeing `vram_ddr_ack`, the FSM dropped `vram_ddr_req <= 0` and transitioned through `S_IDLE`.
* Total time to drain a single 64-bit word: **8 to 10 clock cycles (80–100 ns)**.
* **Effective write drain bandwidth: ~80 MB/s (10% of bus capability).**

### Bottleneck B: The Store Buffer Backpressure Cascade
* The 68040 CPU can issue writes every **30 to 60 ns** during QuickDraw fills, rectangle drawing, and text rendering.
* The CPU write FIFO in `vram_ddr3.sv` is 16 entries deep.
* `vram_wq_room` is defined as `(fifo_count < (FIFO_DEPTH - 4))` (i.e. `< 12`).
* When the CPU emits a burst of stores, after just 12 stores (less than 500 ns of drawing code), the FIFO reaches 12 entries.
* `vram_wq_room` drops to 0.
* In [`rtl/quadra800.sv` line 710](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/quadra800.sv#L710):
  ```systemverilog
  wire bus_vram_direct = ... && mem_vram_wq_room;
  ```
  `bus_vram_direct` becomes 0!
* The CPU drops off the 0-wait-state fast path and is forced through `bus_req_adapter` $\rightarrow$ `S_MEM` $\rightarrow$ wombat bus adapter.
* **The CPU stalls for 5 CPU cycles (150 ns) per store until DDR3 drains.**

### Bottleneck C: Vertical Strided Read Misses in QuickDraw Blits
* Color QuickDraw `CopyBits` and pattern fills perform Read-Modify-Write operations: reading destination pixels, masking with patterns, and writing back.
* Destination reads frequently step vertically from scanline to scanline (stride = 1024 bytes).
* The 32-byte horizontal read line cache hit sequential horizontal runs, but **missed on every vertical step**, stalling the CPU for ~180 ns on each scanline read.

---

## 5. The New High-Throughput DDR3 Architecture

To bridge the performance gap and target **1.2 – 1.3 PR**, the architecture is overhauled based on the `ascal` and `Vectrex` models:

```
┌────────────────────────────────────────────────────────┐
│ 68040 CPU Direct Writes (0 Wait States)                │
└───────────────────────────┬────────────────────────────┘
                            │ Push / Coalesce
┌───────────────────────────▼────────────────────────────┐
│ Write Queue & Contiguous Burst Scanner                 │
│ Detects sequential runs (e.g. 2, 4, or 8 beats)        │
└───────────────────────────┬────────────────────────────┘
                            │ Multi-Beat Burst
┌───────────────────────────▼────────────────────────────┐
│ Pipelined Streaming Arbiter (`MacQuadra800.sv`)        │
│   `write_beat = ddram_we && !DDRAM_BUSY`               │
│   Drains 1 beat / clock cycle (800 MB/s sustained)     │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Cyclone V HPS DDR3 Controller                          │
└────────────────────────────────────────────────────────┘
```

### 5.1 Component 1: Streaming Burst Write Drains
1. **Contiguous Burst Detection**:
   * When popping from the write FIFO, inspect pending entries for contiguous word addresses (`fifo_addr[k+1] == fifo_addr[k] + 1`).
   * Group up to 4 or 8 contiguous words into a single burst (`burstcnt = N`).
2. **Single-Cycle Data Streaming**:
   * Hold `ddram_we = 1` during the burst.
   * Advance `fifo_rptr` and update `ddram_din` / `ddram_be` on every cycle where `write_beat = (ddram_we && !DDRAM_BUSY)`.
   * **Result**: Draining 4 beats drops from **36 cycles to 4 cycles** (an ~9x speedup). The FIFO drains faster than the CPU can fill it, maintaining `vram_wq_room = 1` and keeping CPU stores at **0 wait states**.

### 5.2 Component 2: 4-Way / 2D Read Cache for QuickDraw Blits
* Allocate a 4-line associative BRAM cache (4 lines $\times$ 32 bytes = 128 bytes total, or 256 bytes) dedicated to CPU VRAM reads.
* Vertical QuickDraw operations hitting recent scanlines will hit in BRAM in **1 cycle**, completely eliminating the 180 ns DDR turnaround latency for RMW blits.

### 5.3 Component 3: Clean Scanline 0 Display Buffer Phase Alignment
* In [`rtl/dafb.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/dafb.sv#L457-L466) and [`rtl/vram_ddr3.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/vram_ddr3.sv#L91-L102), synchronize the display buffer swap toggle so Word 0 of line 0 (the Mac menu bar) is read strictly from the newly prefetched buffer, eliminating top-left pixel glitches.

---

## 6. Implementation and Verification Plan

1. **RTL Modifications**:
   * Update [`MacQuadra800.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/MacQuadra800.sv) to support streaming multi-beat write bursts on `ram1`.
   * Update [`rtl/vram_ddr3.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/vram_ddr3.sv) with burst detection, `write_beat` FIFO advance, and 4-way read cache.
   * Align `vid_line_swap` timing in [`rtl/dafb.sv`](file:///Users/alans/dev2/MacQuadra800_MiSTer/rtl/dafb.sv).
2. **Simulation Validation**:
   * Run Verilator testbench `verilator/tb_vram_ddr3.sv` covering burst writes, single writes, write combining, read hits, and DMA prefetch arbitration.
3. **Hardware Compilation & Timing Closure**:
   * Compile Seed 40 on `misterubuntu`.
   * Verify positive setup slack on all clocks (`TNS = 0.000`).
4. **Hardware Benchmarking**:
   * Deploy to MiSTer `10.0.2.192`.
   * Verify screen visual integrity via automated screenshot grab.
   * Run Speedometer 4.02 and record Graphics PR score.
