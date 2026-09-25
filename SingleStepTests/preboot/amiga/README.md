# preboot/amiga — bootable Amiga test floppies (68040 suite)

Boot disks that run the wombat33 68040 corpora on Amiga targets — a
**real 68040 Amiga** (A4000/040 class: extra real-silicon oracles the
community can run without a Quadra), **FS-UAE** (build-loop verifier),
and any **Minimig-style 68040 softcore** (as a DUT). Ported from the
MacIIvi project's 68030 Amiga port; the platform layer is this
directory, everything else is the same shared bench code the Quadra
disks run.

The disks support the **68040 only**: a startup gate checks ExecBase
AttnFlags (plus the FPU bit on FPU-bearing disks, and a `MOVEC TC`
probe on MMU disks — a 68LC040/68EC040 is refused with an on-screen
message).

Troubleshooting playbook: [`DEBUGGING.md`](DEBUGGING.md).

## Prebuilt disks

`SingleStepTests/prebuilt/amiga40-*.adf` (committed raw — copy straight
to a Gotek/MiSTer SD card), plus per-fixture tgz and `SHA256SUMS.amiga40`.

| ADF | Suite | Gate |
|---|---|---|
| `amiga40-cpu.adf` | 722-row integer CPU corpus (040 discriminators incl.) | 68040 |
| `amiga40-fpu.adf` | 270-row FPU corpus (040-lite execute-vs-trap) | 68040+FPU |
| `amiga40-saverestore.adf` | 8 FSAVE/FRESTORE state-frame rows | 68040+FPU |
| `amiga40-integration.adf` | 1328-row CPU+FPU integration corpus | 68040+FPU |
| `amiga40-mmu.adf` | MMU hw-safe rows (translation never enabled) | 68040+MMU |
| `amiga40-mmu-full.adf` | all 24 MMU rows incl. live translation + faults | 68040+MMU |

Run mmu before mmu-full on a new machine, per the usual campaign order.

## Running

- **Real Amiga / MiSTer:** mount the ADF in DF0:, reset. KS 2.0+ strap
  boots it. Live progress paints on screen; the run is complete at the
  bench's DONE screen. **The run writes results back to the ADF/floppy**
  — work on a copy.
- **FS-UAE:**
  ```sh
  cp prebuilt/amiga40-fpu.adf /tmp/run.adf
  fs-uae --amiga-model=A4000/040 --kickstart-file=~/kickstarts/kicka4000.rom \
      --floppy-drive-0=/tmp/run.adf --writable_floppy_images=1 \
      --floppy_drive_speed=0 --stdout
  # mmu disks additionally need: --uae_mmu_model=68040
  ```
  (`--writable_floppy_images=1` is required — otherwise results go to an
  overlay file and the ADF stays clean. `--floppy_drive_speed=0` = turbo
  floppy, cuts run time drastically.)

## Getting results out

The disk is a raw layout, not a filesystem. Results are a JSONL stream
at byte offset `0x78000`:

```sh
python3 -c "open('out.jsonl','wb').write(\
open('run.adf','rb').read()[0x78000:0xD8000].rstrip(b'\x00'))"
```

Score against the Quadra 800 hardware oracle:

```sh
python3 ../../gen/score_vs_oracle.py <suite> \
    ../../results/<suite capture>.jsonl out.jsonl
```

`score_vs_oracle.py` normalizes the cross-platform payload layout
(Amiga loads at chip `$80000`, the Mac at `$40000`) as its `layout`
class; FS-UAE-vs-silicon FPU divergences show up as the documented
`fp-policy`/`fpiar` classes. On a real A4000/040, divergences from the
Quadra captures beyond those classes are new silicon data — capture and
report them.

## Disk layout (raw)

Bootblock `0x0-0x3FF` ('DOS\0' checksummed; `PAYLLEN!`/`ALLOCLN!` patch
slots), payload flat binary at `0x400` (loaded to chip `$80000`),
results region `0x78000-0xDBFFF` (400 KB), diagnostic marker slots at
`0xD8000+` (see DEBUGGING.md — your first stop on any wedge).

## Building from source

```sh
make payloads          # bootblock + 6 payloads (repo's m68k GCC)
./build_amiga_adfs.sh            # ADFs -> /tmp/amiga40_prebuilt/
./build_amiga_adfs.sh --package  # + tgz/adf/SHA256SUMS.amiga40 -> ../../prebuilt/
```

## What's shared vs Amiga-specific

Shared with the Mac supervisor_bench (NOT forked): all bench mains,
`recovery.s`, `display_1bpp.c`, `jsonl_writer.c`, `freestanding.c`.
Amiga-specific platform layer (this directory): `bootblock.s`,
`payload_entry_amiga.s` (SuperState + custom-chip takeover +
copper/bitplane display + .bss zeroing), `jsonl_trackdisk.c` (trackdisk
CMD_WRITE backend + the VBR-swapping OS bracket + 040 D-cache push),
`amiga_gate.c` (68040/FPU/MMU gate), `eject_amiga.c` (stub).

Amiga-specific notes:
- Cache ops here are raw `CPUSHA` (`-DAMIGA_BENCH` in the shared
  mains): no `_HwPriv` exists, the MMU is off on a bare boot (no
  `68040.library`), and the Quadra's raw-CPUSHA bus error is a Mac ROM
  environment effect (findings 16/25). `MOVEC ...,CACR` stays banned.
- The saverestore corpus's `FSAVE/FRESTORE (A0)` rows write frames at
  absolute `$80000` — the payload's own first bytes. That code is dead
  after entry, so it is harmless; expected and validated.
- The mmu-full harness identity-maps 256 KB from the load base
  (`-DMMU_PAYLOAD_WINDOW_BASE=0x80000U`), so keep payload+bss under
  256 KB (the build asserts the disk layout separately).
