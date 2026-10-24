# FP store trace, 2026-10-24: what is in this directory

The evidence behind [`docs/fp-store-path.md`](../../fp-store-path.md): a
cycle-by-cycle trace of one `fmove.d fp0,(a0)+` (and of the other FP store
forms, FMOVEM, and the FP load, arithmetic-then-store and store-then-load
pairs for reference) on the dual-issue core (`rtl/ap68040_faster`, the
hardware parameters of `rtl/quadra_cpu040.sv`) and on the shipping core
(`rtl/ap68040` through `wombat_cpu`), both in Verilator 5.052 on
misterubuntu, checkout `6d8e81d` (branch `pipelined-040-dual-memory`; the
CPU trees are unchanged since the attribution's `236b8c5`).  Nothing under
`rtl/` in the checkout was changed: the benches ran on a `git archive` copy
in `~/mister/q800_fpstore_20261024`, with the probes added to the scratch
copies of the two benches only (`bench/`).

## Method

- **Kernel.** `kernels/fpstore.s` (vasm): the start-up of the bench's
  `crt0.s` (DTT0 user data copyback, DTT1 supervisor noncachable for the
  bench registers, both caches on, user mode, stamps by TRAP #0), then
  fourteen unrolled kernels of 100 (50 for the stack ones) back-to-back
  instructions, each run twice; the first pass warms the I-cache and
  allocates the buffer's lines dirty, the second pass is measured.  Stamp
  tags are `kernel << 4 | pass`; a kernel's closing tag is its opening tag
  + 8, and the cycles printed with the even closing tag (pass 2) are the
  kernel's.  Tag `$18` is two stamps back to back: the stamp overhead
  (191 cycles on the dual core, 80 on the shipping core -- TRAP, the
  noncachable write, RTE).  `kernels/fpstore.lst` has the addresses.
- **Benches.** `scripts/build_fs.sh` verilates both with the attribution's
  flags (dual: `FPU_PIPE=0 LOOP_PRED=0 EARLY_RES=0 SKID=0 DC1_ATC=0 DUAL=1
  BTIC=1 S1_CLASSES=3'b011`, `DIV_STEPS=2`; shipping: the release macro
  set), after `scripts/patch_tb_fstrace.py` / `patch_tb_old_fstrace.py`
  add `+fstag=<n> +fslen=<cycles>`: one line a cycle from the stamp with
  tag `<n>`.  Every probe is a hierarchical reference from the bench
  (`bench/*_patched.sv`).  `scripts/run_fs.sh` assembles, runs the image
  on both benches with `+pcprof`, then captures each kernel's second pass.
  `scripts/trim_traces.py` cuts the traces to the steady-state windows in
  `traces/`; the full logs are in `raw_logs.tar.gz`.
- **Dual-core trace line.** `cycle Qw Rr Uu | AG .. | D1 .. | D2 .. | EX
  .. | WB .. | h a d1 d2 e w adv e w | FP .. | DM ..`: the fetch queue
  (words, records, uops), the uop in each stage (`pc op[.sub]`, `L`/`S`
  load/store, `>Tn` result register, `ag>Rn` AG update, `*` last uop of the
  instruction), the stage holds and advances (`+1`: a second slot
  committed), the FPU interface (`sub` in EX, `sf` safe, `h` hold, `go`
  request out, `dq` done_q, `bg` background op, `rq` f_req/the FPU's rq,
  `dn` f_done, `ac` f_accepted, `pb` f_pbusy, `fst` the FPU state: 0 IDLE,
  1 SRC, 5 SHR, 6 PACKI, 7 BIN, 9 ADDX, 14 ROUND, 4 WB; `mw` mvr_wait) and
  the DMU store path (`st` a store at WB, `fa` wb_fast, `rdy` st_rdy, `e`
  engine state (0 idle), `dw` data RAM write, `d2r` dc2_rdy, `m2f`/`hit`
  the DC2 fast path).
- **Shipping-core trace line.** `cycle st=<state> pc=<dispatched pc> | fp
  req done acc bg fst st n | mgo wr | bus req wr a sz ack | disp`:
  `ap040_core`'s sequencer state (153 S_FPU_DEC, 160 S_FPU_GO, 161
  S_FPU_WR, 164/165 S_FPU_MVM/MVM2, 158 S_FPU_RD, 10 S_MWR, 9 S_MRD, 20
  S_PIPE_START, 3/4 S_FETCH/S_DECODE), the FPU handshake, the store loop
  (`st` store direction, `n` long words done), the memory issue and the bus.

## Cycles per instruction (pass 2, stamp overhead removed)

| tag | kernel (x100, x50 for `-(a7)`) | dual core | shipping core | attribution said |
|---|---|---:|---:|---|
| `$2x` | `fmove.d fp0,(a0)+` | **10.99** | **6.98** | 11.0 / 7.0-7.5 |
| `$3x` | `fmove.d fp0,(a0)` | 10.99 | 6.98 | |
| `$4x` | `fmove.d fp0,(a0)+ ; addq.l #1,d1` | 11.99 | 8.98 | |
| `$5x` | `fmove.d fp0,(a0) ; addq.l #1,d1` | 11.99 | 8.98 | |
| `$6x` | `fmove.s fp0,(a0)+` | 8.99 | 4.98 | |
| `$7x` | `fmove.x fp0,(a0)+` | 12.99 | 8.98 | |
| `$8x` | `fmove.x fp0,-(a7)` | 12.96 | 8.94 | |
| `$9x` | `fmovem.x fp0-fp1,-(a7)` | **79.0** | **17.9** | 79 / 18 |
| `$Ax` | `fmovem.x (a7)+,fp0-fp1` | 55.0 | 11.2 | 51-54 / 11 |
| `$Bx` | `fmove.l fp0,(a0)+` | 10.99 | 8.98 | |
| `$Cx` | `move.l d1,(a0)+` | 0.99 | 2.90 | |
| `$Dx` | `fmove.d (a0)+,fp0` | 7.98 | 6.14 | 8.0-8.3 / 6.0-6.3 |
| `$Ex` | `fadd.x fp1,fp0 ; fmove.d fp0,(a0)+` | 16.98 | 10.97 | |
| `$Fx` | `fmove.d fp0,(a0)+ ; fmove.d (a1)+,fp2` | 18.98 | 13.13 | |

The dual core's FP stores cost 7 + 2 per long word (S 9, D 11, X 13); the
shipping core's 3 + 2 per long word (5, 7, 9).  The whole gap is in the
base.  The `+pcprof` profiles (`raw_logs.tar.gz`, `PCPROF` lines) show
every pass-2 `fmove.d` at exactly 11 and the pass-1 ones at 11 or 24 (every
second one allocates a line: 13 cycles).

## `fmove.d fp0,(a0)+` on the dual core: 11 cycles

Microcode `FPU_K_OUT8` (`tools/ucode.py`): `CHK+EAL` (latches the words,
AG writes the operand address to T11), `DISP d=T0` (the FPU request; the
high long word to T0), `GET const=1 d=T1` (the low long word), `MOV S`
(T0 to (T11)), `MOV S` (T1 to (T11+4)), `END ag=FUPD` (the (An)+ update,
the store exception if any).  From `traces/new_0x20_fmove_d_a0inc.txt`,
instruction `047e`, cycles 4257-4267 (the previous instruction `047a`
retires its END at 4257, the next one's CHK enters EX at 4268):

| cycle | EX | WB | what happens | charged to |
|---:|---|---|---|---|
| 4257 | CHK (hold) | END of `047a` | CHK may act only once no older uop is in flight (`safe`: WB empty, or an earlier uop of its own instruction); the previous instruction's END is retiring this cycle | serialization (1) |
| 4258 | CHK | -- | encoding checks pass, words latched, `safe` -- leaves EX | CHK uop (1) |
| 4259 | DISP (hold) | CHK | `act`: `go <= 1`, `f_req <= 1` registered (`ap68040_fpif.sv` FC_DISP, `if (!go)`) | handshake: request register (1) |
| 4260 | DISP (hold) | -- | the FPU sees `rq` in F_IDLE: the source register is unpacked into the operand register, `fst <= F_SRC`, `r_op <= STORE` (`ap040_fpu.v` ~1813-1835) | FPU: dispatch state (1) |
| 4261 | DISP (hold) | -- | F_SRC: `sd_out` (round to double, exponent rebias, INEX into FPSR) `-> dout`, `done <= 1`, `fst <= F_IDLE` (~1918-1966) | FPU: the conversion (1) |
| 4262 | DISP (hold) | -- | `f_done` seen: `done_q <= 1`, `get_q <= f_dout` (fpif FC_DISP store branch) | handshake: done register (1) |
| 4263 | DISP | -- | `done_q` clears the hold; `res = f_dout[95:64]` to T0 | handshake: done_q register (1) |
| 4264 | GET | DISP | `res = get_q[63:32]` to T1 | GET uop (1) |
| 4265 | MOV S (T0) | GET | the first store's EX cycle | store uop (1) |
| 4266 | MOV S (T1) | MOV S (T0) | the first store at WB: copyback hit, `wb_fast`, `st_rdy` in its own cycle -- no hold | store uop (1) |
| 4267 | END | MOV S (T1) | the second store likewise (its data RAM write `dw` lands the next cycle); END has no exception pending and acts without `safe` (`nosafe`) | END uop (1) |

Totals: FPU proper 2 (its F_IDLE dispatch state and the one-cycle
conversion), fpif/backend handshake 3 (the request register, the FPU's
`done` register, the `done_q` register), FPU-interface uops 3 (CHK, GET,
END), the two data stores 2 (one EX slot each; the DMU never holds: both
are WB fast stores whose tag check was done at DC1 and whose RAM write is
hidden), serialization 1 (CHK behind the older instruction's last uop).

The store uops cost what integer stores cost: `move.l d1,(a0)+` is 0.99
clk (`traces/new_0xC0_move_l_a0inc.txt`: one store a cycle, `st fa rdy`
every cycle).

Variants (`traces/new_0x60..0xB0*`): `fmove.s` has no GET and one store
(9); `fmove.x` two GETs and three stores (13); `fmove.l` the same uops as
`fmove.s` but the FPU goes F_SRC -> F_SHR -> F_PACKI (DISP holds 7 cycles,
11 in all).  `fmove.d fp0,(a0)` (no update) is identical to `(a0)+`: the
update is AG's and free.  `fmove.d ... ; addq.l #1,d1` costs 12: the ADD
takes an EX slot of its own (the second slot does not pair it).

## The same instruction on the shipping core: 7 cycles

`traces/old_0x20_fmove_d_a0inc.txt`, instruction `047e`, cycles 2058-2064:

| cycle | state | what happens | charged to |
|---:|---|---|---|
| 2058 | S_FPU_DEC | dispatch (the sequencer's decode of the F-line words, operand read; `fpu_req <= 1`) | sequencer (1) |
| 2059 | S_FPU_GO, `fpu_req` | the FPU, in F_IDLE, packs the register to double and raises `done_r` in the request cycle (`rtl/ap68040/rtl/ap040_fpu.v` ~1187-1210, "P222/P255 dispatch-clock store") | handshake: request register + FPU conversion (1) |
| 2060 | S_FPU_GO, `fpu_done` | `hint_st_fpgo`: the first long word's write is issued from this cycle (`mwr`, `fp_n <= 1`) | handshake: done (1) |
| 2061 | S_MWR | the write goes to the store buffer | store (1) |
| 2062 | S_FPU_WR | the second long word's write issued | store (1) |
| 2063 | S_MWR | | store (1) |
| 2064 | S_FPU_WR | `fp_n == 2`: An updated, `fetch_next` | store (1) |

Totals: sequencer 1, FPU + handshake 2, two long-word writes 4 (2 each:
S_MWR and the return to S_FPU_WR).  The writes reach the bus through the
store buffer (`bus req` is high throughout, an ack every 3-4 cycles) and
do not stall the state machine at this rate.  No serialization: the next
S_FPU_DEC follows the last S_FPU_WR directly.  (`move.l d1,(a0)+` is 2.9
clk on this bench: write-through stores are bus-bound through the store
buffer, which is why the attribution's integer load/store row is higher on
the shipping core.)

The FPU's share is the one that differs in kind: the shipping FPU answers a
normal single/double/extended store in the request cycle; the dual core's
vendored FPU (`rtl/ap68040_faster/rtl/fpu/ap040_fpu.v`) has no P222/P255
and takes F_IDLE -> F_SRC (2 cycles), and the fpif adds a register on each
side of it (3 cycles) where `ap040_core` has one (`fpu_req`).

## FMOVEM: 8 slots whatever the list

`fmovem.x fp0-fp1,-(a7)` on the dual core (`traces/new_0x90_fmovem_x_push2.txt`,
instruction `10ee`, cycles 33346-33424, 79 cycles):

| cycles | what | cost |
|---|---|---:|
| 33346-33358 | set-up: `FPU_GEN`'s CHK (EX 33346), the sequencer's jump words to `FPU_MVM` (2), `LIST` (EX 33352), `ADDC T0 -> T10` held at AG four cycles waiting for LIST's byte count, the jump to `FPU_MVPD`, `ADDT0 A7+T0 -> T11` | 13 |
| 33359-33422 | **eight slots, 8 cycles each**: `MVR` 2 (the raw read port's set-up cycle `mvr_wait`, then the read), `GET` 1, `GET` 1, three stores 3, `ADDC T11 += 12` 1.  Slots 0 and 1 store FP0 and FP1; slots 2-7 are not in the list: their three stores are cancelled at AG (`dyn`) but still flow through the pipeline as empty uops, one EX cycle each, and their MVR/GET/ADDC run in full | 64 |
| 33423-33424 | `END` (the A7 update, `FPU_MVE`), the next instruction's CHK waiting on `safe` | 2 |

So the attribution's "8-13 clocks per long word" is really 8 cycles per
*slot*, eight slots always: a one-register push costs the same 79, an
eight-register push little more.  The pop (`traces/new_0xA0_*`, 55) is
13 + 8 x 5 (`LD`, `LD`, `LATCH`, `MVW`, `ADDC`) + 2.  The shipping core
iterates over the list's registers only (`traces/old_0x90_*`: S_FPU_MVM,
S_FPU_MVM2, then 3 x (S_MWR + S_FPU_MVM2) = 8 per register, two registers
16, plus the decode and the A7 adjust = 18; the pop S_FPU_MVM, three
S_MRD, S_FPU_MVM2 = 5 per register, 11 for two).

## Pairs

- `fadd.x fp1,fp0 ; fmove.d fp0,(a0)+` (`traces/new_0xE0_*`, 17 a pair):
  the fused CHK+DISP of the FADD spends 5 cycles in EX (1 `safe` wait, the
  request, the FPU's F_BIN, `accepted` -> released to the background); the
  store's CHK then waits 1 on `safe`, 1 on the background FADD (`bg &&
  !f_end`, the FADD in F_ROUND), acts on the third; DISP 5, GET, two
  stores, END -- 12.  Shipping core 11 = FADD 4 + store 7, the FADD's
  background completion overlapping the store's decode.
- `fmove.d fp0,(a0)+ ; fmove.d (a1)+,fp2` (`traces/new_0xF0_*`, 19 = 11
  + 8): the load is CHK (1 `safe` + 1), two `LD` uops, DISP 4 (request,
  F_SRC, `accepted` -> background); the next CHK waits for its `f_end`.

## Files

- `kernels/fpstore.s`, `kernels/fpstore.lst` -- the kernel and vasm's listing.
- `scripts/patch_tb_fstrace.py`, `scripts/patch_tb_old_fstrace.py` -- the
  bench probes (applied to the scratch copies; `bench/` holds the results).
- `scripts/build_fs.sh`, `scripts/run_fs.sh`, `scripts/trim_traces.py` --
  the build, run and trimming commands as executed.
- `stamps/new_stamps.txt`, `stamps/old_stamps.txt` -- every STAMP line
  (`at=` is the absolute cycle, for `+fstag`).
- `traces/<core>_<tag>_<kernel>.txt` -- the steady-state windows.
- `raw_logs.tar.gz` -- the full logs: the `+pcprof` runs (`new.log`,
  `old.log`, with `PCPROF` per address) and every trace run.
