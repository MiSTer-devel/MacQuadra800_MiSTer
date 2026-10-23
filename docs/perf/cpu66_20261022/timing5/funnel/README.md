The reference is the pre-change `ap68040_alu_slow.sv` at commit `6167f2d`, with only its module renamed. The bench compares result, flags, funnel carry and both count-decode outputs for all 128 opcode × 4 size × 64 count × 32 flag combinations, using deterministic randomized operands: 1,048,576 vectors.

Reproduce from the repository root:

```sh
verilator --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir scratch/funnel-check -o funnel_miter rtl/ap68040_faster/rtl/ap68040_pkg.sv docs/perf/cpu66_20261022/timing5/funnel/reference.sv rtl/ap68040_faster/rtl/ap68040_alu_slow.sv docs/perf/cpu66_20261022/timing5/funnel/tb.sv
scratch/funnel-check/funnel_miter
```
