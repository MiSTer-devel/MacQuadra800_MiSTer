# CPU66 timing experiment 14: use latched FPU words directly for results

Experiment 12's worst path starts at EX sub-operation bit 2, selects between current CHK words and latched words, decodes the FPU format, then traverses result selection and operand forwarding. Every result-producing sub-operation differs from `FC_CHK`, so it always uses the latched instruction words. The current-word selection is unnecessary on that path.

This candidate uses `ext_q` and `opw_q` directly in the result block's DISP format/destination tests, COND predicate selection and SV0 direction test. CHK's own current-word decode, the rest of the interface, its state machine and all clock behavior retain their existing expressions. No register, wide bank or pipeline cycle is added. The base is experiment 12; experiment 13's regressing AG rewrite remains removed.

A simulation-only copy of the entire original result expression is compared unconditionally on every active clock, including zero results and inactive EX cases. All **185 CPU cases and four adapters pass** with exactly matching cycle counts to the floor-four baseline. [Validation](perf/cpu66_20261022/timing14/validation.json).

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fitted results are pending. The existing four-clock DBcc integration setting remains enabled only for the 2× CPU.
