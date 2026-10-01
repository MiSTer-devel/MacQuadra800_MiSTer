# Resume: fix the A/UX `copyout` panic (CPU) and the game hangs (VIA1 Timer 2), 2026-10-01

Written at the end of an exploratory session on Dani's Windows box (Opus).
The user asked for diagnosis only: **nothing in the RTL, `.qsf`, `files.qip`
or `.sdc` was changed**. This file hands both findings to the next session
(Fable) to fix, verify in simulation, build, and gate on hardware. Everything
the session produced that is not copyrighted is in
[`docs/resume-20261001/`](docs/resume-20261001/); the copyrighted binaries
(the A/UX kernel, DOTT's code, guest-RAM dumps) stay in `scratch/s1001/`
(gitignored) with the commands to re-create them.

## 0. The two findings in one paragraph each

1. **A/UX 3.1 panics `main.c - copyout of icode failed`** (screenshot
   `docs/resume-20261001/evidence/aux_panic_20261001.png`). CPU regression:
   the read-after-store handoff (`hint_rsr` / `retire_store_read`,
   `rtl/ap68040/rtl/ap040_core.v:3928-3934`) issues the *next* instruction's
   source read on the acknowledge of a store that retires to `S_NEXT`. A
   `MOVES` write is such a store, and the `MOVES` function-code override
   (`fc_ovr_v`/`fc_ovr`) is only cleared on that same edge, so the next
   read goes out in the MOVES space (user data). A/UX's `copyout` loop is
   `move.l -(a1),d1 / moves.l d1,-(a0)`: the kernel's read of its own data
   goes to user space, faults, A/UX's `hardflt040` finds no user region,
   `copyout` returns -1, panic. Introduced 2026-09-23 (P196 `c4a3522`,
   widened to `(An)+/-(An)` by P207 `8e4d06e`). **Proposed fix: one line,
   `!fc_ovr_v &&` in `hint_rsr`** -- reproduced, fixed and self-tested in a
   scratch copy only.
2. **Day of the Tentacle, DOOM II and Dracula Unleashed hang** (DOTT at the
   LucasArts tunnel ~15 s in, DOOM II at the title screen after ~3 min of
   demo, Dracula at the Viacom logo ~15 s in). Not a CPU bug: `rtl/via6522.sv`
   drops a VIA1 Timer 2 interrupt when the timeout lands on the same E clock
   as a CPU write to IFR (full-vector assignment at `:376` overrides the event
   OR at `:305`) or a read of T2C-L (`:505`). T2 is one-shot and the Mac OS
   Time Manager re-arms it only from that interrupt, so the Time Manager
   stops for good; each game spins waiting for its own Time Manager task
   while the OS (VBL, cursor, Force Quit) stays alive. Pre-existing
   (`via6522.sv` unchanged since 2026-08-30; DOTT hangs identically on
   `20260919`). **Proposed fix: an event beats a same-clock clear**, as the
   2026-09-29 IOSB fix (`f9f6da6`, danifunker history) did for VIA2.

## 1. Ground rules for the next session

- **This checkout (`C:\Temp\mistercore\MacQuadra800_MiSTer`, branch `main`) is
  the current source** (user, 2026-10-01: "this source code should be current
  and everything should be re-enabled"); `releases/MacQuadra800_20261001.rbf`
  (md5 `a4d4d00801f1c066fa99093ea8f35f6d`, seed 33) is the build under test.
  Its history is squashed (`d1ce2a3` = the 20260925 release, `884e9a5` =
  "Updating to 2026-10-01", `fd3db53` = rom rename). The full history,
  handoffs (`HANDOFF-20260930.md`, `RESUME-*.md`), `docs/`, the release log
  `releases/README.md` and all older rbfs are in
  **`C:\Temp\mistercore\MacQuadra800_danifunker`** (1,498 commits) -- use it
  to cross-check, not as the place to fix. The handoffs CLAUDE.md names
  (`HANDOFF-20260930.md` etc.) exist only there.
- CLAUDE.md rules still bind: no git worktrees; one Quartus flow on the box at
  a time; never `load_core`/reset while a guest runs (look first with
  `scripts/grab.sh`, read the screenshot, then act); always release the mouse
  button; judge liveness by I/O deltas and the clock; commit as work lands,
  do not push (the user pushes).
- The user judges CD audio by ear; that gate item is theirs.

## 2. This box

- Windows 11, Git Bash for scripts. `scripts/local.env` was **created this
  session** (gitignored) as a copy of `../old-quadra/scripts/local.env`:
  `MISTER_HOST=192.168.99.143`, `MISTER_SSH_KEY=$HOME/.ssh/mister_only`,
  `QUARTUS_BIN=/c/intelFPGA_lite/17.0/quartus/bin64`, `MISTER_HTTP_PORT=8182`,
  `RBF_NAME=MacQuadra800.rbf`, `SEED_FILE=releases/quadra800.rom` (that file
  does not exist in this checkout -- it is `releases/boot0.rom`; the box
  already has `games/MacQuadra800/boot.rom`, so the create-only seed never
  fires; fix the variable if `deploy_screenshot.sh` complains).
- **WSL `Ubuntu-24.04`**: `~/local/bin` has `iverilog`, `vvp`,
  `vasmm68k_mot`; Verilator 5.020 at `/usr/bin/verilator`;
  `qemu-system-m68k` at `/usr/bin`. Invoke as
  `wsl.exe -d Ubuntu-24.04 -e bash -lc '...'` (prints a harmless
  "Failed to mount I:\" line). Strip CRs when copying sources in.
- **Windows Python 3.9** has capstone 5.0.7, PIL, numpy, websockets.
  `python` from Python's `subprocess` resolves `bash` to WSL's bash; call
  `C:/Program Files/Git/bin/bash.exe` explicitly (as `pointer.py` does).
- Quartus 17.0.2 at `C:\intelFPGA_lite\17.0`. Builds take ~27-45 min; the
  danifunker sessions capped fits at 45 min with
  `../MacQuadra800_danifunker/scratch/cpu_area/seed_walk.sh` (hard-codes the
  danifunker path in its `cd` -- copy and change it to this checkout) launched
  detached via PowerShell `Start-Process` (wrap the `bash -lc` command in its
  own double quotes, confirm a `quartus_*` process 45 s later).
- **MiSTer** `192.168.99.143`, `ssh -n -i ~/.ssh/mister_only root@...`
  (always `-n`), mrext websocket on `:8182`. Main `/media/fat/MiSTer` md5
  `148d5679` (= `releases/MiSTer`). The release core is
  `/media/fat/_Computer/MacQuadra800_20261001.rbf`; load any rbf with
  `echo "load_core <path>" > /dev/MiSTer_cmd` (a `/tmp` path works).

## 3. Finding 1 -- A/UX `copyout of icode failed` (CPU)

### 3.1 What A/UX does (from its own kernel)

`/unix` was extracted read-only from `games/MacQuadra800/HD60_512-AUX3.1-Installed.hda`
(COFF, 837,678 bytes, md5 `3961dcabf6abbc8ce8b892289ec09519`; full symbol
table) into `scratch/s1001/unix.bin`. To re-create:

```bash
scp -i ~/.ssh/mister_only scripts/mac_hfs.py scripts/aux_ufs.py root@192.168.99.143:/tmp/
ssh -n -i ~/.ssh/mister_only root@192.168.99.143 'cd /tmp && python3 aux_ufs.py /media/fat/games/MacQuadra800/HD60_512-AUX3.1-Installed.hda cat /unix > /tmp/unix.bin'
```

then `python scripts/aux_dis.py unix.bin <symbol|start end>`
(`scripts/aux_coff.py unix.bin syms <regex>` lists symbols).

- `main()` (`$100077e8`; the call is `$10007cc0-$10007cdc`): `copyout(icode=$5bb24,
  *(long*)$110016ae /*UVTEXT*/, szicode=$34)`; nonzero -> `panic("main.c - copyout of icode failed")`.
  The destination was just `growreg`'d demand-zero, so the first user write
  faults.
- `copyout` (pstart `$556f0`), count < `$100`: `movem.l 4(sp),d0/a0-a1;
  exg d0,a1`, sets `$12fff540` (saved SP for the fault return) and
  `$12fff544`, adds the count to both pointers, then copies **backwards**:
  `move.l -(a1),d1 / moves.l d1,-(a0)` once, aligns, then jumps
  (`jmp ([$65620,pc,d1.w*4])`) into `copyoutbylong%` (`$5573e`, 16 such
  pairs + `dbra`), then `jmp ([$65660,pc,d0.w*4])` into `copyoutbybyte%`
  (`$557ac`, `move.b -(a1),d1 / moves.b d1,-(a0)` x3) and returns 0.
  `p_copyout` (`$55670`, count >= `$100`) probes each page with
  `moves.b d0,(a2)` **followed by a push `move.l a2,-(a7)`** and `jsr
  realvtop`, then copies physically with `p_blt`.
- Mirror image: `copyin` (`$554f0`): `moves.l -(a1),d1 / move.l d1,-(a0)`
  (MOVES **read**, then a kernel store); `copyinbylong%` `$5553e`,
  `copyinbybyte%` `$555ac`; `p_copyin` `$55464` probes with `moves.b (a3),d1`
  then pushes. `fuword $55326` = `moves.l (a0),d0 / clr.l $12fff540.l`;
  `fubyte $55354`; `suword $5536c` = `moves.l d0,(a0) / clr.l $12fff540.l`;
  `subyte $553a4`; `wb_out $55436` (the write-back replay, also MOVES).
- The 040 access-error vector goes to `accerr` (`$54c84`) ->
  `super_accerr` (`$54cd4`) -> `hardflt040` (`$5a4de`). Frame offsets from
  the saved-register base `a2`: SR `$46`, PC `$48`, format/vector `$4c`,
  SSW `$52`, WB3S/WB2S/WB1S `$54/$56/$58`, FA `$5a`, WB3A `$5e`, WB3D `$62`,
  WB2A `$66`, WB2D `$6a`, WB1A `$6e`, WB1D/PD0 `$72`. Decisions (SSW bit
  fields read with `bfextu`): TM even and nonzero -> instruction-fault path
  `$5a78a`; TT=0,TM=0,RW=0 -> data-cache-push fault; **TM=5 (supervisor
  data): any of SSW[15:10] set (CP/CU/CT/CM/MA/ATC) -> return -1**, FA in
  `$50000000-$5fffffff` -> -1, else flush the user page, `wbsup_valid`, 0;
  otherwise (user data): MA -> FA+`$fff`; MOVE16 write -> `wb_line`; writes
  and locked reads check the PTE's write-protect via `L2_ent`; `vtopreg`
  finds the region (stack growth via `u+$534`), `hardsegflt` maps the page,
  `fl_userpg`/`ld_userpg`, then `wb_valid` (`$59e9e`) replays every
  write-back slot whose WBnS bit 7 (V) is set, sized by WBnS[6:5], to user
  space through `wb_out` -- **it ignores the WB TM** -- and a 0 from it means
  failure. Nonzero from `hardflt040` -> `sup_chkprivpc` -> `trap()` ->
  `user_errret` (`$5529a`) unwinds to `$12fff540`, i.e. `copyout` returns -1.
- This core **restarts** the faulting instruction and leaves every WB slot's
  V clear (`ap040_core.v` `aerr_word`, the WB3S comment); `wb_valid` then
  replays nothing and the RTE re-executes the `MOVES`. That model is fine for
  A/UX as long as the SSW TM is the MOVES space (TM 1 here) and the
  predecrement is rolled back -- both verified correct by the test below.

### 3.2 The CPU mechanism (line numbers at `fd3db53`)

- `S_MOVES_WR` (`ap040_core.v:7471`): `fc_ovr_v <= 1; fc_ovr <= dfc;
  mwr(ea_addr, op_size, rf_rdata_a, S_NEXT);` -> the store waits in `S_MWR`
  (`:6093`) with `r_m_ret == S_NEXT`. (`S_MOVES2` does the same with `sfc`
  for a read.)
- `hint_rsr` (`:3928`): `(state == S_MWR) && (r_m_ret == S_NEXT) && m_issued
  && (fast-ready or ack_q) && !ifr_pres && rsr_head && [!pipe_rf_owner &&
  !pipe_write] && !sr[15]`; `retire_store_read = hint_rsr && d_ack` (`:3934`).
  `rsr_head` (`:3922`) accepts a next instruction whose decoded source is
  `(An)`, `(An)+`, `-(An)` (P207) or `d16(An)`.
- `retire_store_read` is in `mem_issue`'s in-place whitelist (`:2081`,
  `:2091`); the in-place issue stamps `fc_r <= fc_ovr_v ? fc_ovr : (sr_s ?
  SUPER_DATA : USER_DATA)` (`:2100`). `fetch_next_body` (`:3230`) clears
  `fc_ovr_v` with a nonblocking assignment on the **same** edge, so the read
  sees the old 1 and goes out with `fc_ovr` = DFC.
- History (danifunker): `c4a3522` 2026-09-23 09:47 "P195b-P197 ... the
  read-after-store handoff"; `8e4d06e` 12:12 "P206-P209 ... read-after-store
  for (An)+/-(An)"; `c214e74` 12:48 "P207 fix ... source mode from the
  record". A/UX last passed the gate on `20260919` (`5b9ad4d`, A/UX 3.1 at
  32 MB, 2026-09-19); every release since lists A/UX as "owed".

### 3.3 Reproduction (`docs/resume-20261001/t_aux_copyout.s`)

A `tb_ap040_program` program that is A/UX's `copyout` instruction for
instruction (both jump tables, `moves.l d1,-(a0)` / `move.l -(a1),d1`), with
SRP `$4000` (identity, 64 x 4 KB pages) and URP `$4800` -> `$4A00` ->
`$4C00` (user page 0 initially invalid, mapped to PA `$A000` by the
handler), DFC = SFC = 1, `copyout(SRC=$6024, 0, $34)`. The access-error
handler has A/UX's shape (`suba.w #$a,sp; movem.l d0-d7/a0-a6,-(sp)`, CACR
rewrite, frame read at `$4c/$52/$5a(sp)`), applies `hardflt040`'s TM=5 rule,
makes the page resident, `pflusha`, RTE. Four passes: caches off; caches on
write-through; user page copyback; source page copyback and hot. Each pass
checks: return 0, a0 = 0, exactly 1 fault, first SSW `$0401`, first FA `$30`,
the 52 bytes via the user mapping and physically. Fail codes: `1x` data /
return, `2x` fault count, `3x` SSW or the TM=5 refusal, `4x` FA, `5x` a0
(x = pass), `91`-`94` internal guards (`94` = more than 8 faults: a fault
loop), `1000+n` = unexpected vector n.

Run (WSL; ~2 min; copies to `~/auxco`):

```bash
wsl.exe -d Ubuntu-24.04 -e bash -lc 'bash /mnt/c/Temp/mistercore/MacQuadra800_MiSTer/docs/resume-20261001/run_aux_copyout.sh'
```

| CPU | rel macros (the ten `AP040_*` of the qsf) | base macros (LEA+XSTORE) |
|---|---|---|
| this checkout (= 20261001) | **FAIL** code 94 in all 3 phases | **FAIL** code 94 |
| this checkout + the fix below (scratch copy) | pass, 3 phases | pass |
| `5b9ad4d` (09-19, `git archive` into `scratch/s1001/r0919`) | pass | pass |

Failure signature (both configs, dumped from `$3600`): 9 faults; the first
is correct (SSW `$0401`, FA `$00000030` -- the MOVES write, TM 1, restarted
fine); the next 8 are SSW **`$0501`** (ATC, **read**, TM 1 = user data),
FA **`$00006030`** (inside the kernel source `$6024-$6057`), PC **`$065e`**
= the `move.l -(a1),d1` after the 8th `moves.l` in `bylong` -- i.e. the
handoff fires once queue/hint timing lines up, not on every pair.

### 3.4 Proposed fix (not applied)

```diff
 wire        hint_rsr = (state == S_MWR) && (r_m_ret == S_NEXT) && m_issued &&
                        ((mwr_fresh && st_hinted && mem_fast_ready) || (!mwr_fresh && mem_ack_q)) && !ifr_pres && rsr_head &&
 `ifdef AP040_EXPERIMENTAL_PIPELINE
                        !pipe_rf_owner && !pipe_write &&
 `endif
+                       // not after a MOVES store: fc_ovr_v/fc_ovr (its DFC) clear only on
+                       // this edge, and mem_issue would stamp the next read with them
+                       !fc_ovr_v &&
                        !sr[15];
```

With exactly this guard (as `!fc_ovr_v &&   // EXPERIMENT` in
`scratch/s1001/patched/rtl/ap68040`) `rtl/ap68040/tb/run_tests.sh` passed
32/32 in both its configurations (default and `CPU_TEST_LEA=1
CPU_TEST_XSTORE=1`). **Not yet run on the guarded tree:** the cycle-count
gates (`scripts/cpu_gates_wsl.sh`: bench_loop / pipe_bench / branch_bench /
first-100 corpus -- the guard only removes the handoff after a MOVES, so
counts should be identical), and the release-macro gates in
`scripts/cpu/*.py` (e.g. `mmu_candidate_gate.py` runs `t_mmu`,
`t_bitfield_mmu`, `t_atcprobe`, `t_moves_fc`, `t_exceptions` with all ten
macros). Note `run_tests.sh` itself never enables the eight `*PIPELINE*`
macros the release ships with -- consider a `CPU_TEST_RELEASE=1` leg.

### 3.5 What was audited, and what is left to audit

- Every other in-place issue source in `mem_issue`'s whitelist was checked
  for the states it fires from: `hint_indexed_read`/`hint_displacement_read`
  (`S_EA_D16`, `S_EA_EXTW2`, `S_FPU_RD`), the FPU hints (`S_FPU_*`,
  `S_FREST*`), `hint_rsp` (`S_MRD`, `r_m_ret == S_UNLK3`), `hint_fpn`
  (`S_MRD`), `hint_mmn` (`S_MRD`, `S_MOVEM_LD`), `move_store_read_handoff`
  (`S_MRD`, `r_m_ret == S_PIPE_SDONE`), `reg_move_store_prepare`
  (`S_PIPE_START`), `hint_st_*`, `pipe_load_launch` (`S_EXPERIMENT_PIPE` /
  `S_PIPE_LOAD_RETURN`), `retire_read_read` (P219, hard-disabled by P232).
  None is reachable from `S_MOVES_RD`/`S_MOVES_WR`/the MOVES `S_MWR`, so
  `hint_rsr` is the only leak found.
- The data hint bus is space-safe: the MMU translates the hint with the live
  request's `a_super`, registers it as `hq_super`, and `m_hint_match`
  requires `hq_super == a_super` (`ap040_mmu.v:874-876`).
- **Still to check / cover by test:** the descriptor and branch-lookahead
  dispatches that also fire at a MOVES write's acknowledge
  (`n_desc_ok`, `:2859`; the Bcc lookahead arm, `:10175`, both keyed on
  `(state == S_MWR) && d_ack && (r_m_ret == S_NEXT)`): they move the next
  instruction into `S_DECODE`/`S_BCC_EXT`/`S_JSR1` and that state's
  push/fetch happens a clock later, after `fc_ovr_v` cleared -- confirm with
  tests rather than by reading. Add to `t_aux_copyout.s` (or a sibling):
  the `copyin` shape (`moves.l -(a1),d1 / move.l d1,-(a0)`), the
  `suword`/`fuword` shapes (`moves` then `clr.l abs.l`), the `p_copyout`
  probe (`moves.b d0,(a2)` then `move.l a2,-(a7)`), `.b`/`.w` sizes,
  `(An)`/`(An)+`/`d16(An)` next sources, and `moves` followed by
  `bsr.s`/`jsr`/`pea`/`link`. Put the test(s) into
  `rtl/ap68040/tb/asm/` and the `run_tests.sh` list.

### 3.6 Hardware verification for this fix

A/UX gate at **32 MB** (CLAUDE.md; at 128 MB A/UX 3.1 hangs `shutdown -h
now` on every build since 2026-09-16). The user's last A/UX run was at
**128 MB with Ethernet On** (`config/MacQuadra800.CFG` byte 0 = `$50`); the
panic is RAM-size independent (the sim reproduces it) but gate at 32 MB:
set byte 0 to `$40` (32 MB, Ethernet On -- keeps the PC sampler usable)
before `load_core`. The A/UX image was left as the user's panicked boot left
it (`HD60_512-AUX3.1-Installed.hda`, mtime 2026-10-01 13:55); per CLAUDE.md
do not sit through fsck -- but **ask the user before overwriting their
image**; safer is `unzip -p backup/HD60_512-AUX3.1-Installed.zip >
HD60_512-AUX3.1-gate.hda` (the zip is dated 2026-09-01, 61 MB) from the
menu core and point `.s0` at the copy. Pass = multiuser Finder desktop,
CommandShell answers (`uname -a` = `A/UX localhos 3.1 SVR2 mc68040`),
`shutdown -h now` reaches "You may now switch off". Earlier A/UX menu-driving
notes: memory `aux-scsi-status` (black-inversion probe, 0.05 s delays) and
`RESUME-aux-*.md` in the danifunker checkout.

## 4. Finding 2 -- the game hangs (VIA1 Timer 2 -> Time Manager stall)

### 4.1 Hardware observations (disk `MacQuadra800_Problem_Games.hda`)

The disk (Mac OS 8.1, active folder "System Folder 8.1"; HFS catalog in
`docs/resume-20261001/evidence/problem_games_hfs_catalog.txt`) has
`:Games:Day Of the Tentacle:Day of the Tentacle` (+ its 282 MB data file, so
no CD needed), `:Games:Doom2:Doom II:DOOM II 1.0.3` (+ `DOOM2.WAD`),
`:Games:Duke Nukem 3D:...`; Dracula runs from `DRACULA.toast` (`DRACULA`,
`DRACDEMO` on the CD). Other toasts on the card: `Day of the
Tentacle.toast`, `Brain Dead 13.toast`, `DOOM II.iso`.

| run | stops at | Time Manager over 3 s | TM queue head | guest busy at |
|---|---|---|---|---|
| DOTT, 20261001 | tunnel, ~15 s | (not measured; same screen) | -- | -- |
| DOTT, caches off (Cache Switch), 20261001 | black screen, earlier | -- | -- | no disk I/O |
| DOTT, 20260919 | tunnel, ~15 s | **FROZEN**, Ticks advancing | `$078DD944` tmAddr `$078A4DB0` **tmCount 0** | `$078C1E1C` loop |
| DOOM II, 20261001 | title screen, ~3 min of demo | **FROZEN** (TimeVars `$10560`) | `$07C886AE` tmAddr `$07522A7A` **tmCount 0** | `$0752E9xx` (SR `$2000`) |
| Dracula, 20261001 | Viacom logo, ~15 s | **FROZEN** | `$07C86514` tmAddr `$07C8799A` **tmCount 0** | `$0007CDEx`, ROM `$408099B0` |
| Finder after Force Quit (09-19) | -- | moving | `$000C6C14` ... | -- |

Every hang: keyboard and Force Quit (Cmd-Option-Esc) work, `Ticks`
(`$16A`) advances ~60/s, zero disk I/O, the frame is byte-identical. Force
Quit revives the Time Manager (the ROM reprograms T2 when tasks are
removed), which is why only an app that waits on its own TM task hangs
permanently. Screenshots in `docs/resume-20261001/evidence/`.

Full queue dumps (qLink, qType, tmAddr, tmCount):
- DOTT/09-19, TimeVars `$00010370` (record `078dd944 05e0 0018 0064bfed
  000003ac ...`, identical 3 s apart): `078DD944 c000 078A4DB0 0` ->
  `078E1F04 c000 078A4DB0 2a` -> `078E1F3C c000 078A4DB0 37d` -> `003B35D8
  8000 004AFB2A 82e` -> `000C6C14 c000 0012B09C 6ee1` -> `0016B432 8000
  00284776 a97a` -> `0000CC02 c000 4080C8E0 7cd818`.
- DOOM II/10-01, TimeVars `$00010560`: `07C886AE c000 07522A7A 0` ->
  `07B78F90 8000 003C10A0 270` -> `000C8284 c000 0012AAEC 3e7` -> `003B7158
  8000 004B454A 52ef` -> `001981E2 8000 00283F36 26bc9` -> `0000CC42 c000
  4080C8E0 a4792c`.
- Dracula/10-01: `07C86514 c000 07C8799A 0` -> `003B7158 8000 004B454A
  347f` -> `001981E2 8000 00283F36 2b60` -> `000C8284 c000 0012AAEC 3e29` ->
  `0000CC42 c000 4080C8E0 7767e4`.

DOTT in detail (09-19 run; heap addresses differ per launch): `CODE 1`
(257,324 bytes, the 68k half of a fat app; the data fork is PPC `Joy!peff`)
loaded at `$0789E300` (in-RAM bytes match the file except 4-byte load-time
relocations). Hot loop `$078C1E1C`: `move.l $07C7EA06,d3; lsr.l #2,d3;
[+15 if $07C7F7E6]; bsr.l $078ABF86; movea.l $07C7D7E2,a0; move.w
$26(a0),d0; ext.l; cmp.l d0,d3; blt` -- the SCUMM frame wait. The tick
counter `$07C7EA06` (frozen at 6) is incremented only by `$078CD120`
(`addq.l #1,$07C7EA06`, ...), installed at `$078CA3F8` through a descriptor
at `$07C80454` (callback, period `$1047` = 4,167 us = 240 Hz) and
`$078A4AF2` (NewPtr `$30`, an extended TMTask; re-armed with `PrimeTime`
`A05A` at `$078A4BFE`). The TMTask `$078E1F3C` was still queued: qLink
`$003B35D8`, qType `$C000` (active + extended), tmAddr `$078A4DB0`,
tmCount `$37D`, tmWakeUp `$0064BFE8`, +`$18` A5 `$07C2B958`, +`$1C` period
`-4167`, +`$2C` callback `$078CD120`.

### 4.2 The mechanism (`rtl/via6522.sv` at `fd3db53`)

- `:305` `irq_flags <= irq_flags | irq_events;` then, in the same block,
  the write decode (`:309`, `wen && falling`): `4'hD` IFR `:376`
  **`irq_flags <= irq_flags & ~data_in[6:0];`** -- a later full-vector
  nonblocking assignment, so every event of that clock is discarded. The
  per-bit clears (ORB/ORA `:314-326`, T1C-H/T1L-H `:343/:352`, T2C-H
  `:360`, SR `:364`) and the read clears (`:472-510`: ORB, ORA, `$F`, T1C-L
  `:501`, **T2C-L `:505`**, SR `:509`) override only their own bit, but a
  T2C-L read on the timeout clock still loses IFR[5].
- Timer B (`:593-657`): `timer_b_timeout` registers at the tick where the
  count passes 0; `timer_b_event = timer_tick & timer_b_timeout` (`:659`)
  is presented on the next E falling. `rtl/iosb.sv:199-203` drives
  `.falling(e_falling)` and `.timer_tick(e_falling)`, so the event and a CPU
  access share clocks.
- The Quadra ROM clears VIA1 flags by writing vIFR: e.g. `$40806e98`
  `move.b #$2,$1a00(a1)` (CA1, the 60 Hz VBL), `$40809d70` `#$1` (CA2),
  `$4080a29a`, `$40848108` `#$62,$1a00(a2)`, `$408885be` `#$90` -- 14 such
  sites in `releases/boot0.rom`. One E clock is 1.28 us; with hundreds of
  T2 timeouts a second (DOTT has three TM tasks, one at 240 Hz) a collision
  comes within seconds to minutes.

Bench (`docs/resume-20261001/tb_via_t2_race.v`, `run_via_t2_race.sh`,
`via6522.sv` alone, iverilog):

| access on the T2 timeout's E clock | IFR[5] |
|---|---|
| none (baseline) | set |
| A: IFR write `$02` | **LOST** |
| B: same write one E clock later | set |
| C: T2C-L read | **LOST** |
| D: IER write `$82` | set |

### 4.3 Proposed fix (not applied)

Collect the clock's clears into a mask and apply events last, e.g. a
blocking `reg [6:0] ifr_clr` built in the write and read decodes, then
`irq_flags <= (irq_flags & ~ifr_clr) | irq_events;` (keep the reset arm).
Decide one semantic deliberately: for a **timer high-byte write that
restarts that same timer** (T1C-H/T1L-H for bit 6, T2C-H for bit 5) the
clear should probably win for that bit (the event belongs to the countdown
being replaced; letting it win gives a spurious interrupt right after a
re-arm); for IFR writes, port accesses, SR and counter-low reads the event
should win. Expected bench after the fix: rows A and C set. Add rows for a
CA1 event + IFR write of `$20`, an SR completion (`sr_ext_complete`) + IFR
write, and T1 in one-shot and free-run. The same lost-event class also
drops CA1 (one VBL tick -- harmless), CA2 (a one-second tick), and the
shift-register completion (`irq_events[2]`, ADB on this machine -- a lost
one stalls ADB input until something re-arms it; possibly behind any
"keyboard/mouse froze" reports). VIA2 is the IOSB's own model (only `via1`
instantiates `via6522`, `iosb.sv:199`); it got the equivalent fix on 09-29
(`f9f6da6`) -- worth a re-read for any remaining same-clock clear.

### 4.4 Verification for this fix

- `run_via_t2_race.sh` (all rows set) plus the new rows.
- `verilator/Makefile`: `tb_adb` (VIA1 SR/ADB), `tb_iosb_scc`, `tb_rtc_pram`
  (RTC on VIA1 port B), `tb_scsi_irq_ack_race`, `tb_sdma_ack_watchdog`;
  `scripts/build_only.sh --check`.
- Hardware, Problem Games disk, OSD Ethernet On so `tmcheck.sh` works:
  DOTT intro plays through to the title/first scene; DOOM II attract demo
  for >= 20 min with `tmcheck.sh` "moving" every minute; Dracula past the
  Viacom logo into its first video; plus the Mac OS 8.1 gate (CLAUDE.md).

## 5. Tools from this session (`docs/resume-20261001/`)

All MiSTer-side tools are read-only towards the guest and live in `/tmp`
(RAM) on the box: `scp -i ~/.ssh/mister_only <file> root@192.168.99.143:/tmp/`.

- **`pcsample.py [secs] [topN]`** -- histogram of the live guest {SR, PC}
  from the SONIC mailbox SAMPLE word (64-bit word `$81A` of the DDR3 window
  at ARM physical `0x1FF00000` -> `0x1FF040D0`; PC bits 31:0, SR 47:32;
  ~28k reads/s, ~16k distinct updates/s). **Needs OSD Ethernet = On** (the
  mailbox, `rtl/sonic_mbx.sv`, is inert otherwise); asserts the magic
  `McQ8ETH4` at `0x1FF04000`.
- **`gdump.py ADDR LEN OUT`** (hex) -- reads guest RAM (logical = physical
  with VM off) through the mailbox DMA engine: writes one dir-0 op to OPS
  (`$820`, `addr<<32 | len<<16`), then DMA_CMD (`$817`, `1<<8 | seq`, count
  bytes before the seq byte), waits for DMA_STAT (`$818`) == seq, copies
  XFER (window offset 0). **Each command needs a seq the FPGA did not just
  complete** (`sonic_mbx.sv:441`: it runs any cmd whose seq differs from
  `dma_done_seq`; a repeated seq returns stale XFER -- this produced bogus
  reads for an hour); the script starts at `cmd+1`, skips 0 and the 16 seqs
  after Main's own (`mac_eth_q8.cpp` keeps a private seq and waits for its
  echo), and logs its last seq in `/tmp/gdump.seq`. Chunks of `$3F00`.
  Never writes guest memory; the only risk is one garbled Ethernet packet if
  Main stages one at the same instant. Verified against DOTT's `CODE 1`.
- **`tmcheck.sh`** -- needs `/tmp/gdump.py`; prints Ticks twice, the
  TimeVars record twice ("FROZEN"/"moving") and walks the active TM queue.
  Healthy idle Finder: "moving".
- **`gdis.py`** -- capstone disassembly of the gdump images with the PC
  histogram's counts beside each instruction.
- **`pointer.py find|goto|click|dbl X Y`** -- closed-loop pointer: finds the
  arrow cursor (either polarity; a game's palette inverts it) in a
  640x480 screenshot and corrects with damped 2-px reports. The guest's
  mouse **accelerates** (6-px reports land as ~15 px; 2-px as 1.4-1.8x;
  open-loop moves are useless). **`mac_ui.py`** -- keys (`key raw:N
  down:N up:N sleep:S`), relative moves; ends with `left_up`.
  **`probe_click.py X0 Y0 X1 Y1`** -- for a hidden cursor (DOTT calls
  `HideCursor`): homes to (0,0), steps, presses, releases only if the button
  rectangle lights up, otherwise slides away first.
- Linux keycodes for `raw:` (`scripts/mister_ws.py`): a30 b48 c46 d32 e18
  f33 g34 h35 i23 j36 k37 l38 m50 n49 o24 p25 q16 r19 s31 t20 u22 v47 w17
  x45 y21 z44, space 57, return 28, esc 1, digits 1-9 = 2-10, 0 = 11;
  **Command 56**, Option 125, Shift 42, Control 29. Finder: type-select a
  name then Cmd-O (`down:56 raw:24 up:56`); Cmd-W `down:56 raw:17 up:56`;
  Force Quit `down:56 down:125 raw:1 up:125 up:56`, then click Force Quit
  at (424,188) (Return does nothing in that dialog). 8.1 Finder at 640x480:
  Apple menu (22,9); Special (181,9) -> Restart (192,87), Shut Down
  (200,104). The Apple-menu "Control Panels" entry on this disk is a stale
  alias; Cache Switch is `System Folder 8.1:Control Panels:Cache Switch`
  (needs a restart to apply).
- **`run_aux_copyout.sh`**, **`run_via_t2_race.sh`** -- the two repros
  (section 3.3 / 4.2); both re-verified from this folder at hand-off.

Untracked, in `scratch/s1001/`: `unix.bin` (A/UX kernel), `dott.rsrc`,
`dott.data`, `dott_code0/1.bin` (from `mac_hfs.py ... cat ':Games:Day Of the
Tentacle:Day of the Tentacle' OUT --rsrc` and `scripts/mac_rsrc.py OUT get
CODE 1`), `g_hi.bin` (guest `$07890000+$40000`), `g_3c.bin`, `g_4e.bin`,
`g_low.bin` (from the DOTT hang on 09-19), `patched/` (the guarded CPU copy),
`r0919/` (the 09-19 CPU), every screenshot, `FINDINGS-20261001.md`.

## 6. Box state at hand-off (2026-10-01 ~16:10)

- `20261001` loaded; Mac OS 8.1 at "It is now safe to switch off".
- `config/MacQuadra800.s0` = `games/MacQuadra800/MacQuadra800_Problem_Games.hda`,
  `.s4` = `games/MacQuadra800/DRACULA.toast`; the user's previous ones (the A/UX
  image, `DOOM II.iso`) are `MacQuadra800.s0.bak_s1001` / `.s4.bak_s1001`.
  Slot files are 1,024 bytes: the path, NUL-padded; `.s2` = the PRAM `.nvr`.
- `MacQuadra800.CFG` unchanged: byte 0 `$50` = RAM `[4:3]=10` 128 MB,
  Ethernet `[6]` On. (Other bits: `[5]` 512x384 monitor, `[8:7]` net iface,
  `[13:12]` Scale, `[46:44]` ADB controller, `[47]` stick moves pointer.)
- Cache Switch on the Problem Games disk restored to "Faster" (applied at
  the next boot, which happened).
- The Problem Games image had one unclean stop (a core reload while DOTT was
  wedged with zero writes in flight; 8.1 showed the "not shut down properly"
  notice and nothing else). All other stops were clean shutdowns.
- `/tmp` on the MiSTer cleaned. Nothing was installed, and Main was not
  restarted.

## 7. Plan for the next session

1. Read this file, CLAUDE.md, and skim `../MacQuadra800_danifunker/HANDOFF-20260930.md`.
   Check WSL tools, `scripts/local.env`, and that no `quartus_*` runs.
2. **CPU fix.** Move `t_aux_copyout.s` into `rtl/ap68040/tb/asm/`, extend it
   (section 3.5 shapes), add it to `run_tests.sh`; confirm it fails on the
   current RTL in both macro sets; apply the `hint_rsr` guard; rerun:
   `run_tests.sh` (both legs), `scripts/cpu_gates_wsl.sh` (cycle counts
   unchanged), the release-macro `scripts/cpu/*.py` gates. Commit
   (`cpu: ...`).
3. **VIA fix.** Turn the race bench into a `verilator/Makefile` target (or
   keep it iverilog beside the others), add the extra rows, fix
   `via6522.sv`, rerun the VIA-adjacent benches and `build_only.sh --check`.
   Commit (`via: ...`).
4. One Quartus flow with both fixes (the qsf's recipe, SEED 33 first; the
   design is at 93 % ALMs, so expect a seed walk with the 45-min cap; record
   every seed's result in the qsf comment block; run
   `quartus_sta -t scripts/cpu/timequest_cross_domain.tcl <tag>` after each
   fit). Deploy a marginal build with `ALLOW_TIMING_VIOLATION=1` to try it;
   prefer a clean CPU-clock seed for the shipped rbf.
5. Hardware: the game checks (4.4), A/UX at 32 MB (3.6), the Mac OS 8.1
   gate; CD audio by ear is the user's.
6. Release: copy the rbf to `releases/MacQuadra800_YYYYMMDD.rbf` and commit,
   with the seeds and timing in the `.qsf` comment block. **Do not create a
   `releases/README.md`** (user, 2026-10-01: "this is not what we do").
   Ask the user whether to mirror the fixes into the danifunker checkout.

## 8. Open questions for the user

- May the A/UX gate overwrite `HD60_512-AUX3.1-Installed.hda` from
  `backup/`, or should it run from a fresh copy?
- Should the CPU self-test runner gain a release-macro leg as part of this
  work?

## 9. Status after the fixing session (2026-10-01 evening, Fable)

Both fixes are in the RTL; sections 3.4 and 4.3 above are what was applied,
with the changes noted here. The user's answers to section 8: the A/UX gate
overwrites `HD60_512-AUX3.1-Installed.hda` from `backup/` (done, 17:25-17:35,
menu core loaded); the release-macro test leg was added.

### 9.1 CPU (`e3fc1a0`)

- `hint_rsr` requires `!fc_ovr_v` (`ap040_core.v`), exactly the proposed line.
- `rtl/ap68040/tb/asm/t_aux_copyout.s` (moved from `docs/resume-20261001/`)
  and the new `t_moves_next.s` are in `run_tests.sh`. `t_moves_next` runs
  twelve shapes of "the instruction after a MOVES", each once with MOVES
  against a user page and once with MOVE against a supervisor copy, and
  compares registers and memory; only user page 0 is mapped, so a leaked
  access faults. `-DONLY=n` assembles one shape. On the unfixed core:

  | shape | what follows the MOVES | unfixed core |
  |---|---|---|
  | 1 copyout `-(An)` .l | kernel read | fault, SSW `$0501` FA `$6018` |
  | 2 `(An)+` .w | kernel read | fault, FA `$6002` |
  | 3 bytes, `(An)` / `d16(An)` | kernel read | fault, FA `$6000` |
  | 4 ADD/OR/SUB/TST/CMP from memory | kernel read | fault, FA `$6000` |
  | 5 mem-to-mem, kernel stores, probe + push | kernel read | fault, FA `$6000` |
  | 6 BSR/JSR/PEA/LINK/UNLK/MOVEM/pops | **a stack pop** | fault, FA `$33f0` |
  | 7 Bcc / DBRA | kernel read | fault, FA `$6024` |
  | 8 copyin, 9 fuword/probe, 10 calls after a MOVES read | | pass |
  | 11, 12 MOVES then MOVES in the other space | | pass |

  So every leak went through `hint_rsr` (the pushes and the descriptor /
  branch-lookahead dispatches of section 3.5 were already correct), and the
  guard closes all of them: 34/34 in the default, `CPU_TEST_LEA=1
  CPU_TEST_XSTORE=1` and the new `CPU_TEST_RELEASE=1` legs (the ten qsf
  macros + `experimental/ap040_pipeline_integer.sv`; no leg built those
  before). The unfixed core fails exactly the two new tests in each leg.
- Cycle counts, unfixed vs fixed, identical in all three legs: bench_loop
  54176 / 54974 / 54974, pipe_bench 99070 / 134348 / 134348, branch_bench
  103134 / 123456 / 123456 (default) and 102136 / 122458 / 122458 (LEA+XSTORE,
  release); first-100 corpus 28,041,145 cycles (default) and 28,020,477
  (release macros), REAL diffs 0.
- On this Windows checkout the corpus gate's sha check fails until the CRs
  are stripped from `scripts/fixtures/corpus100/cpu.hex` and
  `scripts/fixtures/tb_cpu_corpus100.v` in the WSL copy (autocrlf).

### 9.2 VIA (`a9cbda8`)

- `via6522.sv`: the clears of a clock are collected in `ifr_clr` and applied
  once, events on top: `irq_flags <= (irq_flags & ~ifr_clr) | (irq_events &
  ~{write_t1c_h, write_t2c_h, 5'b0})`. The semantic chosen for section 4.3's
  open point: only the two writes that **restart** a timer (T1C-H, T2C-H)
  let the clear win; T1L-H does not restart the timer, so the event wins
  there too.
- `verilator/tb_via_irq_race.v` (`make tb_via_irq_race`, replaces the
  iverilog bench as the regression; the old one stays in
  `docs/resume-20261001/` as the original evidence): 29 rows over T2, T1
  one-shot and free-run, CA1 and the shift register's external completion,
  each access on the event's own E clock and one E clock later. The old
  model loses 12 rows; all pass now.
- `tb_adb`, `tb_rtc_pram`, `tb_iosb_scc`, `tb_scsi_irq_ack_race`,
  `tb_sdma_ack_watchdog` and `lint_sonic` pass. VIA2 (the IOSB's own model)
  was re-read: its IFR write already carries the same-clock edges.
