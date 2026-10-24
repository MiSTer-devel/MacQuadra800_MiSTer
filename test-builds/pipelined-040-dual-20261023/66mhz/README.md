# Experimental dual issue Quadra at 66 MHz

CPU 66 MHz, bus 33 MHz, SDRAM 99 MHz. This exact RBF uses upstream
faster eed15a0 plus the retained Quadra fixes and Quartus17 representation
workarounds. Source88a3b0b with CPU_AP68040_2X and RAM-budget fallback
OFF; the full manifest is docs/perf/dual_20261023/66mhz/r3/source-manifest.json.

CPU timing FAILS: setup -3.308 ns, TNS -2114.552 ns. Other clock setup
and all hold checks pass (SDRAM +0.335 ns, bus +1.040 ns, HDMI +0.269 ns,
minimum hold +0.180 ns). Whole core:35,346 ALMs,497 M10Ks,38 DSPs.
This is an experimental hardware candidate, not a release.

DUAL1 and BTIC1, S1_CLASSES011 (second-slot loads disabled),8KB each
I/D cache, other optionalCPU features off. Hardware boot/Speedometer
are pending; A/UX and CD audio are unqualified. Artifact hashes are in
artifact.json. The original disk images and previous checkpoints are preserved.

The saved baseline RBF also completed the separate FPU suite: see the
[FPU comparison](../../../docs/dual-fpu-comparison.md). These results refer
to checkpoint43a5280; the memory-performance branch adds a subsequent
VRAM retirement experiment.
