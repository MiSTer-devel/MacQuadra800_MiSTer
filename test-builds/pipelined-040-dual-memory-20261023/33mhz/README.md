# Experimental VRAM retirement build at33MHz

Source8e3e0b9, seed38, CPU/bus/SDRAM33/33/99MHz. Complete core34,554ALMs,
497/553M10Ks,38DSPs. All timing passes: CPU/bus+1.245ns,SDRAM+0.511ns,
HDMI+0.668ns,minimumhold+0.194ns. The source reuses the existing DMU bus
registers to retire qualified non-faulting VRAM stores early; no new FIFO.
Mac hardware qualification is pending. This is not a general release.

See [experiment](../../../docs/dual-memory-performance.md) and artifact.json
for exact hashes, source and qualification.
