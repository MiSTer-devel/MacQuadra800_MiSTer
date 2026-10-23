# CPU66 timing experiment 14: use latched FPU words directly for results

Experiment 12's worst path starts at EX sub-operation bit 2, selects between current CHK words and latched words, decodes the FPU format, then traverses result selection and operand forwarding. Every result-producing sub-operation differs from `FC_CHK`, so it always uses the latched instruction words. The current-word selection is unnecessary on that path.

This candidate uses `ext_q` and `opw_q` directly in the result block's DISP format/destination tests, COND predicate selection and SV0 direction test. CHK's own current-word decode, the rest of the interface, its state machine and all clock behavior retain their existing expressions. No register, wide bank or pipeline cycle is added. The base is experiment 12; experiment 13's regressing AG rewrite remains removed.

A simulation-only copy of the entire original result expression is compared unconditionally on every active clock, including zero results and inactive EX cases. All **185 CPU cases and four adapters pass** with exactly matching cycle counts to the floor-four baseline. [Validation](perf/cpu66_20261022/timing14/validation.json).

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fit complete: **33,094 ALMs**, CPU setup **-1.660 ns**, CPU TNS **-318.086 ns**. SDRAM +0.540 ns, bus +1.083 ns, HDMI +0.709 ns and minimum hold +0.189 ns pass. [Reports and RBF hashes](perf/cpu66_20261022/timing14/fit/artifact.json). CPU timing still fails; this variant has not been deployed. The existing four-clock DBcc integration setting remains enabled only for the 2× CPU.

The FPU word-selection path improved, but global worst slack remains −1.660 ns. The new worst path is a memory operand into FMOVEM's dynamic-list population count, byte-count arithmetic, result selection and forwarding into `dc1_b[8]`, 11 logic levels. This exposes a further combinational optimization: compute signed byte contributions for each nibble and combine them with one small sum.
