# SingleStepTests — Status & Blockers (Macintosh Quadra 800 / 68040)

Ported 2026-06-12 from `MacIIvi_MiSTer` (68030) with the FPU material
re-imported from `lbmactwo_MiSTer` (68020) — the Quadra 800's MC68040 has
an on-chip FPU. Lineage: 68020 → 68030 → **68040**. Master plan:
[`QUADRA800_TESTBENCH.md`](../QUADRA800_TESTBENCH.md).

## Hardware bring-up findings (2026-08-26)

7. **Boot block loaded the payload through the 68040 caches with no
   coherency — the "mostly doesn't reach the bench" bug. FIXED.**
   Reported symptom on the physical Quadra 800: the bench almost never
   started, and only very occasionally got as far as painting.

   `common/boot/boot_stub_scsi.s` reads 256 KB of payload to `$40000`
   with a single `_Read` and then `JMP`s into it, with no cache
   management at all. On the 68020 (Mac II) and 68030 (IIvi) that was
   safe — 256-byte, write-through caches. On the 68040 it is not:

   - dirty lines in the 4 KB **copyback** data cache, left over from the
     ROM's own boot-time use of low RAM, are written back **on top of**
     the payload the SCSI transfer just delivered; and
   - stale lines in the 4 KB instruction cache are executed instead of
     the bytes that actually arrived.

   Both are non-deterministic — whether the damage lands on code that
   matters or on padding depends on what the ROM happened to touch —
   which is exactly why it presented as "works one boot in twenty".

   **Fix:** `CPUSHA BC` ($F4F8) + `NOP` on **both** sides of the
   `_Read`. `CPUSHA` (push *and* invalidate) rather than `CINVA`
   (invalidate only) deliberately: post-transfer, a driver that copies
   through the CPU instead of DMAing leaves the payload dirty in the
   D-cache, and `CINVA` would discard it. Applied to all three boot
   stubs (`boot_stub_scsi.s`, `boot_stub_floppy.s`,
   `boot_stub_scsi_fixed_offset.s`) so the hazard can't return through
   another make target. This is the read-side twin of finding 2's
   `CPUSHA DC` fix for `_Write`.

8. **Boot-block diagnostics were painting 1 bpp on an 8 bpp screen —
   FIXED.** Finding 1 fixed the *C* paint kernel for the Quadra's
   640x480x8bpp DAFB, but the **assembly** painters were missed: the
   boot block's readouts (drive number, driver refnum, `_Read`
   ioResult) and `payload_entry_cpu.s`'s "CPU BENCH" banner still wrote
   one byte per *eight* pixels, so they rendered as unreadable speckle.
   That is why the whole bring-up has been blind at exactly the stage
   that was failing. Both now paint one byte per pixel and read the row
   stride from `ScrnRow` ($0106) at runtime. `common/make/common.mk`
   translates each `-DFOO` in `CDEFS_VIDEO` into `--defsym FOO=1` so the
   display variant reaches gas as well as the C compiler — the root
   cause of the two halves drifting apart.

9. **Boot block now paints a payload checksum ('C' row).** A rotating
   32-bit sum over the region HFS allocated to `/Payload`, computed
   straight after the transfer and before anything else touches RAM, so
   a corrupted load is visible on screen instead of being inferred from
   a crash. The window length is patched per image via a `PAYLCKSZ`
   marker (same mechanism as `PAYLDOFF`) set to
   `results_offset - payload_offset` — a fixed window would have covered
   `/Results.jsonl` on the FPU and MMU disks, whose payloads are only
   32 KB / 27 KB, and the checksum would then change every run.
   Expected values per image are tabulated in `prebuilt/README.md`.

10. **Latent: `HANDOFF_ADDR` ($50000) sits inside the Quadra payload.**
    The boot block writes `(refnum, drive)` there *after* loading the
    payload, and the Quadra 800 CPU-bench payload spans
    `$40000..$5E8C0` — so those 4 bytes land 64 KB into the image. They
    currently fall in a zero gap in the captured corpus, so it is
    harmless **today**, but any change to payload layout turns it into
    silent corruption. Not moved yet because the address is duplicated
    across seven files (every bench's `payload_entry*.s` reads it as a
    hard-coded literal) and a boot block and payload that disagree hand
    the bench a garbage refnum. `$00080000` — the first byte past the
    256 KB read window — is the right value; change all seven in one
    commit. `--defsym HANDOFF_ADDR=...` exists to rebuild a boot block
    against an already-built payload meanwhile.

11. **The boot block ran with the 68040 MMU on and no transparent
    translation — its screen wipe destroyed low memory. RETRACTED as a
    hardware finding; the fix is now OFF by default (2026-08-27).**

    > **This finding is emulator-only.** The `DTT0` fix below was
    > justified entirely on MAME/QEMU behaviour and never reproduced on
    > silicon. Worse, the `PFLUSHA` ($F518) it uses **F-line traps on the
    > real Quadra 800** — Sad Mac `0000000F 0000000A`, System Error ID 10
    > — which is the same class as finding 16's `CPUSHA` bus error, and
    > was itself the failure that blocked every hardware run until it was
    > removed. The block is now behind `.ifdef BOOT_SET_DTT0`, off by
    > default; build emulator images with `--defsym BOOT_SET_DTT0=1`.
    >
    > **2026-08-28 correction (docs sweep):** the PFLUSHA attribution in
    > the paragraph above is **disproven** — the ROM itself executes
    > `PFLUSHA` during its own boot phase on every successful hardware
    > run (finding 20's phase correlation), and the MMU-full suite ran
    > its PFLUSH/PFLUSHA corpus rows on silicon 24/24 (finding 26).
    > Findings 20/22 (the ROM hands off with TTRs programmed) explain
    > why only the emulators needed the DTT0 block. What actually killed
    > the DTT0-era boot block on hardware remains formally unresolved;
    > the block stays emulator-only regardless.
    >
    > What the two emulators actually showed is that *their* page-table
    > walk does not map the DAFB aperture, so a `ScrnBase` write lands at
    > physical `$00001000`. The Developer Note (ch. 4) says the ROM
    > "manages the address space for the video frame buffers separately
    > from main memory", and hardware test T1 (finding 16) painted
    > correctly through `ScrnBase` with no `DTT0` at all — so the ROM's
    > mapping is fine and there was nothing to fix.

    Original text follows, kept for the record.

    Measured on `macqd800` at the instant the ROM jumps into the HFS
    boot block (it loads it at ~`$3FD480`):

    ```
    TC   = $0000C000     MMU translation ENABLED, 8 KB pages
    SRP  = $007FCC00     supervisor root pointer (ROM's page tables)
    ITT0 = ITT1 = DTT0 = DTT1 = $00000000    ALL transparent windows OFF
    ```

    So every access the boot block makes goes through the ROM's page
    tables, and those do not map the DAFB aperture flat. A write to
    `ScrnBase` (`$F9001000`) does **not** reach video RAM — it lands at
    physical `$00001000`. The 128 KB screen wipe at the top of
    `startup:` therefore sprays `$FFFFFFFF` over low memory
    `$1000..$21000`.

    That range contains the **drive queue**. Proven by changing the wipe
    fill to `$A5A5A5A5` and finding exactly 128 KB of it at
    `$001000..$020FFC` in RAM, with VRAM untouched. The `DrvQEl` at
    `$4700` reads `$0000A30E` before the wipe and `$FFFFFFFF` after, so
    the `DrvQHdr` walk immediately dereferences `$FFFFFFFF`, takes a
    fault, and the ROM's handler takes the machine back — the CPU
    "parked in ROM" of finding 6. Which low-memory casualty lands first
    is luck, which is why it looked intermittent on the physical Quadra.

    **Fix:** map the IO/framebuffer aperture 1:1 through `DTT0` as the
    very first thing `startup:` does, before `ScrnBase` is touched:

    ```
    move.l  #0xF00FE040, %d0    | base $F0, mask $0F, E=1, S=11, CM=10
    movec   %d0, %dtt0          | $F0000000..$FFFFFFFF, cache-inhibited
    pflusha
    nop
    ```

    Two constraints found the hard way, both by experiment:

    - **Only `DTT0`.** Forcing a blanket 1:1 over the whole address
      space (`$00FFE040` in `ITT0`+`DTT0`) makes the load fail with
      `readErr (-19)`: RAM must keep the ROM's own page-table mapping
      or the SCSI driver behind `_Read` stops working.
    - **Keep `SR = $2700`.** Re-enabling interrupts at boot-block entry
      also breaks the load.

    A TTR is a CPU register, so the mapping stays in force for the
    payload, whose entry shim paints through `ScrnBase` the same way.
    Applied to all three boot stubs (`boot_stub_scsi.s`,
    `boot_stub_floppy.s`, `boot_stub_scsi_fixed_offset.s`), same as
    finding 7, so it cannot return through another make target.

    **Why nothing caught this:** `bbsim` has no MMU and maps VRAM flat,
    so the wipe always "worked" there; MAME was believed unable to boot
    the disk at all (finding 6); and the physical Quadra could only say
    "it didn't start".

    **Independently confirmed on QEMU (2026-08-27).** Use the git-master
    build at `~/nextstep-test/qemu-src/build/qemu-system-m68k`
    (**11.1.50**), not the packaged `/usr/bin/qemu-system-m68k`
    (**8.2.2**). 8.2.2 is useless here: it aborts on its own assertion
    (`qemu_mutex_lock_iothread_impl`, `system/cpus.c:504`) or
    `DOUBLE MMU FAULT` as soon as *any* SCSI disk is attached, including
    a blank template with none of our code, on both ROM revisions and at
    every RAM size. That lock was reworked upstream (it is `bql_lock_impl`
    now), and 11.1.50 boots our disks fine.

    Run: `-M q800 -m 128 -bios <Quadra800 ROM> -display none
    -drive file=X.hda,format=raw,media=disk,if=none,id=hd0
    -device scsi-hd,drive=hd0,scsi-id=0`, ROM extracted from MAME's
    `macqd800.zip`. Screens come out via QMP `screendump`.

    On 11.1.50 the **MMU bench runs to completion — `MMU BENCH DONE`,
    ran=14, skipped=10, byte-identical to the MAME result**, painting
    legible 8 bpp at 640x480. The FPU bench runs clean too. So the DTT0
    fix is confirmed on a second, independent emulator, and QEMU's fault
    dump reports the same handoff state MAME does:

    ```
    TCR 0000c000
    DTTR0/1: 00000000/00000000   ITTR0/1: 00000000/00000000
    ```

    Two emulators sharing no MMU implementation agreeing on that is good
    evidence the state is faithful to silicon rather than a MAME artifact
    — the one assumption the `DTT0` fix rests on. In the CPU run QEMU
    also reports `D5 = e156577e`, exactly the host-computed payload
    checksum, and `DTTR0 = f00fe040`, i.e. it honoured our `MOVEC`.

15. **The payload never zeroed its `.bss` — the bench disks were
    single-use. FIXED 2026-08-27.** Root cause behind finding 14, the
    MAME `DAFB: Aux scanline interrupt` aborts, and any second run of a
    disk that had already been run.

    `payload.ld` declares `.bss (NOLOAD)` and nothing cleared it, so
    every C static came up as whatever the boot block's 256 KB over-read
    left at that address. The payload is ~125 KB of a 256 KB read, so
    `.bss` (`$5E938..$63384`) is filled from the disk *past* `/Payload`
    — which is `/Results.jsonl`. That is zeros exactly once: on a disk
    that has never been run. After one completed run it holds JSON text,
    so on the next boot the statics are garbage.

    The visible casualty is `display_row_bytes()`'s cached stride. It is
    non-zero garbage, so the cache hit returns it instead of reading
    `ScrnRow`, and `display_wipe(480)` computes `stride * 480` from it.
    Measured on QEMU: the wipe ran from `$F9001000` to `$F9400000` —
    ~4 MB — off the end of video RAM, taking a bus error. On MAME it
    instead reaches the DAFB registers at `$F9800000` and trips
    `Aux scanline interrupt enable not supported`, which is why that
    abort was blamed on ROM code earlier; it was our own runaway wipe.

    Proven causally: the pristine shipped image has 137054 zero bytes
    (4 non-zero) between payload end and the end of the load window and
    completes; fill just that region with `0x41` and the same image dies
    at 10 s. With the fix that doctored image completes again.

    **Fix:** `payload_entry_cpu.s` now zeroes `_payload_bss_start ..
    _payload_bss_end` before anything else — it must precede the handoff
    load, which lands in `.bss`. `payload.ld` gained the start symbol and
    a `. = ALIGN(4)` so the clear can be a long loop. All three benches
    share this shim, so all four bundles get it.

    Both emulators now run every bench end to end: MAME and QEMU each
    take the CPU corpus to `ALL TESTS DONE` with `ioResult=0000`.

14. **CPU bench dies on QEMU 11.1.50 with a null stack pointer
    (RESOLVED by finding 15).** Kept for the trail: the null `A7` was
    not a stack bug. A bus error (vector 2) from the runaway wipe hit
    `recovery_core`, which restores SP and resume-PC from slots that are
    still zero before the first test is armed — so it "recovered" into
    `SP = 0, PC = 0`. Worth noting as a latent sharp edge in
    `recovery.s`: any fault before the first armed test lands in a null
    context rather than being reported.

    Original symptom, for reference:
    Only the CPU image does; MMU and FPU are fine. `DOUBLE MMU FAULT`
    with `A7 = 00000000`, `PC = 0000000a`, faulting at `$FFFFFFFC` —
    an exception frame pushed onto a null stack. `VBR = $00062EF0` shows
    `install_vbr` had run, so it is inside `bench_main`, and it happens
    early (~3 s, before anything paints). MAME runs the same image to
    `ALL TESTS DONE`, so this is a MAME/QEMU divergence, not a known
    bench bug — but a genuinely null A7 would bite on hardware too, so
    it is worth finding which row does it before trusting a long
    hardware run. `target/m68k/op_helper.c:346` is where QEMU gives up.

12. **CPU bench wedges at test 180, `ANDI.W #$F8FF,SR` (not a boot
    bug).** With finding 11 fixed the CPU bench boots and runs, then
    stops at test 180 with `run=179 ok=179 trap=0`. That row clears the
    SR interrupt mask to IPL 0 — re-enabling interrupts inside the
    bench's own environment — and control is lost to `$0007FFxx`. Same
    class as the `hw_unsafe` CACR/MOVE16 rows that wedged the 040 at
    test 191. The FPU bench reaches test 266 and the MMU bench runs to
    completion (`MMU BENCH DONE`, ran=14, skipped=10).

    **FIXED 2026-08-27:** marked `hw_unsafe` so the Mac bench skips it,
    in `gen/mame_cpu_capture.lua` (the generator, so a re-capture keeps
    it) and in the generated `gen/cpu_tests.h`. The instruction itself is
    fine and MAME's captured golden still adjudicates it offline
    (`sr $2704 -> $2004`); it is the bench's environment that cannot
    survive handing the machine back to ROM interrupt handlers. With it
    skipped the CPU bench completes all 722 rows — see finding 13.

13. **First full end-to-end CPU run, and what it says about the corpus
    (2026-08-27).** With finding 11 fixed and row 179 skipped as a local
    experiment, the CPU bench ran all 722 rows to `ALL TESTS DONE`,
    wrote `/Results.jsonl` over SCSI with `ioResult=0000`, and the file
    was extracted from the disk and diffed against
    `results/cpu/mame_baseline_2026-06-12.json`. That is the first time
    the loop has ever closed. **717 rows written; 696 comparable;
    667 exact match; 29 divergent; 0 of the 29 are CPU differences.**

    Every divergence is a harness or corpus-portability artifact:

    | n | cause |
    |---|---|
    | 9 | memory-indirect (`([bd,A6],...)`) via an **absolute** pointer stored in scratch |
    | 8 | A6 (the scratch base) copied into a **data** register (`EXG`, `PEA`, `MOVE.L A6,D0`) |
    | 5 | absolute address baked into the test bytes (`(xxx).W`/`(xxx).L` = `$1804`/`$1820`) |
    | 4 | control-register harness state (`MOVEC` `SFC`/`DFC`/`VBR`/`CACR`) |
    | 2 | address register stored to scratch (`MOVEM`) |
    | 1 | absolute preload compared against an A6-relative value (`CMPA.L`) |

    The mechanism, measured: the MAME capture harness puts scratch at
    **A6 = `$1800`**; the Mac bench puts it at **A6 = `$00062D3A`**. On
    the Quadra, absolute `$1800`, `$1804`, `$1810` and `$1820` all read
    `$40809AE6` (ROM-pointer filler in low memory) — and `$40809AE6` is
    exactly the value every affected row reported. So those rows are not
    comparing an instruction, they are comparing where scratch happens
    to live.

    This violates the corpus's own stated invariant, from the header of
    `gen/mame_cpu_capture.lua`: *"Test instruction bytes must be
    IDENTICAL between MAME and the Mac OS bench, so any test that
    touches memory uses (A6) / d16(A6) addressing with A6 pre-loaded by
    the harness to a platform-specific scratch base."* The `(xxx).W` /
    `(xxx).L` rows and the A6-into-Dn rows break it by construction, and
    no amount of silicon will make them agree.

    The four `MOVEC` rows are a different flavour: the capture script
    zeroes `SFC`/`DFC`/`CACR` before each row, the Mac bench does not, so
    those rows compare harness state. Worth noting that
    `MOVEC.L CACR,D0` reads **`$80008000`** on the bench — DE+IE, the
    *correct* real-68040 mask, against a baseline of `0`. That is MAME
    quirk 4 showing up from the other side.

    Exception rows are healthy: 21 rows record a trap vector instead of
    a register snapshot, 18 of them name their expected vector, and all
    18 match (`DIVS`->5, `CHK`->6, `ILLEGAL`->4, odd `JMP`->3,
    `CALLM`->4 on the 040, ...).

    **So: the emulator is not failing the CPU suite.** MAME's 68040
    matches on every row that is actually comparable. The ~29 rows are a
    corpus-portability debt, and they will diverge identically on real
    silicon — they are not a Quadra finding waiting to happen. Fixing
    them means either re-expressing them A6-relative, or marking them
    platform-local and excluding them from the diff — still open, and a
    corpus decision rather than a boot one.

    The row-179 `hw_unsafe` flag was made permanent (finding 12) and the
    shipped `2026-08-27` CPU bundles rebuilt with it. Re-verified end to
    end on the shipped image: same 717 / 696 / **667 match** split, and
    the only rows the bench now skips are the four long-standing
    `hw_unsafe` / Line-A rows plus row 179.

16. **`CPUSHA BC` ($F4F8) bus-errors on real Quadra 800 silicon.
    FIXED 2026-08-27 — first bug in this project found on hardware
    rather than in an emulator.**

    Bisected on the machine with three boot blocks that halt at chosen
    points, so the screen stays up to read:

    | Test | Boot block | Result on hardware |
    |---|---|---|
    | T1 | halt *before* the first `CPUSHA` | **`A 00000008` / `D FFFFFFDF`** — runs, paints, DrvQ walk OK |
    | T3 | execute `CPUSHA`, then halt before `_Read` | **Sad Mac `0000000F 00000001`** |
    | T2 | both `CPUSHA` replaced with `NOP` | **boots; payload runs and paints its banner** |

    T1 proves the boot block, the 8 bpp paint, the drive-queue walk, the
    disk structure and the driver are all fine. T3 executes exactly one
    more instruction than T1 and dies, and its Sad Mac decodes (per
    `docs/quadra800-rom-notes.md`) to System Error ID **1 = vector 2 =
    bus error**, raised by `CPUSHA` itself. T2 removes it and the machine
    boots. Three tests, one instruction isolated.

    Note the ID differs from the original `0000000A` (ID 10, F-line) seen
    with the full boot block; the fault presents differently depending on
    what runs after it. ID 1 from T3 is the clean measurement, because
    nothing executes after the `CPUSHA` except `BRA.S *`.

    **Fix:** stop issuing raw cache instructions and use the ROM's own
    call — `_HwPriv` selector 1 (`moveq #1,d0` + `$A198`). The Developer
    Note, ch. 4: `_FlushInstructionCache` on the 68040 "is to flush both
    the instruction and data caches", deliberately in one call to "avoid
    problems in situations in which interrupts might occur while the
    caches are being flushed individually". That is exactly what finding
    7 wants, done the supported way, and it lets the ROM do whatever this
    silicon actually needs. It clobbers D0/A0, so the boot block saves
    `%d4/%d6/%d7/%a0` around it.

    Applied to `common/boot/boot_stub_scsi.s` and to `flush_icache()` in
    `bench_main.c`, `fpu_bench_main.c` and `mmu_bench_main.c`. Verified:
    full 722-row CPU corpus to `ALL TESTS DONE` with `ioResult=0000`
    under MAME, and bbsim reproduces the new checksum.

    **This invalidates the emulator-only reasoning that produced finding
    11.** Both MAME and QEMU execute `CPUSHA BC` happily, so no amount of
    emulator work could have found this. Finding 11's `DTT0` change was
    justified entirely on emulator behaviour and is still unproven on
    hardware — T1 and T2 are built without it and the machine got further
    than it ever had.

17. **Boot block proven healthy on hardware; last raw cache op removed
    (2026-08-27).** Test T5 (halt at the `JMP` into the payload) on the
    real Quadra 800 painted all five lines:

    ```
    A 00000008     BootDrive 8
    D FFFFFFDF     driver refnum -33
    E 00000000     _Read succeeded
    C A7263EC9     matches the host-computed checksum exactly
    3 <block>
    ```

    So on silicon: the disk mounts, the driver works, `_Read` transfers
    256 KB intact, the 8 bpp paint is correct, and **both `_HwPriv` cache
    flushes execute fine** (T4 had already isolated that one). Everything
    up to entering the payload is healthy. The disk image, the rebuilt
    `~/testdisk.hda` template and the `Apple_Driver43` partition are all
    exonerated.

    That leaves the payload. `common/runtime/jsonl_writer.c` still issued
    a raw `CPUSHA DC` ($F478) before `_Write` (finding 2's fix), the last
    raw cache instruction anywhere in the shipped code. Converted to the
    ROM call, which hardware has now verified. `cpu`, `fpu` and
    `cpu-nowrite` payloads are now free of raw cache opcodes entirely.

    The `PFLUSHA` remaining in the MMU payload is **corpus test data**,
    not code — the MMU bench deliberately executes `PFLUSH` rows inside
    its recovery harness, so a fault there is recorded as a trap rather
    than crashing. Prefer the CPU image for hardware bring-up.

    `cpu-nowrite`'s checksum is unchanged by this commit, which is the
    expected cross-check: `JW_NO_WRITE` stubs out the write path, so that
    `CPUSHA` was never compiled into it.

18. **FIRST FULL HARDWARE RUN of the CPU corpus (2026-08-27), and the
    SCSI write is the last bug.** `quadra800-cpu-nowrite.hda` ran all
    722 rows to completion on the physical Quadra 800, with ~10 traps
    (expected: the corpus has 21 `EXC:` rows that deliberately trap to
    verify vectors). Writes are compiled out in that build.

    So on real silicon the boot block, payload, 8 bpp display, recovery
    harness, corpus and the 68040 itself all work. The one remaining
    failure is the SCSI `_Write` path: the write-enabled image runs, then
    Sad Macs with **no results written at all**.

    The timing corroborates it. Results are buffered in 16 KB batches and
    result lines average 281 bytes, so the **first `_Write` fires around
    test 58** — not at the end. A crash during that first flush leaves
    `/Results.jsonl` untouched, which is exactly what the machine shows.

    Suspect, and the reason finding 5 already flagged it: the write runs
    at **IPL 7**. The Quadra's **53C96** signals transfer completion by
    interrupt, which can never be taken while masked. `_Read` in the boot
    block survives masked because the driver polls on that path. Fix
    under test: drop to IPL 0 across the `_Write` trap only, which is
    safe because `use_os_vbr()` has already installed the ROM's vector
    table so the ROM services the interrupt.

19. **Emulator triage of the write path: my IPL change was a
    regression, and the other two levers are both required
    (2026-08-27).** With `BOOT_SET_DTT0=1` (emulator images need the DAFB
    mapped), three variants of `driver_write_sector` under MAME:

    | Variant | MAME result |
    |---|---|
    | drop IPL to 0 across `_Write` (finding 18's fix) | **hangs at test 58** |
    | remove the `use_os_vbr()` bracket | **crashes, ROM takes over** |
    | remove the cache flush | **hangs at test 58** |
    | flush + VBR bracket, IPL untouched | **`ALL TESTS DONE`, ioResult 0** |

    So the shipped configuration was already correct and all three of my
    candidate "fixes" make it worse. The IPL change was committed in
    258a81c and shipped as T6 before being tested in emulation; it is now
    reverted. T7 and T8 were built and offered for hardware testing —
    both are regressions and should not be run.

    Note test 58 recurs exactly as predicted: results buffer in 16 KB
    batches at ~281 bytes per line, so the first `_Write` lands there.
    Two independent breakages both stall at that row, which is good
    evidence the arithmetic is right and that the first flush is the
    trigger.

    **Neither emulator can reproduce the hardware write failure** — both
    complete the corpus and write `/Results.jsonl` successfully. So MAME
    and QEMU can only catch regressions here, never confirm a fix. That
    is exactly what they did.

    Open lead for the hardware bug, from the Developer Note ch. 4: "the
    ROM software uses **only pages marked uncacheable** when setting up
    communication areas with alternate bus masters", and
    `LockMemory` / `LockMemoryContiguous` "can change the attributes of
    individual pages in the absence of VM". The bench's write buffer is
    ordinary cacheable RAM handed to a 53C96 DMA engine. A flush before
    the transfer is not the same as marking the page uncacheable, and the
    note is explicit that Apple does the latter.

20. **What the `_Write` path actually executes, and the F-line shim
    (2026-08-27).** Instruction-level trace of the write under QEMU
    (`-d in_asm` logs each translated block once, in first-execution
    order, so log position = phase), plus a full read of the ROM's
    `_BlockMove` at `$40884400`:

    - `_BlockMove` on a 68040 (`CPUFlag $12F == 4`): copies > 12 bytes
      with source and destination in the same 16-byte phase go through a
      **`MOVE16 (A0)+,(A1)+`** burst loop (`$40884482/90/96` — the only
      three MOVE16s in the decoded ROM). Then **every** such BlockMove
      runs a cache epilogue at `$408870AA`: rounded length ≥ `$C00` →
      **`CPUSHA BC`** (`$408870D8`); smaller → mask IRQs, **`MOVEC TC`,
      `PTESTR (A1)`, `MOVEC MMUSR`** to translate the destination, then a
      **`CPUSHL BC,(A1)`** per-line loop (`$40887126`), per page. (The
      recursive-descent disassembly fused `$F569 $4E7A` into a bogus
      `frestore`; QEMU's decoder shows the real `ptestr`+`movec`.)
    - The first `_Write` first-executes ~1000 blocks of `$408Dxxxx`
      SCSI Manager code the read path never touches, re-runs the
      BlockMove epilogue, and later `CPUSHA BC` (`$40885032`).
    - **Phase correlation kills the instruction-gap theory for the
      BlockMove family:** the boot block only starts at log line ~53100,
      and `move16` (~43970), `ptestr`/`cpushl` (~41250) and the ROM's own
      `pflusha` (`$40803F80`, `$408815A2`, ~8500-10850) all first-execute
      during the **ROM's own boot/mount phase** — which the physical
      machine survives on every run. So the real CPU executes MOVE16,
      PTEST, CPUSH and PFLUSH fine, and finding 11's "PFLUSHA F-lines on
      real silicon" attribution is doubtful (something else in that DTT0
      block killed it; unresolved). The write-path F-line must come from
      something write-only: an op in the un-decoded SCSI write machinery
      (a hardware-only Turbo SCSI branch the emulators don't steer into),
      an FPU instruction (this machine's FPU has never been exercised
      pre-System; transcendentals without an FPSP → vector 11), or
      garbage execution after a pseudo-DMA recovery failure.
    - Also ruled out: the resume-file lead of `restore_os_traps()` + IPL.
      `use_os_vbr()` swaps the whole VBR to the ROM's table, so our
      vectors 32..63 are dormant during the bracket, nothing of ours
      pokes the ROM's live table, and the epilogue masks/lowers IPL
      itself (`ORI #$700,SR` / driver-internal).

    **Detour that produced its own finding: vector 11's low-mem slot is
    read as DATA by ROM trap code — never patch it in place.** The
    first shim patched `$2C` directly (the ROM's VBR is 0; measured via
    a breakpoint on the installer). MAME then deterministically died at
    the **8th** flush with Sad Mac `0F/0000001B` — DSErrCode `$1B` =
    27 = `dsFSErr`, stored not by the exception dispatcher but by a
    `_SysError` call reached from `$40809A26`, inside the OS-trap
    dispatch machinery — with the thunk itself **never entered**
    (breakpoint on it: zero hits). A control build with the shim linked
    but the vector untouched completes all 717 rows, so the 4-byte
    write at `$2C` alone is what kills the write path. Some ROM
    OS-trap/FS code compares or consumes that slot as data.

    **Fix/instrument shipped: `common/runtime/fline_shim.s` (v2,
    forwarding table).** `install_fline_shim()` (called by all three
    bench mains right after `install_vbr()`) builds a private 256-entry
    table and repoints recovery.s's `orig_vbr` at it, so
    `use_os_vbr()` activates it during every I/O bracket; the live
    table at 0 is never modified. Entry 11 → the thunk; every other
    entry → a 6-byte stub (`move.l (N*4).w,-(sp); rts`) that jumps
    through the **live** low-mem slot at exception time, so runtime
    vector patching by the ROM/driver (e.g. pseudo-DMA bus-error
    handlers, completion IRQs) keeps working mid-transfer. Installs
    only if the captured VBR is 0 (both emulators measure 0); else it
    leaves the machine alone. The thunk: emulates `MOVE16 (A0)+,(A1)+`
    as four longs (both addresses forced 16-aligned, both registers
    +16); skips CINV/CPUSH (`$F4xx`) and PFLUSH/PTEST (`$F5xx`) by
    advancing the stacked PC (safe in composition: a skipped PTESTR
    leaves MMUSR stale, but the CPUSHLs that would consume it are
    skipped too); counts every hit in `g_shim_count`/`g_shim_last_op`/
    `g_shim_last_pc`, which the CPU bench paints on the DONE screen;
    and for anything else — FPU ops, non-format-0 frames, garbage —
    **paints `FLINE OP+PC: xxxx xxxxxxxx` at row 40 and halts with the
    screen alive** instead of letting the ROM Sad Mac. Dormant under
    MAME/QEMU (their 68040 executes everything; the stubs forward
    identically), verified: MAME completes the corpus and the QEMU
    diff report is byte-identical to the pre-shim build's. Every
    hardware outcome now identifies the culprit: a completed run's
    shim line names the emulated/skipped op; a painted halt names the
    un-emulatable one; PC in ROM vs RAM separates an instruction gap
    from control-flow corruption.

    Bookkeeping from the debug loop: MAME needs `-seconds_to_run 400`
    for the full corpus (140 was folklore; ~150 emulated seconds only
    reaches test ~460), and `-seconds_to_run` auto-saves a final
    screenshot under `snap/macqd800/` — no Lua needed for post-mortem
    screens. `-debugger none` silently disables `-debugscript`; run
    the default debugger to get breakpoints headless. Device
    `/Results.jsonl` rows need bridging before `cpu_diff_corpus.py`
    (strip NUL padding, drop `trap_state` rows, add `"initial": {}`).
    QEMU-bench vs MAME-baseline legitimately scores 610/692 — a
    QEMU-vs-MAME 68040 divergence measurement, not a bench bug; the
    MAME-bench yardstick stays 667/696.

21. **Hardware verdict via the shim, and the real root cause: the boot
    block's stack sat on the ROM boot heap and smashed the SCSI
    Manager's write-path glue. FIXED (2026-08-27).**

    First hardware boot of the `-27b` shim disk: all 58 tests to the
    first flush pass (`run=58 ok=58 trap=0`), then instead of the Sad
    Mac the shim paints **`FLINE OP+PC: FFFF 0000FF44`** and halts with
    the screen alive. Decode: `FFFF` is the thunk's sentinel for a
    non-format-0 frame — on a 68040 a vector-11 frame is format 0
    (F-line, PC = the instruction) or format 2 ("unimplemented FP",
    PC = the NEXT instruction) — and `$FF44` is **low RAM**, in the
    region where the ROM boot heap keeps the SCSI Manager 4.3 RAM glue
    (QEMU builds an XPT trampoline at `$F4C8`: `jsr` into the driver,
    return through `[jIODone]` at `$8FC`; QEMU RAM dump `$8000..$18000`
    contains no legitimate FPU code, so a valid-but-unimplemented FP
    *pattern* there means garbage being executed).

    The mechanism: the boot block's first act was
    `move.l #$10000,%sp`, and the write-path glue lives just below
    $10000 — on this hardware ~`$BC` below the stack top, on MAME/QEMU
    ~`$B38` below. Every call the boot block makes (paints, the `_Read`
    nesting) scribbles frames down from $10000; on hardware that
    *guarantees* the glue is dead by the time the payload runs, while
    the emulators' allocation sits just deep enough to survive. `_Read`
    never calls this structure (boots fine everywhere); the first
    `_Write` jumps into the smashed bytes → they decode as an
    unimplemented-FP pattern → vector 11 → previously the ROM's Sad Mac
    `0F/000A`, now the shim's readable paint. Every prior signature
    fits at once: hardware-only, write-only, first-flush timing, the
    F-line ID, and the IPL/VBR/cache dead ends.

    **Fix: park stacks only on RAM we own.** All three boot stubs no
    longer touch SP at all — the ROM enters the boot block with a valid
    stack, and a real System boot block runs far deeper code on it than
    we do. The payload stack moves from `$100000` (unowned no-man's
    land) to `$80000`, the top of the payload's own 256 KB read window
    (grows down into the dead read slack; the planned `HANDOFF_ADDR`
    byte at exactly `$80000` stays untouched since the first
    predecrement lands at `$7FFFC`). `bbsim` keeps feeding its own
    `$10000` as the stand-in for the ROM SP.

    The shim stays in the payloads: it converted this bug from a Sad
    Mac plus emulator goose-chase into one photograph, it still covers
    any real 040 instruction gap, and its unknown path now paints the
    frame format/vector word, the format-2 effective address, the
    instruction bytes around the stacked PC, and up to three
    code-looking return addresses scanned off the exception frame — so
    the next unknown fault identifies itself completely in one boot.

22. **FIRST FULL HARDWARE CAPTURE — CPU, FPU and MMU results off the
    real Quadra 800, and what silicon adjudicated (2026-08-28).** The
    finding-21 stack fix held: all three benches ran to DONE and wrote
    `/Results.jsonl` over SCSI (CPU 717 rows, FPU 270, MMU 24). Raw
    captures: `results/{cpu,fpu,mmu}/hardware_quadra800_2026-08-28.jsonl`.

    **CPU (661/695 vs MAME baseline).** Exactly the 29 known
    corpus-portability rows plus **five real silicon-vs-MAME
    divergences, all `ccr_only`, all in undefined-flag territory**:
    ABCD/SBCD/NBCD (N, V and sticky-Z details) and in-bounds CHK.L
    (undefined Z) — real 68040 silicon computes undefined CCR bits
    differently than MAME's model. Plus two trap adjudications: **RTM
    correctly takes vector 4 on silicon** (the corpus predicted MAME's
    golden was bad — confirmed; MAME executes it), and the
    `BSR.W / RTD #4` row crashes differently (hw vec 2 vs MAME vec 4) —
    a harness-stack artifact, not a CPU difference.

    **FPU: the 040-lite classification had two op families backwards;
    silicon corrected it, and the fixed model scores 270/270.**
    FSGLDIV/FSGLMUL (24 rows) were tagged trap but EXECUTE in hardware;
    FINT/FINTRZ (22 rows) were tagged execute but TRAP vector 11 —
    both exactly per the M68040UM implemented/FPSP tables.
    `gen_fpu_header.py`'s `HW_OPMODES` is corrected and
    `fpu_tests.h` regenerated (both copies; content change is the
    `traps` flags + name tags only). Numeric results agree with MAME on
    every co-executed row except three modeling gaps, silicon
    canonical: **MAME never accrues FPSR AEXC (INEX `$8` sticks on
    silicon from the first inexact op), MAME does not model FPIAR**
    (silicon records the faulting FP instruction address), and MAME
    boots with garbage FP registers where silicon resets them to
    canonical NaNs (`7FFF0000FFFF…`).

    **MMU (14 register-mask rows).** Two adjudications and one broken
    contract. (1) **The real ROM hands off with the TTRs PROGRAMMED**
    — hardware snapshots show `DTT0/ITT0 = $F900C060` (a transparent
    DAFB window!) and `DTT1/ITT1 = $807FC040` — while MAME and QEMU
    both model all four as zero. The two emulators "agreeing" (finding
    11's foundation) was mutual mis-modeling: on silicon, `ScrnBase`
    writes always went through the ROM's own DAFB window, which is why
    hardware never needed `BOOT_SET_DTT0` and why the emulators
    without it spray low memory. Finding 11's mystery is fully closed.
    (2) **`PFLUSH (A0)` / `PFLUSHN (A0)` execute on silicon; MAME's
    68040 F-lines them** (vec 11 in the MAME-bench run). (3) The
    bench↔baseline contract is broken for *everyone*: MAME-bench,
    QEMU-bench and hardware all score 0/14 against
    `results/mmu/mame_baseline_2026-06-12.json` with the same
    systematic signature (harness state: `urp/srp=$3000` tables,
    `itt0=$FFC000`, `d7=0` expectations the on-device bench never sets
    up). The diff needs the same environment-vs-CPU separation the CPU
    corpus got in finding 13. SRP differing (`$77FFA00` hw vs
    `$7FCC00` emulators) is RAM-size-dependent ROM state, not CPU.

    **Coverage answers (asked 2026-08-28).** (a) The CPU+FPU
    integration bench was never missing — `cpu_fpu_bench_main.c` +
    the 1328-row corpus (`macos_bench/cpu_fpu_tests.h`) + the 8-row
    FSAVE/FRESTORE sub-corpus existed from the Mac II lineage, but the
    Quadra Makefile had no link target for them; now wired
    (`make cpu_fpu` / `make cpu_fpu_sr`), shim installed, shipped.
    Rows containing 040-unimplemented FP ops will trap on silicon
    (self-scored `vec` column records it) — that is data, same as the
    FPU bench. (b) The 10 skipped MMU rows (5 LIVE translation, 3
    FAULT, 2 PTEST) need the private-page-table harness: port
    `mmu_bench_main.c.68030-reference`'s relocation scheme to the
    68040 — build the corpus's 3-level tables in payload buffers,
    patch descriptor address fields, add identity early-termination
    descriptors for the harness regions, switch `URP/SRP/TC` around
    each test, and (new requirement from adjudication (1)) **save,
    clear and restore the four TTRs** around live rows since the ROM
    leaves them enabled. Fault rows land on vector 2 with format-$7
    frames; `recovery.s` already forces TC off on entry
    (`MMU_RECOVERY`). The corpus data and the MAME baseline for those
    rows already exist — only the runner is missing.

23. **CPU+FPU integration bench wired into the Quadra build, and the
    emulator ceiling it exposed (2026-08-28).** The Mac II-lineage
    integration bench (`cpu_fpu_bench_main.c`, 1328-row
    `macos_bench/cpu_fpu_tests.h`, 8-row FSAVE/FRESTORE sub-corpus)
    was source-complete but had no Makefile link target on the Quadra
    tree — that is the whole reason it never shipped. Now built as
    `make cpu_fpu` / `make cpu_fpu_save_restore` (shim installed like
    the other benches; `build_cpu_fpu_dsk.sh` had a stale `rb-cli new`
    syntax, fixed). Rows are self-scoring on-device
    (`expected`/`actual`/`pass`/`vec` per line).

    Emulator regression: **972/972 rows pass on MAME and QEMU
    byte-alike, and 8/8 FSAVE/FRESTORE** — then both emulators die on
    the corpus tail, each in its own way: **MAME fatal-aborts the
    whole emulator** (`M68kFPU: unimplemented main op 1 with mode 1`,
    the FDBcc/FScc/FTRAPcc conditional class) and **QEMU dumps core**
    in the same region. Real 68040 silicon implements FScc/FDBcc/
    FTRAPcc in hardware (M68040UM), so the tail is expected to run on
    the Quadra — the machine will be the first to ever score those
    rows. Same epistemic shape as the SCSI-write bug: the emulators
    validate the machinery and the first 972 rows; the tail is
    hardware-first territory. A fatal MAME abort mid-run still leaves
    all flushed batches on the CHD (the extraction pipeline works on
    partial runs).

    Build-system footgun recorded twice today: `EXTRA_ASFLAGS` is not
    a make dependency and the `build_*_hda.sh` scripts re-run `make`
    without it — always `make clean` (or `rm build/boot_stub_patch.*`)
    when switching hardware↔emulator flavors, or the disk silently
    carries the wrong boot block (a hardware stub under MAME shows the
    ROM boot-scanner screen: the finding-11 low-memory wipe).

24. **The MMU live-translation harness (MMU_FULL) — built, QEMU-green,
    and the debugging trail behind it (2026-08-28).** All 24 MMU rows
    now run: `make mmu_full` relocates the corpus's 4K-page world into
    payload buffers — one 4K block replicating corpus page `$3000`
    (root @+0, ptr @+$200, page table @+$400, and our harness page
    table hidden @+$600 so VA-space descriptor edits hit the live
    tables), dedicated pages for `$1E000`/`$1F000` (remap targets) and
    `$3F000` (fault frames), a catch-all page for untouched identity
    pas — rewrites descriptor address fields (plants AND
    descriptor-shaped immediates inside test bytes: the ATC rows edit
    the live table with a baked `$0001E001`), hooks `ptr[1]` to an
    identity map of the payload so register dumps and vector fetches
    work under translation (masked out of emitted windows), and wraps
    each live row in a MOVEC prologue (row URP/SRP rebased, PFLUSHA,
    TC on) and epilogue (dump-then-TC-off, SP juggled to the corpus VA
    stack so fault frames land in the compared window).
    `recovery.s` stubs now kill TC before any data access in
    MMU_RECOVERY builds. Emission: seven corpus-based windows per live
    row, real MMUSR, honest `regs_valid`. The full run buffers in a
    48K batch and flushes once at the end (a single pre-System `_Write`
    above 16 KB drives the ROM Device Manager into a queued path whose
    low-mem structures are still boot-fill `$FFFFFFFF` -> Enqueue
    faults; the writer also now slices any batch into <=16 KB driver
    requests).

    **QEMU (primary oracle): 24/24 rows, deliberate faults recover as
    vec 2, PTESTR/PTESTW return real walk results (MMUSR `$58001` /
    `$58005` = relocated page | resident/WP).** Baseline flag-byte
    comparison: 49 comparable bytes match; the 7 divergences are
    oracle artifacts, not harness bugs — (a) the ATC-staleness row:
    **MAME models no ATC** (its "stale" store re-walked and hit the
    NEW page; QEMU's hit the OLD page and left the edited descriptor
    unwalked — architecturally correct; silicon adjudicates), and (b)
    the capture ran vectors at VA 0, so its fault rows set U on
    page[0]; our VBR lives in the payload. MAME cannot host the full
    bench at all (unhandled-PFLUSHA instruction storms, the
    fragile pre-System Enqueue) — MMU-full is QEMU/hardware territory,
    like the integration-corpus tail (finding 23).

    **The wedge that ate the debugging day: finding 10's landmine
    detonated.** The full payload's .bss (20K page buffers + 48K
    batch) grew past `$50000` = HANDOFF_ADDR, so the entry shim's
    .bss zero-loop wiped the boot block's handoff before the bench
    read it -> `_Write` to refnum 0 -> the Device Manager walked a
    boot-fill queue pointer (`ea=$FFFFFFFF`, Enqueue at `$40809948`)
    -> Sad Mac `0F/01` on QEMU. Diagnosed via QEMU `-d int,cpu`
    register capture at the fault (the writer ctx showed
    refnum=0/drive=0 with correct base/max). **HANDOFF_ADDR moved to
    `$00080000`** (finding 10's prescribed cure) in all eight
    boot-stub/payload-entry sites in one commit; the payload stack at
    `$80000` predecrements so the slot itself is never touched.
    Hardware verdict on the new address pending (the integration
    benches' on-hardware write failures are under live diagnosis with
    a build that paints the writer's refnum/drive/base + ioResult).

25. **The integration bench's hardware write failures: a 68020 CACR
    write that DISABLES the 68040's caches (2026-08-28). FIXED.** The
    new CPU+FPU integration and FSAVE/FRESTORE disks ran on the real
    Quadra (7/8 shown on-screen) but wrote nothing, with the diag row
    painting `rn=0000 dr=0000 base=00000000` and `ioResult=0000` —
    while the same images were flawless under QEMU. Bisection disks
    reverting the two suspected deltas (sliced writer, `HANDOFF_ADDR`)
    changed nothing — correctly, because the culprit predated both:
    `cpu_fpu_bench_main.c` came over from the Mac II campaign with

    ```c
    moveq #9,d0 ; movec d0,cacr   /* 68020: clear+enable I-cache */
    ```

    still in its `flush_icache()`. On the 68040, CACR is a different
    register (bit 31 = DE, bit 15 = IE, no clear bits), so `$09`
    **disables both caches without pushing the dirty data cache**. From
    the first test on, every global the bench had written through the
    copyback cache — the handoff refnum/drive, the writer context —
    became invisible: reads bypassed the cache and returned the raw
    RAM underneath (zeros). `_Write` went to refnum 0 and the ROM
    politely returned `noErr` while touching nothing. The emulators
    model no caches, which is exactly why they never reproduced it —
    the same epistemic shape as findings 16/20/21. Finding 16's fix
    ("all cache ops go through `_HwPriv` selector 1") had been applied
    to the three original mains but the integration main was not in
    the build then. It is now the ROM call; tree-wide sweep shows no
    other `MOVEC ...,CACR` relics outside `old/`.

    The bisection artifacts stay useful: every boot stub and payload
    entry honors `--defsym HANDOFF_ADDR=`, and the DONE screen paints
    `rn=/dr=/base=` + `ioResult` on the integration benches — one
    photo now identifies any future writer-context corruption. The
    sliced writer and `HANDOFF_ADDR=$80000` defaults are exonerated
    and stay.

26. **Full hardware sweep of the new suites — integration, FSAVE/
    FRESTORE and the live MMU harness — with three fresh silicon
    adjudications (2026-08-28).** Raw captures in
    `results/cpu_fpu/hardware_quadra800_2026-08-28.jsonl`,
    `results/cpu_fpu/hardware_saverestore_2026-08-28.jsonl`,
    `results/mmu/hardware_full_quadra800_2026-08-28.jsonl`.

    **FSAVE/FRESTORE: 8/8.** State frames, IDLE-frame no-reload and
    NULL-frame reinit all textbook on silicon (the earlier 7/8 was the
    finding-25 cache bug).

    **CPU+FPU integration: 1328/1328 ran** — the first machine ever to
    execute the corpus tail both emulators die on (finding 23).
    Self-score 1085 pass + 243 fails that decompose exactly:
    - 176 = FINT/FINTRZ-bearing rows trapping vector 11 — the
      already-adjudicated 040 behavior (finding 22), not failures.
    - 51 = **a golden-model bug the silicon exposed**: the FDBcc block
      in `gen_fpu.c` loads a->FPsrc, b->FPdst (the FBcc blocks do the
      reverse) so its emitted FCMP computes b−a, but the model
      evaluated predicates on a−b — every asymmetric predicate's
      golden inverted. Fixed (eval args swapped); regenerated goldens
      are deterministic (same seed, program bytes identical, 51
      expected-values changed) and score **80/80 against the hardware
      run** — silicon validated the fix directly. Corpus files
      regenerated deliberately per the corpus policy:
      `fpu_corpus_baseline.json` (51 values spliced, formatting
      preserved), `cpu_fpu_full_corpus.json`, `cpu_fpu_tests.h`.
    - 16 = **FPIAR adjudication**: `FMOVE.L Dn,FPIAR` of `$12345678`
      reads back `$00005678` on silicon — the 040 keeps only the low
      16 bits of a data-register FPIAR write in this sequence, against
      the 68881-model golden (and MAME models no FPIAR at all,
      finding 22). Recorded as silicon truth; goldens left, rows are
      the ground-truth record.

    **MMU-full: 24/24 ran on hardware, 0 real diffs — byte-for-byte
    the same observables as QEMU** (49 comparable flag/data bytes
    match; the same 7 known-artifact bytes as QEMU's run). That closes
    all three questions the harness was built to ask:
    - **ATC (adjudicated against MAME):** the stale-ATC row's second
      store landed at the OLD physical page (`22222222` at `$1F014`,
      nothing at `$1E000`) and the edited descriptor stayed unwalked —
      real silicon holds stale ATC entries exactly like QEMU; MAME's
      walk-every-access model is wrong.
    - **MMUSR ground truth:** PTESTR -> `$00058001` (pa|R), PTESTW on
      a write-protected page -> `$00058005` (pa|W|R) — identical to
      QEMU, settling MAME's known-incomplete MMUSR.
    - **S-page semantics:** MOVES with user FC from supervisor mode
      does NOT fault on a supervisor-only page — silicon, QEMU and the
      MAME capture all agree (vec 0): the 040's S-bit check keys on
      the privilege mode, not the function code of the access.
    Deliberate WP/invalid faults recovered as vec 2 through live
    translation — the format-$7 fault path works on silicon.

    With this, **every bench in the campaign has now completed on real
    hardware with results captured**: CPU, FPU, MMU-safe, MMU-full,
    CPU+FPU integration, FSAVE/FRESTORE.

27. **The all-in-one chain disk — five suites, one boot, QEMU-green
    (2026-08-28).** `build_allinone_hda.sh` packages cpu → fpu →
    saverestore → mmu-full → integration on one `.hda` (integration
    LAST: the emulator-fatal tail, finding 23). Each payload's DONE
    now RETURNS from `bench_main` to the entry shim (the four mains'
    final `for(;;)` became `return`), which paints `DONE` and either
    hangs (per-suite disks, `NEXTPAYL` zero) or jumps to a chain stub
    copied to `$7C000` — above every payload's read extent, below the
    `$80000` stack — that re-runs the boot block's load step: VBR to
    the ROM table at 0, `_Read` the next payload over `$40000`,
    `_HwPriv` sel 1 flush both sides, JMP. All suites append into one
    1 MB `/Results.jsonl` at fixed per-suite regions (`RJSNLTAG` now
    patched with per-suite offset AND `max_bytes`, each region sized
    to hold a full zero-padded final batch); the sidecar
    `.manifest.json` + `gen/split_allinone_results.py` extract them.
    `gen/boot_cksum.py` reproduces the boot `C` row from any image's
    own markers (build-script lesson: compute AFTER patching — the
    NEXTPAYL/RJSNLTAG longs sit inside the checksum window).

    Two chain-only landmines found by QEMU on the way:
    - **Finding 24 bites `_Read` too**: the first chain build issued
      one 35 KB `_Read` and died in the ROM Enqueue at `$40809948`,
      `ea=$FFFFFFFF` — the exact finding-24 signature. The boot
      block's single 256 KB `_Read` survives only in the boot-time
      environment; at bench time every request must be ≤16 KB. The
      chain stub slices like the writer does.
    - **The saverestore corpus scribbles the handoff**: its
      `FSAVE/FRESTORE (A0)` rows do `movea.l #$80000,a0` and write
      frames (one row `clr.l (a0)`) right over the handoff slot. The
      suite's own flush survives (writer ctx cached in `.bss` at
      start), but the next hop read garbage refnum → a boot-fill unit
      table entry → the same Enqueue Sad Mac. The entry now re-plants
      the handoff from its own entry-time copy before every hop.
      Corpus untouched (hardware ground truth, finding 26).

    QEMU (git master, the oracle) runs the whole chain: cpu 717 +
    fpu 270 + saverestore 8 + mmu-full 25 rows — counts equal to the
    single-suite hardware captures, mmu observables 49 match /
    7 known-artifact / 0 real diffs — then integration rows 1–972
    flush before the known tail core-dump ends the run. Hardware
    validation of the chain is pending; the one silicon-only unknown
    is `_Read` under the ROM vector table at bench time (boot-proven
    only) — a hop Sad-Maccing `0F/000A` would be finding 20's F-line
    class, fallback: bracket the chain read with a forwarding table.
    Prebuilts refreshed as the `2026-08-28b` bundle set (all six
    per-suite disks + all-in-one, new `C` table, SHA256SUMS); the
    `-28` integration bundles are marked superseded (CACR relic +
    inverted FDBcc goldens).

    **HARDWARE-VALIDATED same day.** One boot of
    `quadra800-allinone.hda` on the real Quadra 800 captured all five
    suites into the one results file (split copies:
    `results/allinone/*_hardware_quadra800_2026-08-28.jsonl`):
    cpu 717 + fpu 270 + saverestore 8 + mmu-full 25 + **integration
    1328/1328**. Versus the single-suite hardware captures:
    saverestore and mmu-full byte-identical; cpu rows differ ONLY by a
    constant +340 on recorded payload addresses and fpu by +300 on
    FPIAR (the chain code shifted the layout; zero vec/ccr changes —
    the fpu name diffs are the retired `[040-unimpl->vec11]` FSGL*
    labels in the old capture). Integration self-scores 1136/1328 with
    the 51 corrected-golden FDBcc rows now **51/51 pass** — this file
    is the first hardware capture against the corrected corpus — and
    the 192 fails decompose exactly as adjudicated: 176 FINT/FINTRZ
    vector-11 traps + 16 FPIAR low-16 rows. The silicon-only unknown
    is closed: the chain `_Read` under the ROM vector table at bench
    time works on hardware (all four hops, no F-line).

28. **The golden-baseline scoring layer — the captures become a
    turnkey RTL oracle (2026-08-28).** The hardware captures were
    complete but the scoring contract was not: two golden classes
    deliberately diverge from silicon in the corpus (176 FINT/FINTRZ
    vec-11 rows, 16 FPIAR low-16 rows), the CPU/FPU captures embed
    payload-layout addresses, `mmu_diff_corpus.py` scored 0/14
    everywhere (finding 22), FPSR AEXC is sticky across rows, and
    undefined-CCR-bit policy lived only in prose. Now:

    - **`gen/score_vs_oracle.py`** is THE pass/fail golden contract:
      score any candidate run (RTL, emulator, device) of a suite
      against its hardware capture. Every known divergence class is
      recognized and classified instead of failed: `layout` (the
      single constant payload shift, derived per run pair and applied
      only to values inside `$40000..$80000` — the chained-vs-single
      captures proved the model: one delta explains every diff),
      `golden` (host-side expected/pass changed, machine behavior
      equal — the FDBcc fix), `fp-policy` (vec 11 vs execution on
      040-unimplemented FP ops: a full-FPU core legitimately
      differs), `fpiar` (low-16 agreement), `ccr` (undefined bits:
      ABCD/SBCD/NBCD + CHK2/CMP2 N,V; CHK Z,V,C; DIVx-overflow N,Z —
      default `--ccr-policy arch` masks them, `silicon` compares
      exact), `aexc` (opt-in `--mask-aexc`, ONLY for candidates that
      did not run the full corpus in order), `env`/`frame` (mmu
      platform registers / fault-frame windows). Exit 1 on REAL
      diffs only. Validated both directions: chained-vs-single
      captures = 0 REAL across all five suites with exactly the
      expected classifications; injected faults (wrong d-reg, wrong
      vec, defined-CCR-bit flips) all detected, undefined-bit flips
      classified.
    - **`gen/mmu_live_check.py`** now also scores the 14 safe rows
      (vs the MAME baseline) with the finding-13 environment split:
      vec is the REAL signal; the row's target register, harness
      d/a regs and non-target MMU registers are labeled
      `mask`/`dreg`/`areg`/`env` (MAME harness state + its over-wide
      writable masks — silicon adjudicates). It is an adjudication
      REPORT vs MAME; pass/fail belongs to score_vs_oracle.
    - **`mmu_diff_corpus.py` is marked superseded** (docstring
      pointer); kept for the trail.
    - **AEXC decision:** the fpu bench is UNCHANGED — the captures'
      row-order AEXC accumulation is deterministic (chained == single
      proved it), so a full in-order candidate run needs no masking
      and the existing captures stay the golden contract. A per-row
      FPSR-clear bench variant would require ONE new hardware
      capture and is only worth it if isolated-row replay ever
      matters; until then `--mask-aexc` covers partial runs.
    - **Undefined-CCR policy:** both stances are implemented; `arch`
      (mask undefined bits, classify) is the default for RTL
      bring-up, `silicon` (exact Quadra values) for cloning this
      chip's undefined-bit behavior.

    **Hardware status: the campaign needs NO further silicon runs.**
    The optional-only future captures: a FPIAR probe suite (word vs
    long write paths, FMOVEM variant — finding 26's low-16 result is
    already recorded ground truth) and a per-row-FPSR-clear FPU
    re-capture; neither blocks RTL bring-up.

29. **The Amiga 68040 test floppies — every suite as a bootable ADF,
    FS-UAE-validated (2026-08-28).** The MacIIvi project's 68030 Amiga
    port (raw-layout bootblock, SuperState + custom-chip takeover,
    trackdisk JSONL backend, diagnostic marker slots) ported forward
    into `preboot/amiga/` for the 68040 suite: six disks (cpu, fpu,
    saverestore, integration, mmu, mmu-full) in `prebuilt/amiga40-*`.
    040 adaptations: the gate checks AttnFlags AFB_68040 (+FPU40 on
    FPU disks, +a MOVEC-TC probe under recovery on MMU disks — LC040/
    EC040 refused); every cache op is raw CPUSHA (`-DAMIGA_BENCH` in
    the shared mains — no _HwPriv exists, the bare-boot MMU is off,
    and the Quadra CPUSHA bus error is a Mac ROM effect; the old
    gate's `MOVEC #9,CACR` was the finding-25 relic class); the entry
    zeroes .bss (finding 15 postdated the original); the trackdisk
    bracket pushes the 040 D-cache; the mmu-full identity window
    follows the `$80000` load base (`MMU_PAYLOAD_WINDOW_BASE`). Mac
    binaries verified byte-identical across the shared-file edits.

    FS-UAE (A4000/040, kicka4000) validation — baselines in
    `results/amiga40/`: saverestore 8/8 **identical to Quadra
    silicon**; mmu-safe 25 rows, 0 real diffs; cpu 717/717 with 33
    FS-UAE-model divergences (incl. the finding-13 platform-local
    rows); **integration 1328/1328 — FS-UAE is the only emulator that
    survives the corpus tail** (finding 23) — with exactly the 16
    FPIAR rows real-diverging; fpu 270/270 but 243 per-op FPU
    divergences (FS-UAE, like MAME, is a CPU-shaped oracle only);
    mmu-full 20/25 rows (FS-UAE's 040 MMU loses 5 live rows — QEMU/
    silicon stay the MMU oracles). `score_vs_oracle.py` grew
    cross-platform layout support for this: a small trusted set of
    payload deltas (each seen ≥3 times) instead of exactly one, and
    a7 classified as harness `stack` state. The disks' purpose:
    real-silicon captures from A4000/040 owners and Minimig-style
    68040 softcore DUTs, no Quadra required. WinUAE-on-Linux (newer
    core than FS-UAE 3.1's) noted as an optional better referee.

30. **First RTL campaign: AP68040 vs the silicon oracle — every suite
    0 REAL diffs (2026-08-28).** `preboot/sim040/` runs the shared
    bench payloads against an RTL 68040 (`rtl/ap68040` submodule,
    apolkosnik/AP68040 @ 3fed526) in a flat-RAM Verilog testbench
    (tb_corpus.v: 16-bit TG68K-shaped bus, dedicated 32-bit table-
    walker port, doorbell + RAM results window), scored with
    `gen/score_vs_oracle.py` against the 2026-08-28 hardware captures.
    Results (results/ap68040/): saverestore 8/8, fpu 270/270,
    integration 1328/1328 and mmu 24/24 — **zero REAL diffs on all of
    them.** The core matches silicon on the emulator-fatal FDBcc tail,
    the 176 FINT/FINTRZ vector-11 traps, the FPIAR low-16 write quirk,
    stale-ATC retention, and the MMUSR flag ground truth. (Full cpu
    corpus run in flight at writing time.)

    RTL-campaign lessons:
    - The corpus's safe `MOVEC TC w/r` rows ENABLE translation and
      inherit the platform's tables — fine on the Quadra (ROM tables,
      finding 22) and survivable on FS-UAE, a double-fault HALT on
      real RTL with root=0. The sim provides a Quadra-equivalent
      identity world (8K-page tables at RAM top, URP/SRP pointed at
      them by the SIM_MMU_WORLD entry) — translation-on rows then run
      1:1.
    - score_vs_oracle's mmu path adopted mmu_live_check's relocation
      rules for cross-build comparison: table-window descriptor
      ADDRESS bytes and the MMUSR PA field are per-build (`reloc`/
      `layout` classes); descriptor FLAG bytes stay strict — they are
      the ATC/M/U signal.
    - Verilog unsized literals are 32-bit: `maxcycles = 2500000000`
      went negative and ended runs at 9 cycles. Size big literals.
    - iverilog ~50k cycles/s vs Verilator --binary ~800k on this
      design; corpus-scale runs are Verilator territory.

31. **The full 722-row cpu corpus HANGS at results-row 408 — state-
    dependent, still open (2026-08-28).** Two full runs (2.5G-cycle
    default guard and a raised 6.5G guard via the new `MAXCYCLES`
    passthrough in run_corpus.sh) both stopped at exactly 407 emitted
    rows with the 408th row's JSON cut off at `{"` — 4 billion extra
    cycles bought zero additional rows, so this is a hard hang, not
    slowness (the hand-off note "needs a >2G cycle guard" was wrong).
    Last complete row: `ANDI.W #0x1234,(A6)`. A fresh slice around the
    suspect indices (`CDEFS="-DFIRST_TEST_INDEX=405 -DLAST_TEST_INDEX=420"`)
    completes in 9.5M cycles, so the hang needs the accumulated state of
    the ~400-row prefix; a 0..430 reproduction run is the next step.
    The 10-row smoke and every other suite (fpu/saverestore/integration/
    mmu) remain 0 REAL, so this does not retract finding 30's scores —
    it does block calling the cpu suite RTL-complete.
    UPDATE: a 0..430 run with `CDEFS="-DLAST_TEST_INDEX=430"` (which
    forces the payload rebuild) completed in 151M cycles and sailed past
    the row both full runs hung on — the prime suspect is now stale
    hand-off-era build products (the full reruns reused them; CDEFS
    evicts them).  A forced-rebuild full 722 run adjudicates.

32. **cpu corpus env-read rows vs the flat-RAM TB: the `envread` class
    (2026-08-28).** Scoring the 0..430 RTL run against the silicon
    capture surfaced 11 diffs on 7 rows, all environment reads a bare
    flat-RAM TB cannot reproduce: `MOVE.L (xxx).W=$1820,D1` and the
    memory-indirect/postindexed family read Mac low-memory globals
    (silicon returned $40809BE6 — a ROM pointer that lives at $1820 on
    a real Quadra; the TB returns 0 and correctly sets Z), and
    `MOVEC.L VBR/CACR,D0` read platform state.  The RTL behaved
    correctly for its environment.  score_vs_oracle.py grows a
    `--flat-env` flag (passed only by the bare-TB runner
    run_corpus.sh) classifying exactly those seven names as `envread`;
    the machine acceptance scoring does NOT pass the flag — on the
    full machine (real ROM + low memory) these rows compare strictly.
    With the flag: 427 rows, 0 REAL diffs.


### Offline verification harness (new)

Findings 7-9 were validated without hardware and without MAME (the local
MAME binary has no Apple drivers built in): the assembled boot block is
executed under **Musashi** against a simulated Quadra 800 low memory +
DAFB framebuffer, and the resulting framebuffer is rendered to a PNG.
That confirmed the painted screen is legible at both 8 bpp/stride 1024
and 1 bpp/stride 80, that the handoff slot receives `FFDF 0003`, and
that the 68k checksum routine reproduces the host-computed value for all
eight shipped images. The homebrew `m68k-elf-binutils` reproduce the
Retro68 boot block byte-for-byte, so boot-block-only changes can be
built and shipped **without the Retro68 toolchain** — which is how the
`2026-08-26` bundles were produced.

### Findings 7-9 now ship in the payloads too (2026-08-27)

The `2026-08-26` bundles were **boot-block-only** re-splices: pure
assembly, built without Retro68 and dropped into the 2026-06-13 images,
whose payloads were left untouched. So finding 8's *other* half — the
`payload_entry_cpu.s` 8 bpp paint fix — was fixed in the source but
present in **no shipped image**.

The `2026-08-27` bundles are **full rebuilds on a machine with Retro68**:
boot block *and* payload recompiled from source, so findings 7, 8 and 9
are now in both halves of every image. Payloads moved accordingly
(cpu 125142 -> 125218 B, fpu 32442 B, mmu 27040 B, cpu-nowrite
124938 B), which is why every expected `C` value in
`prebuilt/README.md` changed.

Re-verified for the new payloads: all four are contiguous on disk
(`rb-cli locate` reports `fragmented: false`, so the boot block's single
`_Read` still gets the whole image), and finding 10's `HANDOFF_ADDR`
($50000, payload offset `0x10000`) still lands in a **zero gap** in all
four — the latent hazard has not detonated, but it remains latent.

## Hardware bring-up findings (2026-06-13)

First real-Quadra-800 run surfaced two display/IO issues:

1. **Display depth — FIXED.** The Quadra 800 ROM boots the built-in DAFB
   at **640×480 @ 8 bpp (256 colors)**, not the NuBus-era 1 bpp default.
   The bench was painting 1 bit-per-pixel into the 8 bpp framebuffer, so
   each font byte became a single 8 bpp pixel → garbled speckle (confirmed
   by reconstructing a MAME VRAM dump). Fixed: `display_1bpp.c` now has an
   8 bpp paint path (`-DDISPLAY_BPP8`, one byte/pixel, bg `0xFF`/fg `0x00`)
   selected by `VIDEO_VARIANT=dafb` (the default). Verified by host-
   rendering the paint kernel to a legible image. **Requirement: run the
   display at 640×480, 256 colors** (other 256-color resolutions also work
   — the byte stride is read from ScrnRow `$0106` at runtime; only the
   depth is fixed). `dafb1` variant keeps 1 bpp for B&W screens.

2. **Froze at `run=58`, `/Results.jsonl` all-zero — FIX shipped, awaiting
   re-test.** The writer buffers 16 KB batches, so the first `_Write`
   ($A003) fires only when the buffer fills (~line 58 at ~280 B/line) —
   exactly where it froze. Root cause: the 16 KB buffer is filled through
   the 68040 **copyback data cache**, but the Quadra's SCSI does **DMA
   from physical RAM**, so the driver read stale/zero RAM and wedged.
   (`_Write`'s param block is identical to the boot block's `_Read` that
   succeeds, so refnum/drive are fine — it's cache coherency, a 68040-only
   issue the 68020 Mac II never had.) **Fix:** `jsonl_writer.c` now does
   `CPUSHA DC` ($F478) before every `_Write`. If it still fails, boot the
   `quadra800-cpu-nowrite-diag` disk (`-DJW_NO_WRITE`, via `make cpu
   CDEFS=-DJW_NO_WRITE`) to confirm write-vs-CPU-hang, then move the
   results channel to the SCC serial port (polled, no DMA/cache/IRQ).

3. **CACR-write + MOVE16 discriminators wedged the bench at test 191 —
   FIXED (marked hw_unsafe).** With the write fix in place, the CPU run
   reached test 191 = `MOVEC.L D0,CACR; CACR,D1 write all-ones`, which
   RE-ENABLES the 68040 data cache (DE) without a preceding CINV. The
   bench's own next instructions then read stale cache lines → corruption
   → intermittent hang/crash (sometimes a reboot to the Happy Mac). The
   neighboring `CACR write 0` (190) and `MOVE16` (192, also alignment-/
   burst-sensitive) have the same hazard. These three rows now carry
   `hw_unsafe` so the live bench skips them (like STOP/RESET); their MAME
   goldens remain for offline adjudication. General rule: a test that
   writes global CPU state the bench depends on (CACR, VBR, MMU) must be
   `hw_unsafe` unless the runner save/restores that state. (SR-write tests
   are fine — the runner re-masks SR after every test.)

5. **SCSI `_Write` ran with the bench VBR (not the OS VBR) — FIXED, the
   real supervisor-environment bug.** The `_Write` ($A003) goes through
   the ROM's SCSI driver, which takes its own traps/faults while servicing
   the interrupt-driven DMA. But the bench runs with its OWN VBR
   (vectors 2..9, 11..15, 32..47 are recovery stubs), so any trap/fault
   the driver took mid-write hijacked `recovery_core` and longjmp'd out —
   corrupting the write (the intermittent crashes / slowness). The boot
   block's `_Read` works precisely because it runs in the ROM's VBR
   (before `install_vbr`). Fix: `jsonl_writer.c` now brackets each
   `_Write` with `use_os_vbr()` / `use_recovery_vbr()` (the I/O-bracket
   machinery built for the Amiga port but never wired into the Mac path),
   so the driver runs in the OS/ROM environment. IPL is left at the
   bench's level (the `_Read` runs masked and works — the driver polls or
   lowers IPL itself); if the write is still unreliable, lowering IPL
   around the bracket is the next lever. (`use_os_vbr`/`use_recovery_vbr`
   declared weak so iotest/keytest, which don't link recovery.o, skip it.)

6. ~~**MAME won't boot the SCSI `.hda`**~~ — **WRONG, retracted
   2026-08-27.** This was recorded as a MAME `macqd800` boot-device
   quirk. It is not. MAME boots SCSI disks fine (an unrelated System
   7.5.5 disk boots on `macqd800`), and the ROM *does* execute our HFS
   boot block. The CPU parking in ROM at `$408046C6` was **our own bug**
   — see finding 11. With that fixed, all four benches boot end to end
   under MAME. The diagnosis stood for ten weeks and sent verification
   down the offline-harness path instead of at the real defect.

## What is DONE and VERIFIED (against MAME `macqd800`, 2026-06-12)

- **CPU corpus** captured: 722 rows, `results/cpu/mame_baseline_2026-06-12.json`.
  `make cpu` builds the runner (`-m68040`, 125K payload).
- **MMU corpus** captured: 24 rows with live translation (U/M writeback),
  remap, ATC flush, and format-$7 fault frames (vector 2). `make mmu` builds.
- **FPU corpus** classified execute-vs-trap (270 rows, 142 trap). `make fpu`
  builds; the runner records the taken vector.
- All three payloads link with the Retro68 `m68k-apple-macos-gcc -m68040`.

## MAME 68040 quirks found (silicon adjudicates — flag where it disagrees)

1. **PTEST not implemented.** The single-word 68040 PTEST (`$F548`/`$F568`)
   hits MAME's "unknown PMMU instruction group" default (`m68kmmu.h`) — no
   MMUSR update, no fault. The MMU PTEST rows are placeholders carrying the
   right test bytes; capture real goldens on the Quadra 800.
2. **MMUSR impoverished.** Even via the 030-style two-word PTEST path,
   MAME's 040 MMUSR composition (`m68kmmu.h` ~858) uses a logical-OR, so
   only the R/W bits are meaningful (no physical address, no M/S/G/U).
3. **TC writable mask over-wide.** MAME's 040 stores all 32 TC bits; real
   silicon implements only E (15) + P (14) → reads back `$C000`.
4. **CACR writable mask over-wide.** `MOVEC #$FFFFFFFF,CACR` reads back
   `$FFFFFFF3` in MAME; real 68040 CACR is DE (31) + IE (15) → `$80008000`.
   The CPU corpus row name records the silicon expectation.
5. **CAAR still accepted.** The 68040 removed CAAR; MAME still round-trips
   MOVEC to/from `$802`. Adjudicate on HW.
6. **RTM no-ops.** MAME wires RTM (`$06C0`) into the 030/040 decode as a
   logerror no-op instead of the vector-4 illegal trap. The CPU corpus row
   is named "MAME golden known-bad" — a core that traps RTM correctly will
   FAIL this row against MAME, which is the correct behaviour.
7. **FPU executes everything.** MAME's 68040 executes the transcendentals
   (FSIN/FCOS/…) instead of taking the vector-11 unimplemented-FP trap. So
   MAME is NOT the FPU oracle — `gen_fpu.c` (host IEEE) is, and the TRAP
   rows expect vector 11 from the 68040 manual.

### Finding 33 — boot Sad Mac 0000000F/00000033 was dsBadSlotInt, one bad concat bit (2026-08-28)

The machine boot's Sad Mac at ~2.21G cycles printed `0000000F /
00000033`. The hand-off read $33 through the exception dispatcher's
`ID = vector − 1` formula (vector 52 = FPU OPERR) and queued an FPU
exception-delivery hunt. **The trace refuted it**: a 20.7M-cycle
`--trace-after` window ending at the Sad Mac entry contains no FPSP
handler flow at all. The real path (`cpu_trace` tail):

- ROM enables pseudo-VIA slot interrupts (`move.b #$82,($1c13,A0)` =
  IER set bit 1) once video is up;
- pseudo-VIA IFR bit 1 (any-slot) is pending — the DAFB VBL — so the
  autovector handler dispatches to the slot-int service at `$4088BC56`;
- it reads the per-slot active-low status (pseudo-VIA reg $F / Port A,
  the `($1e00,A1)` read), finds a LOW bit, maps it to a slot, looks up
  the slot's handler in the table at `[[$D04]+$40]` — entry is zero —
  and does `moveq #$33,d0` + `_SysError`. **$33 = 51 = dsBadSlotInt**
  ("unserviceable slot interrupt"), an explicit SysError, NOT vector−1.

Root cause in `rtl/iosb.sv`: `nubus_irqs = {1'b1, ~vbl_irq, 5'b11111}`
is a 7-bit concat zero-extended to [7:0], so the DAFB VBL landed on
**bit 5 = NuBus slot $E** (and bit 7 read 0) instead of **bit 6 =
internal video** (QEMU `VIA2_NUBUS_IRQ_INTVIDEO`, q800.c wires macfb
there). The ROM has a handler installed for internal video but slot $E
is an empty socket → dsBadSlotInt. Fix: `{1'b1, ~vbl_irq, 6'b111111}`.
QEMU q800 boots the same ROM through this exact sequence with VBL on
bit 6.

Side discovery while chasing the (wrong) FPU theory, kept for upstream
AP68040 work — real bugs, NOT this Sad Mac: the core's FSAVE frame
payloads are one longword low versus the real 040 layout that the ROM
FPSP's a6-relative equates (Motorola fpsp.h, LOCAL_SIZE=192) address —
the $30 unimp frame writes 13 longs (52 B) and FRESTORE pops 52, the
$41/$60 busy frame writes 25 longs (100 B) and pops 100, both
overrunning their architected 48/96 sizes, and displacing
STAG/CMDREG1B/DTAG/E-T/FPTEMP/ETEMP by +4 from where fpsp.h equates
(ETEMP LV-12, FPTEMP LV-24, E_BYTE LV-28 with E1=bit2/E3=bit1, T_BYTE
LV-27 with TFLAG=bit4, CMDREG1B LV-36, STAG LV-40, CMDREG3B LV-48)
place them. The ROM's vector-52 handler `$4088D28C` is a compacted
x_operr port reading exactly those offsets. The fpu corpus (270/270)
never caught it because its frames were generated against the same
shifted layout, and "68040 FSAVE/FRESTORE frames" under Open work
already flags the corpus side.

## Open work (hardware-iterated)

- **MMU live/fault runner.** `mmu_bench_main.c` runs the register-mask +
  PFLUSH rows; the live-translation and fault rows are emitted
  `skipped:"live-reloc-todo"`. Port the private-identity-page-table install
  + descriptor/address relocation from `mmu_bench_main.c.68030-reference`
  (it solved the equivalent 030 problem against live ROM low memory).
- **68040 FSAVE/FRESTORE frames.** The carried cpSAVE/cpRESTORE corpus uses
  68881/68882 frame formats. The 68040 frames differ ($00 null / $30 idle /
  $60 busy). Regenerate before using those rows.
- **build_prebuilts.sh** still bundles the `cpu`/`mmu` variants only and
  defaults to the old fixed-stride names; add the `dafb` (auto-stride) and
  `fpu` payloads when packaging release images. `make cpu/fpu/mmu` already
  produce the payloads directly.
- **Musashi** (`~/repos/Musashi`) not checked out — needed only for the
  alternate CPU generator `gen/gen.c` (MAME `macqd800` is the canonical
  CPU oracle). **verilator** not installed — the `fpu/`, `cpu_fpu/`
  verilator harnesses await it plus a 68040 / 68881-fpga-lite DUT.

## Decisions on record

- **FPU = MC68040-lite + FPSP-trap** (Dani, 2026-06-12): the bench expects
  the hardware arithmetic subset to execute and the transcendental/extended
  ops to trap to vector 11. If the FPGA core embeds a full 68882 FPU
  instead, move those opmodes into `HW_OPMODES` (gen_fpu_header.py) /
  the execute lists (gen_fpu.c) to flip the expectation.
- **MAME usage minimal** (Dani, 2026-06-12): capture starting baselines,
  then adjudicate on real Quadra 800 silicon.
