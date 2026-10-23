# CPU66 timing experiment 4: predecode FPU hold

Experiment 3 exposed an 11-level path from FPU sub-operation bits through hold, EX advance and operand forwarding. This candidate retains 66/33/99 MHz and seed 38. It decodes eight hold selectors alongside the existing FPU instruction-word decode before EX. The hold output combines the selected wait predicates directly; exception and result logic retain their original priority. The backend uses the interface hold output directly, since that output already includes the qualified EX-valid input.

Eight single-bit registers are added. No pipeline stage, operand/result bank or timing exception is added. A simulation check compares the new hold decision with the original priority expression on every clock, and compares the registered selectors with the live sub-operation for valid FPU uops.

The sequential-FPU configuration passes all 185 CPU tests and four adapter tests. All 185 cycle counts exactly match experiment 2. Evidence is under [timing4](perf/cpu66_20261022/timing4/cycle-comparison.json). Additional pipelined-FPU validation and fitted timing are pending. Experiment 2 remains the best measured build and has passed Mac OS 8.1 boot, benchmarks and shutdown.
