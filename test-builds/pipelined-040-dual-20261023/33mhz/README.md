# Experimental dual issue Quadra,33 MHz

CPU/bus33MHz andSDRAM99MHz; upstreamfastereed15a0 plus retainedQuadra
correctness patches andQuartus17 representation workarounds. Source88a3b0b
with compilerRAM-budget fallback disabled; the exact input manifest is in
docs/perf/dual_20261023/33mhz/r3/source-manifest.json. Main's recipe will be
updated after the ongoing66MHz fit completes.

DUAL1, BTIC1, second-slot register/address operations enabled (011),
second-slot loads disabled,8KB I/D caches; other optionalCPU features off.
The complete core uses34,643ALMs and497M10Ks. All setup/hold checks pass:
CPU/bus+1.374ns,SDRAM+0.099ns,HDMI+0.407ns,minimumhold+0.167ns.

This exact RBF is preserved beforehardware testing. Mac boot and
Speedometer are pending; A/UX andCD audio are unqualified. This is an
experimental checkpoint, not a general release. See artifact.json for
hashes and the working branch for source and test evidence.
