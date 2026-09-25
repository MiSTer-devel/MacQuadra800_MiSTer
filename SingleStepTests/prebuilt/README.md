# Prebuilt Quadra 800 bench disks (committed fixtures)

Compressed, ready-to-run bootable disk images of the three 68040 benches.
Each `.tgz` holds the SCSI hard-disk image (`.hda`) and the 1.44 MB HFS
floppy (`.dsk`) for one bench. Boot a Quadra 800 (or any 68040 Mac) from
the disk and it runs the bench straight from the HFS boot block — no
System needed — painting progress on the built-in DAFB display and
writing `/Results.jsonl` back to the same disk.

> ## ⚠️ REQUIREMENT: set the display to **640×480, 256 colors**
> The bench paints the built-in DAFB at **8 bits-per-pixel** (the Quadra
> 800's boot default — the Apple 640×480 @ 67 Hz mode). If the monitor is
> in a different colour depth the on-screen text will be garbled. Set
> Monitors to **640×480, 256 Colors** before running (or just leave the
> machine at its default). The byte stride is read from the ROM at
> runtime, so other *resolutions* at 256 colors also work; the depth is
> what matters. (A `dafb1` build exists for 1 bpp / B&W screens.)

| Bundle (`2026-06-13`) | Bench | Corpus |
|---|---|---|
| `quadra800-cpu-2026-06-13.tgz` | 68040 integer CPU | 722 rows (full ISA + 040 discriminators: MOVE16, CACR/CAAR mask, RTM) |
| `quadra800-fpu-2026-06-13.tgz` | 68040 FPU | 270 rows; hardware subset executes, unimplemented ops trap (vector 11) |
| `quadra800-mmu-2026-06-13.tgz` | 68040 MMU | 24 rows; register-mask + PFLUSH run, live/fault rows skipped (see note) |
| `quadra800-cpu-nowrite-diag-2026-06-13.tgz` | CPU bench, **disk writes stubbed out** | diagnostic only — runs all 722 to confirm the freeze was the SCSI write, not a CPU hang |

## Use

```sh
tar xzf quadra800-cpu-2026-08-27.tgz       # -> quadra800-cpu.hda + .dsk
sha256sum -c SHA256SUMS                     # verify the bundles first
```
- **`.hda`** — write to a BlueSCSI / SCSI2SD / real SCSI disk, or attach
  in an emulator. APM + Apple_HFS, boots directly into the bench.
- **`.dsk`** — 1.44 MB HFS floppy; write with Disk Copy / Greaseweazle /
  `dd`, or mount in an emulator.

Run it to **"ALL TESTS DONE"**, power off, pull `/Results.jsonl`, and diff:
```sh
../gen/cpu_diff_corpus.py ../results/cpu/mame_baseline_2026-06-12.json Results.jsonl
../gen/mmu_diff_corpus.py ../results/mmu/mame_baseline_2026-06-12.json Results.jsonl
# fpu: per row, vec 11 = an unimplemented op correctly trapped; vec 0 = executed
```

## Amiga 68040 floppies (`amiga40-*.adf`, 2026-08-28)

The same six 68040 suites as bootable **Amiga** floppies — for real
A4000/040-class machines (extra silicon oracles anyone can run without
a Quadra), FS-UAE, and Minimig-style 68040 softcore DUTs. Raw ADFs are
committed next to this file (copy straight to a Gotek/MiSTer SD card);
`SHA256SUMS.amiga40` covers them. A startup gate refuses anything that
is not a 68040 (FPU-bearing disks also refuse the 68LC040; MMU disks
probe and refuse the 68EC040).

The disk is a raw layout, not a filesystem: boot it, let it run to the
DONE screen, then pull the JSONL stream from byte `0x78000` of the
mutated ADF and score it against the Quadra captures with
`gen/score_vs_oracle.py`. Full instructions, FS-UAE command lines and
the debugging playbook: `../preboot/amiga/README.md`.

FS-UAE (A4000/040) validation status is recorded in
`../results/amiga40/` — every suite boots, gates, runs and writes
results; the saverestore suite matches the Quadra 800 silicon capture
exactly. FS-UAE-vs-silicon divergences on the other suites are the
scorer's documented classes (emulator FPU model, layout normalization);
real-silicon Amiga captures are the interesting contribution.

## 2026-08-28b bundles — the full set on one tree, plus the all-in-one chain disk

**Boot these.** Every suite rebuilt from one tree carrying every hardware
fix on record (CACR relic out, corrected FDBcc goldens, sliced writer,
`HANDOFF_ADDR=$80000`), plus the new **all-in-one disk** that runs every
suite in sequence with no image swapping. Supersedes the `2026-08-28`
integration bundles below (those carry the CACR relic and the inverted
FDBcc goldens) and every earlier per-suite set.

| Bundle (`2026-08-28b`) | Corpus | expected `C` |
|---|---|---|
| `quadra800-allinone-2026-08-28b.tgz` | **all five suites chained**: cpu → fpu → saverestore → mmu-full → integration | `862D7F48` |
| `quadra800-cpu-2026-08-28b.tgz` | 68040 integer CPU, 722 rows | `BBBAB3E8` (dsk `FD9DAB49`) |
| `quadra800-fpu-2026-08-28b.tgz` | 68040 FPU, 270 rows | `D7B33439` (dsk `1FB33427`) |
| `quadra800-mmu-2026-08-28b.tgz` | MMU hw-safe rows | `3B2760E6` (dsk `EA840339`) |
| `quadra800-mmu-full-2026-08-28b.tgz` | MMU all 24 rows, live translation | `20472FDB` |
| `quadra800-cpu-fpu-2026-08-28b.tgz` | CPU+FPU integration, 1328 rows | `6104B2AD` (dsk `61041CED`) |
| `quadra800-cpu-fpu-saverestore-2026-08-28b.tgz` | FSAVE/FRESTORE, 8 rows | `E55EE0AE` |

Recompute any `C` with `../gen/boot_cksum.py <image>` — it reads the
image's own patched markers.

### The all-in-one chain disk

One `.hda`, five payloads at known partition offsets, one pre-allocated
1 MB `/Results.jsonl` with a fixed region per suite. Each payload ends by
jumping to a small stub above the read window that `_Read`s the next
payload over `$40000` (sliced into ≤16 KB driver requests, caches flushed
via `_HwPriv` sel 1 on both sides) and re-enters it — the boot block's own
load step, repeated. Integration runs LAST because both emulators die in
its corpus tail (finding 23); on hardware it runs to completion.

To read a finished (or partial) run:
```sh
rb-cli get disk.hda@1 /Results.jsonl results.bin
../gen/split_allinone_results.py quadra800-allinone.hda.manifest.json results.bin outdir/
```
The manifest ships in the bundle; the splitter carves the per-suite
regions, strips NULs, and reports row counts.

QEMU (git-master q800, the MMU/FPU oracle) validated the chain end to
end: cpu 717 + fpu 270 + saverestore 8 + mmu-full 25 rows — counts and
mmu observables identical to the single-suite runs (mmu: 49 match /
7 known-artifact / 0 real diffs) — then integration rows 1–972 flushed
before QEMU's known tail crash. The tail remains hardware territory, as
on the singles. One hardware-only unknown remains flagged: the chain's
`_Read` runs under the ROM vector table at bench time, a path silicon has
only proven at boot time — if a hop Sad-Macs `0F/000A` on the real
machine, that's the F-line-in-`_Read` signature (finding 20's class) and
the fallback is a forwarding table around the chain read.

Behavior changes shared by every 28b image: the bench mains now RETURN to
the entry shim (which paints `DONE` at row 56 and hangs, or chains on the
all-in-one), and the entry re-plants the `$80000` handoff before a chain
hop because the saverestore corpus's `FSAVE/FRESTORE (A0)` rows scribble
that address — per-suite disks are behaviorally identical to the
hardware-validated 28/27c builds apart from the extra `DONE` glyphs.

## 2026-08-28 bundles — CPU+FPU integration bench

**Superseded by the 2026-08-28b bundles above** — these builds carry the
68020 CACR relic (finding 25) and the inverted FDBcc goldens (finding 26).

The Mac II-lineage CPU+FPU integration suite, finally wired into the
Quadra build (`../test-blockers.md` finding 23). Rows are self-scoring
on-device: each JSONL line carries `expected`/`actual`/`pass`/`vec`, so
no external baseline is needed to read a run.

| Bundle | Contents | expected `C` |
|---|---|---|
| `quadra800-cpu-fpu-2026-08-28.tgz` | 1328-row CPU+FPU integration corpus, `.hda` + `.dsk` | `CE2ED223` |
| `quadra800-cpu-fpu-saverestore-diag-2026-08-28.tgz` | 8-row FSAVE/FRESTORE state-frame set, `.hda` | `379A169A` |

Emulator regression: 972/972 rows pass identically on MAME and QEMU,
8/8 on the FSAVE/FRESTORE set — then **both emulators die on the
corpus tail** (MAME fatal-aborts on the FDBcc/FScc/FTRAPcc conditional
class, QEMU dumps core nearby). Real 68040 silicon implements those in
hardware, so the Quadra is expected to run the full 1328 and will be
the first machine to score the tail. Some rows also contain
040-unimplemented FP ops that trap vector 11 on silicon — the `vec`
column records it; that is data, not failure.

The prior hardware-campaign results (2026-08-28, from the `-27c` set)
live in `../results/{cpu,fpu,mmu}/hardware_quadra800_2026-08-28.jsonl`
with the adjudications in finding 22.

## 2026-08-27c bundles — the write bug is root-caused and FIXED

**Boot these.** The `-27b` CPU disk did its diagnostic job on hardware:
instead of the Sad Mac it painted `FLINE OP+PC: FFFF 0000FF44` at the
first flush — a garbage jump into low RAM. Root cause
(`../test-blockers.md` **finding 21**): the boot block parked its stack
at `$10000`, on top of the ROM boot heap, and its own calls smashed the
SCSI Manager 4.3 write-path glue that lives just below — on this
hardware ~$BC below the stack top (always destroyed), on MAME/QEMU
~$B38 below (never reached, which is why no emulator ever reproduced
it). `_Read` doesn't use that structure; the first `_Write` executed
the corpse.

**Fix in these builds: stacks only on RAM we own.** The boot block no
longer touches SP at all (the ROM's stack is valid), and the payload
stack moved from `$100000` to `$80000`, the top of its own 256 KB read
window. The F-line shim stays in every payload — dormant when all is
well, and on any future unknown fault it now paints the frame
format/vector, the format-2 effective address, the instruction bytes
around the stacked PC, and up to three return addresses, so one photo
identifies the fault completely.

This is the **complete bench set** — all payloads carry the stack fix
and the shim:

| Bundle | Contents | expected `C` |
|---|---|---|
| `quadra800-cpu-2026-08-27c.tgz` | CPU corpus `.hda` + `.dsk` | `15B290B9` |
| `quadra800-fpu-2026-08-27c.tgz` | FPU corpus `.hda` + `.dsk` | `ACA128F0` |
| `quadra800-mmu-2026-08-27c.tgz` | MMU corpus `.hda` + `.dsk` | `F1F9AAAE` |
| `quadra800-cpu-nowrite-diag-2026-08-27c.tgz` | CPU bench, writes stubbed | `AF16311A` |
| `quadra800-cpu-bootwritetest-diag-2026-08-27c.tgz` | boot-block `_Write` probe (`.hda`) | `15B290B9` |

Regression state (all on these exact payloads): MAME `macqd800` — CPU
corpus `ALL TESTS DONE`, `ioResult=0000`, no shim line, extracted
results **667/696 match** vs baseline; FPU 270/270 rows,
`ioResult=0000`; MMU 24 rows (`ran=14 skipped=10`); nowrite full
corpus. QEMU — CPU diff report **byte-identical** to the pre-shim
build; FPU 270/270; MMU 24/10.

## 2026-08-27b bundles — the SCSI `_Write` F-line shim (SUPERSEDED by -27c)

**Boot these for the write investigation.** The one thing the `-27`
CPU bundle cannot do on the real machine — write `/Results.jsonl` (Sad
Mac `0000000F 0000000A` at the first 16 KB flush, ~test 58) — is what
this build addresses. The payload now carries an F-line safety net for
the OS-side write path; full analysis in `../test-blockers.md`
**finding 20**, next-step matrix in `../../RESUME-scsi-write.md`.

| Bundle | Contents |
|---|---|
| `quadra800-cpu-2026-08-27b.tgz` | CPU bench `.hda` + `.dsk`, F-line shim in the payload |
| `quadra800-cpu-bootwritetest-diag-2026-08-27b.tgz` | boot-block-only `_Write` probe (no payload runs, no shim) |

What the shim does during each `_Write` bracket (only there — tests
still run under the bench's own recovery table):

- `MOVE16 (A0)+,(A1)+` → emulated; CINV/CPUSH (`$F4xx`) and
  PFLUSH/PTEST (`$F5xx`) → skipped. These are what the ROM's 68040
  `_BlockMove` and its cache epilogue execute on the write path.
- anything else → paints **`FLINE OP+PC: xxxx xxxxxxxx`** at row 40
  and **halts with the screen alive** — photograph that line; it names
  the exact instruction and address that used to Sad Mac.
- every hit is counted; a completed run paints
  `shim=NNNNNNNN op=XXXX pc=XXXXXXXX` on the DONE screen. **A DONE
  screen with no shim line means the write worked with the shim never
  firing.**

The live vector table at 0 is never modified (patching `$2C` in place
trips a ROM data-read of that slot → SysError `0F/1B`; finding 20).
The bracket instead runs under a private table that forwards every
other vector through the live low-mem slots at exception time.

The `bootwritetest` image is the environment discriminator: it runs
one 512-byte `_Write` from the boot block itself — ROM vectors, no
payload, no shim — after the usual five lines. **7 lines painted** =
`_Write` returned, row 76 holds its `ioResult`; **6 lines** = it hung
inside `_Write`; **Sad Mac** = same crash even in the pristine boot
environment (the write path is broken independent of the bench).
The write is the payload's own first sector rewritten in place, so
the disk is unchanged.

Regression state: MAME `macqd800` runs this exact payload to
`ALL TESTS DONE`, `ioResult=0000`, no shim line, and the extracted
results diff **667/696 match** against the baseline — identical to the
pre-shim build. QEMU's diff report is byte-identical pre/post shim.
Neither emulator can reproduce the hardware failure (their 68040
executes every suspect instruction); they only prove no regression.

Expected `C` line for both `-27b` images: **`678854F7`**
(window `0x1F200`; both flavors share the payload byte-for-byte).

## 2026-08-27 bundles — FULL rebuild (boot block **and** payload)

**Boot these.** Two things are new. First, unlike the 2026-08-26
bundles, which were **boot-block-only** re-splices carrying the
unchanged 2026-06-13 payloads, these are **full rebuilds: the payload
was recompiled too**, so the `payload_entry_cpu.s` 8 bpp paint fix
ships in an image for the first time here.

Second, and more important: the boot block now **sets up transparent
translation (`DTT0`) for the DAFB aperture before it touches the
screen.** The ROM hands the boot block a machine with the 68040 MMU
enabled and every transparent-translation window disabled, so writes to
`ScrnBase` did not reach video RAM — they landed at physical
`$00001000`, and the 128 KB screen wipe destroyed low memory
`$1000..$21000`, drive queue included. That is the real "the bench
mostly does not start" bug (finding 11 in `../test-blockers.md`); the
2026-08-26 cache fix was necessary but not sufficient.

With it, **all four benches now boot end to end under MAME `macqd800`**
— the first time that has ever worked.

Third: `ANDI.W #$F8FF,SR` is now marked `hw_unsafe` and skipped. It was
the only row in the 722 that lowers the SR interrupt mask, and it wedged
the bench at test 180 (finding 12). With it skipped the **CPU bench runs
all 722 rows to `ALL TESTS DONE` and writes `/Results.jsonl` with
`ioResult=0000`** — verified under MAME by extracting the file back off
the disk and diffing it: 717 written, 696 comparable, **667 exact match**
against the MAME baseline. The 29 that differ are corpus-portability
artifacts, not CPU divergences (finding 13).

Fourth, and the one that matters if you reuse a disk: the payload now
**zeroes its own `.bss`**. It never did. `.bss` is `NOLOAD`, so every C
static started as whatever the boot block's 256 KB over-read happened to
leave at those addresses — zeros *only while `/Results.jsonl` is still
blank*. After one completed run that region holds JSON text, so the
statics came up as garbage on the next boot: the cached display stride
became nonsense and the screen wipe ran ~4 MB past the framebuffer into
the DAFB registers. In other words **the disks used to be single-use** —
they worked once and then failed. Fixed in `payload_entry_cpu.s`, which
all three benches share (finding 15).

Fifth, and this one came from the machine rather than an emulator:
**raw `CPUSHA BC` (`$F4F8`) takes a bus error on real Quadra 800
silicon.** Finding 7 had put it on both sides of the payload `_Read`, and
`flush_icache()` used it once per test. Every cache flush now goes
through the ROM instead — `_HwPriv` selector 1, which the Developer Note
says flushes *both* caches on the 68040 in a single call. See finding 16.

All `C` values changed with this rebuild, because every payload did.

| Bundle | Bench |
|---|---|
| `quadra800-cpu-2026-08-27.tgz` | 68040 integer CPU, 722 rows |
| `quadra800-fpu-2026-08-27.tgz` | 68040 FPU, 270 rows |
| `quadra800-mmu-2026-08-27.tgz` | 68040 MMU, 24 rows |
| `quadra800-cpu-nowrite-diag-2026-08-27.tgz` | CPU bench with SCSI writes stubbed out |

Both fixes are now in both halves of the image:

- **boot block** — `CPUSHA BC` either side of the payload `_Read`, and
  8 bpp diagnostics (shipped 2026-08-26, unchanged here).
- **payload entry** — `payload_entry_cpu.s` now paints 8 bpp with a
  runtime `ScrnRow` stride instead of 1 bpp. On the Quadra's DAFB the
  old code was unreadable speckle. **New in these bundles.**
- **boot block checksum** — the `C` line is sized per image from the
  `PAYLCKSZ` marker the build scripts patch.

Payload sizes (they moved, because the payload actually changed):

| Image | payload | `C` window |
|---|---|---|
| cpu | 125218 B | `0x1EA00` |
| fpu | 32442 B | `0x8000` |
| mmu | 27040 B | `0x6A00` |
| cpu-nowrite | 124938 B | `0x1EA00` |

### Reading the boot screen

Five lines appear before the bench itself starts:

```
A 00000003     boot block running; BootDrive = 3
D FFFFFFDF     driver refnum from the drive queue (negative = normal)
E 00000000     _Read ioResult -- 00000000 is noErr; anything else = load failed
C 5A9646DF     checksum of the payload as loaded into RAM
3 <block>      about to JMP into the payload
```

`C` is the diagnostic that settles whether the cache fix took. It is a
rotating 32-bit sum over the region HFS allocated to `/Payload`, taken
straight after the transfer and **before** anything else touches RAM.
Expected values, per image (**these are the 2026-08-27 rebuilds** —
every payload rebuild changes them):

| Image | expected `C` |
|---|---|
| `quadra800-cpu.hda` | `1D983A3F` |
| `quadra800-fpu.hda` | `F1B384AB` |
| `quadra800-mmu.hda` | `19300E07` |
| `quadra800-cpu-nowrite.hda` | `1F98DFE8` |

- Matches, and the bench runs → the payload arrived intact.
- **Differs, or differs between two boots of the same disk** → the
  payload is still being corrupted in transit; the cache fix is not the
  whole story. Photograph the value and the `E` line.
- `E` non-zero → the load itself failed; the block halts there and the
  code on screen is the driver's `ioResult`.

## 2026-08-26 bundles — 68040 cache fix + readable boot diagnostics

**Superseded by the 2026-08-27 bundles above.** Same bench payloads as
06-13, byte for byte; the only change is the 1024-byte HFS boot block.
The `C` values these images paint differ from the table above, because
their payloads are the older 06-13 builds.

| Bundle | Bench |
|---|---|
| `quadra800-cpu-2026-08-26.tgz` | 68040 integer CPU, 722 rows |
| `quadra800-fpu-2026-08-26.tgz` | 68040 FPU, 270 rows |
| `quadra800-mmu-2026-08-26.tgz` | 68040 MMU, 24 rows |
| `quadra800-cpu-nowrite-diag-2026-08-26.tgz` | CPU bench with SCSI writes stubbed out |

### What changed and why

Symptom on the physical Quadra 800: the bench **mostly did not start at
all**, and only very occasionally got as far as painting. The boot block
loads 256 KB of payload to `$40000` with one `_Read` and then `JMP`s
into it — with no cache management. That was safe on the 68020/68030
(256-byte write-through caches); on the 68040 it is not:

- dirty lines in the 4 KB **copyback** data cache, left over from the
  ROM's own use of low RAM, get written back **on top of** the payload
  that the SCSI transfer just delivered, and
- stale lines in the 4 KB instruction cache get executed instead of the
  bytes that actually arrived.

Whether a given boot lands the damage on code that matters or on padding
is luck, which is exactly why it looked intermittent. The boot block now
issues `CPUSHA BC` on **both** sides of the `_Read` (push *and*
invalidate — `CINVA` would throw away the payload if the driver copies
through the CPU rather than DMAing), with a `NOP` after each for
pipeline sync. Same class of bug as the `CPUSHA DC` fix for `_Write`;
the read side had simply never been covered.

The boot block's own readouts were also still painting **1 bpp** into
the Quadra's 8 bpp framebuffer — one byte per eight pixels — so the
drive number, driver refnum and `_Read` result code have been
unreadable speckle for the whole bring-up. They now paint one byte per
pixel and take the row stride from `ScrnRow` at runtime.

### Provenance

The boot block was rebuilt from
`../preboot/common/boot/boot_stub_scsi.s` and spliced into the 06-13
images; every byte outside the 1024-byte boot block is unchanged
(verified by byte-diff). It was validated before shipping by executing
the assembled block under Musashi against a simulated Quadra 800 low
memory + DAFB framebuffer: the painted screen renders legibly, the
handoff slot receives `FFDF 0003`, and the 68k checksum routine
reproduces the host-computed expectation for every image above. The
1 bpp path was re-checked the same way at stride 80 so the Mac II /
IIvi lineage is not regressed.

## Provenance / validation (2026-06-13)

Built by `preboot/supervisor_bench/build_<bench>_<hda|dsk>.sh` from the
captured corpora (`gen/{cpu,mmu,fpu}_tests.h`) with the Retro68
`m68k-apple-macos-gcc -m68040` toolchain. The 8 bpp paint kernel was
**verified by host-rendering** the bench screen through the exact same
`display_1bpp.c` code (`-DDISPLAY_BPP8`): "SUPERVISOR CPU BENCH …" and the
`run=/ok=/trap=` tally render as clean, legible white-on-black text at
640×480×8 bpp. ScrnBase on the Quadra is `$F9001000` (DAFB VRAM); the byte
stride (1024 for 640×480) is read from the ROM's `ScrnRow` ($0106) global
at runtime.

> **Display history:** the first cut painted 1 bpp into the 8 bpp DAFB
> framebuffer → garbled characters (one font byte became one 8 bpp pixel).
> Fixed 2026-06-13 by painting one byte per pixel; hence the 640×480×256
> requirement above.
>
> **Results write-back (2026-06-13 hardware finding + fix):** on the
> first real run the bench froze at `run=58` with an all-zero
> `/Results.jsonl`. Cause: the writer buffers into 16 KB batches, so the
> first SCSI `_Write` fires only when that buffer fills (~line 58) — and
> on the 68040 the buffer was filled through the **copyback data cache**
> while the Quadra's SCSI does **DMA from physical RAM**, so the driver
> read stale RAM and wedged. (The Mac II this code came from is a 68020
> with no copyback cache, so it never hit this.) **Fix:** the writer now
> issues `CPUSHA DC` (push the data cache to RAM) before every `_Write`.
>
> If a run still freezes or `/Results.jsonl` is still empty, boot the
> **`quadra800-cpu-nowrite-diag`** disk: it stubs the SCSI write out
> entirely, so it should run all 722 tests to `ALL TESTS DONE`. If it
> does, the remaining issue is purely the write path (next stop: a
> serial-port results channel, which sidesteps SCSI/DMA). If it *still*
> freezes at the same test, the problem is that test's execution, not the
> write. Either way the on-screen `run=/ok=/trap=` tally + final
> `ioResult=` are a valid readout — photograph the screen.

## Notes

- **MMU bench:** the register-characterization + PFLUSH rows run; the
  live-translation and fault rows are emitted `skipped:"live-reloc-todo"`
  pending the private-identity-page-table relocation (port from
  `../preboot/supervisor_bench/mmu_bench_main.c.68030-reference`).
- **FPU bench:** assumes MC68040-lite + no FPSP — transcendentals are
  expected to trap (vector 11). If the core embeds a full 68882 FPU,
  those rows execute instead; that *is* the discriminator.
- Rebuild from source: `cd ../preboot/supervisor_bench && make {cpu,fpu,mmu}`
  then `./build_<bench>_<hda|dsk>.sh`. The raw images land in `dist/`
  (gitignored); these `.tgz` are the committed copies.

See [`../../QUADRA800_TESTBENCH.md`](../../QUADRA800_TESTBENCH.md) for the
full plan and [`../test-blockers.md`](../test-blockers.md) for status.
