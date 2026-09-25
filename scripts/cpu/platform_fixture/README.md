# Platform Whetstone fixture

The Speedometer Whetstone image (`scratch/whetstone_full_fixture_20260920/ram.bin`)
running on the machine's real memory path, not on a fixed-latency RAM model.

```bash
TREE=/home/alans/mister/MacQuadra800_MiSTer/scratch/tree_p205 \
  python3 scripts/cpu/platform_fixture/run_platform_whet.py --out scratch/platform_fixture/runs/p205
#   --romlat N      clk_sys cycles from a ROM beat to its ack (DDR3 stand-in, default 6)
#   --image FILE    another RAM image (with EXTRA_PLUSARGS=+any_ssp if its SSP is not $640000)
#   --ref DIR       latency-fixture run whose whet_{globals,code,stack}.hex are compared
#   --no-compile    reuse DIR/obj
```

It takes about 2 minutes to compile and run (the latency-model fixture takes
50 s). It prints `WHETSTONE_LOOP cycles=` (clk_sys cycles between the two
`$F108` markers, counted at the external write's acknowledge as `tb_w.sv` does),
the instrumentation summary, the SDRAM chip-model protocol error count (the
run fails if it is not zero), and a byte-for-byte `MEMCHECK` of the globals,
the CODE3 patch area and the stack against the latency fixture's captures.

## What is modelled (all RTL is taken from `$TREE/rtl` without changes)

* The whole `quadra800` machine: wombat_cpu (core, MMU, caches, store buffer),
  wombat_bus32, the service FSM with the retained-line fast paths, the
  DIRECT_WRITES push port, `mem_wq_room`, walker arbitration, and every device
  (idle). The parameters are `CDROM=0, SONIC=0`, the qsf's current settings.
  The macros are the qsf's CPU flags plus `CACHE_CD_OFF`, `CACHE_SMALL` and
  `SIMULATION` (behavioural BRAMs, as in the full-machine sim).
* RAM goes through `sdram_beat32` (the 33/99 MHz bridge, the 8-entry write
  FIFO, the retained line) and `sdram.sv` (open-page BL8, refresh every 764
  clk_ram, per-rank row state), wired as `MacQuadra800.sv` wires them. The chip
  model is `verilator/tb_sdram.sv`'s `sdram_model`, both ranks. The runner
  extracts it and changes only its storage from an associative array to a flat
  array, so that 32 MB can be backdoor-loaded with sdram.sv's address decode.
* The clocks are clk_ram at 99.0 MHz and clk_sys at exactly one third of it,
  with their edges aligned at t=0 (`tb_sdram.sv`'s clocking). The hardware PLL
  gives 99/33.000 MHz.
* The SDRAM controller finishes its ~122 us power-up before the machine leaves
  reset.

## What is not modelled

* **The boot overlay is forced off** (`force dut.overlay = 0`), so the image's
  own reset vectors at $0 come from RAM. `store_buffer_ok` and the retained-line
  sideband follow it, as they do after boot on hardware.
* **ROM is a fixed-latency stand-in for the DDR3 bridge** (`--romlat`). About
  12.5 k ROM beats occur in the loop, all SANE/runtime I-cache misses. Moving
  romlat from 6 to 30 adds about 0.3 M cycles to both trees and changes the
  ratio by 0.001.
* There are no interrupts (IPL stays 7), no DAFB scanout clock, and no SCSI,
  Ethernet or ADB traffic. On hardware VBL and the Time Manager also run and
  evict cache lines.
* **The stack alignment is the fixture's choice.** SSP is $640000, a longword
  boundary. The results depend strongly on it (see below), and the alignment
  Speedometer's Whetstone runs with on hardware is not known.

## Results (2026-09-23, romlat 6)

| tree | loop cycles | vs P193 | latency fixture wl=1 / wl=3 |
|---|---:|---:|---:|
| P193 | 23,432,105 | 1.000 | 21,664,729 / 22,143,543 |
| P205 | 21,433,345 | 1.0933 | 19,171,712 / 20,871,638 |
| P210 | 20,773,721 | 1.1280 | |
| P210sb8 | 19,185,896 | 1.2213 | |

On hardware P193 to P205 was 1.078 (1387 to 1495 KWhet/s). The latency fixture
gives 1.130 at wl=1 and 1.061 at wl=3. Every run returns $600D with zero chip
protocol errors, and every capture matches the latency fixture's.

The SSP=$63FFFE experiment (`ram_ssp63fffe.bin`, `+any_ssp`) gives P193
25,746,071 and P205 24,151,507, a ratio of 1.066. The hardware's 1.078 lies
between the two alignments.

## Where the memory path costs time (P205, loop window)

* **Stores that straddle a longword** (914,001 of them, all `move.l` to
  addr ≡ 2 mod 4 in the stack page $63xxxx, from the SANE 10-byte extended
  temporaries) cannot take the DIRECT_WRITES push (`bus_wr_end <= 4`). They go
  through wombat_bus32 as two S_MEM beats and take **10 clk_sys each**, which
  is 9.14 M bus-busy cycles. The 1,485,247 in-longword stores take 2 cycles
  each (2.97 M).
* The 4-entry store buffer is therefore full (a store waiting on it) for
  **3.14 M cycles, 14.6 % of the loop** (P193: 2.53 M). With 8 entries
  (P210sb8) it is 1.22 M, and the loop is 7.6 % shorter than P210.
* The bridge FIFO is never full and never refuses room (maximum occupancy 4).
  94 % of RAM reads find it empty, and reads wait on it for 649 cycles in total.
  It costs nothing here.
* Reads: 1,112 first misses (mean 7.9 clk_sys, 7-10), 315 retained-line hits
  (2 cycles), and 2,190 bus32 reads (mean 14.6). RAM reads are negligible at
  SSP=$640000. At SSP=$63FFFE, line-crossing reads rise to about 117 k SDRAM
  reads and dominate the extra 2.7 M cycles.
* SDRAM write commands: 6.54 M page hits, 82.9 k to a closed row (the first
  write after each refresh closed all rows) and 760 row conflicts. Reads:
  3,062 hits, 1,192 conflicts and 738 closed. The controller is busy 32 % of
  clk_ram cycles, and 84 k refreshes fall in the loop.
