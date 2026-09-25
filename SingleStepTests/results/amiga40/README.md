# FS-UAE A4000/040 baselines — the Amiga 68040 test floppies

One run of each `prebuilt/amiga40-*.adf` under FS-UAE 3.1
(`--amiga-model=A4000/040`, kicka4000, turbo floppy; mmu disks with
`--uae_mmu_model=68040`), extracted from the mutated ADFs (stream at
byte 0x78000). Scored against the Quadra 800 silicon captures with
`gen/score_vs_oracle.py`:

| suite | rows | vs silicon |
|---|---|---|
| saverestore | 8/8 | **identical** (0 real diffs) |
| mmu (safe) | 25 | 0 real diffs (env class only) |
| cpu | 717/717 | 33 real diffs — FS-UAE CPU-model divergences incl. the finding-13 platform-local rows (A6/scratch-dependent CCR outcomes) |
| integration | **1328/1328** | 16 real diffs = exactly the FPIAR adjudication rows (silicon keeps low 16 bits; FS-UAE differs); 176 fp-policy (FS-UAE executes FINT/FINTRZ, silicon traps), 51 golden (capture predates the FDBcc fix) |
| fpu | 270/270 | 243 real diffs — FS-UAE's FPU executes the whole corpus (like MAME) and diverges per-op; FS-UAE is a CPU-shaped oracle only |
| mmu-full | 20/25 rows | FS-UAE's 040 MMU emulation loses 5 live rows — QEMU/silicon remain the MMU oracles |

Notable: FS-UAE is the only emulator that survives the integration
corpus tail (MAME fatal-aborts, QEMU core-dumps — finding 23) — 1328
rows on one boot.

These files are emulator baselines, not ground truth. The prize remains
real-silicon runs from A4000/040 owners: anything diverging from the
Quadra captures beyond the classes above is new data.
