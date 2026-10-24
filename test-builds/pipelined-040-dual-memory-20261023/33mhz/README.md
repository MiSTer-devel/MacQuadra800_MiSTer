# Experimental VRAM retirement build at33MHz

Source8e3e0b9, seed38, CPU/bus/SDRAM33/33/99MHz. Complete core34,554ALMs,
497/553M10Ks,38DSPs. All timing passes: CPU/bus+1.245ns,SDRAM+0.511ns,
HDMI+0.668ns,minimumhold+0.194ns. The source reuses the existing DMU bus
registers to retire qualified non-faulting VRAM stores early; no new FIFO.
Mac OS8.1 boot, input, clock, Mix1.801, full PR1.617 and clean shutdown
pass on the disposable32MB/Ethernet Off test image. Graphics0.982 is4.8%
higher than the saved dual33 baseline0.937 in this single comparison.
A/UX and CD audio remain unqualified; this is an experimental checkpoint.

See [experiment](../../../docs/dual-memory-performance.md) and artifact.json
for exact hashes, source and qualification.
