# AP68040 RTL runs — scored against the Quadra 800 silicon captures

Verilator runs of the shared bench payloads against the AP68040 core
(rtl/ap68040 submodule @ 3fed526) via preboot/sim040. Scored with
gen/score_vs_oracle.py against results/*/hardware*2026-08-28*.jsonl:

| suite | rows | verdict |
|---|---|---|
| saverestore | 8/8 | 0 REAL diffs |
| fpu | 270/270 | 0 REAL diffs — traps exactly where 040-lite silicon traps |
| integration | 1328/1328 | 0 REAL diffs (incl. the emulator-fatal tail, the 176 vec-11 rows, and the FPIAR low-16 quirk) |
| mmu (full, live translation) | 24/24 | 0 REAL diffs — stale-ATC held like silicon, MMUSR flags = silicon ground truth, faults recover vec 2 |
| cpu | 722-row corpus | run in progress at archive time; see the file when it lands |

Classified-not-failed divergences are the documented classes only:
layout/reloc (payload + table addresses differ per build), env (the sim
has no Mac ROM handoff state), frame (fault frames contain PCs).

The mmu run needs the sim's identity translation world (tb_corpus.v +
SIM_MMU_WORLD in the entry): the corpus's safe MOVEC TC row enables
translation expecting the Quadra ROM's valid tables (finding 30).
