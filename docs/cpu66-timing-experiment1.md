# CPU66 timing experiment 1

This experiment keeps CPU/bus/SDRAM at **66/33/99 MHz**, seed 38 and the existing CPU options. The reference is the hardware-tested `397f3df` RBF, preserved on `pipelined-040-66mhz` at `3077255`: 34,213 ALMs, CPU setup −2.391 ns, CPU TNS −1175.353 ns and SDRAM setup −0.209 ns. Work continues on `pipelined-040-66mhz-timing`.

Two changes from the [path analysis](cpu66-timing-analysis.md) are pinned in hardware source **`4b18c73`**:

- `1c70092`: write the second micro-op slot on `emit`, independently of the late backend pop. `room_out` prevents emitting into a full FIFO; writes to an invalid second slot are harmless. Queue capacity and issue timing are unchanged.
- `4b18c73`: capture `redir_pc = ex_next` on every EX advance. The valid/flush decision remains conditional on early redirect, and the later WB/refetch writes retain priority. This removes the late branch decision from the PC bank's enable.

Neither change introduces another pipeline stage or wide register bank. No clock or timing exception was changed. The first fit will establish their actual logic cost and whether the targeted paths improve.

## Functional validation

The FIFO-only change passed the 1× adapter workload with normal and fast acknowledgements. Both changes together pass all four 1×/2× adapter cases with **exactly the reference cycle and bus-beat counts**. [Results](perf/cpu66_20261022/timing1/combined/adapter-results.json) and logs are saved.

Simulation-only observers retain the old FIFO rules and compare every valid queue entry at each clock; a second observer retains the old redirect-PC assignment priorities and compares every consumed redirect address. These checks are compiled into the benches, outside the synthesis file list. They cover empty/full queue transitions, simultaneous enqueue/dequeue, and overlapping EX advances with older redirects.

The complete CPU suite passed **37 programs × 5 bus configurations = 185 runs**, plus the exhaustive decoder check, with `FPU_PIPE`, `LOOP_PRED`, `EARLY_RES`, `SKID` and `DC1_ATC` all zero, matching the minimal build. Configurations cover zero/random waits, burst inhibit/retry, half-speed BCLK, and the combined case. [Summary](perf/cpu66_20261022/timing1/combined/cpu-regression.json) and [full results](perf/cpu66_20261022/timing1/combined/cpu-regression.log) are archived.

[Directed coverage captures](perf/cpu66_20261022/timing1/combined/coverage/coverage.json) include 1,919 EX redirects and 270 WB redirects in `t_eredir`, 428 overlapping EX-advance/older-redirect events and a refetch in `t_exceptions`, plus FPU exceptions and halt/reset tests. Every consumed redirect matched the old rule. This is simulation evidence, not a formal proof or timing qualification.

The existing test runner gained NUL-separated `xargs` input for macOS/Linux portability and an optional `EXTRA_SV` input after the package files for these observers. CPU microcode generation ran in an isolated test copy, and did not modify the FPGA source inputs.

## FPGA measurement

Build root: `/home/alans/mister/q800_cpu66_timing1_s38_20261022`, unit `q800-cpu66-timing1-s38-20261022.service`. The [source manifest](perf/cpu66_20261022/timing1/source-manifest.json) records the full commit and verified archive hash. This is an isolated project/database, so the user-authorized parallel-flow mode uses `--no-wait` without pausing other projects.

Synthesis and fitting completed successfully. Timing still fails on the CPU; all other reported domains pass. [Fit evidence and artifact identity](perf/cpu66_20261022/timing1/fit/artifact.json) are saved alongside the reports.

| Metric | Original CPU66 | Experiment 1 |
|---|---:|---:|
| ALMs | 34,213 | **34,146** (−67) |
| CPU worst setup | −2.391 ns | **−1.681 ns** |
| CPU total negative slack | −1175.353 ns | **−361.024 ns** |
| SDRAM setup | −0.209 ns | **+0.363 ns** |
| Machine-bus setup | +1.103 ns | +0.900 ns |
| HDMI setup | +0.461 ns | +0.348 ns |
| Minimum hold | +0.217 ns | +0.245 ns |

Matched endpoint reports show that the two targeted paths now pass: second FIFO slot **+0.924 ns** (was −2.391), redirect PC **+0.406 ns** (was −2.340). Other endpoint families: cache tag −1.681, first FIFO slot −1.162, ALU forwarding −0.403, cache engine way −0.299 ns. These include placement effects and do not attribute every improvement solely to one source edit.

The new worst CPU path ends at the D-cache tag read register. A separate synthesis probe found that the generic two-write-port RAM template drops its M10K attribute and is re-inferred as two AUTO memories, even with port A's write tied low. A literal single-write template infers one true-dual-port M10K with the same latency. The next experiment specializes this unused port at elaboration time, retaining the generic default behavior. This targets both the remaining cache path and logic area, without adding another pipeline stage.

The experiment-1 RBF is preserved locally as `scratch/cpu66-timing/fit1/MacQuadra800.rbf`, MD5 `ffa8200338924982c1d5479fb3a70dd5`. It passed Mac OS 8.1 boot, Speedometer Mix **3.162**, Performance Rating **2.469**, and clean Finder shutdown on `.192`, using the cloned CPU66 disk at 32 MB/Ethernet Off. [Hardware records and captures](perf/cpu66_20261022/timing1/hardware/run.json) are saved. The halt capture was delayed by report analysis, so its timestamp bounds observation rather than actual shutdown duration. A/UX is not yet qualified for this candidate. The tester ZIP and frozen hardware-tested branch still contain the original RBF.
