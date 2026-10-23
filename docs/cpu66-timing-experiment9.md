# CPU66 timing experiment 9: predecode EX memory operand selects

This compares the [registered engine transparency candidate](cpu66-timing-experiment8.md) with two more single-bit classifications loaded alongside `ex_u`: whether operand A/B comes from memory. The EX operand muxes use those flags rather than comparing the two-bit source fields on the ALU data path. Raw operand registers and sign extension retain their existing behavior.

The simulation classification observer also compares both memory-source flags with the original source expressions for every valid EX uop. All **185 CPU cases and four adapter tests pass**, and all 185 cycle counts match experiment 8. [Validation](perf/cpu66_20261022/timing9/validation.json). No wide bank, cycle or timing exception is added.

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fit complete: **33,202 ALMs**, CPU setup **-2.281 ns**, CPU TNS **-630.852 ns**. SDRAM +1.195 ns, bus +1.425 ns, HDMI +0.503 ns and minimum hold +0.138 ns pass. [Reports and RBF hashes](perf/cpu66_20261022/timing9/fit/artifact.json). This is not timing qualified and has not been hardware tested.

The two extra operand flags regressed global setup and total negative slack. The worst path is `ex_ld[3]` → operand/ALU/forwarding → `dc1_b[10]`, 11 logic levels. The flags will be removed for the next candidate; this fitted comparison remains preserved.
