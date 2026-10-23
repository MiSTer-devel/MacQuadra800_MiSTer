# CPU66 timing experiment 12: A/UX DBcc compatibility

This fits experiment 11 with the independently committed integration fix `f8aa787`: the existing CPU `dbcc_floor` input is four CPU clocks in the 2× configuration, zero in the 1× configuration. It prevents A/UX's 16-bit `SetUpTimeK` trial count from overflowing when the warm bare DBcc loop is faster than the firmware anticipated. Other instruction classes retain their existing timing. The core's existing floor counter is enabled; no new pipeline stage or wide bank is added.

[Exact guest-byte reproduction](perf/cpu66_20261022/aux-timek/README.md) compares the real CPU adapter and VIA at 1×, 2× with floor zero, and 2× with floor four. Both original and optimized CPU sources reproduce the overflow at 2×/zero and return with the other two settings. [185 CPU cases and four adapters](perf/cpu66_20261022/aux-timek/floor4-regression/validation.json) pass with the fix. The 1× adapter counts are unchanged. This source is the exact wrapper tested there; the floor change intentionally changes some 2× loop timing.

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fit complete: **33,335 ALMs**, CPU setup **-1.667 ns**, CPU TNS **-196.113 ns**. SDRAM +0.366 ns, bus +0.830 ns, HDMI +0.329 ns and minimum hold +0.130 ns pass. [Reports and RBF hashes](perf/cpu66_20261022/timing12/fit/artifact.json). CPU timing still fails.

The remaining worst path is EX condition bit 2 → FPU extension decode/result selection → forwarding → `dc1_a[26]`, 11 logic levels. The exact bitstream is undergoing A/UX hardware testing on the same clone and PRAM; no boot/shutdown PASS is claimed yet.
