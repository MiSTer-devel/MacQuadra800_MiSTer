# Experimental dual issue Quadra at 33 MHz

This exact bitstream runs the CPU and machine bus at33 MHz, with SDRAM
at99 MHz. The complete core uses **34,643 ALMs (82.66%)**,497 M10Ks and
38 DSPs. All setup and hold checks pass: CPU/bus+1.374 ns,SDRAM+0.099 ns,
HDMI+0.407 ns and minimum hold+0.167 ns.

Mac OS8.1 passes Finder, keyboard/mouse interaction, an advancing clock,
Speedometer Mix **1.800**, full Performance Rating **1.569**, and clean
shutdown. The tests use32 MB, Ethernet Off, and a verified disposable
Mac image. These are single-iteration measurements. A/UX and CD audio
remain unqualified; this is an experimental checkpoint.

The CPU is upstream faster eed15a0, with the retained Quadra correctness
fixes and documented Quartus17 workarounds. DUAL and BTIC are enabled,
S1_CLASSES=011 (register/address companions; second-slot loads disabled),
with8 KB each I/D cache and the other optional CPU features off.

The branch defaults to this33 MHz recipe. All190 build-source files were
verified against the fitted archive; active QSF assignments match source
commit19d9fc3. Artifact hashes, the original source88a3b0b plus its pinned
compiler setting, and verification are recorded in artifact.json and
[the fit manifest](../../../docs/perf/dual_20261023/33mhz/r3/source-manifest.json).
See [hardware evidence](../../../docs/perf/dual_20261023/33mhz/mac/result.json).
