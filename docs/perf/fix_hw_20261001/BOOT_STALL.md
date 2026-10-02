# The "Starting Up..." boot stall: an SCC command dropped by clock-enable phase (2026-10-01)

Found while gating the VIA and CPU fixes; **not caused by them**. It is in
the shipped `MacQuadra800_20261001.rbf` too. Fixed in `rtl/scc.v`
(`8c223c8`), bench `make tb_scc_ctl_phase`.

## Symptom

A Mac OS 8.1 boot (Problem Games disk, 128 MB, AppleTalk active) freezes at
"Starting Up..." before any extension icon: the frame is byte-identical,
`Ticks` (`$16A`) stops at `$277`-`$27B` (about 10.5 s into the boot, 63-65 s
after `load_core`), the guest clock stops, there is no disk I/O. One to
seven minutes later it carries on by itself and everything works; the
guest clock stays behind by the length of the stall.

## How often

| run | build | boots | stalls |
|---|---|---|---|
| games run, 17:56 and 18:45 | F33 (fixes, seed 33) | 2 | 1 (3 min 50 s) |
| brief B, 19:41-20:16, `REL F33 F21` x4 | REL / F33 / F21 | 4 / 4 / 4 | 0 / 0 / 0 |
| probes, 20:21 and 20:26 | REL | 2 | 0 |
| unattended loop, 20:30-22:31, `REL F33` x20 | REL / F33 | 20 / 20 | 2 / 2 |
| **total** | **REL (20261001 release, no fixes)** | **26** | **2** |
| | **F33** | **26** | **3** |
| | F21 | 4 | 0 |

The four loop stalls (`boot_stall/loop_c15_c54.log`, `stall_c*.txt`):

| cycle | build | Ticks frozen at | from | to | ended by |
|---|---|---|---|---|---|
| 24 | F33 | `$278` | t+65 | t+485 | itself, 7 minutes in |
| 25 | REL | `$279` | t+65 | t+130 | the capture's DMA reads at t+125 |
| 28 | F33 | `$278` | t+65 | t+135 | the capture's DMA reads |
| 31 | REL | `$27B` | t+65 | t+130 | the capture's DMA reads |

(The first stall, 17:56, also ended within seconds of a 16 KB `gdump`.)

## What the CPU is doing

`pcsample` during every stall (`boot_stall/stall_c*.txt`): SR `$24xx` 99.9 %
of the samples, i.e. interrupt level 4, the SCC. The PCs, in loop order:

- `$3196`, `$3150-$3192`: the level-4 dispatcher in low memory (reads RR2
  on channel B, calls `Lvl2DT[n]`);
- `$40809D40-5C`: the ROM's channel-A external/status handler: reads RR0,
  reads RR15, writes WR0 = `$10` (Reset Ext/Status Interrupts), jumps
  through `ExtStsDT[2]`;
- `$2C094-$2C0FA`: the async serial driver's external/status routine
  (System file, `.AIn`/`.AOut`). It counts external/status interrupts per
  tick at `$70(a2)`; at 80 in one tick it writes WR15 = `$80` through
  `$4086B14C` to turn the CTS interrupt off -- its storm guard. Ticks is
  frozen, so it does that on every pass;
- `$40809B68-B90`: interrupt exit;
- `$4086AEFC`: the one main-line PC. It is the `RTS` of the driver's
  register-table writer, right after its `move.w (a7)+,sr`. The interrupt
  is taken there again on every return: the main line does not advance one
  instruction, and level 1 (VBL, the one-second tick, the Time Manager)
  never gets in.

## Where in the boot

A fast in-process sampler (`boot_stall/B_bprobe.py`, about 4,500 samples/s
through the SONIC mailbox) on a normal boot of the unfixed release
(`boot_stall/normal_boot_serial_state_c14REL.txt`) shows the step every
boot goes through at this point: AppleTalk claims the printer port
(`PortBUse` = `$01`), then the async serial driver on the **modem port** is
opened and closed twice within 13 ms (`PortAUse` `$FF` -> `$02` -> `$FF`,
`SerialVars` = `$000C0C00`, `Lvl2DT[4,6,7]` = `$4086B276`, `$2BFC6`,
`$2C038`, `ExtStsDT[2]` = `$2C094`), then LocalTalk's handlers go in on
channel B. The stalled boots are stuck inside that 13 ms window with exactly
that state (`g_low.bin` of the first stall, the `stall_c*.txt` captures).

## The bug

`iosb.sv` gives the SCC two clock enables from one clk/4 divider: `cep`
(phase 0) and `cen` (phase 2). It raises CS in whatever phase the CPU's
access arrives, `scc.v` consumes the access on the next `cen`, and the bus
acknowledges on the `cen` after that. `scc.v`'s write strobes (`wreg_a`,
`wreg_b`) are therefore high from CS until the first `cen`.

The external/status logic (`ex_irq_ip_*`, `latch_open_*`), the EOM latches
and the two "WR8 through the control port" clears sampled the strobe only
`if (cep)`. A write whose CS rises in phase 1 or 2 reaches its `cen` without
a `cep` in between and those actions never happen:

| CS rises in phase | sees | WR0 = `$10` |
|---|---|---|
| 3 | cep (0), then cen (2) | applied |
| 0 | cep (0), then cen (2) | applied |
| 1 | cen (2) only | **dropped** |
| 2 | cen (2) only | **dropped** |

Because the acknowledge comes on `cen`, the phase in which the *next* access
arrives is set by the CPU's instruction timing since the previous one. For
the ROM handler that is the time from its RR15 read to its `move.b
#$10,(a1)`. Normally it lands in a live phase. When it lands in a dead one,
the interrupt stays pending, the handler runs again with the same timing
and so the same phase, and nothing in the loop can change it: the driver's
own guard (CTS interrupt off in WR15) cannot help, because the pending bit
is already set and only the dropped command clears it. A DMA read from the
ARM steals bus cycles and shifts the timing, which is why the captures
ended three of the four loop stalls.

`verilator/tb_scc_ctl_phase.v` raises the channel-A external/status
interrupt with a CTS edge and acknowledges it with CS rising in each phase:

| model | phase 0 | phase 1 | phase 2 | phase 3 |
|---|---|---|---|---|
| `scc.v` before `8c223c8` | cleared | **still pending** | **still pending** | cleared |
| after | cleared | cleared | cleared | cleared |

## The fix

`wstb_a` / `wstb_b` = `cen & wreg_*`: one clock per control-register write,
the pulse that consumes the access. The external/status acknowledge and
latch reopen, the "Reset Tx Underrun/EOM" command and the WR8 clears act on
it; the event side (latching a CTS/DCD change, EOM set) stays on `cep`.

The same dropped-command window existed for LocalTalk's "Reset Tx
Underrun/EOM Latch" (`$C0`) and for an ext/status acknowledge during a
serial print with CTS handshake; neither was seen to fail, both are covered
by the same change.

## Still open

- `cts_latch_a` follows the pin on every `cep` whether the latch is open or
  not (the assignment sits outside its `if`), so a CTS edge that arrives
  while an external/status interrupt is pending is not re-reported after
  the acknowledge. RR0 always shows the live pin, so the driver's hold flag
  is right at each interrupt; left alone here.
- Which piece of the System opens the modem port's async driver during
  AppleTalk start-up, and why, was not looked into: it is normal Mac OS
  behaviour on every boot.
- `tb_scc_printer` dies with SIGILL in its RX section on this box (WSL,
  Verilator 5.020) with and without the change; its TX section passes.
