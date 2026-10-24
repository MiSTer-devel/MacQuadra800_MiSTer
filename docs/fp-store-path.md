# The dual core's FP store path: where the 11 clocks go (2026-10-24)

The attribution ([fp-gap-attribution.md](fp-gap-attribution.md)) left one
question open: of the 11 clocks a `fmove.d fpN,<ea>` costs on the
dual-issue core (`rtl/ap68040_faster`, against 7.0-7.5 on the shipping
core), how much is the FPU and how much the DMU store engine.  This note
answers it from a cycle-by-cycle trace of the instruction on both cores'
standalone benches, and says what the smallest RTL change would be.  The
kernels, bench probes, raw traces and annotated per-cycle tables are under
[`docs/perf/fp_store_trace_20261024/`](perf/fp_store_trace_20261024/README.md);
nothing under `rtl/` was changed and nothing was built for hardware.

## The path

A register-to-memory FMOVE is microcode routine `FPU_K_OUT8` (`FPU_K_OUT4`
/ `FPU_K_OUT12` for single / extended; `rtl/ap68040_faster/tools/ucode.py`):

1. **CHK+EAL** -- an `OP_FPU` uop.  At AG the operand address goes to T11
   (`FEA`); at EX the FPU interface (`ap68040_fpif.sv`) checks the encoding,
   latches the two instruction words, and may act only when it is the
   oldest uop in flight (`safe`: WB empty, or holding an earlier uop of the
   same instruction) so that no FPU side effect is ever taken back.
2. **DISP d=T0** -- the FPU request.  fpif registers `f_req`; the FPU
   (`fpu/ap040_fpu.v`) sees it in F_IDLE, unpacks the source register into
   its operand register and goes to F_SRC; F_SRC rounds to the destination
   format (`sd_out`), sets INEX in FPSR if any, and registers `done` and
   `dout`; fpif registers `done_q` and `get_q`; `done_q` releases the
   uop, whose result is the high long word.
3. **GET const=1 d=T1** -- the low long word out of `get_q` (an `OP_FPU`
   uop that needs no `safe`).  Extended adds a second GET.
4. **MOV S** x2 (x1 / x3) -- ordinary store uops, T0 to (T11), T1 to
   (T11+4), through AG / DC1 (ATC and tag lookup) / DC2 / EX / WB; a
   copyback hit is a **WB fast store** (`ap68040_dmu.sv` `wb_fast`): the
   data RAM is written the cycle after WB and `st_rdy` comes in WB's own
   cycle.
5. **END ag=FUPD last** -- the (An)+/-(An) update at AG; raises the store's
   exception, if the FPU reported one, after the writes; needs no `safe`
   when nothing is pending.

## The 11 clocks, cycle by cycle

Dual core, steady state of back-to-back `fmove.d fp0,(a0)+` (copyback hit,
user mode, FPCR enables clear; `perf/fp_store_trace_20261024/traces/new_0x20_fmove_d_a0inc.txt`,
one instruction = cycles 4257-4267):

| cyc | EX holds | why the cycle is spent | class |
|---:|---|---|---|
| 1 | CHK (held) | the previous instruction's END is retiring from WB; CHK waits for `safe` | serialization |
| 2 | CHK | checks pass, words latched, leaves | FPU-interface uop |
| 3 | DISP (held) | fpif registers the request (`f_req`) | handshake register |
| 4 | DISP (held) | FPU F_IDLE sees the request, unpacks FP0, `fst <= F_SRC` | FPU dispatch state |
| 5 | DISP (held) | FPU F_SRC: the extended-to-double rounding, `done`/`dout` registered | FPU conversion |
| 6 | DISP (held) | fpif registers `done_q`/`get_q` | handshake register |
| 7 | DISP | `done_q` clears the hold; high long word to T0 | handshake register |
| 8 | GET | low long word to T1 | FPU-interface uop |
| 9 | MOV S (T0) | first store's EX cycle | store uop |
| 10 | MOV S (T1) | second store's EX cycle; the first retires at WB as a fast store, no hold | store uop |
| 11 | END | the An update; nothing pending | FPU-interface uop |

**Split: FPU proper 2** (dispatch state + one conversion cycle),
**fpif/backend handshake 3** (a register before the FPU and two after it),
**FPU-interface uops 3** (CHK, GET, END), **DMU stores 2** (one EX slot
each, zero stall: the tag check happened at DC1, the data write is hidden
behind WB), **serialization 1** (CHK behind the older instruction's last
uop).  The DMU is not the problem: an integer `move.l d1,(a0)+` costs 0.99
clk on this core and the FP store's two writes cost exactly two of those.
The formats confirm the shape: `fmove.s` 9 (no GET, one store), `fmove.x`
13 (two GETs, three stores) -- 7 + 2 per long word.  A following integer
instruction adds its own EX cycle (`fmove.d ; addq` = 12): nothing of the
store overlaps with it.

The shipping core (`traces/old_0x20_*`, 7 cycles): S_FPU_DEC 1 (decode and
dispatch, `fpu_req` registered), S_FPU_GO 2 (the FPU packs a normal
register value and raises `done` **in the request cycle** -- its
"P222/P255 dispatch-clock store", `rtl/ap68040/rtl/ap040_fpu.v` ~1187-1210
-- and the first write is issued from the `done` cycle), then 2 per long
word (S_MWR, S_FPU_WR): 3 + 2 per long word (5 / 7 / 9).  The writes go
to the bus through the store buffer and keep up at this rate.  So the two
cores pay the same per long word; the dual core's whole deficit is its
base: 8 cycles (safe wait, CHK, five DISP cycles, END) against 3.  Of the
five DISP cycles the FPU's own work is one; the shipping FPU does that
work in the request cycle and `ap040_core` has one register in the
handshake where fpif has three.

Serialization beyond the `safe` cycle: after a register operation the
store's CHK also waits for the background op (`bg && !f_end`): in `fadd.x
fp1,fp0 ; fmove.d fp0,(a0)+` the pair costs 17 (FADD 5 in EX, store 12 =
one extra wait), the shipping core 11 (4 + 7).  With `FPU_PIPE=1` the FPU
itself defers a store request while its pipeline is busy (`req_pend`
while `pbusy`): the attribution's 14.

## FMOVEM: eight slots whatever the list

`fmovem.x fp0-fp1,-(a7)` costs 79 because routine `FPU_MVS` has **eight
static register slots and runs all of them**: per slot MVR 2 (the raw
read port's set-up cycle, then the read), GET 2, three stores 3, the T11
step 1 = 8 cycles; slots not in the list have their stores cancelled at
AG (`dyn`) but the cancelled uops still take an EX cycle each and the
MVR/GET/step run in full.  13 cycles of set-up (the `FPU_GEN` jump words,
LIST, an AG interlock on LIST's byte count) + 8 x 8 + 2 = 79; a
one-register push costs the same.  The pop is 13 + 8 x 5 + 2 = 55.  The
shipping core iterates over the listed registers only: 8 per register
pushed, 5 popped (18 / 11 for two).  The "8-13 clocks per long word" of
the attribution was 8 cycles per slot spread over the six long words
actually stored.

## The minimal change

Four local changes, each independent, take `fmove.d` from 11 to the
shipping core's 7 without touching the store engine or the exception
model.  Listed smallest first; cycles saved are for `fmove.d`.

1. **Take `done` live in fpif** (-1): hold the store DISP on `!(done_q ||
   f_done)` instead of `!done_q`; `res` already muxes `f_dout` directly,
   and `done_q`/`get_q` stay for the GET and for a `done` pulse that EX
   cannot consume because WB stalls.  No area; `f_done` is a flop, the
   hold path keeps its depth.
2. **Port the shipping FPU's dispatch-clock store** (P222/P255) into the
   dual FPU's F_IDLE opclass-011 branch (-1): a raw extended store, and a
   single/double store of a normal register value that neither overflows
   nor denormalizes and whose inexactness, if any, is not an enabled
   exception, produce `dout` and `done` in the request cycle; everything
   else keeps the F_SRC / F_SHR / F_STDONE paths.  The
   dual FPU's `sd_out` rounder is driven from the operand register; it
   needs its input muxed from the register-file read in F_IDLE (the
   `unpack_x` F_IDLE already computes): ~100-150 ALMs, more if the rounder
   is duplicated instead.  The conditions are the shipping core's,
   corpus-validated there (`rtl/ap68040/tb/run_tests.sh` legs).
3. **Issue the request as the DISP enters EX** (-1): register `f_req` from
   the DC2-to-EX transfer, as `dw_ld` already registers CHK's decode "of
   the uop EX has next" and as `n_srcr`/`n_class` already pre-select the
   FPU's ready flags a cycle ahead.  Allowed only when the DISP's sole
   older uop is its own instruction's CHK that has just acted (then no
   older fault or interrupt boundary can intervene -- the condition
   `wb_fpchk` already expresses).  `kill` clears `go` today; `done_q` must
   be cleared with it.  Small area; it touches the stall chain, so the
   timing at 33 MHz is the thing to check.
4. **Drop the GET uops** (-1 for double, -2 for extended, -2 per FMOVEM
   slot): a store-operand selector that reads the fpif's `get_q` long
   words at EX, so `MOV S` 2 and 3 take their data from the FPU's latched
   result instead of T1/T2 (the fpif's FC_GET result is already just that
   mux).  A 32-bit 3:1 mux on the store data plus two uop bits: ~50 ALMs.
   In order, no exception interaction: the data is final once DISP left EX.

Result with all four: `fmove.s` 6 (shipping 5), `fmove.d` 7 (7),
`fmove.x` 8 (9); on the attribution's kernels that is the whole FP-store
share (1.9 % Whetstone, 5.4 % matmul, 10.8 % FFT).  Total area ~150-250
ALMs on a ~20,000-ALM CPU; the fit is a seed walk as always.

Risks.  Ordering: none -- every consumer of the store data is a younger
uop of the same instruction, and the stores still retire in order through
WB.  Exceptions: an FP store's operand error / SNAN (integer formats) or
inexact / overflow / underflow (float formats) is reported by the FPU
before the memory write and raised by END after it (post-instruction,
format $3, as today); the fast path is taken only when none is possible
(enables clear, normal in-range value), so the exception path is the
unchanged slow one.  Precise state: the FPSR INEX update moves one cycle
earlier inside the same DISP residency, with `safe` still true; FSAVE
frames are untouched.  Change 3 is the one with a speculation argument
and a stall-chain timing cost; changes 1, 2 and 4 have neither.

Further, not minimal: fold END into the last store (-1; the store's own
access error, known after WB, must then precede the FPU's post-instruction
exception), fuse CHK with DISP as `FPU_RRF` does for register operands
(-1), relax CHK's `safe` for stores (-1; it guards `pend` consumption and
FPIAR writes) -- 4 cycles is the floor without them, 3 with.  With
`FPU_PIPE=1` the store should go *into* the pipeline (an FMOVE whose
destination is the `dout` latch) rather than wait for it to drain; that
is the change that would stop the pipeline costing stores 3 clocks.

**FMOVEM** needs a different change: let the D2 sequencer expand the slot
group once per register in a *static* list (the mechanism integer MOVEM
uses, "repeats a MOVEM micro-instruction once per register in the
mask"), keeping the 8-slot routine for the dynamic (Dn) list.  With change
4 a slot is MVR 2 + 3 stores + step = 6 (5 if the next slot's register is
selected while the current one stores); a two-register push 79 -> ~27
(shipping 18), pop 55 -> ~25 (11); a direct `FPU_K_MVM` routine for the
static forms and the list's byte count as an immediate would take most of
the 13-cycle set-up as well.  ~100-200 ALMs in the sequencer.  Risk: the
slot-to-register order (`mv_lsb`/`mv_rev`) and the `dyn` cancel stay as
they are; An is updated only at END, so a mid-instruction access error
restarts the instruction as today.  On Whetstone this is worth roughly
60 % of the 15 % FMOVEM share.

## What this trace does not determine

- Hardware.  Nothing was built or fitted: the timing of change 3 (and of
  any hold-path change) at 33 MHz, and the area figures, are estimates.
- The shipping core's 7 is partly its bench: its FP store is two
  write-through bus writes absorbed by the store buffer at the bench's
  zero latency.  On the Quadra's SDRAM path the shipping core's stores
  cost what the write queue allows, while the dual core's copyback cache
  retires them without the bus; the hardware gap on FP stores may be
  smaller than 11 against 7.  (The reverse holds for the dual core's
  uncached stores, which the 2026-10-22 comparison measured separately.)
- `FPU_PIPE=1` stores were not re-traced (the bench was built with
  `FPU_PIPE=0`, the shipping configuration); the 14 and its cause
  (`req_pend` while `pbusy`) are from the attribution and the code.
- How often real code uses the dynamic-list FMOVEM (which the proposed
  expansion would not speed up), `fmove.x` stores, or FMOVEM with one
  register -- vbcc's prologues use static two-register lists; Speedometer's
  compiler is unknown, as before.
