/* amiga_gate.c — the wombat33 Amiga disks support the 68040 ONLY.
 *
 * Checks, all before any test runs (which apply depends on the suite):
 *   1. ExecBase->AttnFlags has AFB_68040 (exec already probed the CPU).
 *   2. -DGATE_NEED_FPU (fpu / saverestore / integration disks):
 *      AttnFlags has AFB_FPU40 — a 68LC040 has no FPU.
 *   3. -DGATE_NEED_MMU (mmu disks): a MOVEC from TC actually executes
 *      (run under the recovery handler) — a 68EC040 has no MMU and
 *      traps instead, as does an RTL core without the MMU wired up.
 *
 * Cache flush: raw CPUSHA BC. The Mac's _HwPriv rule (findings 16/25)
 * is about the Quadra ROM environment; on a bare-boot Amiga the MMU is
 * off (no 68040.library) and CPUSHA is legal on every 040 variant in
 * supervisor mode. NO MOVEC to CACR anywhere — the 68020-era idiom
 * disables the 040 caches (finding 25).
 *
 * Returns 0 = proceed; nonzero = refused (verdict painted on screen,
 * caller hangs). The results region stays empty on refusal — host-side
 * absence of rows is the machine-readable signal. */

#include "bench_types.h"

extern u8  *g_amiga_execbase;
extern void install_vbr(void);
extern int  invoke_test_with_recovery(u8 *entry);
extern void paint_string(u32 row, u32 col_byte, const char *s, u32 max_chars);
extern void display_wipe(u32 rows);
extern void amiga_diag_marker(u32 slot, u32 tag);

#define ATTNFLAGS_OFF 0x128
#define AFF_68040     (1u << 3)
#define AFF_FPU40     (1u << 6)

static u32 g_probe_scratch __attribute__((unused));
static u8  g_probe_prog[16] __attribute__((unused));

static void flush_caches(void) __attribute__((unused));
static void flush_caches(void)
{
    asm volatile (".short 0xF4F8 \n nop" : : : "memory");   /* CPUSHA BC */
}

int amiga_gate(void)
{
    u16 attn = *(volatile u16 *)(g_amiga_execbase + ATTNFLAGS_OFF);

    /* Recovery vectors FIRST: every disk-marker/jsonl bracket flips
     * between the OS VBR and ours, so ours must be real before any
     * bracket runs. (Idempotent — bench_main calls it again.) */
    install_vbr();

    display_wipe(480);
    paint_string(4, 4, "68040 TEST DISK (wombat33_MiSTer)", 40);
    amiga_diag_marker(2, 0x47415430u);   /* 'GAT0' — bracket works */

    amiga_diag_marker(4, 0x41544E00u | attn);   /* 'ATN' + flags */
    if (!(attn & AFF_68040)) {
        paint_string(16, 4, "REFUSED: this disk requires a 68040", 40);
        paint_string(24, 4, "(AttnFlags has no 68040 bit)", 40);
        return 1;
    }

#ifdef GATE_NEED_FPU
    if (!(attn & AFF_FPU40)) {
        paint_string(16, 4, "REFUSED: 68040 FPU required (not LC040)", 40);
        paint_string(24, 4, "(AttnFlags has no FPU40 bit)", 40);
        return 2;
    }
#endif

#ifdef GATE_NEED_MMU
    {
        /* MOVEC TC,D0 ; MOVE.L D0,(abs).L ; RTS — takes an exception on
         * a 68EC040 (or an RTL core without the MMU register file). */
        u8 *p = g_probe_prog;
        u32 dst = (u32)&g_probe_scratch;
        int vec;
        amiga_diag_marker(5, 0x56425249u);          /* 'VBRI' */
        *p++ = 0x4E; *p++ = 0x7A;
        *p++ = 0x00; *p++ = 0x03;                   /* movec %tc,%d0 */
        *p++ = 0x23; *p++ = 0xC0;                   /* move.l %d0,(abs).l */
        *p++ = (u8)(dst >> 24); *p++ = (u8)(dst >> 16);
        *p++ = (u8)(dst >> 8);  *p++ = (u8)dst;
        *p++ = 0x4E; *p++ = 0x75;                   /* rts */
        flush_caches();
        vec = invoke_test_with_recovery(g_probe_prog);
        asm volatile ("move.w #0x2700, %%sr" : : : "memory");
        amiga_diag_marker(6, 0x56454300u | (u32)(vec & 0xFF));  /* 'VEC'+n */
        if (vec != 0) {
            paint_string(16, 4, "REFUSED: 68040 without working MMU", 40);
            paint_string(24, 4, "(MOVEC TC took an exception)", 40);
            return 3;
        }
    }
#endif

    paint_string(16, 4, "gate: 68040 present", 40);
    amiga_diag_marker(3, 0x47415445u);   /* 'GATE' — gate passed */
    return 0;
}
