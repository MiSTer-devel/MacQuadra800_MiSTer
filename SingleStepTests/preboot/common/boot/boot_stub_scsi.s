| boot_stub_scsi.s — SCSI-bootable HFS boot block (canonical).
|
| Historical name: preboot/iotest/boot_stub.s. Promoted to the
| shared preboot/common/boot/ tree during the reorg because it's
| medium-agnostic — the only difference from the supervisor_bench's
| older boot_stub_scsi.s (now boot_stub_scsi_fixed_offset.s) is the
| PAYLDOFF marker + .long placeholder which lets the image-build
| script patch /Payload's byte offset at build time instead of
| baking 0x51600 as a compile-time constant.
|
|
| Same boot block header as the floppy version (bbVersion=$D000 to
| make ROM execute bbEntry directly). At bbEntry time on a SCSI
| boot, the Mac ROM has:
|   - Read the Driver Descriptor Record (block 0)
|   - Loaded Apple_Driver43 from the driver partition
|   - Registered the driver in the Unit Table with a refnum
|   - Allocated a drive number for our HFS partition
|   - Stored that drive number in BootDrive (low-mem $0210)
|   - Added a DrvQEl to the drive queue (DrvQHdr at $0308)
|   - Read the HFS partition's boot blocks (sectors 0-1) and jumped
|     here because bbVersion=$D000.
|
| We need to load /Payload from the HFS partition. Approach:
|   1. Read BootDrive ($0210) - the drive number for "us".
|   2. Walk DrvQHdr ($030A is qHead) to find the matching DrvQEl.
|   3. Read its dQRefNum field - that's the driver refnum.
|   4. Call _Read ($A002) with PB containing that refnum.
|
| The driver presents the partition as a drive with offset 0 = start
| of HFS partition (i.e. byte 0xC000 of physical disk). So /Payload
| at byte offset 0x51600 within the partition is what we ask for.
|
| ---------------------------------------------------------------------
| 68040 NOTE (Quadra 800, 2026-08-26) — cache coherency around _Read.
|
| This stub loads 256 KB of payload with one _Read and then JMPs into
| it. On the 68020 (Mac II) and 68030 (IIvi) that was safe: their
| caches are 256 bytes and WRITE-THROUGH, so a DMA'd buffer could
| never be shadowed by dirty cache lines. The 68040 has a 4 KB
| instruction cache and a 4 KB data cache in COPYBACK mode, and the
| Quadra's SCSI transfers into PHYSICAL RAM — so without explicit
| cache management:
|
|   - dirty data-cache lines covering $40000..$80000 (left over from
|     the ROM's own boot-time use of low RAM) get written back ON TOP
|     of the freshly transferred payload, and
|   - stale instruction-cache lines for that range get executed
|     instead of the bytes that just arrived.
|
| Both are non-deterministic: whether a given boot lands the damage on
| code that matters or on padding depends on what the ROM happened to
| touch. Observed symptom on the physical Quadra 800 was exactly that
| — "mostly doesn't reach the bench, very occasionally does".
|
| Fix: CPUSHA BC ($F4F8) on BOTH sides of the _Read.
|   - Before: pushes every dirty line to RAM and invalidates both
|     caches, so nothing can be written back over the payload later.
|   - After:  pushes anything the driver wrote through the CPU (a
|     driver that copies rather than DMAs leaves the payload dirty in
|     the D-cache) and invalidates both caches, so the JMP fetches the
|     bytes that are actually in RAM.
| CPUSHA (push+invalidate) is used rather than CINVA (invalidate only)
| precisely because the post-read case must not discard a CPU-copying
| driver's data. NOP after each — the 68040 UM requires pipeline sync
| around cache-control instructions.
|
| This is the same class of bug as the jsonl_writer.c CPUSHA DC fix
| for _Write; the read side was simply never covered.
|
| ---------------------------------------------------------------------
| DISPLAY NOTE (Quadra 800) — 8 bpp diagnostics.
|
| The Quadra 800 ROM boots the built-in DAFB at 640x480 @ 8 bpp, one
| BYTE per pixel. The old painter wrote one byte per EIGHT pixels
| (1 bpp), so every readout below rendered as unreadable speckle —
| which is why the _Read result code, the refnum and the drive number
| have been invisible during Quadra bring-up. Assemble with
| --defsym DISPLAY_BPP8=1 for the byte-per-pixel path (background
| $FF = black, stroke $00 = white, matching display_1bpp.c), and with
| --defsym ROW_BYTES_AUTO=1 to take the row stride from the ROM's
| ScrnRow low-mem global ($0106) at runtime instead of the
| compile-time ROW_BYTES. common/make/common.mk passes both for
| VIDEO_VARIANT=dafb.

.ifndef ROW_BYTES
    ROW_BYTES = 80
.endif

| Bytes per character cell: 8 bpp paints an 8x8 pixel glyph as 8x8
| bytes; 1 bpp packs each glyph row into a single byte.
.ifdef DISPLAY_BPP8
    CELL_BYTES = 8
.else
    CELL_BYTES = 1
.endif

    .text
    .global _start
_start:
    .ascii  "LK"
bbEntry:
    bra.w   startup

bbVersion:    .word 0xD000
bbPageFlags:  .word 0

bbSysName:    .byte 6;  .ascii "System";          .space 9
bbShellName:  .byte 6;  .ascii "Finder";          .space 9
bbDbg1Name:   .byte 7;  .ascii "Macsbug";         .space 8
bbDbg2Name:   .byte 12; .ascii "Disassembler";    .space 3
bbScreenName: .byte 13; .ascii "StartUpScreen";   .space 2
bbHelloName:  .byte 6;  .ascii "Finder";          .space 9
bbScrapName:  .byte 14; .ascii "Clipboard File";  .space 1

bbCntFCBs:        .word 10
bbCntEvts:        .word 20
bbHeapSize128K:   .long 0x00004300
bbHeapSize256K:   .long 0x00008000
bbHeapSize:       .long 0x00020000

PB_OFF_IORESULT     = 16
PB_OFF_IOVREFNUM    = 22
PB_OFF_IOREFNUM     = 24
PB_OFF_IOBUFFER     = 32
PB_OFF_IOREQCOUNT   = 36
PB_OFF_IOACTCOUNT   = 40
PB_OFF_IOPOSMODE    = 44
PB_OFF_IOPOSOFFSET  = 46
PB_SIZE             = 80

PAYLOAD_LOAD_ADDR     = 0x00040000
PAYLOAD_READ_BYTES    = 262144          | 256 KB — comfortable headroom for the bench payload
| Fallback checksum window, used only if the PAYLCKSZ marker below was
| never patched. The real value comes from the image build script — see
| payload_cksum_len.
PAYLOAD_CKSUM_BYTES   = 0x1E000         | 122880 bytes

| /Payload's byte offset within the partition is no longer a compile-
| time constant. Build scripts probe it at image-build time with
| `rb-cli locate IMG[@N] /Payload` and patch the 4-byte value sitting
| immediately after the 8-byte "PAYLDOFF" marker below. Code loads
| the value PC-relative from `payload_offset_value`. Placeholder is
| 0xDEADBEEF; if the bench faults early with that as the read offset,
| the build pipeline didn't patch correctly.

| Slot where the boot block stashes (refnum << 16) | drive for the
| payload to find. Written AFTER the payload has been read into
| $40000, so it MUST NOT overlap the loaded image.
|
| Was $00041000 before 2026-05-25 (collided with iotest payload
| .rodata). $00050000 is fine for the small 68020/68030 payloads, but
| it sits 64 KB INTO the Quadra 800's 125 KB CPU-bench payload
| ($40000..$5E8C0), so the boot block scribbles 4 bytes over it. Today
| those 4 bytes land in a zero gap in the captured corpus, so it is
| harmless — but it is a landmine: any change to payload layout turns
| it into silent payload corruption.
|
| The real fix is $00080000 (the first byte past the 256 KB read
| window, right where the payload's $00080000 stack now tops out;
| the handoff longword at $80000 itself stays untouched). It is NOT the
| default because the address is duplicated in seven places — every
| bench's payload_entry*.s reads it as a hard-coded literal — and a
| boot block and payload that disagree hand the bench a garbage
| refnum. To move it, change ALL of these in one commit:
|   common/boot/boot_stub_scsi{,_fixed_offset}.s
|   supervisor_bench/payload_entry{,_cpu,_scsi}.s
|   iotest/payload_entry.s  diskcopy/payload_entry.s  keytest/payload_entry.s
| Until then --defsym HANDOFF_ADDR=... lets a boot block be rebuilt to
| match whatever an already-built payload expects.
.ifndef HANDOFF_ADDR
HANDOFF_ADDR          = 0x00080000
.endif

| DrvQHdr / DrvQEl
DRVQHDR_QHEAD         = 0x0000030A
BOOTDRIVE             = 0x00000210
DRVQEL_OFF_QLINK      = 0
DRVQEL_OFF_DQDRIVE    = 6
DRVQEL_OFF_DQREFNUM   = 8

| Mac low memory
SCRNBASE              = 0x00000824
SCRNROW               = 0x00000106

| AT row,col — point %a0 at pixel row `row`, character column `col`.
| Rows are pixels, columns are 8-pixel character cells, matching
| display_1bpp.c's paint_string(row, col_char, ...).
    .macro AT row, col
    move.w  #\row, %d0
    moveq   #\col, %d1
    bsr.w   at_rc
    .endm

| GAP — skip one character cell, so a label glyph and the hex field
| after it don't run together on screen.
    .macro GAP
    lea     CELL_BYTES(%a0), %a0
    .endm

startup:
    move.w  #0x2700, %sr
    | Keep the ROM's SP: $10000 sat on the ROM boot heap and smashed the
    | SCSI Manager's write-path glue just below it (finding 21).

    | --- Make the DAFB aperture transparently translated (MUST be first) ---
    | The ROM hands the boot block a machine with the 68040 MMU ENABLED
    | (TC = $C000: E + P, 8 KB pages, SRP = $007FCC00) and ALL FOUR
    | transparent-translation registers DISABLED. Every access we make
    | therefore goes through the ROM's page tables -- and those do not
    | map the DAFB aperture the way this code assumes. A write to
    | ScrnBase ($F9001000) does NOT reach video RAM: it lands at
    | physical $00001000. The 128 KB wipe just below would then scribble
    | $FFFFFFFF over low memory $1000..$21000, taking out the drive
    | queue at $4700 (and the low-memory globals) before the DrvQ walk
    | ever reads it. The walk then dereferences $FFFFFFFF, faults, and
    | the ROM's handler takes the machine back -- which is exactly the
    | "bench mostly does not start" symptom seen on the physical Quadra.
    |
    | Fix: map $F0000000..$FFFFFFFF 1:1 through DTT0, cache-inhibited
    | (CM = 10) as memory-mapped IO and a framebuffer must be.
    |   $F00FE040 = base $F0, mask $0F, E=1, S=11 (user+supervisor), CM=10
    |
    | ONLY DTT0 is touched, deliberately. RAM keeps the ROM's own
    | page-table mapping, which is what the SCSI driver behind _Read
    | needs: forcing a blanket 1:1 over the whole address space instead
    | makes _Read fail with readErr (-19). Leaving SR at $2700 likewise
    | matters -- re-enabling interrupts here also breaks the load.
    | The TTR is a CPU register, so it stays in force for the payload,
    | whose entry shim paints through ScrnBase the same way.
    | OFF by default: this block crashed the real-hardware boot (root
    | cause formally unresolved; the old PFLUSHA attribution is disproven
    | — silicon executes PFLUSH fine, findings 20/26). Only MAME/QEMU
    | need it, and only because their page-table walk does not map the
    | DAFB (findings 20/22). Emulator images: --defsym BOOT_SET_DTT0=1.
.ifdef BOOT_SET_DTT0
    move.l  #0xF00FE040, %d0
    movec   %d0, %dtt0
    pflusha
    nop
.endif

    | --- Wipe screen black ---
    move.l  SCRNBASE.l, %a3
    tst.l   %a3
    beq     halt
    cmp.l   #0x00100000, %a3
    blo     halt
    move.l  %a3, %a0
    move.l  #(128*1024/4)-1, %d0
1:  move.l  #0xFFFFFFFF, (%a0)+
    dbra    %d0, 1b

    bsr.w   init_stride

    | Layout (label glyph at col 4, 8 hex digits at cols 5..12):
    |   row  4  'A' + BootDrive      — boot block entered
    |   row 16  'D' + driver refnum  — DrvQ walk succeeded
    |   row 28  'E' + _Read ioResult — payload load result
    |   row 40  'C' + payload cksum  — is the loaded image intact?
    |   row 52  '3' + solid block    — about to JMP into the payload

    | --- Marker 'A' + BootDrive (signed word) ---
    move.w  BOOTDRIVE.l, %d4              | %d4 = drive number for our partition
    AT      4, 4
    moveq   #10, %d0                      | 'A'
    bsr.w   draw_glyph_d0
    GAP
    move.w  %d4, %d5
    ext.l   %d5
    bsr.w   hex8

    | --- Walk DrvQHdr to find matching dQDrive, extract dQRefNum ---
    moveal  DRVQHDR_QHEAD.l, %a1          | %a1 = qHead
    moveq   #0, %d5                       | %d5 = sanity hop counter
.scan:
    cmp.l   #0, %a1
    beq     fail_noref
    cmp.w   DRVQEL_OFF_DQDRIVE(%a1), %d4
    beq.s   .found
    moveal  DRVQEL_OFF_QLINK(%a1), %a1
    addq.l  #1, %d5
    cmpi.l  #32, %d5                      | guard: max 32 drives
    blt.s   .scan
    bra     fail_noref
.found:
    move.w  DRVQEL_OFF_DQREFNUM(%a1), %d6 | %d6 = driver refnum (negative)

    | --- Paint 'D' (Driver) + refnum ---
    AT      16, 4
    moveq   #13, %d0                      | 'D'
    bsr.w   draw_glyph_d0
    GAP
    move.w  %d6, %d5
    ext.l   %d5
    bsr.w   hex8

    | --- Zero PB ---
    lea     pb(%pc), %a0
    moveq   #(PB_SIZE/4)-1, %d0
1:  clr.l   (%a0)+
    dbra    %d0, 1b

    | --- Issue _Read via the SCSI driver refnum ---
    lea     pb(%pc), %a0
    move.w  %d6, PB_OFF_IOREFNUM(%a0)     | driver refnum
    move.w  %d4, PB_OFF_IOVREFNUM(%a0)    | drive number
    move.l  #PAYLOAD_LOAD_ADDR, PB_OFF_IOBUFFER(%a0)
    move.l  #PAYLOAD_READ_BYTES, PB_OFF_IOREQCOUNT(%a0)
    move.w  #1, PB_OFF_IOPOSMODE(%a0)     | fsFromStart
    | Patched at build time — see payload_offset_value below.
    move.l  payload_offset_value(%pc), PB_OFF_IOPOSOFFSET(%a0)

    | Flush both caches before the transfer. Raw CPUSHA BC ($F4F8) took a
    | bus error on real Quadra 800 silicon, so use the ROM's own call:
    | _HwPriv selector 1 flushes BOTH caches on the 68040 (Developer Note,
    | ch.4). It clobbers D0/A0, so save the PB pointer around it.
    movem.l %d4/%d6/%d7/%a0, -(%sp)
    moveq   #1, %d0
    .word   0xA198                         | _HwPriv FlushInstructionCache
    movem.l (%sp)+, %d4/%d6/%d7/%a0
    nop

    .word   0xA002                         | _Read
    move.w  PB_OFF_IORESULT(%a0), %d7

    | Same again after the transfer, so the JMP below fetches the payload
    | from RAM rather than a stale I-cache line.
    movem.l %d4/%d6/%d7/%a0, -(%sp)
    moveq   #1, %d0
    .word   0xA198                         | _HwPriv FlushInstructionCache
    movem.l (%sp)+, %d4/%d6/%d7/%a0
    nop

    | --- Paint 'E' (rEad) + ioResult ---
    AT      28, 4
    moveq   #14, %d0                      | 'E'
    bsr.w   draw_glyph_d0
    GAP
    move.w  %d7, %d5
    ext.l   %d5
    bsr.w   hex8

    | --- Checksum the loaded payload -------------------------------
    | Rotating 32-bit sum over the first 128 KB at $40000, computed
    | BEFORE the handoff write below so it reflects exactly what came
    | off the disk. The host knows the expected value for a given
    | image, so a mismatch (or a value that changes between boots) is
    | direct proof that the payload did not survive the transfer.
    movea.l #PAYLOAD_LOAD_ADDR, %a1
    moveq   #0, %d5
    move.l  payload_cksum_len(%pc), %d3
    cmpi.l  #0x1000, %d3                  | unpatched / absurd length ->
    blo.s   1f                            |   use the built-in fallback
    cmpi.l  #PAYLOAD_READ_BYTES, %d3
    bls.s   2f
1:  move.l  #PAYLOAD_CKSUM_BYTES, %d3
2:  lsr.l   #2, %d3                       | byte count -> longword count
    subq.l  #1, %d3                       | dbra counts n-1 (16 bits, so
                                          | the cap above matters)
3:  add.l   (%a1)+, %d5
    rol.l   #1, %d5
    dbra    %d3, 3b

    AT      40, 4
    moveq   #12, %d0                      | 'C'
    bsr.w   draw_glyph_d0
    GAP
    bsr.w   hex8

    | If read failed, hang here so the operator can read the codes.
    tst.w   %d7
    bne     halt

    | --- Hand off refnum+drive to the payload ---
    move.w  %d6, HANDOFF_ADDR.l           | refnum
    move.w  %d4, (HANDOFF_ADDR+2).l       | drive

    | --- '3' + solid block = about to jump ---
    AT      52, 4
    moveq   #3, %d0
    bsr.w   draw_glyph_d0
    moveq   #16, %d0                      | solid block
    bsr.w   draw_glyph_d0

.ifdef BOOT_WRITE_TEST
    | Diagnostic: does _Write work in the boot block's environment, where
    | _Read demonstrably does? Writes 512 bytes of the payload back over
    | itself at the same offset, so the disk content is unchanged.
    | Paints 'W' + ioResult at row 64, then halts. No payload is entered.
    | Row 64 marker '6' is painted BEFORE the trap, so the screen tells us
    | whether we even reached the write: 6 lines = hung inside _Write,
    | 7 lines = it returned and row 76 holds ioResult, gray = never booted.
    AT      64, 4
    moveq   #6, %d0
    bsr.w   draw_glyph_d0

    lea     pb(%pc), %a0
    move.l  #PAYLOAD_LOAD_ADDR, PB_OFF_IOBUFFER(%a0)
    move.l  #512, PB_OFF_IOREQCOUNT(%a0)
    move.l  payload_offset_value(%pc), PB_OFF_IOPOSOFFSET(%a0)
    .word   0xA003                        | _Write
    move.w  PB_OFF_IORESULT(%a0), %d7

    AT      76, 4
    moveq   #7, %d0
    bsr.w   draw_glyph_d0
    GAP
    move.w  %d7, %d5
    ext.l   %d5
    bsr.w   hex8
1:  bra.s   1b
.endif

    jmp     PAYLOAD_LOAD_ADDR.l

fail_noref:
    | "FFFF" at row 16 = no matching DrvQEl found for BootDrive.
    AT      16, 4
    moveq   #3, %d3
1:  moveq   #15, %d0
    bsr.w   draw_glyph_d0
    dbra    %d3, 1b

halt:
1:  bra.s   1b

| --- Patchable /Payload byte offset ---------------------------------
| `payload_offset_marker` is an 8-byte ASCII sentinel that the image-
| build script finds via byte search; the 4-byte big-endian longword
| immediately after it (`payload_offset_value`) is the actual partition-
| relative byte offset of /Payload. Loaded PC-relative above; absolute
| address depends on where the boot block sits in the partition (LBA
| 0 of HFS = byte 0), but PC-relative addressing means we don't need
| to care. Placeholder 0xDEADBEEF makes it obvious if patching missed.
    .align 2
payload_offset_marker:
    .ascii  "PAYLDOFF"
payload_offset_value:
    .long   0xDEADBEEF

| --- Patchable payload-checksum window ------------------------------
| Length in BYTES of the region at $40000 that the boot block sums and
| paints on the 'C' row. It has to stay inside /Payload: the 256 KB
| _Read runs off the end of the file into whatever follows it on disk,
| and on these images that is /Results.jsonl — which the bench itself
| rewrites, so covering it would make the checksum change from run to
| run and destroy its value as a corruption detector. The image build
| script patches this with (results_offset - payload_offset): exactly
| the region HFS allocated to /Payload. Must be a multiple of 4 and no
| larger than PAYLOAD_READ_BYTES, since dbra counts only 16 bits.
    .align 2
payload_cksum_marker:
    .ascii  "PAYLCKSZ"
payload_cksum_len:
    .long   PAYLOAD_CKSUM_BYTES

| Row stride in bytes, resolved at runtime (see init_stride). The boot
| block executes from RAM, so this .text word is writable; it is read
| PC-relative so the block stays position-independent.
stride_w:
    .word   ROW_BYTES

| init_stride: take the framebuffer row stride from the ROM's ScrnRow
| ($0106) when built with ROW_BYTES_AUTO, so one boot block is correct
| at whatever resolution the ROM programmed. Falls back to the
| compile-time ROW_BYTES if the value is implausible — same
| plausibility test display_1bpp.c uses.
init_stride:
.ifdef ROW_BYTES_AUTO
    moveq   #0, %d0
    move.w  SCRNROW.l, %d0
    cmpi.w  #16, %d0
    blo.s   1f
    cmpi.w  #4096, %d0
    bhi.s   1f
    btst    #0, %d0                       | must be a multiple of 4
    bne.s   1f
    btst    #1, %d0
    bne.s   1f
    lea     stride_w(%pc), %a0
    move.w  %d0, (%a0)
1:
.endif
    rts

| at_rc: %d0 = pixel row, %d1 = character column -> %a0 = framebuffer
| pointer. Clobbers d0/d1.
at_rc:
    mulu.w  stride_w(%pc), %d0            | row * stride (both < 65536)
    mulu.w  #CELL_BYTES, %d1
    add.l   %d1, %d0
    movea.l %a3, %a0
    adda.l  %d0, %a0
    rts

| hex8: paint %d5 as 8 hex digits at (%a0), advancing %a0.
| Clobbers d0-d3, d5, a1, a2.
hex8:
    moveq   #7, %d3
1:  rol.l   #4, %d5
    move.l  %d5, %d0
    andi.l  #0xF, %d0
    bsr.w   draw_glyph_d0
    dbra    %d3, 1b
    rts

| draw_glyph_d0: paint hex_font glyph %d0 at (%a0) and advance %a0 by
| one character cell. Clobbers d0, d1, d2, a1, a2.
draw_glyph_d0:
    lea     hex_font(%pc), %a1
    lsl.l   #3, %d0
    adda.l  %d0, %a1
    move.l  %a0, %a2
    moveq   #7, %d1                       | 8 glyph rows
.dg_row:
    move.b  (%a1)+, %d2                   | glyph row bitmap, bit 7 = leftmost
.ifdef DISPLAY_BPP8
    moveq   #7, %d0                       | 8 pixels, one byte each
.dg_col:
    add.b   %d2, %d2                      | shift bit 7 into carry
    bcs.s   .dg_on
    move.b  #0xFF, (%a2)+                 | background: black
    bra.s   .dg_next
.dg_on:
    clr.b   (%a2)+                        | stroke: white
.dg_next:
    dbra    %d0, .dg_col
    subq.l  #8, %a2                       | back to the start of this row
.else
    not.b   %d2                           | 1 bpp: strokes are 0 bits
    move.b  %d2, (%a2)
.endif
    adda.w  stride_w(%pc), %a2            | next scanline
    dbra    %d1, .dg_row
    lea     CELL_BYTES(%a0), %a0          | advance the caller's cursor
    rts

hex_font:
    .byte 0x3C,0x42,0x46,0x4A,0x52,0x62,0x3C,0x00   | 0
    .byte 0x18,0x28,0x08,0x08,0x08,0x08,0x3E,0x00   | 1
    .byte 0x3C,0x42,0x02,0x0C,0x30,0x40,0x7E,0x00   | 2
    .byte 0x3C,0x42,0x02,0x1C,0x02,0x42,0x3C,0x00   | 3
    .byte 0x04,0x0C,0x14,0x24,0x7E,0x04,0x04,0x00   | 4
    .byte 0x7E,0x40,0x7C,0x02,0x02,0x42,0x3C,0x00   | 5
    .byte 0x1C,0x20,0x40,0x7C,0x42,0x42,0x3C,0x00   | 6
    .byte 0x7E,0x02,0x04,0x08,0x10,0x20,0x20,0x00   | 7
    .byte 0x3C,0x42,0x42,0x3C,0x42,0x42,0x3C,0x00   | 8
    .byte 0x3C,0x42,0x42,0x3E,0x02,0x04,0x38,0x00   | 9
    .byte 0x3C,0x42,0x42,0x7E,0x42,0x42,0x42,0x00   | A
    .byte 0x7C,0x42,0x42,0x7C,0x42,0x42,0x7C,0x00   | B
    .byte 0x3C,0x42,0x40,0x40,0x40,0x42,0x3C,0x00   | C
    .byte 0x78,0x44,0x42,0x42,0x42,0x44,0x78,0x00   | D
    .byte 0x7E,0x40,0x40,0x7C,0x40,0x40,0x7E,0x00   | E
    .byte 0x7E,0x40,0x40,0x7C,0x40,0x40,0x40,0x00   | F
    .byte 0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF   | 16: solid block

    .align 2
pb:
    .space  PB_SIZE
