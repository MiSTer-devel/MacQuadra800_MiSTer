| payload_entry_cpu.s — entry for the CPU-bench payload (SCSI or
| floppy). Sets up SP, hands the boot block's handoff slot to C,
| clears the screen, paints "CPU BENCH", calls bench_main().
|
| The banner is the only evidence the payload started that appears
| BEFORE bench_main()'s C paint kernel takes over (its first act is a
| full-screen wipe), so it has to be readable on the target display.
| Like common/boot/boot_stub_scsi.s this shim therefore paints one
| BYTE per pixel when built with --defsym DISPLAY_BPP8=1 (the Quadra
| 800's 640x480 @ 8 bpp boot mode) and takes the row stride from the
| ROM's ScrnRow low-mem global with --defsym ROW_BYTES_AUTO=1.
| common/make/common.mk passes both for VIDEO_VARIANT=dafb.

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

SCRNBASE = 0x00000824
SCRNROW  = 0x00000106

| Handoff slot written by the boot block: refnum word, drive word.
| Must match HANDOFF_ADDR in common/boot/boot_stub_scsi.s — see the
| long comment there before changing it.
.ifndef HANDOFF_ADDR
HANDOFF_ADDR = 0x00080000
.endif

    .text
    .global _payload_start
_payload_start:
    move.w  #0x2700, %sr
    move.l  #0x00080000, %sp              | top of our 256 KB read window: only RAM we own (finding 21)

    | --- Zero .bss (MUST precede the handoff load, which lives in .bss) ---
    | .bss is NOLOAD, so C statics start as whatever the boot block's 256 KB
    | over-read left at those addresses — zeros only while /Results.jsonl is
    | still blank, i.e. only on a disk that has never been run.
    lea     _payload_bss_start, %a0
    lea     _payload_bss_end, %a1
1:  cmp.l   %a1, %a0
    bcc.s   2f
    clr.l   (%a0)+
    bra.s   1b
2:

    | --- Load handoff slot (refnum word, drive word) ---
    move.w  HANDOFF_ADDR.l, %d0
    move.w  %d0, g_handoff_refnum
    move.w  (HANDOFF_ADDR+2).l, %d0
    move.w  %d0, g_handoff_drive

    | --- Wipe screen ---
    move.l  SCRNBASE.l, %a4
    move.l  %a4, %d0
    beq     .hang
    cmp.l   #0x00100000, %d0
    blo     .hang
    move.l  %a4, %a0
    move.l  #(128*1024/4)-1, %d0
1:  move.l  #0xFFFFFFFF, (%a0)+
    dbra    %d0, 1b

    bsr.w   init_stride

    | --- Paint "CPU BENCH" at row 4, char column 4 ---
    move.w  #4, %d0
    moveq   #4, %d1
    bsr.w   at_rc
    lea     banner, %a1
    moveq   #8, %d0
    bsr.w   draw_string_n_d0

    jsr     bench_main

    | --- Paint "DONE" at row 56, char column 4 ---
    move.w  #56, %d0
    moveq   #4, %d1
    bsr.w   at_rc
    lea     done_str, %a1
    moveq   #3, %d0
    bsr.w   draw_string_n_d0

    | --- Chain to the next suite if the build script patched one in ---
    move.l  g_next_offset, %d0
    beq.w   .hang

    move.w  #0x2700, %sr
    | VBR back to the ROM table at 0: the _Read below replaces this whole
    | payload — including its vector table — while the trap executes.
    suba.l  %a0, %a0
    .short  0x4E7B, 0x8801                | movec a0,vbr
    | Re-plant the handoff from the copy taken at entry: corpus rows may
    | scribble $80000 (the saverestore FSAVE/FRESTORE (A0) rows do).
    move.w  g_handoff_refnum, %d1
    move.w  %d1, HANDOFF_ADDR.l
    move.w  g_handoff_drive, %d1
    move.w  %d1, (HANDOFF_ADDR+2).l
    | Stage the stub's parameters, then copy stub+params to CHAIN_ADDR:
    | the stub cannot run from $4xxxx while _Read overwrites $4xxxx.
    move.l  %d0, chain_next_off
    move.l  g_next_length, %d0
    move.l  %d0, chain_next_len
    lea     chain_stub, %a0
    lea     chain_stub_end, %a1
    movea.l #CHAIN_ADDR, %a2
1:  move.l  (%a0)+, (%a2)+
    cmp.l   %a1, %a0
    blo.s   1b
    move.l  #0x00080000, %sp              | fresh stack; handoff at $80000 stays
    moveq   #1, %d0                       | _HwPriv sel 1: push + invalidate both
    .word   0xA198                        | caches so the jump fetches the stub
    nop
    movea.l #CHAIN_ADDR, %a2
    jmp     (%a2)

.hang:
1:  bra.s   1b

| --------------------------------------------------------------------
| Chain stub — runs at CHAIN_ADDR (position-independent; data refs are
| PC-relative). Repeats the boot block's own load step: _Read the next
| payload over $40000 under the ROM VBR at SR $2700, _HwPriv-flush both
| sides, JMP $40000. CHAIN_ADDR sits below the $80000 stack top yet
| above any payload's read extent (build script asserts <= $3C000).
| --------------------------------------------------------------------
CHAIN_ADDR          = 0x0007C000
PAYLOAD_LOAD_ADDR   = 0x00040000
PB_OFF_IORESULT     = 16
PB_OFF_IOVREFNUM    = 22
PB_OFF_IOREFNUM     = 24
PB_OFF_IOBUFFER     = 32
PB_OFF_IOREQCOUNT   = 36
PB_OFF_IOPOSMODE    = 44
PB_OFF_IOPOSOFFSET  = 46
PB_SIZE             = 80

    .align 4
chain_stub:
    | Slice the load into <=16 KB driver requests: a single pre-System
    | request above 16 KB hits the ROM Device Manager's queued path
    | through garbage low memory (finding 24 — and it bites reads too:
    | the boot block's one 256 KB _Read only survives in the boot-time
    | environment). d3-d7 are preserved across the traps.
    move.l  chain_next_off(%pc), %d4      | disk offset cursor
    move.l  #PAYLOAD_LOAD_ADDR, %d5       | RAM cursor
    move.l  chain_next_len(%pc), %d3      | bytes remaining

    moveq   #1, %d0                       | flush before the transfer
    .word   0xA198                        | _HwPriv FlushInstructionCache
    nop

.next_chunk:
    tst.l   %d3
    ble.s   .load_done
    move.l  #16384, %d6
    cmp.l   %d6, %d3
    bge.s   1f
    move.l  %d3, %d6                      | final partial chunk
1:  lea     chain_pb(%pc), %a0
    moveq   #(PB_SIZE/4)-1, %d0
2:  clr.l   (%a0)+
    dbra    %d0, 2b
    lea     chain_pb(%pc), %a0
    move.w  HANDOFF_ADDR.l, %d0           | refnum (boot block's handoff)
    move.w  %d0, PB_OFF_IOREFNUM(%a0)
    move.w  (HANDOFF_ADDR+2).l, %d0       | drive
    move.w  %d0, PB_OFF_IOVREFNUM(%a0)
    move.l  %d5, PB_OFF_IOBUFFER(%a0)
    move.l  %d6, PB_OFF_IOREQCOUNT(%a0)
    move.w  #1, PB_OFF_IOPOSMODE(%a0)     | fsFromStart
    move.l  %d4, PB_OFF_IOPOSOFFSET(%a0)
    .word   0xA002                        | _Read
    lea     chain_pb(%pc), %a0
    move.w  PB_OFF_IORESULT(%a0), %d7
    tst.w   %d7                           | read failed: hang after DONE with
    bne.s   .chain_dead                   | no next banner = chain _Read error
    add.l   %d6, %d4
    add.l   %d6, %d5
    sub.l   %d6, %d3
    bra.s   .next_chunk

.load_done:
    moveq   #1, %d0                       | flush after, so the JMP fetches
    .word   0xA198                        | the bytes that actually arrived
    nop
    jmp     PAYLOAD_LOAD_ADDR.l
.chain_dead:
    bra.s   .chain_dead

    .align 4
chain_next_off: .long 0                   | filled from g_next_offset pre-copy
chain_next_len: .long 0
chain_pb:       .space PB_SIZE
    .align 4
chain_stub_end:

| --------------------------------------------------------------------
| Globals exported to C
| --------------------------------------------------------------------
    .data
    .align 4
    .global g_handoff_refnum
    .global g_handoff_drive
g_handoff_refnum:   .word 0
g_handoff_drive:    .word 0

| Framebuffer row stride in bytes, resolved at runtime by init_stride.
stride_w:           .word ROW_BYTES

    .text

| init_stride: take the row stride from the ROM's ScrnRow ($0106) when
| built with ROW_BYTES_AUTO, so one binary is correct at whatever
| resolution the ROM programmed. Falls back to the compile-time
| ROW_BYTES if the value is implausible — the same plausibility test
| display_1bpp.c applies.
init_stride:
.ifdef ROW_BYTES_AUTO
    moveq   #0, %d0
    move.w  SCRNROW.l, %d0
    cmpi.w  #16, %d0
    blo.s   1f
    cmpi.w  #4096, %d0
    bhi.s   1f
    btst    #0, %d0                        | must be a multiple of 4
    bne.s   1f
    btst    #1, %d0
    bne.s   1f
    move.w  %d0, stride_w
1:
.endif
    rts

| at_rc: %d0 = pixel row, %d1 = character column -> %a0 = framebuffer
| pointer. Reads ScrnBase itself so it is safe to call from C-entered
| code (which has no %a4 convention). Clobbers d0/d1.
at_rc:
    mulu.w  stride_w, %d0                  | row * stride (both < 65536)
    mulu.w  #CELL_BYTES, %d1
    add.l   %d1, %d0
    movea.l SCRNBASE.l, %a0
    adda.l  %d0, %a0
    rts

    .global paint_progress
| paint_progress(u32 idx, u32 total) — 4 hex digits at row 56, char
| column 32. Currently unused by bench_main (it paints its own tally
| through the C kernel), but it is declared extern there, so keep it
| callable AND ABI-correct: d2-d7/a2-a6 are callee-saved on m68k.
paint_progress:
    movem.l %d2-%d4/%a2-%a3, -(%sp)        | 20 bytes of saves
    move.w  #56, %d0
    moveq   #32, %d1
    bsr.w   at_rc
    move.l  20+4(%sp), %d3                 | idx (past saved regs + return addr)
    moveq   #3, %d4                        | 4 hex digits
.pp_loop:
    move.l  %d3, %d0
    rol.w   #4, %d0
    move.w  %d0, %d3
    andi.l  #0xF, %d0
    bsr.w   draw_glyph_d0
    dbra    %d4, .pp_loop
    movem.l (%sp)+, %d2-%d4/%a2-%a3
    rts

| draw_string_n_d0: paint (%d0)+1 consecutive 8-byte glyphs starting at
| (%a1) to (%a0), advancing both. Clobbers d0,d1,d2,a1,a2.
draw_string_n_d0:
    move.l  %d0, -(%sp)
1:  bsr.w   draw_glyph_a1
    subq.l  #1, (%sp)
    bpl.s   1b
    addq.l  #4, %sp
    rts

| draw_glyph_d0: paint hex_font glyph %d0. Clobbers d0,d1,d2,a1,a2.
draw_glyph_d0:
    lea     hex_font, %a1
    lsl.l   #3, %d0
    adda.l  %d0, %a1
    bra.w   draw_glyph_a1

| draw_glyph_a1: paint the 8-byte glyph at (%a1) to (%a0); advances
| %a1 by 8 and %a0 by one character cell. Clobbers d0,d1,d2,a2.
draw_glyph_a1:
    move.l  %a0, %a2                       | running scanline pointer
    moveq   #7, %d1                        | 8 glyph rows
.dg_row:
    move.b  (%a1)+, %d2                    | glyph row bitmap, bit 7 = leftmost
.ifdef DISPLAY_BPP8
    moveq   #7, %d0                        | 8 pixels, one byte each
.dg_col:
    add.b   %d2, %d2                       | shift bit 7 into carry
    bcs.s   .dg_on
    move.b  #0xFF, (%a2)+                  | background: black
    bra.s   .dg_next
.dg_on:
    clr.b   (%a2)+                         | stroke: white
.dg_next:
    dbra    %d0, .dg_col
    subq.l  #8, %a2                        | back to the start of this row
.else
    not.b   %d2                            | 1 bpp: strokes are 0 bits
    move.b  %d2, (%a2)
.endif
    adda.w  stride_w, %a2                  | next scanline
    dbra    %d1, .dg_row
    lea     CELL_BYTES(%a0), %a0           | advance the caller's cursor
    rts

    .section .rodata
banner:
    .byte 0x3C,0x42,0x40,0x40,0x40,0x42,0x3C,0x00   | C
    .byte 0x7C,0x42,0x42,0x7C,0x40,0x40,0x40,0x00   | P
    .byte 0x42,0x42,0x42,0x42,0x42,0x42,0x3C,0x00   | U
    .byte 0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00   | space
    .byte 0x7C,0x42,0x42,0x7C,0x42,0x42,0x7C,0x00   | B
    .byte 0x7E,0x40,0x40,0x7C,0x40,0x40,0x7E,0x00   | E
    .byte 0x42,0x62,0x52,0x4A,0x46,0x42,0x42,0x00   | N
    .byte 0x3C,0x42,0x40,0x40,0x40,0x42,0x3C,0x00   | C
    .byte 0x42,0x42,0x42,0x7E,0x42,0x42,0x42,0x00   | H

done_str:
    .byte 0x78,0x44,0x42,0x42,0x42,0x44,0x78,0x00   | D
    .byte 0x3C,0x42,0x42,0x42,0x42,0x42,0x3C,0x00   | O
    .byte 0x42,0x62,0x52,0x4A,0x46,0x42,0x42,0x00   | N
    .byte 0x7E,0x40,0x40,0x7C,0x40,0x40,0x7E,0x00   | E

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
