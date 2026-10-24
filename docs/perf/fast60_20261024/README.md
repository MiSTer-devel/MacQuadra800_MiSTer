# 60/30/90 MHz fits of the dual-issue memory core (Phase 1, 2026-10-24)

Branch `pipelined-040-fast60` (`a474308`): the dual-issue core with VRAM
retirement (RTL of `6bfd9c0`) built for CPU 60 / bus 30 / SDRAM 90 MHz --
`CPU_AP68040_2X` for the 2:1 CPU clock, `CLK_60_30_90` for the PLL strings
and the `SYS_HZ` time bases (see the branch's commit message and
`RESUME-20261024-dual-memory-and-fpu.md`, "60/30/90 time-base audit").
Recipe otherwise the release one; Quartus 17.0 on misterubuntu, one
isolated copy per seed.

## ctrl-s38: the unchanged core, seed 38

| | |
|---|---|
| CPU clock (60 MHz, PLL `general[2]`) | setup **-0.729 ns, TNS -30.713 ns**, hold +0.107; Fmax 57.49 MHz |
| SDRAM clock (90 MHz, `general[1]`) | setup +0.653; Fmax 98.21 MHz |
| bus clock (30 MHz, `general[0]`) | setup +1.228 (the clk_ram -> clk_sys handoff) |
| HDMI | setup +0.257 |
| clk_sys <-> clk_ram crossings | +2.762 / +1.228 ns |
| area | 35,483 ALMs (85 %), 31,110 registers, 497 / 553 M10K, 38 DSP |
| RBF | md5 `9bcfd99e80df5ef3ce01aae425dade3a`, 4,424,536 bytes (`rbf-identity.txt`); CPU-clock miss, not for release |

For scale: the same RTL at 66/33/99 (dual R3) was -3.308 ns with TNS
-2,114 ns and Fmax 54.17 MHz.

### Where the miss is

`dual_cpu_top100.txt` (100 worst CPU-clock pairs, full detail). Endpoint
families of the 100 negative paths:

| endpoints | family |
|---:|---|
| 43 | `ap68040_backend:be\|ap68040_rf:rff\|lvt[..]` -- the register file's live-value table (write-port select) |
| 23 | `ap68040_backend:be` -- `agx_q[..]`, address generation |
| 19 | `ap68040_dmu:dmu` -- `atc_set_q` and other DMU registers |
| 15 | `ap68040_dmu:dmu\|ap68040_atc:datc\|...\|rdaddr_reg[..]` -- the data ATC LUTRAM read address |

Start points: `ex_u.op` 44, `fpsr` 13, `ex_u.cond` 11, `ex_a` 9,
`ag_u.upd2_reg` 9, `uq0.idx` 6, `sk_vr` 5, `ag_u.dynk` 3.

Three of the four families are one cone. The worst path (#1, -0.729 ns,
10 levels, 16.773 ns data delay) runs `ex_u.op[4]` -> opcode compare
`Equal97~1/~2` -> `stall_ex~10..12` -> `stall_dc2~0` -> ... -> the RF
write enable -> `lvt[29][1]`; paths #4 (-0.676, the ATC read address) and
#18 (-0.549, `atc_set_q`) leave the same `ex_u.op[4]` through the same
stall logic. **12.269 ns of the 16.773 (73 %) is interconnect** -- six
hops of 1.3-2.1 ns between LABs at X43, X63 and X57; the twelve cells
total 4.504 ns. The separate family is #3 (-0.698, 12 levels, 17.068 ns):
`ag_u.upd2_reg[0]` through an adder carry chain to `agx_q[21]`.

This is not the family that limited the 66/33/99 fit (76 of its worst 100
ended at the D1 attribute-ROM address). Targeting 16.67 ns instead of
15.15 ns the fitter got decode under the line and the next cones surfaced.

### What follows from it

- The routing share says placement, not logic, sets this slack: seeds
  39-42 were launched before any RTL change (results below as they land).
- If no seed closes, the RTL change is in the backend, not decode:
  decide the EX stall a stage earlier (register the opcode-class flags
  that `Equal97` / `stall_ex` compare when the uop enters EX, so the RF
  write enable, the ATC read address and `stall_dc2` read a flop instead
  of a comparator cone), then the AG adder path.

## Files

- `ctrl-s38/MacQuadra800.{sta,fit,map}.summary`, `rbf-identity.txt`
- `ctrl-s38/dual_cpu_top100.txt` (setup, CPU clock, 100 pairs, full path), `dual_cpu_hold.txt`, `dual_ram_paths.txt`, `dual_all_setup.txt`, `dual_all_hold.txt`, `dual_fmax.txt`
- `ctrl-s38/cross_sys2ram_fast60_ctrl_s38.txt`, `cross_ram2sys_fast60_ctrl_s38.txt` (`scripts/cpu/timequest_cross_domain.tcl`)
- Benches of every module the clock change touched, at the 33 MHz defaults: all pass (`verilator/bench2.log`, `bench4.log` in the build copy; summary in the handoff).

## Seeds 39-42

(filled in as each fit finishes)
