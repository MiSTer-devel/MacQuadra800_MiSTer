# CPU66 timing experiment 3: control before wide datapaths

The [M10K candidate](cpu66-timing-experiment2.md) fits at 33,351 ALMs, only 151 above the frozen minimal 33 MHz core, but misses CPU timing by 1.604 ns. Its worst path starts with EX opcode classification and propagates through stall control to the ATC read address. Another failing path runs from FPU state through the shared sticky shifter to `sh_v` (−1.487 ns, 13 logic levels).

This experiment keeps **66/33/99 MHz**, seed 38, all CPU performance options off, and the existing pipeline depth. Hardware source is pinned by the [manifest](perf/cpu66_20261022/timing3/source-manifest.json); the two RTL commits are `31e5d05` and `649ac36`.

- Register the multiply/divide and slow-operation classifications alongside `ex_u` when DC2 advances. Reuse the existing registered FPU class `ex_kc[0]`. This adds two single-bit flags, moving the opcode decode before EX rather than onto the late stall path. No operand/result bank or issue cycle is added.
- With FPU `PIPE=0`, feed the shared sticky shifter directly from `sh_v`/`sh_cnt`. The only sequential consumer is state `F_SHR`; the disabled arithmetic pipeline cannot issue commands. This removes the state-controlled input selection before the wide barrel shift and sticky reduction. The expression for `PIPE=1` is algebraically unchanged, retaining the original shared-shifter arbitration. No second shifter or new state is introduced.

## Functional evidence

The classification-only version passed all 185 CPU runs and four adapter cases. A new simulation observer compares the registered flags against the original opcode expressions whenever EX holds a valid uop.

With both changes, the complete **37-program × 5-configuration CPU suite** and all four 1×/2× adapter cases pass again, with queue/redirect/classification checks enabled. The [cycle comparison](perf/cpu66_20261022/timing3/combined/cycle-comparison.json) shows **all 185 CPU run cycle counts match experiments 1 and 2 exactly**.

The FPU differential bench also passed **20,000 randomized commands and 2,487 synchronization points** (seed 1), comparing the sequential FPU with the pipelined FPU across precisions, rounding modes, ordinary/special values and enabled exceptions. [Validation summary](perf/cpu66_20261022/timing3/combined/validation.json), [CPU results](perf/cpu66_20261022/timing3/combined/cpu-regression.log) and [FPU results](perf/cpu66_20261022/timing3/combined/fpu-differential.log) are saved. These are functional simulation checks; they do not establish FPGA timing closure.

## FPGA measurement

The isolated fit completed. It uses **33,657 ALMs**, 30,344 registers and 489 M10Ks. CPU setup is **−2.082 ns**, TNS **−567.544 ns**; SDRAM +0.873 ns, bus +1.091 ns, HDMI +0.200 ns, and minimum hold +0.107 ns. [Artifact and source hashes](perf/cpu66_20261022/timing3/fit/artifact.json).

This is worse than experiment 2, which remains the best measured candidate. No hardware promotion was made. The new worst path starts at `ex_u.cond[1]`, passes through FPU hold, EX advance and operand forwarding, and ends at `dc1_a[1]`: 11 logic levels, with 13.068 ns interconnect delay and 3.514 ns cell delay. The original opcode-decode and shared-shifter changes alone did not close the design; placement and the remaining sub-operation decode/stall chain now dominate. Full path reports are preserved in the fit directory. Clocks and timing constraints remain unchanged.
