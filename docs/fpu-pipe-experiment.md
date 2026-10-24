# FPU_PIPE at 33 MHz

Retain `FPU_PIPE=0` for the smaller default. Enabling the existing FPU
pipeline adds 1,077 ALMs (3.12%) for a measured 0.67–1.21% gain in the
separate FPU suite, with no improvement in PR Math. Each hardware suite
used one iteration; the small score changes do not establish a repeatable
performance gain. The experimental source and exact RBF remain preserved.

## Controlled comparison

The experiment branches from memory checkpoint `6bfd9c0`, tagged
`pipelined-040-dual-memory-20261023`. The only functional RTL change is
`.FPU_PIPE(0)` to `.FPU_PIPE(1)` in the CPU wrapper. CPU/bus/SDRAM remain
33/33/99 MHz, seed 38, with posted non-faulting VRAM retirement enabled.
LOOP_PRED, EARLY_RES, SKID and DC1_ATC remain off; DUAL and BTIC remain on;
S1_CLASSES stays `011`, keeping second-slot loads off. Caches remain 8+8 KB.

The arithmetic pipeline handles eligible FMOVE/FABS/FNEG/FADD/FSUB/FMUL
operations and forwards results between stages. Its eligibility guard
requires every FPCR exception enable clear; the sequential engine handles
other operands and operations. This experiment does not relax that guard.
There is no fresh workload trace proving the reason for the small hardware
gain, so it should not be attributed to eligibility alone.

Both exact RBFs used the same disposable Mac OS 8.1 image, 32 MB RAM,
Ethernet Off, restored baseline PRAM, and the same suite order: first FPU,
Mix, after-Mix FPU, then full PR. Original user disk images were untouched.
The new baseline avoids attributing a memory-port effect to FPU_PIPE.

| Metric | Memory baseline, PIPE=0 | Candidate, PIPE=1 | Change |
|---|---:|---:|---:|
| FPU first | 0.741 | 0.750 | +1.21% |
| FPU after Mix | 0.744 | 0.749 | +0.67% |
| Mix | 1.802 | 1.806 | +0.22% |
| PR overall | 1.604 | 1.623 | +1.18% |
| PR CPU | 1.807 | 1.806 | −0.06% |
| PR graphics | 0.985 | 0.985 | unchanged |
| PR disk | 2.228 | 2.417 | +8.48% |
| PR Math | 13.313 | 13.313 | unchanged |
| ALMs | 34,554 (82.45%) | 35,631 (85.02%) | +1,077 (+3.12%) |
| Fitted registers | 30,052 | 31,097 | +1,045 |
| M10Ks | 497 / 553 | 497 / 553 | unchanged |
| DSPs | 38 | 38 | unchanged |
| CPU/bus setup slack | +1.245 ns | +0.964 ns | −0.281 ns |
| SDRAM setup slack | +0.511 ns | +0.377 ns | −0.134 ns |
| HDMI setup slack | +0.668 ns | +0.357 ns | −0.311 ns |
| Minimum hold slack | +0.194 ns | +0.109 ns | −0.085 ns |

All scores are higher-is-better. FPU ratings normalize to Quadra 650 = 1;
Mix uses Quadra 605 = 1. PR is the separate performance-rating suite.
The PR overall improvement accompanies disk variation; CPU, graphics and
Math do not improve. Do not treat that disk change as an FPU benefit.

After-Mix FPU details: baseline/candidate KWhetstones/s 3508.624/3573.164,
matrix 0.829/0.827 s, FFT 0.406/0.406 s. The largest difference is in
Whetstone; matrix and FFT are essentially unchanged.

## Validation and artifacts

225 existing CPU cases and all six Quadra adapter cases pass with the
hardware option selection explicitly set. The adapter cases cover both
clock ratios and normal/fast/platform operation, including posted VRAM
retirement. Earlier general regressions had enabled LOOP_PRED/EARLY_RES
through testbench defaults; these new runs match the candidate options.

The existing differential FPU bench also passes 20,000 mixed commands and
20,000 pipeline-focused commands, comparing registers and FPSR against
PIPE=0. Those benches take 145,250→136,776 and 119,017→86,398 cycles
respectively; these are standalone eligible-workload results, separate
from the measured Mac application scores.

All 41 setup, hold, recovery, removal and pulse checks pass. The fit retains
36 RF MLAB banks, four cache-tag M10Ks and three OSD/LCD M10Ks. Block memory
bits remain 3,722,339 and DSPs remain 38. Eight additional timing-path reports
are preserved. The mapped-register increase from 29,318 to 30,241 supports
that pipeline registers remain in the fit, but is not a witness of pipeline
activity during Speedometer.

- Source: `bd398e4bcaa644223f45a1c25e4e8008b87ea940`.
- Baseline RBF MD5: `500c366118057e8034d7a93d93dd107f`.
- Candidate RBF MD5: `f1289c23369dda33a76bb79ef33123b1`.
- Candidate SHA256: `b34586c5c0af555922158bdd57731f0ee08eca5e4549bfca213c5cb4756a3c15`.
The evidence directory and the candidate RBF are committed on the
experiment's own branch and tag only, `pipelined-040-dual-fpu-pipe` /
`pipelined-040-dual-fpu-pipe-20261024` (pushed to `alanswx`); this report
is the one file carried onto the memory branch, so the links below point
at the tag:

- Exact candidate: [RBF and manifest](https://github.com/alanswx/MacQuadra800_MiSTer/tree/pipelined-040-dual-fpu-pipe-20261024/test-builds/pipelined-040-dual-fpu-pipe-20261024/33mhz).
- [Matched baseline evidence](https://github.com/alanswx/MacQuadra800_MiSTer/tree/pipelined-040-dual-fpu-pipe-20261024/docs/perf/fpu_pipe_20261024/baseline33/mac).
- [Candidate evidence](https://github.com/alanswx/MacQuadra800_MiSTer/tree/pipelined-040-dual-fpu-pipe-20261024/docs/perf/fpu_pipe_20261024/candidate33/mac).
- [Fit and timing reports](https://github.com/alanswx/MacQuadra800_MiSTer/tree/pipelined-040-dual-fpu-pipe-20261024/docs/perf/fpu_pipe_20261024/fit-s38).
- [Source manifest](https://github.com/alanswx/MacQuadra800_MiSTer/blob/pipelined-040-dual-fpu-pipe-20261024/docs/perf/fpu_pipe_20261024/source-manifest.json).
- Locally: `git show pipelined-040-dual-fpu-pipe-20261024:docs/perf/fpu_pipe_20261024/comparison.json`.

This is an experimental benchmark qualification, not a release. A/UX and
CD audio were not requalified for this candidate. Clean Finder shutdown
reached the explicit safe-to-switch-off screen. The input controller closed
with button-up, the board returned to Menu, and original S0/PRAM bytes were
restored with S2/CFG still absent. See the candidate final-state record.
