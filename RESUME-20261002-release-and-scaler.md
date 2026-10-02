# Resume: 20261002 is released; the scaler fault and the area are next (2026-10-02, 05:45)

Written at the end of a 13-hour session (Fable) on Dani's Windows box. Paste
the section "Prompt" into the next session. Read `CLAUDE.md` first, then
section 9 of [`RESUME-20261001-aux-and-timemgr.md`](RESUME-20261001-aux-and-timemgr.md)
(what was fixed and how) and `docs/perf/fix_hw_20261001/` (every hardware
report of the night).

## Where things stand

**Released: `releases/MacQuadra800_20261002.rbf`** (md5
`1928f231dd9ac9ef5935e69272d305a4`, RTL commit `8c223c8`, seed 38, every clock
met: CPU +0.118, HDMI +0.217, SDRAM +1.078; stamp `261002`). Three fixes over
20261001:

| fix | commit | what it cures |
|---|---|---|
| VIA1: an interrupt event beats a same-clock IFR clear | `a9cbda8` | Day of the Tentacle, DOOM II, Dracula Unleashed hangs (Time Manager stall) |
| CPU: no read-after-store handoff after a MOVES store | `e3fc1a0` | A/UX 3.1 `copyout of icode failed` panic |
| SCC: write-triggered actions on the access's own strobe | `8c223c8` | the one-boot-in-ten "Starting Up..." stall (a level-4 interrupt storm; it is in 20261001 and earlier) |

Hardware on that rbf (reports `REPORT_M_C38.md`, `REPORT_H_C38.md`,
`REPORT_A2_C38.md`): Mac OS 8.1 gate + CD player transport, the three games,
A/UX 3.1 at 32 MB, ten boots straight through the old stall point. All pass.

**Known defect of the released rbf: the scaler fault.** About one load in
seven comes up with no picture and stays that way until the MiSTer is
rebooted (1 of 11 ordinary loads, 3 of 20 loads after a reboot). The shipped
20261001 did not do it in 52 loads. `docs/perf/fix_hw_20261001/SCALER_FAULT.md`
has the measurements and the mechanism they point to. The user released it
knowing this ("I need something to release").

**Still owed to the user:** CD audio by ear (`ToneTest.cue`), and a look at
the OSD version (`261002`; only the synthesis report was checked).

**In the tree but NOT in the released rbf: `79cb5f4`**, a guard in
`sys/sysmem.sv` that keeps the scaler's HPS port shut until the core's first
reset is over, with a bench (`make tb_sysmem_vbuf_gate`) that reproduces the
cut burst without it. **Unproven on hardware.** Guarded fits so far
(`docs/perf/fix_hw_20261001/fpga_guard/`):

| seed | timing | rbf | hardware |
|---|---|---|---|
| 38, 33 | timed out (45 min) | | |
| 21 | CPU -0.465, HDMI +0.147 | `3202eeb5`, on the box as `_Unstable/MacQuadra800_W21.rbf` | video on 17 of its own 17 loads; nothing else run |
| 40 | HDMI -0.135, CPU -0.012, SDRAM +1.169 | `81f4d157`, `scratch/s1002/MacQuadra800_G40_81f4d157.rbf` | not yet loaded |

The design is at 93 % ALMs (38,800-39,100 of 41,910): of 14 fits started
tonight, 6 timed out, 3 failed in the fitter, 4 missed timing and 1 was
clean. The user: "we may need to look for some other ALM / space savings ...
this core might just be too full."

## Box state at hand-off

- MiSTer `192.168.99.143`: menu core loaded, Main `148d5679`, `.s0` =
  Problem Games, `.s4` = `DRACULA.toast`, CFG byte 0 `$50` (128 MB, Ethernet
  On) -- as found at the start of the session. The A/UX image was restored
  from the backup zip (the user's choice) and has had two clean boots since.
- Test bitstreams left in `/media/fat/_Unstable/`: `MacQuadra800_C38.rbf`
  (= the release), `_F33`, `_F21` (two-fix builds, stamp 261001), `_W21`
  (guarded, seed 21), `_BAD24` (the 20260930_2 fit that fails nearly every
  load). About 500 screenshots under `/media/fat/screenshots/MacQuadra800`
  and `MENU` from the night's runs. Nothing else was installed.
- This PC: no Quartus running; the Quartus GUI was closed (user's
  permission). `db/` holds a killed seed-41 fit: delete `db/` and
  `incremental_db/` before the next build. Seed 38's complete fit database
  is in `scratch/s1002/c38_fit/`. The seed walk is
  `scratch/s1002/seed_walk.sh <walkdir> <seeds...>`, launched detached with
  `MISTER_BUILD_DATE=<yymmdd>` in front when a stamp other than today's is
  wanted.
- Nothing is pushed. `git log --oneline 83f774b..` is the night's work.

## Rules learned tonight (also in memory)

1. **No reboot loops or repeat-load screens on the MiSTer without asking.**
   About 80 reboots went into screening fits before the user stopped it:
   "your test of loading the core a bunch of times doesn't seem reasonable."
   One or two loads to see a picture is fine; anything statistical needs the
   user's go-ahead with the count stated, and then loads from the menu
   without rebooting (a failed load does need one reboot to clear).
2. **A release must not carry the previous release's OSD date.** Build with
   `MISTER_BUILD_DATE`; after any stamp change move `db/` and
   `incremental_db/` away (smart recompile ignores `build_id.v`).
3. A rare anomaly seen while gating a build is not evidence against that
   build until the previous release has had as many tries (the boot stall).

---

## Prompt

Continue the MacQuadra800 core from the 20261002 release. Read `CLAUDE.md`,
`RESUME-20261002-release-and-scaler.md` and
`docs/perf/fix_hw_20261001/SCALER_FAULT.md` first. Ask the user before using
the MiSTer for anything beyond a single load, and never reboot it in a loop.

Open work, in the order the user has asked for it:

1. **Area.** The core is too full to fit reliably (93 %, most seeds time out
   or miss). Find ALM savings so that a normal seed walk closes timing.
   **By optimising code only: do not disable, remove or shrink any feature**
   (user, 2026-10-02) -- no `*_OFF` macros, no smaller caches, no dropped
   options; the same behaviour in fewer ALMs, as the 2026-09-30 FPU / ALU /
   muldiv work did. Start from `docs/AREA_BUDGET_20260924.md` and the `area-levers` memory in
   `../MacQuadra800_danifunker`, and from the per-entity table of the seed 38
   fit (`scratch/s1002/c38_fit/MacQuadra800.fit.rpt`: `ap040_core` 22,071
   ALMs, `iosb` 3,836, `ascal` 1,846, `ap040_cache` 2,233, `ap040_mmu` 1,141).
   Every CPU change must stay cycle-identical: the three `run_tests.sh` legs
   (default, `CPU_TEST_LEA=1 CPU_TEST_XSTORE=1`, `CPU_TEST_RELEASE=1`), the
   bench cycle counts and the first-100 corpus in section 9.1 of the 10-01
   resume are the reference (strip CRs from the corpus fixtures in the WSL
   copy). Agree the target and the candidates with the user before cutting.
2. **The scaler fault.** Decide with the user how the guard `79cb5f4` is to
   be judged, since reboot loops are out. Cheap first steps that need one
   load each: put the guarded seed 40 (`scratch/s1002/MacQuadra800_G40_81f4d157.rbf`,
   HDMI -0.135 / CPU -0.012) on the box and see that it has a picture and
   boots; the user's own daily loads of a guarded build are the real test.
   Open questions in `SCALER_FAULT.md`: why a fit holds a 1 on the scaler's
   write strobe through the first reset in some loads only, and whether
   `reg reset_req = 1` in `sys_top.v` plus a reset value for ascal's
   `avl_write_i` / `avl_read_i` (with the terminator counting real beats)
   would be the cleaner cure. If the guard proves out, it belongs upstream
   (the stock menu core shows the fault on about 4 % of boots).
3. **Next release**: guard + whatever area work lands, built with a fresh
   stamp, gated as in `CLAUDE.md` (the briefs and operator notes of this
   night are in `scratch/hw_20261001/`: `OPERATOR.md`, `BRIEF_81.md`,
   `BRIEF_GAMES.md`, `BRIEF_AUX.md`; Day of the Tentacle needs its CD image
   in slot 4).

Smaller things left open: A/UX's Finder shows "This disk is unreadable" at
boot with nothing in slots 1 and 4 (dismissable; which device is not known);
`cts_latch_a` in `scc.v` tracks the pin while the latch is closed;
`tb_scc_printer` dies with SIGILL in its RX section on this box; A/UX at
128 MB still hangs in `shutdown -h now` (older issue); the user has not been
asked whether to mirror the fixes into `../MacQuadra800_danifunker`.
