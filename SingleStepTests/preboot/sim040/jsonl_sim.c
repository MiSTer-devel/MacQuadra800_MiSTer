/* jsonl_sim.c — RTL-simulation backend for the shared JsonlWriter
 * (jsonl_writer.c with -DJW_BACKEND_EXTERN): each batch is copied
 * straight into a RAM window (ctx->base_offset is a RAM address here)
 * that the testbench dumps to a host file at the DONE doorbell. */

#include "bench_types.h"
#include "jsonl_writer.h"

i16 jw_backend_write(const JwCtx *ctx, u32 batch_idx, const u8 *buf)
{
    u8 *dst = (u8 *)(ctx->base_offset + batch_idx * JW_BATCH_BYTES);
    u32 i;
    for (i = 0; i < JW_BATCH_BYTES; i++)
        dst[i] = buf[i];
    return 0;
}
