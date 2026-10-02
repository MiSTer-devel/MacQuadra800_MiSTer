# The scaler fault: a write burst cut during the start-up reset (2026-10-02)

The open fault of 2026-09-30 (`../MacQuadra800_danifunker/RESUME-20260930-video-bisect.md`):
on some loads of some fits the picture comes up displaced or absent, Main's
screenshots fail, and the HPS FPGA-to-SDRAM port of the scaler stays broken
for every core loaded afterwards until the MiSTer is rebooted. It stopped the
first three-fix candidate (seed 38) from being released. This note has what
was measured tonight, the mechanism it points to, and the guard that went
into `sys/sysmem.sv` (`79cb5f4`). **Whether the guard cures it on hardware is
recorded at the end; until that says so, treat it as a hypothesis with a
bench behind it.**

## What was measured

Tools in `scaler_fault/` (run from this checkout; they reboot the MiSTer, so
only with the Mac halted or still in its RAM test):

- `vscreen.sh <rbf> <tag> <loads>`: for each load reboot the box, wait for
  the menu, load the core, sample the scaler's header at DDR3 `0x20000000`
  five times (`vbuf_probe.py`, from the 09-30 session). It also records the
  **menu core's** header before the load.
- `vk_probe.py` / `vk.sh`: on a failing load, where did the 16-byte header
  beat go? It should be beat 0 of the burst at offset 0; with the data
  running k beats ahead of the port's commands it lands in the tail of the
  previous burst in time, the last burst of the previous frame at `0xF0000`.
- `vtiming.sh`: plain loads against loads made while Main's `sync()` (after
  the FPGA is configured, before the new Main releases the reset) is slowed
  by 24 MB of dirty pages.

| fit | clean-boot loads with video | other loads |
|---|---|---|
| shipped 20261001 (`a4d4d008`, seed 33) | 15 of 15 (the 16th was a menu-core failure, below) | 26 of 26 in the boot loop; 8 of 8 and 3 of 3 on 10-01 |
| F33 (two fixes, seed 33, `faf2eacd`) | 9 of 9 (the 10th: menu core) | 27 of 27 |
| **C38** (three fixes, seed 38, `1928f231`) | **17 of 20** | 10 of 11 and 27 of 32 |
| 20260930_2 (`491eb3df`, seed 24) | 0 of 7 tonight; 0 of 6 on 09-30 | |

Three more things came out of the logs:

1. **The displacement is random.** Seven failing loads of 20260930_2:
   k = 8, 4, 14, 10, 5, 1, 2 beats. The "exactly half a burst" of 09-30 was
   one sample. A random k in 1..15 with nothing at 0 is what a stream of
   16-beat bursts cut at an arbitrary moment leaves behind: the port waits
   for the rest of the last burst, takes it from the first real one, and
   every burst after that lands k beats early. One cut in sixteen falls on a
   burst boundary and does no harm, which is about what a fit that "always"
   fails shows.
2. **The stock menu core does it too**, on its first load after a reboot:
   3 of about 75 boots tonight had an invalid menu header before anything
   else was loaded, and the core loaded next then found the port dead
   (markers not overwritten). So it is a property of the framework's
   start-up, not of this core's fits; the fit only sets the odds.
3. **Main's timing does not matter**: 2 failures in 16 plain loads, 3 in 16
   slowed ones.

## The mechanism this points to

- `sys/f2sdram_safe_terminator.sv` exists to finish a burst that a reset
  would cut. It passes its master straight through until it has seen the
  reset **de**asserted once (`init_reset_deasserted`), so during the very
  first reset after configuration it protects nothing.
- `sys/ascal.vhd`: `avl_write_i` and `avl_read_i` are not in the reset
  branch of the `Avaloir` process. With `avl_reset_na` low the clocked branch
  does not run, so they **hold** whatever they had.
- `sys/sys_top.v`: `reg reset_req = 0`. The scaler's `reset_na` is
  `~reset_req`, so for the first clock or two after configuration the scaler
  is out of reset, and then the reset arrives asynchronously to the scaler's
  100 MHz Avalon clock.

If `avl_write_i` holds a 1 when that first reset arrives, the port (enabled
by Main's `do_bridge(1)` a moment later) takes burst after burst for as long
as Main keeps the core in reset, and Main's release stops the stream at a
random beat. How a given fit gets a 1 there (the power-up level Quartus
picked for a register without a reset or an initial value, or what it
captured in the wake-up clocks) was not established; it does not have to be,
because the port should not be listening at all at that point.

`verilator/tb_sysmem_vbuf_gate.sv` (`make tb_sysmem_vbuf_gate`) is that
scenario around the real `sysmem_lite`: a master whose write strobe holds a
1 through the reset, released at 16 consecutive clocks, before and after the
20 ms start-up reset. Without the guard all 32 units put beats on the port
during the reset and 30 start their first real burst inside a cut one (the
other two stop on a boundary: the 1 in 16); with it none does.

Not explained by this: that physical page 0 was unchanged after a failing
load (so the stream, if that is what it is, does not go to address 0), and
why seed 38 does it on one load in seven rather than always or never.

## The guard

`sysmem.sv`: the scaler port is shut (write and read masked, `waitrequest`
high towards the scaler) from configuration until 32 clocks after the first
reset deassertion, then open for good, so the terminator's handling of the
reset at the next core load is untouched. The scaler waits on `waitrequest`
and its first burst starts whole.

## Does it work? (hardware)

See section 9.6 of `RESUME-20261001-aux-and-timemgr.md` for the screens of
the fits built with the guard.
