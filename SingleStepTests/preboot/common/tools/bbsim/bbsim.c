/* bbsim.c — run an assembled Mac boot block under Musashi against a
 * simulated Quadra 800 low-memory + DAFB framebuffer, so the paint
 * path can be validated without hardware or MAME.
 *
 * Simulates: 8 MB RAM, DAFB VRAM at $F9000000, ScrnBase/ScrnRow/
 * BootDrive/DrvQ low-mem globals, and a _Read ($A002) trap that
 * "succeeds" (the payload bytes are pre-placed in RAM by the harness,
 * standing in for the SCSI DMA).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m68k.h"

#define RAM_SIZE   0x00800000u
#define VRAM_BASE  0xF9000000u
#define VRAM_SIZE  0x00300000u

static unsigned char ram[RAM_SIZE];
static unsigned char vram[VRAM_SIZE];

static int trap_a_hits = 0, trap_f_hits = 0;

static unsigned char *xlat(unsigned int a, unsigned int len)
{
    if (a < RAM_SIZE && a + len <= RAM_SIZE) return ram + a;
    if (a >= VRAM_BASE && a + len <= VRAM_BASE + VRAM_SIZE) return vram + (a - VRAM_BASE);
    fprintf(stderr, "!! bus error: access 0x%08X len %u (PC=0x%08X)\n",
            a, len, m68k_get_reg(NULL, M68K_REG_PPC));
    exit(3);
}

unsigned int m68k_read_memory_8(unsigned int a)  { return *xlat(a,1); }
unsigned int m68k_read_memory_16(unsigned int a) { unsigned char*p=xlat(a,2); return (p[0]<<8)|p[1]; }
unsigned int m68k_read_memory_32(unsigned int a) { unsigned char*p=xlat(a,4); return ((unsigned)p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3]; }
unsigned int m68k_read_disassembler_16(unsigned int a){ return m68k_read_memory_16(a); }
unsigned int m68k_read_disassembler_32(unsigned int a){ return m68k_read_memory_32(a); }
void m68k_write_memory_8(unsigned int a, unsigned int v)  { *xlat(a,1)=(unsigned char)v; }
void m68k_write_memory_16(unsigned int a, unsigned int v) { unsigned char*p=xlat(a,2); p[0]=v>>8; p[1]=v; }
void m68k_write_memory_32(unsigned int a, unsigned int v) { unsigned char*p=xlat(a,4); p[0]=v>>24; p[1]=v>>16; p[2]=v>>8; p[3]=v; }

static void w8 (unsigned int a, unsigned int v){ ram[a]=v; }
static void w16(unsigned int a, unsigned int v){ ram[a]=v>>8; ram[a+1]=v; }
static void w32(unsigned int a, unsigned int v){ ram[a]=v>>24; ram[a+1]=v>>16; ram[a+2]=v>>8; ram[a+3]=v; }

int main(int argc, char **argv)
{
    if (argc < 3) { fprintf(stderr, "usage: bbsim <bootblock.bin> <payload.bin> [load_addr]\n"); return 1; }
    unsigned int base = (argc > 3) ? (unsigned int)strtoul(argv[3], NULL, 0) : 0x00090000u;

    /* boot block */
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 1; }
    size_t bb_len = fread(ram + base, 1, 1024, f); fclose(f);

    /* payload: pre-placed at $40000, standing in for the _Read's DMA */
    f = fopen(argv[2], "rb");
    if (!f) { perror(argv[2]); return 1; }
    size_t pay_len = fread(ram + 0x40000, 1, 0x40000, f); fclose(f);
    printf("boot block %zu bytes @ 0x%08X ; payload %zu bytes @ 0x00040000\n",
           bb_len, base, pay_len);

    /* --- Quadra 800 low memory the boot block reads --- */
    w32(0x0824, 0xF9001000);     /* ScrnBase  = DAFB VRAM + 4K */
    unsigned int scrnrow = (unsigned int)strtoul(getenv("SCRNROW") ? getenv("SCRNROW") : "1024", NULL, 0);
    w16(0x0106, scrnrow);        /* ScrnRow */
    w16(0x0210, 3);              /* BootDrive = 3 */
    w32(0x030A, 0x00003000);     /* DrvQHdr qHead -> our fake DrvQEl */
    w32(0x3000 + 0, 0);          /* qLink   = NULL */
    w16(0x3000 + 6, 3);          /* dQDrive = 3 (matches BootDrive) */
    w16(0x3000 + 8, 0xFFDF);     /* dQRefNum = -33 */

    /* --- trap stubs -------------------------------------------------
     * vector 10 (Line A) = the _Read trap: report noErr and step over
     * the trap word. vector 11 (Line F) catches the 68040 cache ops if
     * this Musashi build doesn't decode them — the simulation has no
     * caches, so skipping them is faithful. Both frames are format 0:
     * SR at 0(sp), PC at 2(sp), and the stacked PC points AT the
     * faulting instruction, so it must be advanced by 2. */
    unsigned int a_stub = 0x00004000, f_stub = 0x00004100;
    /* _Read stub: ioResult = noErr, step over the 2-byte trap word. */
    w16(a_stub+0, 0x4268); w16(a_stub+2, 0x0010);   /* clr.w   16(a0)  */
    w16(a_stub+4, 0x54AF); w16(a_stub+6, 0x0002);   /* addq.l  #2,2(sp) */
    w16(a_stub+8, 0x4E73);                          /* rte             */
    /* Line F stub: step over an undecoded 68040 cache op. */
    w16(f_stub+0, 0x54AF); w16(f_stub+2, 0x0002);   /* addq.l  #2,2(sp) */
    w16(f_stub+4, 0x4E73);                          /* rte             */
    w32(10*4, a_stub);
    w32(11*4, f_stub);

    /* reset vector */
    w32(0, 0x00010000);
    w32(4, base + 2);

    m68k_init();
    m68k_set_cpu_type(M68K_CPU_TYPE_68040);
    m68k_pulse_reset();
    m68k_set_reg(M68K_REG_PC, base + 2);
    m68k_set_reg(M68K_REG_SP, 0x00010000);  /* stands in for the ROM SP the block now inherits (finding 21) */

    /* Single-step so we can stop EXACTLY at the JMP into the payload —
     * the payload's first act is to wipe the screen, which would erase
     * the boot block's diagnostics before we can dump them. */
    unsigned int stop_at = (unsigned int)strtoul(getenv("STOP_AT") ? getenv("STOP_AT") : "0x40000", NULL, 0);
    long steps = 0;
    for (;;) {
        unsigned int pc = m68k_get_reg(NULL, M68K_REG_PC);
        if (pc == stop_at) { printf("-> stopped at 0x%08X after %ld instructions\n", pc, steps); break; }
        if (m68k_read_memory_16(pc) == 0x60FE) { printf("-> parked in halt spin at PC=0x%08X after %ld instructions\n", pc, steps); break; }
        if (++steps > 5000000) { printf("-> instruction budget exhausted at PC=0x%08X\n", pc); break; }
        m68k_execute(1);
    }
    printf("final PC=0x%08X D7(ioResult)=0x%08X D5(cksum)=0x%08X D4(drive)=0x%08X D6(refnum)=0x%08X\n",
           m68k_get_reg(NULL, M68K_REG_PC), m68k_get_reg(NULL, M68K_REG_D7),
           m68k_get_reg(NULL, M68K_REG_D5), m68k_get_reg(NULL, M68K_REG_D4),
           m68k_get_reg(NULL, M68K_REG_D6));
    printf("handoff $50000 = %02X%02X %02X%02X\n", ram[0x50000], ram[0x50001], ram[0x50002], ram[0x50003]);

    f = fopen("fb_dump.bin", "wb");
    fwrite(vram + 0x1000, 1, (size_t)scrnrow * 96, f);   /* 96 rows from ScrnBase */
    fclose(f);
    printf("wrote fb_dump.bin (96 rows x 1024 bytes)\n");
    return 0;
}
