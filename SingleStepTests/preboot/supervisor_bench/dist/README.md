# Prebuilt Quadra 800 supervisor-mode bench disks

Bootable disk images of the 68040 benches, ready to run on a real
Macintosh Quadra 800. Each disk boots straight into the bench (no System
needed) via the HFS boot block; the bench runs in supervisor mode, paints
progress on the built-in DAFB display, and writes results to
**`/Results.jsonl`** on the same disk.

**REQUIREMENT: set the display to 640×480, 256 colors** (8 bpp — the
Quadra 800 boot default). See `../../../prebuilt/README.md`.

| Disk | Bench | Corpus |
|---|---|---|
| `quadra800-allinone.hda` | **all five suites, chained** | cpu → fpu → saverestore → mmu-full → integration, one results file |
| `quadra800-cpu.{hda,dsk}` | 68040 integer CPU | 722 rows (full ISA + 040 discriminators) |
| `quadra800-fpu.{hda,dsk}` | 68040 FPU | 270 rows; 040-lite subset executes, unimplemented ops trap (vector 11) |
| `quadra800-mmu.{hda,dsk}` | 68040 MMU, hw-safe rows | register-mask + PFLUSH rows |
| `quadra800-mmu-full.hda` | 68040 MMU, all rows | 24 rows incl. live translation + deliberate faults |
| `quadra800-cpu-fpu.{hda,dsk}` | CPU+FPU integration | 1328 rows, self-scoring; the tail runs only on silicon |
| `quadra800-cpu-fpu-saverestore.hda` | FSAVE/FRESTORE | 8 state-frame rows |

- **`.hda`** — SCSI hard-disk image (APM + Apple_HFS). Write to a
  BlueSCSI / SCSI2SD / real SCSI disk, or attach in an emulator.
- **`.dsk`** — 1.44 MB HFS floppy image.

All hardware-flavor: the boot stub does NOT set `BOOT_SET_DTT0` (that
block crashed the real boot; emulators need it — rebuild with
`EXTRA_ASFLAGS="--defsym BOOT_SET_DTT0=1"` after `make clean`, finding 23).

## Boot screen + expected `C`

The boot block paints `A` (BootDrive), `D` (driver refnum), `E` (`_Read`
ioResult), `C` (payload checksum), `3` (jumping). `C` must match the
table below on EVERY boot; a differing or unstable value means the
payload was corrupted in transit (findings 7/16).

| Image | expected `C` |
|---|---|
| `quadra800-allinone.hda` | `862D7F48` |
| `quadra800-cpu.hda` / `.dsk` | `BBBAB3E8` / `FD9DAB49` |
| `quadra800-fpu.hda` / `.dsk` | `D7B33439` / `1FB33427` |
| `quadra800-mmu.hda` / `.dsk` | `3B2760E6` / `EA840339` |
| `quadra800-mmu-full.hda` | `20472FDB` |
| `quadra800-cpu-fpu.hda` / `.dsk` | `6104B2AD` / `61041CED` |
| `quadra800-cpu-fpu-saverestore.hda` | `E55EE0AE` |

Recompute after any rebuild: `python3 ../../../gen/boot_cksum.py <image>`.

## The all-in-one disk

Runs every suite in sequence with no image swapping: at each suite's
DONE the entry shim jumps to a chain stub at `$7C000` that `_Read`s the
next payload over `$40000` (≤16 KB slices, `_HwPriv` sel 1 cache flushes
both sides) and re-enters it. All suites append into ONE 1 MB
`/Results.jsonl` at fixed regions; `quadra800-allinone.hda.manifest.json`
records the layout. Suite order puts integration LAST (emulators die in
its tail — finding 23; silicon runs it).

Expected screens, in order: CPU bench → ALL TESTS DONE → FPU bench →
ALL FPU TESTS DONE → integration runner (8 saverestore rows) → MMU
bench → MMU BENCH DONE → integration runner (1328 rows) → final DONE
and hang. Each DONE screen is replaced by the next suite's wipe within
a second or two; only the last one persists.

Extraction:
```sh
rb-cli get quadra800-allinone.hda@1 /Results.jsonl results.bin
python3 ../../../gen/split_allinone_results.py \
    quadra800-allinone.hda.manifest.json results.bin outdir/
```

QEMU-validated end to end (suites 1–4 complete + integration rows 1–972,
the known emulator ceiling); per-suite row counts and MMU observables
identical to the single-suite runs.

## Per-suite runs

1. Boot, let the bench run to its DONE screen (the entry paints `DONE`
   at the bottom and hangs).
2. Power off, pull `/Results.jsonl` (strip NULs).
3. CPU rows diff against `../../../results/cpu/mame_baseline_2026-06-12.json`
   via `gen/cpu_diff_corpus.py` (bridge: drop `trap_state` rows, add
   `"initial": {}`); FPU/MMU/integration rows are self-describing —
   the 2026-08-28 hardware captures in `../../../results/` are the
   silicon ground truth to compare against.

Older diagnostic images in this directory (`*-nowrite*`, `*-srtest-*`,
`*-bootwritetest*`, `*-27c-writepath*`) are superseded bisection
artifacts from the write-path campaign (findings 19–25); keep for
archaeology, do not boot expecting current behavior.
