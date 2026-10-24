# Handoff: dual-issue memory core and FPU experiment — 2026-10-24

## Resume here

The working checkout is `pipelined-040-dual-memory`. Its last hardware-
qualified checkpoint is `6bfd9c0103f569c6cd951036d1c832eeb2f81f67`, tagged
`pipelined-040-dual-memory-20261023`. This handoff advances documentation
only; the hardware recipe remains that checkpoint's 33/33/99 MHz core.

The isolated FPU_PIPE experiment is finished and preserved. The recommendation
is to retain **FPU_PIPE=0** on the smaller memory core: enabling it costs
1,077 ALMs (+3.12%) for only 0.67–1.21% higher separate FPU scores, with
unchanged PR Math. These single-iteration observations do not establish a
repeatable small gain. The working checkout has already returned to PIPE=0.

No build, hardware benchmark, or input session from this experiment remains
active. The final observed MiSTer state was Menu with original settings
restored. Check the screen again before any future hardware action.

## User direction and boundaries

The user wants a small core close to apolkosnik's pipeline integration and a
separate performance version, while avoiding feature growth that erases area
savings. Keep useful checkpoints recoverable before further CPU changes.
The requested clock target remains **66/33/99 MHz**; do not silently replace
it with a lower set. On 2026-10-24 the user said **60/30/90 MHz is possible**
as an explicit intermediate step (CPU/bus/SDRAM, same 2:1 ratio; the dual
R3 fit's Fmax is 54.17 MHz, so 60 needs about 10 % off the worst path
where 66 needs 18 %) -- offer it as a named option, never as a quiet
substitute. The latest experiment tried FPU_PIPE alone at 33 MHz.

A later DDR-VRAM experiment is desired for more user VRAM/video capacity.
The user explicitly requested discussion before making that architectural
change. No VRAM storage, video-size, or DDR change was made in this work.
The sibling MacPPC checkout is under `~/dev2`; recheck its revision if using
it for a future comparison rather than assuming it is still current.

## Preserved branches and artifacts

| Purpose | Branch / recovery point | Status |
|---|---|---|
| Minimal pipeline + integration/boot fixes | `pipelined-040-min`, tag `pipelined-040-min-20261022` | Separate conservative checkpoint |
| Earlier scalar 66 MHz timing work | `pipelined-040-66mhz-timing` | Historical comparison; last tested timing24-small still misses CPU setup |
| Ranzbak dual issue, before memory port | `pipelined-040-dual`, checkpoint `43a5280`, tag `pipelined-040-dual-checkpoint-20261023` | Saved 33 and 66 MHz RBFs/results |
| Posted VRAM retirement | `pipelined-040-dual-memory`, checkpoint `6bfd9c0`, tag `pipelined-040-dual-memory-20261023` | Current checkout; 33 MHz timing and Mac tests pass |
| FPU_PIPE-only trial | `pipelined-040-dual-fpu-pipe`, final `0bcf3b43f90564e08b8f0d41e054a582e0d464ac`, tag `pipelined-040-dual-fpu-pipe-20261024` | Saved and pushed; not selected for smaller default |

All pushes in this work went to **`alanswx`**, the user's repository.
`origin` points to MiSTer-devel: do not push there.

The FPU report and the two comparison documents (with the matched
memory/FPU trial rows) were carried onto this branch on 2026-10-24. The
candidate screenshots, source manifests, timing reports and RBF stay on
the **FPU experiment branch/tag** only:

- [FPU evidence and manifests](https://github.com/alanswx/MacQuadra800_MiSTer/tree/pipelined-040-dual-fpu-pipe-20261024/docs/perf/fpu_pipe_20261024).
- [Exact FPU candidate RBF](https://github.com/alanswx/MacQuadra800_MiSTer/tree/pipelined-040-dual-fpu-pipe-20261024/test-builds/pipelined-040-dual-fpu-pipe-20261024/33mhz).

Current-checkout references:

- **[One-table comparison: real Quadra 800, shipping core, every pipelined/dual experiment](docs/core-comparison-20261024.md)** -- start here.
- [FPU_PIPE experiment report](docs/fpu-pipe-experiment.md).
- [Memory port and qualification](docs/dual-memory-performance.md).
- [Dual integration and compiler fixes](docs/pipelined-040-dual.md), [upstream/local provenance](rtl/ap68040_faster/UPSTREAM_QUADRA.md).
- [Speedometer, timing and real Quadra comparison](docs/dual-speedometer-comparison.md).
- [Separate FPU comparison and older shipping reference](docs/dual-fpu-comparison.md).
- [Exact memory RBF and manifest](test-builds/pipelined-040-dual-memory-20261023/33mhz/).
- The old-vs-pipelined analysis (cycle costs per structure, the write
  buffer, the `?`-disk bug) is `docs/pipelined-040-compare.md` on branch
  `pipelined-040` only: `git show pipelined-040:docs/pipelined-040-compare.md`.

## Current hardware recipe and retained memory change

CPU/bus/SDRAM are 33/33/99 MHz, seed 38. DUAL=1, BTIC=1,
S1_CLASSES=011, FPU_PIPE=0, LOOP_PRED=0, EARLY_RES=0, DC1_ATC=0,
SKID=0, DIV_STEPS=2, PA_IO_SERIAL=1 and PA_VRAM_POST=1; caches are 8+8 KB.
Second-slot loads remain disabled because of upstream hardware corruption
concerns. Do not enable them based only on passing simulation.

The memory port lets eligible non-faulting on-chip VRAM stores retire while
the existing DMU bus registers hold the downstream transaction. It adds no
external write FIFO. Translation/protection checks precede retirement;
locked/RMW, MOVE16, crossing-word, cache-hit and other ineligible accesses
retain the ordinary path. Subsequent uncached/device/cache-maintenance
operations wait for bus completion. Reconsider this policy if VRAM moves
to DDR. A prototype external queue was rejected for area without demonstrated
gain under the platform response model; its patch/logs remain in the docs.

The first memory hardware run raised graphics 0.937→0.982 (+4.8%), with
Mix essentially unchanged. Its whole-core fit used 89 fewer ALMs than the
pre-port dual fit; synthesis added only three registers. Do not attribute
all placement-area or disk-score changes to this RTL optimization.

## Measured comparison

| Build | CPU MHz | ALMs | CPU setup | Mix | FPU after Mix | PR graphics | PR Math |
|---|---:|---:|---:|---:|---:|---:|---:|
| Saved dual R3 | 33 | 34,643 | +1.374 ns | 1.800 | 0.744 | 0.937 | 13.309 |
| Saved dual R3 | 66 | 35,346 | −3.308 ns | 3.614 | 1.492 | 1.579 | 26.824 |
| Memory, latest matched baseline | 33 | 34,554 | +1.245 ns | 1.802 | 0.744 | 0.985 | 13.313 |
| Memory + FPU_PIPE trial | 33 | 35,631 | +0.964 ns | 1.806 | 0.749 | 0.985 | 13.313 |

All four fits use 497/553 M10Ks and 38 DSPs. The memory core occupies
82.45% of ALMs; the FPU candidate occupies 85.02%. There is no fitted or
hardware-qualified 66 MHz memory-port build yet. Functional 2x adapter tests
are not physical 66 MHz timing qualification.

Matched PIPE=0/1 details: first FPU 0.741/0.750; PR CPU 1.807/1.806,
disk 2.228/2.417, overall PR 1.604/1.623. The PR change accompanies disk
variation; CPU, graphics and Math do not improve. After-Mix Whetstone is
3508.624/3573.164 KWhetstones/s, matrix 0.829/0.827 s, FFT 0.406/0.406 s.
FPU ratings normalize to Quadra 650=1, while Mix uses Quadra 605=1.

Both matched runs used the same disposable Mac OS 8.1 image, 32 MB RAM,
Ethernet Off and restored baseline PRAM. Order: FPU first → Mix → FPU after
Mix → full PR. Each suite used one iteration. Both boot and clean shutdown
pass. Disk scores are sensitive to storage/host activity.

The physical Quadra photograph gives Mix 1.899, PR graphics 1.347,
PR Math 20.011, separate FPU 1.011. The older shipping reference is the
September 30 RBF: separate warm FPU 0.961/0.968. Do not label those as
newly measured performance of the October 2 shipping RBF; exact October 2
Speedometer results were not recovered. Provenance is in the comparison docs.

## Timing, validation and outstanding qualification

Memory33: CPU/bus +1.245 ns, SDRAM +0.511 ns, HDMI +0.668 ns,
minimum hold +0.194 ns; all timing checks pass. Exact RBF MD5
`500c366118057e8034d7a93d93dd107f`, SHA256
`c6605e7ce94fb129cc1c9958ccd4ce5f9a19c2da856dae0f85c2afa21cb2f642`.

FPU33: CPU/bus +0.964 ns, SDRAM +0.377 ns, HDMI +0.357 ns,
minimum hold +0.109 ns; all 41 checks pass. Exact RBF MD5
`f1289c23369dda33a76bb79ef33123b1`, SHA256
`b34586c5c0af555922158bdd57731f0ee08eca5e4549bfca213c5cb4756a3c15`.
The only functional RTL change was `.FPU_PIPE(0)`→`.FPU_PIPE(1)`;
source `bd398e4`. No eligibility-guard relaxation was attempted.

The FPU trial passes 225 CPU cases with hardware options explicitly set,
six adapter configurations (both clock ratios × normal/fast/platform), and
40,000 differential FPU commands comparing registers/FPSR against PIPE=0.
Standalone pipeline-focused gains do not establish application gains.
The existing guard requires FPCR exception enables clear; there is no
fresh timed trace proving why Speedometer benefits so little. Do not
attribute it to that guard without measurement or relax architectural checks.

The fits retain 36 RF MLAB banks, four cache-tag M10Ks and three framework
OSD/LCD M10Ks. Preserve the Quartus structure-argument workaround and
resource-aware RAM-inference setting; earlier synthesis silently removed
paired issue or spilled framework RAM into registers. Check mapping guards
again after changes, not just simulation and total ALMs.

**66 MHz dual timing remains open.** CPU slack −3.308 ns, TNS −2114.552 ns,
reported Fmax 54.17 MHz. This is 1.769 ns worse than the prior scalar
24-small fit (−1.539 ns). Completing Mac benchmarks does not close timing.
[Path analysis](docs/perf/dual_20261023/66mhz/r3/path-analysis.json): 76/100
reported paths end at the D1 attribute-ROM address, six involve MMU/cache-hit
logic. Worst fetch→decode path has 14 levels and 18.416 ns data delay;
MMU path has 13 levels and 17.763 ns. No timing exceptions hide these paths.

A/UX and CD audio remain **unqualified on the new dual-issue CPU and its
memory/FPU variants**. These are experimental checkpoints, not release RBFs.
Older scalar/minimal results do not qualify a newly imported CPU.

## Hardware and build state at handoff

The test board is **10.0.2.192**, reached through `misterubuntu`.
The last test ended at Menu after visually verified safe-to-switch-off.
The agent's input controller closed with explicit mouse-up + EOF; ownership
was released, with no active input session. No reset or Main/service restart
was used. **10.0.2.14 was untouched; do not use it for this task.**

Disposable disk: `/media/fat/games/MacQuadra800/TestImages/Dual040/QuadSquad8_dual.hda`.
Original user images were not used as writable test media. The final restore
verified original `MacQuadra800.s0` and `.nvr` bytes MATCH, with `.s2` and
`.CFG` still ABSENT. Restored S0 points to
`games/MacQuadra800/TestImages/CPU66/QuadSquad8_cpu66.hda`.
Baseline PRAM SHA256:
`076a27c79e5ace2a3d47f9dd2e83e4ff6ea8872b3c2218f66c92b89b55f36560`.
Clean candidate settings were saved in `TestImages/Dual040/config-after-fpupipe-candidate`.
The final-state record and Menu/halt screenshots are on the FPU tag.

Exact RBF copies remain on the board:
`/media/fat/_Development/MacQuadra800_dual_memory33_261023.rbf` and
`/media/fat/_Development/MacQuadra800_dual_fpu_pipe33_261024.rbf`.

The completed FPU Quartus directory on `misterubuntu` is
`/home/alans/mister/q800_dual_fpu33_s38_20261024`;
unit `q800-dual-fpu33-s38-20261024.service` is inactive. Local raw reports,
source archive and working logs remain under `scratch/fpu-pipe-20261024/`.
Other sessions may have their own builds; inspect current process working
directories before launching anything and never kill another session's flow.

## Suggested next work and operating rules

No next optimization is already running. Retain the memory-retirement win
and leave FPU_PIPE off on this branch. If returning to 66 MHz, use a new
branch from the memory checkpoint, first fit an unchanged 66/33/99 control,
then target the measured decode/MMU path families one change at a time.
Track whole-core ALMs, setup/hold and matched graphics/FPU/Mix results;
avoid accumulating optional features without demonstrated benefit.

**Owed: the full hardware matrix on the actual MiSTer.** Every dual-issue
number so far is one Speedometer iteration of Mac OS 8.1 on one box; the
shipping core's figures are medians of five on a different box. Before any
decision between the cores, run on the real MiSTer, per candidate RBF
(memory 33 `500c3661`, dual R3 33/66, the 20261002 release as control):
Mac OS 8.1 gate, A/UX 3.1 at 32 MB, CD audio, Speedometer Mix / PR / FPU
suite as **medians of 3-5**, plus the DOTT / DOOM II / Dracula hang
checks from `docs/perf/fix_hw_20261001/`. The user wants this mechanical
run driven by a **Sonnet or Opus session**, not hand-stepped from the
design session (user, 2026-10-24); its recipe is in the memory
`test-hosts-2026-10` (kvms on mister192) and `scratch/hw/k.sh`.

## Plan of record (agreed with the user 2026-10-24)

The comparison behind it is [docs/core-comparison-20261024.md](docs/core-comparison-20261024.md),
including the 33/66 scaling proof that Speedometer's Mix, CPU, Math and
FPU never wait on memory and that about a fifth of Graphics is ROM fetch.
Two cores are the goal: a **small** one and a **fast** one. VRAM in DDR3
and the other video modes come **after** the CPU reaches its target: the
CPU decision decides which core the video work builds on (it does not fit
the shipping core at 94 %), and A/UX on the dual core is the biggest
unknown left. Meanwhile the CPU work must not harden around on-chip VRAM
assumptions (keep the 1-clk-ack / `PA_VRAM_POST` policy behind its
parameter).

**Decision rule.** Fast core: beats the shipping core on every PR component
and the FPU suite, CPU clock timing clean, both guest gates and CD audio
pass. Small core: at most 36,000 ALMs, Mix at least the shipping core's,
Graphics and FPU within 10 % of it, same gates. Whether the small core
needs Ethernet (the SONIC snoop, cost unknown) is still open.

| Phase | Work | Gate / stop rule |
|---|---|---|
| **0. Measure** (started 2026-10-24, no RTL) | Hardware sweep on mister192 by a Sonnet/Opus session: memory33 `500c3661`, dual R3 66, the 20261002 release as same-box control -- 8.1 gate, A/UX 3.1 at 32 MB, CD audio transport, Speedometer Mix / PR / FPU as medians of 3-5 with the full Mix sub-tests transcribed, the DOTT / DOOM II / Dracula hang checks where the images exist. In parallel: a cycle attribution of the FP gap on the dual core (divider vs FP store path vs op latency) and a `--check` synthesis to read the dual FPU's entity size against the shipping FPU. | A/UX must boot and shut down on memory33; if not, the MMU comes before everything else. The attribution decides which FP fix Phase 2 makes. |
| **1. Fast core, 60/30/90** (new branch from `6bfd9c0`) | Fit 1: the unchanged core at 60/30/90 as control. Fit 2: one change, a register stage on the D1 attribute-ROM address path (76 of the worst 100 paths). Fit 66/33/99 as well, for the record. | Closes at 60: sweep it, ship candidate. Slack improves by 1.5 ns or more but still open: one more iteration on the MMU / cache-hit family. Under 1 ns: **stop**, the fast core stays the shipping core. About four fits. |
| **2. Small core at 33** (second branch from `6bfd9c0`, concurrent with 1; the two do not share files) | Only what Phase 0 points at, one change per fit, hardware medians after each: the FP fix (divider steps and/or the FP store path), uncached-read ordering (Graphics), then the ROM next-line prefetch (platform side, helps both cores). | Hard cap 36,000 ALMs. No FPU_PIPE / LOOP_PRED / EARLY_RES / second-slot loads: all measured as area for nothing. |
| **3. VRAM to DDR3 and the video modes** | After a core meets its target. First a DDR3 bridge model with randomised latency for the sim (the full-machine sim instantiates `quadra800`, not `emu`), then write FIFO + read line cache + scanline buffer, then the DAFB timing generator and monitor-sense codes (the video PLL is already reconfigurable). | Discussed with the user before it starts. |

**60/30/90 time-base audit (2026-10-24, before Phase 1's first fit).** The
66/33/99 experiments kept the bus at 33 MHz; 60/30/90 is the first time
`clk_sys` itself changes, and everything divided from it would otherwise
run 10 % slow -- including the VIA timers Speedometer times itself with,
which would inflate every score by ~11 %. The PLL is
`rtl/pll/pll_0002.v:34-41` (strings "33.000000 MHz" / "99.000000 MHz" /
"66.000000 MHz"; the `.sdc` uses `derive_pll_clocks`, so no constraint
edit). The constants to re-derive from one `SYS_HZ` parameter plumbed from
the top: `rtl/iosb.sv:18` `E_HALF = 21` (VIA E clock, 783 kHz), `:19`
`TICK_HALF = 274314` (60.15 Hz tick), `:300-301` `SHIFT_DELAY` /
`IDLE_DELAY` (ADB ms), `:639` `DBG_BAUD_DIV`, `:1048` `scc
#(.SYS_CLK_HZ(33_000_000))`; `rtl/easc.sv:69` `SAMPLE_DIV = 1483` (22.257
kHz); `rtl/ncr53c96.sv:1849` `cd_audio #(.CLK_HZ(33_000_000))`;
`rtl/rtc3430042.sv:17` `SEC_DIV = 33000000`. The SDRAM controller's
refresh count in `rtl/sdram.sv` must be checked for the 99 -> 90 MHz
`clk_ram` as well. The CPU clock enters as PLL `outclk_2` under
`CPU_AP68040_2X` (`MacQuadra800.sv:382`, `rtl/quadra_cpu040.sv:106-115`,
`cpu_bclk_en` on the falling edge); the 2:1 ratio is what that adapter
assumes, so 60/30 stays paired.

Housekeeping for the first RTL commit on either branch: the header of
`MacQuadra800.sv` still says RAM and ROM live in DDR3; RAM is in SDRAM
(`MacQuadra800.sv:1007`).

Read [CLAUDE.md](CLAUDE.md) and [BUILD.md](BUILD.md) before hardware work.
Never deploy/reset a running guest, and never hash/copy a mounted image.
A prior recovery-reset exception applied to a failed disposable A/UX boot,
not blanket authorization to reset a live Mac. Look first; use a verified
clean halt or Menu. Send explicit mouse-up after every menu operation, and
make every click a continuous down -> hold -> up gesture: the "Shut Down
hang" reported on 2026-10-22 was the tester script sending button down and
up in the same event, not a core fault (user, 2026-10-24).
No Main/mrext restart under a guest. Use disposable clones for testing.

No git worktrees. Commit and pin build inputs, use isolated Quartus
source/db/output directories, and freeze those inputs through the flow.
Parallel builds in separate directories are explicitly user-authorized;
the old global single-flow restriction was superseded. Save timing paths,
update the QSF seed ledger after a fit, preserve exact RBF/hashes before
hardware loading, and push only to `alanswx`.

Pre-existing untracked files remain deliberately unstaged: `MacQuadra800_wbuf.rbf`,
`docs/osd-standard.md`, `releases/quadra800.rom`, generated CPU build directories,
and Verilator run/log/program outputs. Do not bulk-add or delete them.
