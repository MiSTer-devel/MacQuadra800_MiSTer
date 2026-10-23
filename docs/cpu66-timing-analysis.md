# Closing timing at 66 MHz

The first 66 MHz build boots Mac OS 8.1, completes Speedometer Mix/PR and shuts down, with 34,213 ALMs. The exact source, RBF and evidence are preserved on `pipelined-040-66mhz` at `3077255`. Subsequent optimization uses `pipelined-040-66mhz-timing`; the original checkpoint remains frozen.

Current status, 2026-10-23: **66 MHz timing is still open.** Experiment24-small now gives the best useful size/timing result:33,328ALMs (79.52%), CPU setup -1.539ns/TNS -147.124ns, all other setup domains and hold checks positive. It uses the original five RF ports and adds no state or cycle. Mac OS8.1 Finder, clock, Mix3.159, fullPR2.420 and clean shutdown pass on the preserved RBF. A matched A/UX32MB Off run now passes Finder, root shell checks, advancing clock and clean halt. One earlier boot on the old clone2 failed at partial startup and remains unexplained. CD audio is still pending. [Exact checkpoint](../test-builds/cpu66-timing24-small-20261023/README.md), [Mac evidence](perf/cpu66_20261022/timing24/small/mac/result.json).

Experiments21–23 are complete with no global win; [comparison](perf/cpu66_20261022/timing23/results.md). The extra RF read port and word-index scaling variants did not independently justify promotion. [Experiment24](cpu66-timing-experiment24.md) removes an exception-vector dependency from WB address selection and does improve the smaller combined fit. [Experiment25](cpu66-timing-experiment25.md), five FPU decision flags plus one binary-op cycle, is **not retained**: both variants are larger and globally slower. [Experiment26](cpu66-timing-experiment26.md) measures the cache-selector cost; [experiment27](cpu66-timing-experiment27.md) targets the remaining vector-to-address path without new state or cycles. Both26 and27 failed globally and are not retained. Experiment28 also fails CPU timing; [experiment29](cpu66-timing-experiment29.md) is fitting an earlier memory-operand selection using existing EX registers, without new state or cycles. The candidates remain in pinned scratch archives. The main checkout still contains experiment20 until the active flows finish and a measured candidate is selected. The VRAM experiment is deferred until this work is finished.

Measured progress at the unchanged **66/33/99 MHz** and seed 38:

| Candidate | ALMs | CPU setup | CPU TNS | Hardware |
|---|---:|---:|---:|---|
| Original CPU66 | 34,213 | −2.391 ns | −1175.353 ns | Mac pass; A/UX startup fails |
| [FIFO + redirect](cpu66-timing-experiment1.md) | 34,146 | −1.681 ns | −361.024 ns | Mac pass |
| [Tag RAM specialization](cpu66-timing-experiment2.md) | 33,351 | **−1.604 ns** | −229.615 ns | Mac pass; A/UX startup fails |
| [EX classes + FPU shifter](cpu66-timing-experiment3.md) | 33,657 | −2.082 ns | −567.544 ns | Not deployed |
| [FPU hold](cpu66-timing-experiment4.md) | **33,098** | −1.879 ns | −521.688 ns | A/UX startup fails |
| Same RTL, speed synthesis | 33,154 | −1.934 ns | −218.618 ns | Not deployed; HDMI fails |
| [Integer funnel](cpu66-timing-experiment5.md) | 33,192 | −2.394 ns | −308.920 ns | Not deployed |
| [Circular queue](cpu66-timing-experiment6.md) | 33,286 | −2.121 ns | −583.940 ns | Not deployed |
| [Registered cache selector](cpu66-timing-experiment8.md) | 33,323 | −1.648 ns | −397.008 ns | Not deployed |
| [Operand source flags](cpu66-timing-experiment9.md) | 33,202 | −2.281 ns | −630.852 ns | Not deployed |
| [Parallel stalls](cpu66-timing-experiment10.md) | 33,151 | −1.987 ns | −370.294 ns | Not deployed |
| [Parallel stalls + circular queue](cpu66-timing-experiment11.md) | 33,280 | −1.898 ns | **−184.885 ns** | Not deployed |
| [A/UX DBcc compatibility](cpu66-timing-experiment12.md) | 33,335 | −1.667 ns | −196.113 ns | A/UX On/Off pass; Mac boot/Mix/clean halt pass |
| [Remove overwritten bypass](cpu66-timing-experiment13.md) | **33,063** | −2.509 ns | −588.172 ns | Not deployed; not retained |
| [Latched FPU result words](cpu66-timing-experiment14.md) | 33,094 | −1.660 ns | −318.086 ns | Not deployed |
| [Combined FPU/AG bypass removal](cpu66-timing-experiment15.md) | 33,496 | −1.919 ns | −352.419 ns | Not deployed; not retained |

The smallest fit is 137 ALMs below the frozen minimal 33 MHz core (experiment 13), but it regressed timing and is not retained. None closes 66 MHz timing. Experiment 8 fixes the cache tag/way paths without an extra cycle; its worst path is now a late write-back store hold through the serial stall chain into the FIFO immediate field. Experiment 9 regressed timing and will be removed. [Experiment 7](cpu66-timing-experiment7.md), an added cache lookup cycle, was rejected before fitting because split-store tests found a livelock; the tests were retained.

[Controlled A/UX comparison](perf/cpu66_20261022/aux-original66/README.md): the frozen minimal 33 MHz build boots and cleanly halts the same disposable clone that stalls with the frozen original 66 MHz build. Thus the failure predates these timing optimizations. The later DBcc compatibility candidate passes A/UX on clone2 with Ethernet On and Off, including root shell checks and clean halt; an earlier clone4 attempt still failed and its cause is unknown. Follow-up symbol lookup and an exact-byte CPU/adapter/VIA regression reproduce a `SetUpTimeK` 16-bit calibration overflow; the existing four-clock DBcc minimum resolves that reproduction. [Evidence and proposed fix](perf/cpu66_20261022/aux-timek/README.md). [A/UX hardware evidence and limits](perf/cpu66_20261022/timing12/aux/README.md). The temporary debug configuration was removed. The last verified hardware state is the user-clean-halted Mac OS8.1 experiment12; no newer candidate has been deployed.

The detailed path analysis below describes the **original** fitted checkpoint; each experiment links its own measured reports.

**66 MHz looks plausible, but this fit needs several changes.** The worst CPU setup slack is −2.391 ns, with a reported Fmax of 57.01 MHz. Under this fit's clock skew and uncertainty, the worst data path needs to shrink from 16.856 ns to about 14.465 ns (14.2%). The worst paths are control and routing problems, with a separate ALU/forwarding path close behind. Fixing just the highest-ranked endpoint will not close timing.

## What the fitted paths show

These are post-fit slow-model reports (1100 mV, 100 °C), from the preserved seed-38 database, not estimates from source code. A second TimeQuest run expanded the report to the worst 20,000 failing CPU start/end pairs. That limit was reached; the sample contains 1,326 distinct endpoint bits and is **not** a complete failure inventory. [Grouped destinations](perf/cpu66_20261022/s38/analysis/failing-families.json), [representative full paths](perf/cpu66_20261022/s38/analysis/representative_cpu_paths.txt), [SDRAM paths](perf/cpu66_20261022/s38/analysis/ram_paths.txt), and the [reproduction script](perf/cpu66_20261022/s38/analysis/analyze_paths.tcl) are saved.

| Path family | Worst slack | Fitted explanation |
|---|---:|---|
| FPU `unsupp` → sequencer `uq1.disp` | −2.391 ns | FPU hold → EX/DC2/DC1/AG stall chain → FIFO write enable; 11 logic levels, 12.038 ns routing + 4.818 ns cell delay |
| EX operand B → `redir_pc` | −2.340 ns | Operand mux → FDBcc zero test → FPU taken → selected taken → mispredict → early redirect → PC enable; 11 levels, 11.809 ns routing + 5.013 ns cells |
| FPU `unsupp` → D-cache tag read register | −2.261 ns | Same hold/stall chain, then AG advance selects lookup address and tag RAM output; 11 levels, 11.841 ns routing + 4.892 ns cells |
| EX operand selector → `exq_val` | −2.087 ns | Operand mux → ALU addition → result selection → forwarding → registered value for AG; 7 levels, 11.786 ns routing + 4.822 ns cells |
| D-cache engine way selection | −1.757 ns | `m2.r.a` → `f_way` is a further failing family behind the four above; its full path needs a targeted report before choosing a remedy |
| SDRAM request rank bit → command | −0.209 ns | Rank/bank selects stored open row → row equality → command decision; 5 levels, 8.212 ns routing + 2.486 ns cells |

The CPU paths above spend about 70% of their data delay in routing. In the worst sequencer path, shared control nodes have fanout 519 and 252, and the final route to a register enable alone costs 2.481 ns. This supports removing unnecessary late controls and reducing their fanout before adding more pipeline stages or duplicating large datapaths.

The second family is specifically an **FDBcc branch-decision path**, not an integer target-address adder. The fourth family does contain an ALU adder. Their remedies differ.

CPU → bus (+2.504 ns), bus → CPU (+4.084 ns), and bus-phase sampling (+6.293 ns) pass in the original targeted reports. Machine-bus setup is +1.103 ns and minimum hold is +0.217 ns. Those results support retaining the existing 66/33/99 clock arrangement while working inside the CPU. They do not waive the failing internal paths.

## First changes to try, with area held in check

1. **Simplify the second micro-op FIFO slot's write control.** In [the sequencer](../rtl/ap68040_faster/rtl/ap68040_useq.sv), `room_out` is false whenever the two-entry FIFO is full, even if a pop occurs. Therefore `emit` cannot occur at occupancy two. `uq1` only needs the new uop when an emit fills the second slot; writing it on every emit also changes it when that slot is invalid, which is harmless to queue contents. Moving its assignment out of the pop-dependent branch to `if (emit) uq1 <= nu` can remove `uq_pop` and the backend stall chain from that wide register's write control. It adds no registers or queue capacity. An [abstract exhaustive queue check](perf/cpu66_20261022/s38/analysis/fifo_slot_model.py) covered 27 reachable paired states and 162 transitions with matching valid contents; this is a preliminary proof of the queue rule, not RTL/formal or post-fit validation. The first-slot and cache-tag stall paths still need attention.

2. **Remove `ex_early` from the redirect PC bank's enable.** In [the backend](../rtl/ap68040_faster/rtl/ap68040_backend.sv), the current EX redirect captures `redir_pc` only inside `if (ex_early)`, nested under `adv_ex`. A candidate is to capture `ex_next` whenever EX advances, while keeping `redir_v`/`fe_flush` conditional and preserving the later WB/exception assignment priorities. The fetch unit uses this address with `redir_v`; capturing an unused candidate earlier can shorten the late FDBcc decision's route to the 32-bit bank. No extra PC register or branch cycle is required in principle. The data-side `ex_next` selection still has to meet timing, and reset, exceptions, simultaneous WB redirect and RTE must be checked.

3. **Shorten the shared stall/address path before buying a skid stage.** The cache-tag failure remains even if the FIFO change works. First examine whether the FPU hold qualification and the cascaded valid/hold equations can be factored into shallower parallel terms, with local control copies only where needed. The existing `SKID=1` option is a useful comparison experiment, but it stores an entire extra uop and only breaks the sequencer side of the chain. It should not be enabled as an assumed solution to all of these paths. Record its measured ALM cost if tried.

4. **Treat ALU/forwarding as the next independent problem.** `exq_val` is already captured every cycle; another enable rewrite will not fix it. Inspect operand selection and the result/forwarding muxes, and try to shorten or localize that route while retaining the existing arithmetic latency. A new execution pipeline stage would change forwarding/interlocks and needs a broader CPU regression; it is a later option.

5. **Close the small SDRAM miss after CPU changes settle.** This is the existing open-row selection path at an unchanged 99 MHz, not the new CPU/bus crossing. One route is 4.752 ns. A small placement change or a seed may recover 0.209 ns, but it must be measured again after every fit. A logic alternative is a bank-local row comparison followed by selection; that can multiply comparator logic and needs an area check. Keep `open_row` in logic as documented in `sdram.sv`, avoiding the known cross-clock RAM inference problem.

## Experiment sequence and stopping criteria

Start with the FIFO and redirect capture changes separately, then together if each remains correct. Use the same seed and build settings initially, run the existing 1×/2× adapter tests plus directed branch/queue/exception coverage, and compare **worst slack, total negative slack, failing path families and ALMs**, not just the one endpoint that improved. Broaden CPU tests for actual semantic changes, then repeat hardware Mix/PR/shutdown and A/UX before promoting a candidate. Only seed-walk after the structural problems are smaller.

Keep 34,213 ALMs as the reference for this experiment, and 33,200 as the frozen minimal reference. Favor changes with no added wide state first. There is no measured promise that these two small changes alone reach 66 MHz: the cache and ALU families would still fail if their paths were unchanged. Do not add false-path or multicycle exceptions to hide a real single-cycle CPU path.

A 55 MHz CPU with the bus still at 33 MHz is not a drop-in fallback for the current 2:1 bus-enable circuit. Changing the ratio requires another clock/enable and related-clock analysis; scaling the bus as well changes peripheral timing. Keep that as a separate clock-mode experiment if structural timing work cannot retain the area advantage.

Experiments 10/11 are complete. The circular queue plus parallel stalls has the lowest CPU TNS measured so far, with only 80 ALMs above the frozen minimal core, but its worst slack still fails. [Experiment 12](cpu66-timing-experiment12.md) applies the independently committed A/UX compatibility fix; [experiment 13](cpu66-timing-experiment13.md) removes a provably overwritten AG bypass exposed by experiment 11's worst path. Both retain 66/33/99 and the existing pipeline stages.

Experiments 12/13 are complete. The DBcc-only compatibility candidate has better global setup and TNS; the active RTL retains its exact CPU/clock behavior. Experiment 13 is preserved as an area comparison. Experiment 12 still fails CPU setup and is undergoing hardware qualification; it is not a release.

The hardware-tested experiment12 is preserved under [test-builds/cpu66-auxfix-20261022](../test-builds/cpu66-auxfix-20261022/README.md). MacOS8.1 Mix3.160 retains the originalCPU66 performance, and the user's clean shutdown was visually verified. Experiments14/15 complete this comparison: neither closes CPU timing; 14 is smaller but has worse TNS than12, and15 is not retained. FMOVEM arithmetic, fetch-queue arithmetic, branch data and cache maintenance selectors were subsequently tested in experiments16–20; none closed timing. The current results and experiment24 are linked at the top of this document.
