#include "freestanding.h"

/* Terminal reporter for fline_shim.s: paint the un-emulatable fault where
 * a photo can read it; the asm halts after we return. Rows 40..88 are
 * free during the corpus run (header 4, test 16, tally 28).
 *
 *   row 40  FLINE OP+PC: oooo pppppppp      opcode ($FFFF = non-format-0
 *                                           frame) + stacked PC
 *   row 52  FV=ffff FR=ffffffff EA=eeeeeeee frame fmt/vec word, frame
 *                                           address, format-2 EA field
 *   row 64  M-: 8 bytes at PC-8             the instruction bytes
 *   row 76  M+: 8 bytes at PC               (guarded; "--" if unmapped)
 *   row 88  RA: up to 3 code-looking longs  poor-man's backtrace scanned
 *                                           from the exception frame     */

extern void paint_string(u32 row, u32 col_byte, const char *s, u32 max_chars);

static char hexc(u32 v) { return (char)(v < 10 ? '0' + v : 'A' + v - 10); }

static char *put_hex(char *p, u32 v, u32 digits)
{
    u32 i;
    for (i = 0; i < digits; i++) *p++ = hexc((v >> (4 * (digits - 1 - i))) & 0xF);
    return p;
}

/* Readable without faulting inside the handler: low/driver RAM or ROM. */
static int mem_ok(u32 a)
{
    if (a >= 0x00001000 && a < 0x007FFFF0) return 1;
    return a >= 0x40800000 && a < 0x408FFFF0;
}

static int code_like(u32 v)
{
    if (v >= 0x40800000 && v < 0x40900000) return 1;   /* ROM */
    return v >= 0x00002000 && v < 0x00040000;          /* RAM driver/glue */
}

void fline_shim_report(u32 op, u32 pc, u32 fmtvec, u32 frame)
{
    char buf[40];
    char *p;
    u32 i, n;

    p = buf; p = put_hex(p, op, 4); *p++ = ' '; p = put_hex(p, pc, 8); *p = 0;
    paint_string(40, 4, "FLINE OP+PC:", 12);
    paint_string(40, 17, buf, 13);

    p = buf; p = put_hex(p, fmtvec, 4);
    *p++ = ' '; *p++ = 'F'; *p++ = 'R'; *p++ = '=';
    p = put_hex(p, frame, 8);
    *p++ = ' '; *p++ = 'E'; *p++ = 'A'; *p++ = '=';
    if ((fmtvec & 0xF000) == 0x2000 && mem_ok(frame + 8))
        p = put_hex(p, *(u32 *)(frame + 8), 8);
    else
        { for (i = 0; i < 8; i++) *p++ = '-'; }
    *p = 0;
    paint_string(52, 4, "FV=", 3);
    paint_string(52, 7, buf, 28);

    for (n = 0; n < 2; n++) {
        u32 base = pc - 8 + 8 * n;
        p = buf;
        for (i = 0; i < 8; i++) {
            if (mem_ok(base + i)) p = put_hex(p, *(u8 *)(base + i), 2);
            else { *p++ = '-'; *p++ = '-'; }
            *p++ = ' ';
        }
        *p = 0;
        paint_string(64 + 12 * n, 4, n ? "M+:" : "M-:", 3);
        paint_string(64 + 12 * n, 8, buf, 24);
    }

    p = buf;
    for (i = 8, n = 0; i < 256 && n < 3; i += 2) {
        u32 v;
        if (!mem_ok(frame + i) || !mem_ok(frame + i + 3)) break;
        v = *(u16 *)(frame + i);
        v = (v << 16) | *(u16 *)(frame + i + 2);
        if (code_like(v)) { p = put_hex(p, v, 8); *p++ = ' '; n++; }
    }
    *p = 0;
    paint_string(88, 4, "RA:", 3);
    paint_string(88, 8, buf, 27);
}
