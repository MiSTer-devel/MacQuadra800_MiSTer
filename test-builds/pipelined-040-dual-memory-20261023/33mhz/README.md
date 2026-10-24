# Experimental VRAM retirement build at 33 MHz

Source 8e3e0b9, seed 38, CPU/bus/SDRAM 33/33/99 MHz. Complete core 34,554 ALMs,
497/553 M10Ks, 38 DSPs. All timing passes: CPU/bus +1.245 ns, SDRAM +0.511 ns,
HDMI +0.668 ns, minimum hold +0.194 ns. The source reuses the existing DMU bus
registers to retire qualified non-faulting VRAM stores early; no new FIFO.
Mac OS 8.1 boot, input, clock, Mix 1.801, full PR 1.617 and clean shutdown
pass on the disposable 32 MB / Ethernet Off test image. Graphics 0.982 is 4.8%
higher than the saved dual33 baseline 0.937 in this single comparison.
A/UX and CD audio remain unqualified; this is an experimental checkpoint.

See [experiment](../../../docs/dual-memory-performance.md) and artifact.json
for exact hashes, source and qualification.
