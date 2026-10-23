# Fixed 66 MHz CPU experiment

Branch `pipelined-040-66mhz` starts from the published minimal checkpoint `ca780e8` (`pipelined-040-min-20261022`). It enables `CPU_AP68040_2X` to run the existing pipelined AP68040 at 66 MHz, with the machine bus at 33 MHz and SDRAM at 99 MHz. The CPU's internal configuration and performance options are unchanged.

The main PLL provides a third, phase-aligned 66 MHz output. The Quadra adapter and all peripherals remain on the 33 MHz clock. At the falling CPU-clock edge, sampling the low bus-clock phase enables the next coincident CPU/bus rising edge. This gives `bclk_en` a deterministic phase; the CPU samples and drives its external bus only once per 33 MHz cycle. The retired-PC debug registers use the CPU clock. The OSD version identifies the fixed `66MHz` build.

## Validation so far

The existing adapter workload passes at both 1:1 and 2:1 processor/bus ratios, with normal and fast acknowledgements. It covers transfer sizes, misalignment, cache fills/pushes, interrupts including the copy stress case, and FPU operations. The 2:1 bench additionally asserts the bus-enable phase at every processor edge. [Results](perf/cpu66_20261022/adapter-results.json) and the four run logs are archived alongside it.

Run with:

```sh
make -C verilator tb_quadra_cpu040
make -C verilator tb_quadra_cpu040_2x
```

## First FPGA fit and hardware boot

Seed 38, hardware source `397f3df`, synthesized and fitted successfully on 2026-10-22. The resulting bitstream **boots Mac OS 8.1 to Finder** on `.192`, with 32 MB and Ethernet Off. The [desktop capture](perf/cpu66_20261022/s38/desktop.png) was taken about 67 seconds after loading the core; [OSD settings](perf/cpu66_20261022/s38/osd.png) were checked afterward. This is an experimental hardware result, not timing qualification.

| Check | Result |
|---|---:|
| ALMs | 34,213 / 41,910 (82%) |
| Increase over minimal 33 MHz build | 1,013 ALMs (3.05%) |
| CPU 66 MHz setup slack | **−2.391 ns** |
| SDRAM 99 MHz setup slack | **−0.209 ns** |
| Machine bus 33 MHz setup slack | +1.103 ns |
| CPU → bus setup slack | +2.504 ns |
| Bus → CPU setup slack | +4.084 ns |
| Bus-phase sampling register setup slack | +6.293 ns |
| Minimum hold slack | +0.217 ns |

The CPU and SDRAM setup failures make the build unsuitable for release. The build wrapper correctly returned failure for timing despite producing an RBF. The worst CPU paths include FPU `unsupp` into the microsequencer dispatch and execution-backend branch redirect logic. The reported CPU Fmax is 57.01 MHz; SDRAM Fmax is 96.99 MHz. Passing the interface checks and one hardware boot does not establish reliable operation across boards or conditions. No timing exceptions have been added for the new CPU/bus paths.

Speedometer 4.02 completed a one-iteration [Benchmark Mix](perf/cpu66_20261022/s38/mix-complete.png), scoring **3.162**, compared with the minimal 33 MHz build's [1.611](perf/shutdown_20261022/min-mix-complete.png): a 1.963× result in this single-run comparison. [Performance Rating](perf/cpu66_20261022/s38/pr-complete.png) also completed: overall 2.456, CPU 3.468, graphics 1.463, disk 2.413, math 26.633. These are initial smoke-test measurements; disk performance depends on host/storage activity, and the timing failures remain unresolved.

After both tests, Speedometer was quit with No at the save prompt. A continuous Finder mouse gesture [selected Shut Down](perf/cpu66_20261022/s38/shutdown-selected.png); the [safe-to-switch-off screen](perf/cpu66_20261022/s38/halted.png) was observed within 15 seconds. `.192` was left halted. A/UX has not yet been tested at 66 MHz.

The [artifact manifest](perf/cpu66_20261022/s38/artifact.json), [fit summary](perf/cpu66_20261022/s38/MacQuadra800.fit.summary), [timing summary](perf/cpu66_20261022/s38/MacQuadra800.sta.summary), full STA report, and targeted CPU/bus reports are archived in the same directory. `scripts/cpu/timequest_cpu_bus.tcl` produces the targeted reports. The experimental RBF is `scratch/cpu66-s38/MacQuadra800_cpu66_s38.rbf` locally and `/media/fat/_Development/MacQuadra800_cpu66_s38.rbf` on `.192`; MD5 `238b10a91e219725fdcc90ff73e8848b` was verified before loading.

The published 33 MHz minimal artifact remains intact. Hardware trials use a separate Mac OS disk copy on `.192`; `.14` stays on its existing session. This is a fixed-clock experiment, with the OSD clock selector deferred until a useful mode is established.
