# CPU66 timing experiment 10: parallel stall equations

Experiment 8's worst path is a late store hold through serial pipeline stalls into the wide sequencer head. This candidate expands the five stall equations into equivalent sums of valid-prefix/hold products. Ten preserved combinational prefixes depend only on pipeline valid bits, allowing the late holds to enter each stage in parallel. There are no new flip-flops, wide banks, cycles or timing exceptions. Experiment 9's regressing operand flags are removed; the base is experiment 8.

All 1,024 combinations of the five valid and five hold inputs match the original serial equations. A simulation observer compares the original and new stalls every active clock. All **185 CPU cases and four adapter tests pass**, with all 185 cycle counts matching experiment 8 exactly. [Validation](perf/cpu66_20261022/timing10/validation.json).

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fit complete: **33,151 ALMs**, CPU setup **-1.987 ns**, CPU TNS **-370.294 ns**. SDRAM +0.533 ns, bus +0.842 ns, HDMI +0.653 ns and minimum hold +0.167 ns pass. [Reports and RBF hashes](perf/cpu66_20261022/timing10/fit/artifact.json). CPU timing still fails; this candidate is not hardware qualified. The original two-slot queue is retained in this candidate.

The remaining worst path is fetch `qw[0][4]` → decoder word consumption/selection → registered attribute-ROM address, 11 logic levels. Area is 49 ALMs below the frozen minimal core, but the circular comparison has better global worst slack and TNS.
