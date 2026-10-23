# CPU66 timing experiment 4: predecode FPU hold

Experiment 3 exposed an 11-level path from FPU sub-operation bits through hold, EX advance and operand forwarding. This candidate retains 66/33/99 MHz and seed 38. It decodes eight hold selectors alongside the existing FPU instruction-word decode before EX. The hold output combines the selected wait predicates directly; exception and result logic retain their original priority. The backend uses the interface hold output directly, since that output already includes the qualified EX-valid input.

Eight single-bit registers are added. No pipeline stage, operand/result bank or timing exception is added. A simulation check compares the new hold decision with the original priority expression on every clock, and compares the registered selectors with the live sub-operation for valid FPU uops.

The sequential-FPU configuration passes all 185 CPU tests and four adapter tests. All 185 cycle counts exactly match experiment 2. Evidence is under [timing4](perf/cpu66_20261022/timing4/cycle-comparison.json). The pipelined-FPU configuration also passes all 185 CPU runs with the hold equivalence check enabled. Fitted timing is pending. Experiment 2 remains the best measured build and has passed Mac OS 8.1 boot, benchmarks and shutdown.

The isolated fit is running in `/home/alans/mister/q800_cpu66_timing4_s38_20261022`, unit `q800-cpu66-timing4-s38-20261022.service`. [Pinned source manifest](perf/cpu66_20261022/timing4/source-manifest.json). It checks all four D-cache tag RAMs remain M10Ks before fitting, then exports CPU, clock crossing, bus phase and targeted endpoint reports.

## Controlled synthesis comparison

A second isolated directory, `/home/alans/mister/q800_cpu66_timing4_speed_s38_20261022`, uses exactly the same RTL and seed with only `OPTIMIZATION_TECHNIQUE` changed from `BALANCED` to `SPEED`. The main checkout recipe and the normal experiment are unchanged. [Manifest](perf/cpu66_20261022/timing4/speed/source-manifest.json) and [exact recipe patch](perf/cpu66_20261022/timing4/speed/recipe.patch) identify the comparison. Its area and timing must be measured before choosing either recipe.

## Normal recipe fit result

The normal fit completed at **33,098 ALMs**, 30,143 registers and 489 M10Ks: 102 ALMs fewer than the frozen minimal 33 MHz build. CPU setup is **−1.879 ns**, TNS **−521.688 ns**. SDRAM +1.171 ns, bus +1.258 ns, HDMI +0.637 ns and minimum hold +0.187 ns pass. [Artifact and hashes](perf/cpu66_20261022/timing4/fit/artifact.json).

The targeted cache-tag path passes at **+0.578 ns**, redirect +0.903 ns and second FIFO +0.119 ns. First FIFO still misses by 1.314 ns and ALU forwarding by 1.067 ns. The new overall worst path is `ex_b[12]` → operand selection → shift/rotate funnel → `xs_q.res[4]`, with 12 logic levels. The FPU control rewrite helps the intended family and area, but experiment 2 still has the best CPU slack/TNS. This candidate has not been deployed. Speed-synthesis results remain pending.

## Speed recipe fit result

Speed synthesis completed at **33,154 ALMs**, 30,379 registers and 490 M10Ks. CPU setup is **−1.934 ns**, TNS **−218.618 ns**. SDRAM +0.325 ns, bus +1.168 ns and minimum hold +0.098 ns pass; HDMI misses by **0.043 ns**. [Artifact and hashes](perf/cpu66_20261022/timing4/speed/fit/artifact.json).

Its worst path is fetch queue `qw[0][1]` → decoder attribute-ROM address, 12 logic levels. The recipe improves CPU TNS, but does not improve the worst CPU slack and introduces an HDMI miss. Retain the normal recipe for the next targeted RTL experiment. Neither fourth-experiment RBF has been hardware qualified.

## A/UX comparison

The normal RBF was tried with a fresh verified copy of the known working A/UX image, 32 MB and Ethernet Off. It remained gray at 94 and 252 seconds with no disk-I/O progress. The user authorized recovery resets of the disposable test clone. The frozen 33 MHz minimal RBF then booted the **same clone with the same settings** to Unix Finder, returned normal `uname -a`, `date` and `df` results, and shut down to the explicit safe screen. [CPU66 record](perf/cpu66_20261022/timing4/aux/run.json), [matched baseline](perf/cpu66_20261022/timing4/aux/baseline33/run.json).

This rules out a persistently unbootable clone/setup for that comparison, but does not distinguish physical timing from CPU66 integration or later RTL changes. No 66 MHz A/UX pass is claimed. The test MiSTer is left safely halted after the baseline check.
