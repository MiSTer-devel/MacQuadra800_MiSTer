#include "jsonl_writer.h"
#include "freestanding.h"

/* IOParam offsets (Inside Macintosh: Files) */
#define PB_OFF_IORESULT     16
#define PB_OFF_IOVREFNUM    22
#define PB_OFF_IOREFNUM     24
#define PB_OFF_IOBUFFER     32
#define PB_OFF_IOREQCOUNT   36
#define PB_OFF_IOACTCOUNT   40
#define PB_OFF_IOPOSMODE    44
#define PB_OFF_IOPOSOFFSET  46
#define PB_SIZE             80

static u8 g_pb[PB_SIZE];

#ifdef JW_BACKEND_EXTERN
/* Platform-provided batch writer (e.g. Amiga trackdisk.device). Same
 * contract as the Mac _Write path below: write JW_BATCH_BYTES from buf
 * to ctx->base_offset + sector_idx*JW_BATCH_BYTES; return 0 on ok. */
extern i16 jw_backend_write(const JwCtx *ctx, u32 sector_idx, const u8 *buf);
#define driver_write_sector jw_backend_write
#else
/* recovery.s I/O bracket: flip the WHOLE vector base between our table
 * and the OS/ROM original. The Quadra 800 SCSI driver takes traps and
 * faults of its own while servicing an interrupt-driven DMA _Write; with
 * the bench VBR active those would hijack our recovery stubs (vectors
 * 2..9, 11..15, 32..47) and longjmp out of the write, corrupting it.
 * Running _Write under the OS VBR puts it in the exact environment the
 * boot block's _Read (which works) runs in. Declared weak so benches that
 * don't link recovery.o (iotest/keytest) just skip the bracket. */
extern void use_os_vbr(void)       __attribute__((weak));
extern void use_recovery_vbr(void) __attribute__((weak));

/* Single-sector _Write at byte offset (ctx.base_offset + sector_idx * 512).
 * Returns ioResult (0 = noErr). Inline asm calls $A003 _Write.
 * Batches above 16 KB are sliced into 16 KB driver requests (see the
 * JW_BATCH_BYTES note below) by the wrapper at the end of this block. */
static i16 driver_write_chunk(const JwCtx *ctx, u32 byte_off, const u8 *buf, u32 len)
{
#ifdef JW_NO_WRITE
    /* Diagnostic build: skip the SCSI _Write entirely so we can confirm
     * whether the bench freeze is the disk write (runs to completion with
     * this defined => yes) or a CPU hang in a test (still freezes => no). */
    (void)ctx; (void)byte_off; (void)buf; (void)len;
    return 0;
#else
    u8 *pb = g_pb;
    u32 i;
    for (i = 0; i < PB_SIZE; i++) pb[i] = 0;
    *(i16 *)(pb + PB_OFF_IOREFNUM)   = ctx->refnum;
    *(i16 *)(pb + PB_OFF_IOVREFNUM)  = ctx->drive;
    *(u32 *)(pb + PB_OFF_IOBUFFER)   = (u32)buf;
    *(u32 *)(pb + PB_OFF_IOREQCOUNT) = len;
    *(i16 *)(pb + PB_OFF_IOPOSMODE)  = 1;     /* fsFromStart */
    *(u32 *)(pb + PB_OFF_IOPOSOFFSET) = byte_off;

    /* 68040 cache coherency: the buffer and param block were filled
     * through the copyback data cache, but the Quadra 800's SCSI does
     * DMA from PHYSICAL RAM — without pushing the data cache first, the
     * DMA reads stale/zero RAM (writes zeros) and can wedge the driver.
     * CPUSHA DC ($F478) pushes all dirty data lines to RAM + invalidates.
     * (The Mac II this code came from is a 68020 with no copyback cache,
     * so it never needed this.) */
    /* Raw CPUSHA faults on real Quadra 800 silicon (finding 16); the ROM
     * call is verified working on hardware. Clobbers D0/A0. */
    asm volatile ("moveq #1,%%d0 \n .short 0xA198"
                  : : : "d0", "a0", "a1", "d1", "d2", "memory");

    /* Restore the OS/ROM VBR so the SCSI driver's own traps/faults +
     * completion IRQ are serviced by the ROM (not our recovery stubs),
     * then switch back to our table. IPL stays at the bench's level (the
     * boot block's _Read runs masked and works, so the driver polls or
     * lowers IPL itself). */
    if (&use_os_vbr) use_os_vbr();
    /* IPL stays masked. Lowering it across the trap was tried and is a
     * regression: MAME then hangs at the first flush (test 58). */
    asm volatile (
        "movel %0, %%a0   \n"
        ".short 0xA003    \n"   /* _Write */
        :
        : "g" (pb)
        : "a0", "a1", "d0", "d1", "d2", "cc", "memory"
    );
    if (&use_recovery_vbr) use_recovery_vbr();

    return *(i16 *)(pb + PB_OFF_IORESULT);
#endif
}

static i16 driver_write_sector(const JwCtx *ctx, u32 sector_idx, const u8 *buf)
{
    u32 base = ctx->base_offset + sector_idx * JW_BATCH_BYTES;
    u32 off = 0;
    while (off < JW_BATCH_BYTES) {
        u32 len = JW_BATCH_BYTES - off;
        if (len > 16384) len = 16384;
        i16 r = driver_write_chunk(ctx, base + off, buf + off, len);
        if (r != 0) return r;
        off += len;
    }
    return 0;
}
#endif /* JW_BACKEND_EXTERN */

void jw_init(JsonlWriter *w, const JwCtx *ctx)
{
    f_memset(w, 0, sizeof(*w));
    w->ctx = *ctx;
}

/* Internal: write the current batch (zero-padding any unused tail) to
 * disk at base_offset + batch_idx*JW_BATCH_BYTES. Caller decides
 * whether to advance `written` to start a new batch (true flush) or
 * leave it alone (partial-progress commit). */
static void write_current_batch(JsonlWriter *w)
{
    if (w->used < JW_BATCH_BYTES)
        f_memset(w->sector + w->used, 0, JW_BATCH_BYTES - w->used);
    u32 batch_idx = w->written / JW_BATCH_BYTES;
    i16 r = driver_write_sector(&w->ctx, batch_idx, w->sector);
    if (r != 0 && w->last_err == 0) w->last_err = r;
}

#if JW_BATCH_BYTES > 16384
/* Big-batch builds only: a single pre-System _Write above 16 KB drives
 * the ROM Device Manager into a queued path whose low-mem structures
 * are still boot-fill ($FFFFFFFF) -> Enqueue faults -> Sad Mac. Slice
 * every batch into <=16 KB requests, the size every bench has proven. */
#endif

static void flush_sector(JsonlWriter *w)
{
    /* Full advance: write the batch then move to the next one. */
    write_current_batch(w);
    w->written += JW_BATCH_BYTES;
    w->used = 0;
}

void jw_putc(JsonlWriter *w, char c)
{
    if (w->written + w->used >= w->ctx.max_bytes) return;  /* full */
    w->sector[w->used++] = (u8)c;
    if (w->used == JW_BATCH_BYTES) flush_sector(w);
}

void jw_puts(JsonlWriter *w, const char *s)
{
    while (*s) jw_putc(w, *s++);
}

void jw_putul(JsonlWriter *w, u32 v)
{
    char tmp[12];
    char *t = f_putul(tmp, v);
    char *p;
    for (p = tmp; p < t; p++) jw_putc(w, *p);
}

/* Write the current batch to disk without advancing `written`.
 *
 * Each call costs one full JW_BATCH_BYTES (16 KB) SCSI write. The cost
 * buys us per-record persistence: if the bench hangs partway through a
 * size sweep, every JSONL line emitted before the hang is on disk and
 * can be extracted post-mortem via `rb-cli get IMG@1 /Results.jsonl`.
 *
 * The advance-on-full path (flush_sector) is unchanged; once the
 * batch fills, it gets written and `written` advances normally. So
 * this scheme degrades to ~1 commit per record while a batch is
 * actively being filled, plus the usual one-write-per-full-batch.
 * For a 24-record iotest run that's 24 writes of 16 KB = 384 KB,
 * negligible compared to the bench's read/write traffic. */
void jw_commit_line(JsonlWriter *w)
{
    if (w->used == 0) return;  /* nothing new since last commit */
    write_current_batch(w);
}

void jw_flush(JsonlWriter *w)
{
    if (w->used > 0) flush_sector(w);
}
