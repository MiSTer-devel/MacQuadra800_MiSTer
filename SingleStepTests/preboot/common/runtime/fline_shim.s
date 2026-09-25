| fline_shim.s — F-line safety net for the OS-VBR I/O bracket.
|
| The ROM's SCSI _Write path executes 68040 cache/MMU ops the boot-time
| environment never needed for _Read: _BlockMove's 040 epilogue runs
| PTESTR + CPUSHL (copies < $C00) or CPUSHA BC (bigger), and its
| phase-matched copy loop is MOVE16. On the bench Quadra 800 an op in
| this family dies with vector 11 under the ROM's own table -> Sad Mac
| 0000000F/0000000A at the first results flush (test-blockers 20).
|
| Patching vector 11 of the LIVE table at $2C is not an option: ROM
| OS-trap code reads that slot as data and SysErrors dsFSErr ($1B) at
| the next flush when it changes (measured under MAME, finding 20). So
| install_fline_shim() (call AFTER install_vbr) builds a private
| forwarding table instead and repoints recovery.s's orig_vbr at it, so
| use_os_vbr() activates it during every I/O bracket:
|   vector 11               -> fline_thunk below
|   every other vector N    -> a 6-byte stub that jumps through the
|                              LIVE low-mem slot (N*4) at exception
|                              time, so runtime vector patching by the
|                              ROM/driver keeps working mid-transfer
| The thunk: emulates MOVE16 (A0)+,(A1)+; skips CINV/CPUSH ($F4xx) and
| PFLUSH/PTEST ($F5xx); paints "FLINE OP+PC" and halts readable for
| anything else. Every hit is counted so a completed run reports what
| fired. On MAME and QEMU the thunk is dormant (their 68040 executes
| all of these) and the stubs forward identically to the live table.
| Requires the ROM's VBR to be 0 (both emulators measure 0): if
| orig_vbr is nonzero the installer leaves everything alone.

    .text
    .global install_fline_shim
    .global g_shim_count
    .global g_shim_last_op
    .global g_shim_last_pc

    .data
    .align 4
g_shim_count:   .long 0
g_shim_last_op: .long 0     | low 16 bits = last opcode seen
g_shim_last_pc: .long 0
shim_ready:     .word 0

    .bss
    .align 4
fwd_table:      .space 1024     | 256 vectors, entry 11 = fline_thunk

    .text
| ---- forwarding stubs ------------------------------------------------
| One per vector 2..255, contiguous 6-byte entries: push the LIVE
| handler address from low memory, rts into it with the frame intact.
    .altmacro
    .macro FWDSTUB n
    move.l  (\n*4).w, -(%sp)
    rts
    .endm
fwd_stubs:
    .set i, 2
    .rept 254
    FWDSTUB %i
    .set i, i+1
    .endr

| ---- install_fline_shim ---------------------------------------------
| Requires recovery.s's install_vbr to have captured orig_vbr already.
| SHIM_NO_INSTALL (--defsym): keep the code linked but never activate —
| an A/B lever for isolating layout effects from the table swap.
install_fline_shim:
    .ifdef SHIM_NO_INSTALL
    rts
    .endif
    movem.l %d0/%a0-%a1, -(%sp)
    tst.w   shim_ready
    bne     9f
    tst.l   orig_vbr                | stubs assume the live table is at 0
    bne     9f
    movea.l orig_vbr, %a0
    lea     fwd_table, %a1
    move.l  (%a0), (%a1)            | reset SP/PC entries, never vectored
    move.l  4(%a0), 4(%a1)
    lea     fwd_stubs, %a0
    lea     8(%a1), %a1
    move.w  #253, %d0               | vectors 2..255
1:  move.l  %a0, (%a1)+
    addq.l  #6, %a0
    dbra    %d0, 1b
    lea     fwd_table, %a1
    move.l  #fline_thunk, 44(%a1)   | vector 11 only diverges
    move.l  %a1, orig_vbr           | use_os_vbr() now lands on our table
    move.w  #1, shim_ready
9:  movem.l (%sp)+, %d0/%a0-%a1
    rts

| ---- fline_thunk -----------------------------------------------------
| After the movem, the exception frame sits at 16(sp):
|   16(sp) SR.w   18(sp) PC.l   22(sp) format/vector.w
| Format 0 stacks the PC of the faulting instruction itself.
fline_thunk:
    movem.l %d0-%d1/%a0-%a1, -(%sp)
    move.w  22(%sp), %d0
    andi.w  #0xF000, %d0
    bne     .Lnofetch               | non-format-0 frame: report, halt
    movea.l 18(%sp), %a0            | fault PC
    move.w  (%a0), %d0              | faulting opcode
    move.l  %a0, g_shim_last_pc
    moveq   #0, %d1
    move.w  %d0, %d1
    move.l  %d1, g_shim_last_op
    addq.l  #1, g_shim_count
    move.w  %d0, %d1
    andi.w  #0xFFF8, %d1
    cmpi.w  #0xF620, %d1
    beq     .Lmove16
    move.w  %d0, %d1
    andi.w  #0xFF00, %d1
    cmpi.w  #0xF400, %d1
    beq     .Lskip2                 | CINV/CPUSH (all one word)
    move.w  %d0, %d1
    andi.w  #0xFF80, %d1
    cmpi.w  #0xF500, %d1
    beq     .Lskip2                 | PFLUSH/PTEST (all one word)
    bra     .Lunknown

.Lmove16:
    | Only the (A0)+,(A1)+ form _BlockMove uses; anything else reports.
    cmpi.w  #0xF620, %d0
    bne     .Lunknown
    move.w  2(%a0), %d1
    cmpi.w  #0x9000, %d1
    bne     .Lunknown
    | Both addresses are forced 16-byte aligned; regs advance by 16.
    move.l  8(%sp), %d0             | interrupted A0 (source)
    andi.l  #0xFFFFFFF0, %d0
    movea.l %d0, %a0
    move.l  12(%sp), %d1            | interrupted A1 (destination)
    andi.l  #0xFFFFFFF0, %d1
    movea.l %d1, %a1
    move.l  (%a0)+, (%a1)+
    move.l  (%a0)+, (%a1)+
    move.l  (%a0)+, (%a1)+
    move.l  (%a0), (%a1)
    addi.l  #16, 8(%sp)
    addi.l  #16, 12(%sp)
    addq.l  #4, 18(%sp)             | past opcode + extension word
    bra     .Lresume

.Lskip2:
    addq.l  #2, 18(%sp)
.Lresume:
    movem.l (%sp)+, %d0-%d1/%a0-%a1
    rte

.Lnofetch:
    addq.l  #1, g_shim_count
    move.w  #0xFFFF, %d0            | sentinel: frame format wasn't 0
    movea.l 18(%sp), %a0
.Lunknown:
    | Un-emulatable: paint the evidence and halt with the screen alive.
    | Args: (op, pc, fmt/vec word, frame address) — computed pre-push.
    move.w  22(%sp), %d1
    andi.l  #0xFFFF, %d1
    lea     16(%sp), %a1
    move.l  %a1, -(%sp)
    move.l  %d1, -(%sp)
    move.l  %a0, -(%sp)
    moveq   #0, %d1
    move.w  %d0, %d1
    move.l  %d1, -(%sp)
    jsr     fline_shim_report
0:  bra.s   0b
