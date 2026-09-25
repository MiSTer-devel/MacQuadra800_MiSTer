| payload_entry_sim.s — entry shim for RTL-simulation runs of the bench
| (AP68040 or any 68040 core in a flat-RAM testbench). The TB resets the
| core with SP/PC vectors pointing here (payload linked at $40000 via
| the shared payload.ld). No OS, no disk: results go straight to RAM
| (jsonl_sim.c) and the TB dumps them; DONE is a doorbell write the TB
| watches. Display paints into a .bss buffer nobody renders.

DOORBELL     = 0x00F00000
RESULTS_BASE = 0x00100000

    .text
    .global _payload_start
_payload_start:
    move.w  #0x2700, %sr
    move.l  #0x00080000, %sp

    | zero .bss (finding 15)
    lea     _payload_bss_start, %a0
    lea     _payload_bss_end, %a1
1:  cmp.l   %a1, %a0
    bcc.s   2f
    clr.l   (%a0)+
    bra.s   1b
2:
    lea     sim_fb, %a0
    move.l  %a0, g_display_fb

.ifdef SIM_MMU_WORLD
    | Point URP/SRP at the TB's identity page tables (Quadra-equivalent
    | handoff state): the corpus's safe MOVEC TC row enables translation
    | and needs a walkable world (finding 30).
    move.l  #0x003FE000, %d0
    .short  0x4E7B, 0x0806                | movec d0,urp
    .short  0x4E7B, 0x0807                | movec d0,srp
.endif

    jsr     bench_main

    move.w  #0x600D, (DOORBELL).l         | DONE — TB dumps results + exits
.hang:
1:  bra.s   1b

    .data
    .align 4
    .global g_handoff_refnum
    .global g_handoff_drive
    .global g_results_offset
    .global g_results_max_bytes
| Mac-compat handoff fields referenced by the shared runners (unused here).
g_handoff_refnum:    .word 0
g_handoff_drive:     .word 0
| The sim backend treats base_offset as a RAM ADDRESS, not a disk offset.
g_results_offset:    .long RESULTS_BASE
g_results_max_bytes: .long 409600

    .bss
    .align 4
sim_fb: .space 480*80
