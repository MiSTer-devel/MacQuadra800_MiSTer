# CPU66 timing experiment 10: parallel stall equations

Experiment 8's worst path is a late store hold through serial pipeline stalls into the wide sequencer head. This candidate expands the five stall equations into equivalent sums of valid-prefix/hold products. Ten preserved combinational prefixes depend only on pipeline valid bits, allowing the late holds to enter each stage in parallel. There are no new flip-flops, wide banks, cycles or timing exceptions. Experiment 9's regressing operand flags are removed; the base is experiment 8.

All 1,024 combinations of the five valid and five hold inputs match the original serial equations. A simulation observer compares the original and new stalls every active clock. All **185 CPU cases and four adapter tests pass**, with all 185 cycle counts matching experiment 8 exactly. [Validation](perf/cpu66_20261022/timing10/validation.json).

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fitted results are pending. The original two-slot queue is retained in this candidate.
