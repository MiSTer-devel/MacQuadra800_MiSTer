MacQuadra800 MiSTer: experimental 66 MHz CPU build (2026-10-22)

For Dani and Elle. Hardware source: 397f3df, branch pipelined-040-66mhz.
Based on the minimal pipelined AP68040 checkpoint; CPU internal options unchanged.
CPU 66 MHz, machine/peripheral bus 33 MHz, SDRAM 99 MHz. Fixed clock mode.
Area: 34,213 ALMs (82%), versus 33,200 for the 33 MHz minimal build (+3.05%).

EXPERIMENTAL: this fit does not meet timing. CPU setup slack -2.391 ns;
SDRAM setup slack -0.209 ns. CPU/bus crossing checks and hold timing pass.
One successful trial is not proof of reliable operation on every board.
Use a COPY of your disk image for testing.

Tested on MiSTer 10.0.2.192 at 32 MB RAM, Ethernet Off:
- Mac OS 8.1 boots to Finder (desktop captured about 67 seconds after load).
- Speedometer 4.02 Benchmark Mix: 3.162 (33 MHz minimal: 1.611), one iteration.
- Performance Rating: 2.456; CPU 3.468, Graphics 1.463, Disk 2.413, Math 26.633.
- Quit benchmark without saving, then Finder Special > Shut Down:
  safe-to-switch-off screen observed within 15 seconds.
- A/UX and CD audio have not been qualified at 66 MHz.

Copy MacQuadra800_cpu66_s38.rbf to /media/fat/_Development/ on your MiSTer
and select it through the MiSTer menu after shutting down any running guest.
Use your existing Quadra ROM/PRAM setup and a cloned Mac OS disk. Start with
32 MB RAM and Ethernet Off, matching the tested configuration.
No ROM, disk image, or replacement Main binary is included.
The existing 33 MHz release is a separate build.

Please report board/SDRAM configuration, OS and memory size, benchmark scores,
and whether boot/shutdown or applications fail. Include this build's MD5:
238b10a91e219725fdcc90ff73e8848b
