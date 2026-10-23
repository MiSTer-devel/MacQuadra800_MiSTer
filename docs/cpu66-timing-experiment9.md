# CPU66 timing experiment 9: predecode EX memory operand selects

This compares the [registered engine transparency candidate](cpu66-timing-experiment8.md) with two more single-bit classifications loaded alongside `ex_u`: whether operand A/B comes from memory. The EX operand muxes use those flags rather than comparing the two-bit source fields on the ALU data path. Raw operand registers and sign extension retain their existing behavior.

The simulation classification observer also compares both memory-source flags with the original source expressions for every valid EX uop. All **185 CPU cases and four adapter tests pass**, and all 185 cycle counts match experiment 8. [Validation](perf/cpu66_20261022/timing9/validation.json). No wide bank, cycle or timing exception is added.

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fitted results are pending.
