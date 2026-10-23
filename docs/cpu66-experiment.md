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

FPGA synthesis, placement, timing, and hardware boot are pending. The old 33 MHz fit has a 21.511 ns CPU-internal data path, so a new fit must establish the achievable 66 MHz timing; the period is 15.152 ns. No timing exceptions have been added for the new CPU/bus paths. `scripts/cpu/timequest_cpu_bus.tcl` reports both crossing directions, internal CPU paths, and the phase register after fitting.

The published 33 MHz minimal artifact remains intact. Hardware trials use a separate Mac OS disk copy on `.192`; `.14` stays on its existing session. This is a fixed-clock experiment, with the OSD clock selector deferred until a useful mode is established.
