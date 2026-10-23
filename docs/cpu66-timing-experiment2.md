# CPU66 timing experiment 2: tag RAM inference

Hardware source `4504365` keeps the successful queue/redirect rewrites from [experiment 1](cpu66-timing-experiment1.md) and specializes the D-cache tag RAM's unused write port. CPU/bus/SDRAM remain **66/33/99 MHz**, seed 38, with the minimal CPU options unchanged. The first experiment's post-fit reference is 34,146 ALMs and CPU worst setup −1.681 ns; other clocks passed.

## Change and inference evidence

The generic `ap68040_tdp` source has two conditional writes in one clocked process. In Quartus 17 the M10K attribute on that template is rejected, even when port A's write is tied low at the instance. Later optimization infers AUTO memories instead. Simply qualifying the write with a constant parameter inside that same process did not fix the early inference failure.

The new `WRITE_A` parameter defaults to 1, retaining the generic two-write-port behavior. When it is 0, a generate branch elaborates a literal single-write template: both ports still read, only B writes. The four D-cache tag instances select this mode because their A write input was already tied low. The registered-address/read latency and external write-bypass rules are unchanged, and no pipeline state was added.

The [original probe](perf/cpu66_20261022/timing2/tag-probe/original/cache_tag_probe.map.rpt) infers two AUTO simple-dual-port copies. The [exact specialized probe](perf/cpu66_20261022/timing2/tag-probe/generated/cache_tag_probe.map.rpt) infers one true-dual-port M10K, 64 × 22 bits. Their source and project files are archived beside the reports.

Full-core synthesis passed and the build guard verified [all four tag memories are M10Ks](perf/cpu66_20261022/timing2/tag-inference.txt) before allowing the fit to continue. Synthesis registers fell from 29,855 to **28,402** (−1,453); block-memory bits fell from 3,616,611 to 3,613,795. DSPs remain 38 and PLLs 4.

The completed fit uses **33,351 ALMs**, down 795 from experiment 1 and 862 from the original CPU66 fit. This is only 151 ALMs (0.45%) above the frozen minimal 33 MHz artifact. Actual fitted registers are 30,325; M10Ks 489/553 (+2 from experiment 1).

CPU setup still fails at **−1.604 ns**, TNS **−229.615 ns**. SDRAM +0.661 ns, machine bus +0.959 ns, HDMI +0.103 ns and minimum hold +0.183 ns pass. The formerly worst tag-read path improves to −0.805 ns; the new worst path runs from EX opcode classification through stall control into the address-translation lookup. FPU state-to-shifter control also fails at −1.487 ns. [Reports and artifact identity](perf/cpu66_20261022/timing2/fit/artifact.json) are archived.

## Validation and build

The [tag RAM test](perf/cpu66_20261022/timing2/tag-ram.log) checks read latency, raw old data, both read results and write bypass against a software memory model. It passed 8,192 cycles with 4,065 writes and 1,064 same-address read/write collisions. The four 1×/2× adapter cases retain the original cycle/beat counts and pass the queue/redirect observers. The complete CPU suite again passed all **185 runs** across five bus configurations, plus the exhaustive decoder check. [Results](perf/cpu66_20261022/timing2/validation.json) and logs are archived.

The [source manifest](perf/cpu66_20261022/timing2/source-manifest.json) pins the build in `/home/alans/mister/q800_cpu66_timing2_s38_20261022`. Fitting and STA completed; the wrapper correctly rejects the CPU timing miss. The endpoint-report script needed a follow-up run to use packed M10K address-register names in place of the old tag output flops; that diagnostic retry passed. The RBF's MD5 is `870bcaf84f21b741126f855808231662`. Hardware testing is in progress; it is not packaged for testers. The existing Downloads ZIP remains the original tested CPU66 build.

## Mac OS 8.1 hardware result

The exact RBF above passed boot, Speedometer Mix **3.162**, PR **2.467** (CPU 3.474, graphics 1.397, disk 2.787, math 26.636), and clean Finder shutdown on `.192`, using the cloned CPU66 disk with 32 MB and Ethernet Off. The safe halt was captured within 17.51 seconds of releasing Shut Down; this is an observation bound, not the shutdown duration. [Run record](perf/cpu66_20261022/timing2/hardware/run.json). A/UX and CD audio remain unqualified at 66 MHz.
