# bbsim — run a Mac boot block against a simulated Quadra 800

Offline verification for `preboot/common/boot/*.s` and the payload entry
shims: assembles nothing, just **executes** an already-built boot block
under [Musashi](https://github.com/kstenerud/Musashi) with a simulated
Quadra 800 low memory and DAFB framebuffer, then dumps the framebuffer so
you can look at what it painted.

It exists because the physical Quadra is a slow loop, and it catches
paint-polarity, row-stride and register-clobber mistakes in seconds.

> **Caveat, added 2026-08-27 — bbsim has no MMU.** It maps VRAM flat at
> `$F9000000`, so a screen wipe through `ScrnBase` always "works" here.
> On the real machine the ROM hands the boot block an MMU that is *on*
> with no transparent-translation windows, and that wipe went to
> physical `$00001000` instead — destroying low memory. bbsim was blind
> to it for ten weeks (finding 11 in `test-blockers.md`). A clean bbsim
> run is necessary, not sufficient; MAME `macqd800` **does** boot these
> disks end to end and is the stronger check.

## What it simulates

| Piece | Value |
|---|---|
| RAM | 8 MB at `$0` |
| VRAM | 3 MB at `$F9000000` |
| `ScrnBase` `$0824` | `$F9001000` |
| `ScrnRow` `$0106` | `$SCRNROW` (default 1024) |
| `BootDrive` `$0210` | 3 |
| `DrvQHdr` `$030A` | one DrvQEl: `dQDrive`=3, `dQRefNum`=-33 |
| `_Read` (`$A002`) | stub: returns `noErr`; the "transferred" payload is placed in RAM by the harness |
| Line F (vector 11) | stub that steps over the instruction — Musashi does not decode the 68040 `CINV`/`CPUSH` cache ops |

The cache instructions are therefore **not** exercised here; their
encodings are verified instead by assembling the mnemonics
(`m68k-elf-as -m68040`) and reading back the opcode.

## Build and run

```sh
cc -O1 -I ~/repos/Musashi -o bbsim bbsim.c \
   ~/repos/Musashi/m68kcpu.c ~/repos/Musashi/m68kops.c \
   ~/repos/Musashi/m68kdasm.c ~/repos/Musashi/softfloat/softfloat.c

# boot block + the payload it would have loaded, injected at $90000
./bbsim boot_stub.bin payload.bin 0x90000
./render_fb.py fb_dump.bin screen.png --stride 1024 --bpp 8
```

Environment:

- `STOP_AT` — PC to stop at (default `0x40000`, the `JMP` into the
  payload — stop there or the payload's own screen wipe erases the boot
  block's diagnostics before you can see them).
- `SCRNROW` — row stride to advertise (default 1024; use 80 to
  regression-check the 1 bpp Mac II / IIvi lineage).

It prints the final `ioResult`, the payload checksum the block computed,
the drive/refnum it found, and the handoff longword — so the checksum
can be cross-checked against a host-side computation over the same disk
region.

## Extracting the inputs from a built image

```sh
python3 - <<'PY'
import struct
img  = open('quadra800-cpu.hda','rb').read()
part = 0xC000                                   # 0 for a raw .dsk
poff = struct.unpack('>I', img[img.index(b'PAYLDOFF', part, part+1024)+8:][:4])[0]
open('bootblk.bin','wb').write(img[part:part+1024])
open('payload.bin','wb').write(img[part+poff:part+poff+0x40000])
PY
```
