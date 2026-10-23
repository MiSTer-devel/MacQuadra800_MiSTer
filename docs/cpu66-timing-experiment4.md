# CPU66 timing experiment 4: predecode FPU hold

Experiment 3 exposed an 11-level path from FPU sub-operation bits through hold, EX advance and operand forwarding. This candidate retains 66/33/99 MHz and seed 38. It decodes eight hold selectors alongside the existing FPU instruction-word decode before EX. The hold output combines the selected wait predicates directly; exception and result logic retain their original priority. The backend uses the interface hold output directly, since that output already includes the qualified EX-valid input.

Eight single-bit registers are added. No pipeline stage, operand/result bank or timing exception is added. A simulation check compares the new hold decision with the original priority expression on every clock, and compares the registered selectors with the live sub-operation for valid FPU uops.

The sequential-FPU configuration passes all 185 CPU tests and four adapter tests. All 185 cycle counts exactly match experiment 2. Evidence is under [timing4](perf/cpu66_20261022/timing4/cycle-comparison.json). The pipelined-FPU configuration also passes all 185 CPU runs with the hold equivalence check enabled. Fitted timing is pending. Experiment 2 remains the best measured build and has passed Mac OS 8.1 boot, benchmarks and shutdown.

The isolated fit is running in `/home/alans/mister/q800_cpu66_timing4_s38_20261022`, unit `q800-cpu66-timing4-s38-20261022.service`. [Pinned source manifest](perf/cpu66_20261022/timing4/source-manifest.json). It checks all four D-cache tag RAMs remain M10Ks before fitting, then exports CPU, clock crossing, bus phase and targeted endpoint reports.

## Controlled synthesis comparison

A second isolated directory, `/home/alans/mister/q800_cpu66_timing4_speed_s38_20261022`, uses exactly the same RTL and seed with only `OPTIMIZATION_TECHNIQUE` changed from `BALANCED` to `SPEED`. The main checkout recipe and the normal experiment are unchanged. [Manifest](perf/cpu66_20261022/timing4/speed/source-manifest.json) and [exact recipe patch](perf/cpu66_20261022/timing4/speed/recipe.patch) identify the comparison. Its area and timing must be measured before choosing either recipe.
