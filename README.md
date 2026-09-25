# MacQuadra800_MiSTer — Macintosh Quadra 800 (MC68040)

A MiSTer FPGA core (DE10-Nano) for the Apple **Macintosh Quadra 800**
(codename *Wombat*): an authentic 33 MHz 68040 bus, the AP68040 CPU
(Adam Polkosnik's core with Alan Steremberg's performance work, vendored in `rtl/ap68040/`), 128 MB of SDRAM main memory,
DAFB built-in video, NCR 53C96 SCSI with two hard disks and an AppleCD
CD-ROM (data, audio, TOC), Z8530 SCC serial (MIDI / MT32-pi), ASC/EASC
sound, ADB via the VIA. It boots Mac OS 7.x / 8.1 and A/UX 3.1, and
installs Mac OS 8.1 from the retail CD.

The core was called `wombat33` until 2026-09-02. The internal module names
`wombat_cpu` / `wombat_bus32` / `wombat_store_buffer` are a separate
codename and stay.

## Status (2026-09-25 interim)

- **Full-feature performance branch:** the experimental AP040 pipeline and
  structural area reductions fit with Ethernet, CD-ROM/CD audio, disk caching,
  and the normal MiSTer feature set enabled. Five valid Speedometer Mix runs
  give a **1.828 median**; a fresh follow-up gives **1.816**, versus **1.897**
  in the real Quadra 800 photo. See the
  [clean screenshot and metric comparison](docs/perf/INTERIM_VS_REAL_QUADRA800_20260925.md).
- **Experimental artifact, not a timing-clean release:** CPU/RAM/HDMI setup
  misses are **-2.406/-0.697/-0.426 ns**. Audible CD output and OSD usability
  remain unverified at the user's request; A/UX testing is deferred to Dani.
  The [test build](test-builds/README.md),
  [validation audit](docs/INTERIM_COMPLETION_AUDIT_20260925.md), and
  [handoff](RESUME-pr-review-20260925.md) identify the exact artifact
  and coverage. Hardware success does not remove the timing failures.
- **Published releases:** see the table in
  [`releases/README.md`](releases/README.md) for released artifacts, checksums,
  timing, and hardware results. The experimental test build above is separate.
- **Main:** the CD-ROM translation (CUE/CHD discs, CD audio), the BlueSCSI
  Toolbox and the CD changer need the Main fork, whose binary ships beside
  each release as `releases/MiSTer_<date>`. The fork is
  `danifunker/Main_MiSTer`, branch `mac-ethernet-pr`, rebased onto upstream
  `20260907`. A flat `.iso` works on upstream's Main too.
- **Gate before a release:** Mac OS 8.1 to a responsive Finder with a
  ticking clock and a clean Shut Down, and A/UX 3.1 to the multiuser desktop
  and a clean `shutdown -h now`, both on the candidate bitstream.
- **Known, and not the core:** with the retail Mac OS 8.1 CD in the drive,
  the *Quad Squad* system disk shows the disc twice on the desktop. QEMU
  reproduces it with its own CD emulation from the same disk image, and a
  fresh Mac OS 8.1 install shows one icon on both QEMU and the FPGA, so it
  is something in that system folder (its Apple CD-ROM 5.4.2 copy is
  excluded: swapping in Mac OS 8.1's own changed nothing; the rest is not
  yet bisected). Cosmetic, both icons are the same volume
  (`RESUME-cdrom-fix.md`).

## Layout

| path | what |
|---|---|
| `MacQuadra800.{qpf,qsf,sdc,sv}` | the Quartus project; `MacQuadra800.sv` is the MiSTer `emu` top. The `.qsf` **is** the release recipe: its default switches and seed are what ships |
| `files.qip` | the RTL file list (mirrored in the `.qsf`; add new RTL to both) |
| `rtl/quadra800.sv` | the machine: address decode, service FSM, ROM overlay, fast paths |
| `rtl/wombat_cpu.sv`, `rtl/ap68040/` | the CPU wrapper (MMU, cache, store buffer) and the **vendored AP68040** (`rtl/ap68040/UPSTREAM.md`) |
| `rtl/sdram*.sv`, `rtl/wombat_bus32.sv`, `rtl/wombat_store_buffer.sv` | open-page BL8 SDRAM at 99 MHz, the 33/99 MHz beat bridge, the write queue |
| `rtl/ncr53c96.sv`, `rtl/cd_audio.sv`, `rtl/scsi_cache.sv` | SCSI: the 53C96 with disks + AppleCD, the CD TOC/audio engine, the block cache in front of hps_io |
| `rtl/iosb.sv`, `rtl/scc.v`, `rtl/via6522.sv`, `rtl/asc*.sv`, `rtl/dafb*.sv` | I/O, serial, ADB, sound, video |
| `verilator/` | the full-machine Verilator sim and the directed benches (`tb_*.sv`) |
| `SingleStepTests/` | the CPU / FPU / MMU corpus benches against MAME (below) |
| `scripts/`, `tools/misterdeploy/` | build, deploy, screenshot, input injection, guest driving |
| `releases/` | shipped `.rbf`s, Main binaries, the release log, `quadra800.rom` |
| `docs/` | design notes: SDRAM fast path, the block cache, the CD-ROM, performance measurements |
| `BUILD.md`, `CLAUDE.md`, `RESUME-*.md` | the build / deploy / disk handbook, the working rules, session hand-offs (newest first) |

## Building and deploying

**Read [`BUILD.md`](BUILD.md)** before touching hardware. Short form:

```sh
bash scripts/setup_env.sh            # once per machine: writes scripts/local.env
bash scripts/build_only.sh --check   # Analysis & Synthesis only (~13 min), no rbf
bash scripts/build_only.sh           # full compile (~25-40 min) -> output_files/MacQuadra800.rbf
bash scripts/deploy_screenshot.sh    # md5-verified push + load_core (refuses a timing-failed build)
bash scripts/grab.sh out.png         # screenshot of the MiSTer's output
```

Quartus Prime 17.0 Lite. Build from Git bash (not WSL). The design sits at
**98 % of the 5CSEBA6's 41,910 ALMs**, so:

- **Timing must be met** (positive worst slack in `output_files/*.sta.summary`).
  The HDMI PLL domain moves by about ±0.15 ns with any netlist change; a
  failing fit usually wants a different seed, not a source change. Walk seeds
  (`SEED` in the `.qsf`) and record the result in the `.qsf` comment block.
- **After any array change, check the RAM Summary** in the `.map.rpt`: an
  array falling out of M10K into registers costs tens of thousands of ALMs,
  and a small cross-clock array being *inferred* as an M10K is a memory
  fault (`docs/sdram-open-row-crossing.md`).
- `SCSI_TRACE` in the `.qsf` makes a debug build that takes over the serial
  port; it must stay commented out for anything released.

The core mounts its boot ROM from `games/MacQuadra800/boot.rom` and the SCSI
disks from OSD slots `S0` / `S1`, the CD-ROM from `S4`; `BUILD.md` covers
seeding them and the disk images.

## Area: what each piece costs and how to leave it out

For CPU work that needs room, the `.qsf` has one-line switches. Measured
logic (cells or ALMs from the fit and map reports, 2026-09-03 to 09-08):

| block | logic | how to leave it out |
|---|---|---|
| AP68040 core (`ap040_core`) | ~25,100 own cells with Alan's `299cb36` (24,000 with `5aa596f`, 17,600 before it); FPU 7,044 (8,559 before its register bank moved into MLABs), ALU 2,491, MMU 1,205, muldiv 732, I/D cache 721; the whole `wombat_cpu` hierarchy is 37,779 cells | this is the part being optimized |
| CD-ROM target + CD audio engine (`ncr53c96` CD paths, `cd_audio`) | **~3,000 ALMs** (36,830 -> 33,794 at seed 19) | `CDROM_OFF=1` — no CD-ROM at all; the switch is the `CDROM` parameter on `ncr53c96` |
| SCSI block cache (`scsi_cache`) | ~1,750 cells; the CD slot's share ~250 ALMs | `CACHE_CD_OFF=1` (default on: the CD passes through) and `CACHE_SMALL=1` (default on: 32/32/16-sector cache instead of 64/48/16) |
| 512x384 monitor retarget (`pll_cfg_hdmi`) | ~300 cells (715 with the generic `pll_cfg` IP) | `VIDEO_512_OFF=1` |
| composite / Y-C encoder (`yc_out`) | 458 cells | `MISTER_DISABLE_YC=1` — releases keep it |
| ALSA audio over the HPS (`alsa`) | 400 cells | `MISTER_DISABLE_ALSA=1` (default on; MT32-pi is a separate module and is unaffected) |
| scaler refinements (`ascal`) | the scaler is 2,861 cells + 4.4k registers in total | `MISTER_DOWNSCALE_NN=1`, `MISTER_DISABLE_ADAPTIVE=1` (default on) |
| framework OSDs, `audio_out` IIR, `pll_hdmi_adj` | 1,800 / 798 / 779 cells | no switch; part of the MiSTer framework |
| serial (`scc`, four UARTs), `iosb`, `dafb`, `easc`, `sdram` | 1,112 / 1,172 / 561 / 481 / 613 cells | no switch |

The switches live near the end of `MacQuadra800.qsf` as
`set_global_assignment -name VERILOG_MACRO "NAME=1"` lines, next to a
comment block that records what the release recipe is. Rules of thumb:

- **The release recipe** (the `.qsf` defaults): `OPTIMIZATION_MODE` and
  `OPTIMIZATION_TECHNIQUE` **BALANCED**, physical-synthesis register
  duplication **off**, `CACHE_CD_OFF`, `CACHE_SMALL`, `MISTER_DISABLE_ALSA`,
  `MISTER_DOWNSCALE_NN`, `MISTER_DISABLE_ADAPTIVE` on; Y/C kept; CD-ROM kept.
  Speed-directed synthesis no longer fits; all-area synthesis fits but fails
  timing in the HDMI PLL domain.
- **For a CPU experiment that is over budget,** set `CDROM_OFF=1` first
  (3,000 ALMs, by far the largest lever) and add `VIDEO_512_OFF=1` and
  `MISTER_DISABLE_YC=1` if still short. `CDROM_OFF=1` also removes the
  M10K/DSP use of the CD engine. Such a build is a measurement build: a
  release always has the CD on, because users install from it.
- A LAB is 10 ALMs; the fitter reports a shortfall in LABs (4,191 in this
  part). Fitter register-packing knobs change nothing here: the pressure is
  LUT logic.
- The CPU's own tests: `sh rtl/ap68040/tb/run_tests.sh` (iverilog + vasm),
  and the corpus benches below. The CPU is vendored, not a submodule: commit
  changes to it here; `rtl/ap68040/UPSTREAM.md` records its origin.

## Simulation

Verilator 5 in WSL (`bash scripts/sim_wsl.sh build|disk|run|log`) runs the
whole machine from the real ROM and disk images; the directed benches are
`make tb_sdram tb_wombat_bus32 tb_store_buffer tb_memory_path tb_ncr53c96
tb_scsi_cache tb_easc` in `verilator/`. QEMU's `q800` (built from `../qemu`)
boots the same ROM and disks and is the reference for SCSI behaviour.
Verilator is lenient where Quartus is not: run `build_only.sh --check` after
new RTL passes its bench.

## Testbench (`SingleStepTests/`)

Per-instruction CPU / FPU / MMU benches captured against MAME's
`macquadra800` driver as the oracle, designed to also run on real Quadra
800 hardware (boot the payload, collect `/Results.jsonl`, diff offline).
Lineage: the 68020 Mac II bench (`../lbmactwo_MiSTer`) via the 68030
Macintosh IIvi bench (`../MacIIvi_MiSTer`), with the FPU material
re-imported (the 040 has an on-chip FPU).

**Read [`QUADRA800_TESTBENCH.md`](QUADRA800_TESTBENCH.md) first** for the
plan, the verified machine facts, the 040-lite FPU execute-vs-trap model, the
68040 MMU corpus design and the hardware campaign. Status and quirks:
[`SingleStepTests/test-blockers.md`](SingleStepTests/test-blockers.md).

```sh
# Build the bootable bench payloads (Retro68 toolchain, -m68040):
cd SingleStepTests/preboot/supervisor_bench
make cpu        # 68040 integer corpus  (722 rows)
make fpu        # 68040 FPU corpus       (execute-vs-trap, vector 11)
make mmu        # 68040 MMU corpus       (MOVEC regs, live walk, format-$7)

# Re-capture the MAME baselines (needs ~/repos/mame built with the driver):
cd ~/repos/mame
./mame macqd800 -skip_gameinfo -nothrottle -video none -sound none -seconds_to_run 200 -autoboot_delay 1 -autoboot_script <repo>/SingleStepTests/gen/mame_cpu_capture.lua

# Diff a hardware run against the baseline:
SingleStepTests/gen/cpu_diff_corpus.py SingleStepTests/results/cpu/mame_baseline_2026-06-12.json /path/to/Results.jsonl
```

Verified 2026-06-12: CPU + MMU corpora captured from MAME `macqd800`; the
MMU bench exercises live 68040 translation (U/M writeback), remap, ATC flush
and format-$7 access faults; the FPU bench distinguishes the 040 hardware
subset from the unimplemented ops (vector-11 trap). The payloads draw on the
built-in DAFB at `$F9000000`, 1 bpp, with the row stride read from the ROM's
`ScrnRow` / `ScrnBase` globals.
