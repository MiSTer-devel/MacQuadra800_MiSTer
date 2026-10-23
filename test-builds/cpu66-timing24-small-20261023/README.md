# Experimental small 66 MHz checkpoint

This is the exact timing24-small RBF: CPU/bus/SDRAM **66/33/99 MHz**, balanced seed 38, OSD stamp 261023, and the original five register-file read ports. It uses **33,328 ALMs (79.52%)**, only 128 ALMs above the frozen minimal 33 MHz core.

**CPU timing is still violated. This is not a release.**

| Timing check | Slack |
|---|---:|
| CPU setup | -1.539 ns (TNS -147.124 ns) |
| SDRAM setup | +0.339 ns |
| Machine-bus setup | +0.672 ns |
| HDMI setup | +0.347 ns |
| Minimum hold | +0.165 ns |

Mac OS 8.1 passes Finder, keyboard/mouse interaction, an advancing clock, Benchmark Mix **3.159**, full Performance Rating **2.420**, and clean shutdown. A matched A/UX 32 MB/Ethernet Off run passes Finder, root shell checks, an advancing clock, and clean shutdown. An earlier A/UX attempt on the old clone stopped at partial startup; its cause remains unknown, and repeated-boot reliability is not established. CD audio has not been qualified on this RBF. [Mac evidence](../../docs/perf/cpu66_20261022/timing24/small/mac/result.json), [A/UX evidence and limits](../../docs/perf/cpu66_20261022/timing24/small/aux/README.md).

The working branch now contains the equivalent CPU RTL at `e6b54b3`; [all 26 file hashes and default adapter verification](applied-source.json) record that match. To reproduce the original archive, start from `a6cb17af25003b26d15433fa10a86bdeaff1e70e` and apply `cpu-source.patch` with `git apply --unidiff-zero`. All 26 CPU source/data files were compared; the backend is the only changed file. The patch combines the overwritten-bypass removal, separate word-index scaling, and exception-address selection changes. No register, extra RF port, cycle, or timing exception is added. The 2× DBcc minimum remains four clocks for A/UX compatibility.

The pinned source-archive chain and RBF hashes are in [artifact.json](artifact.json). Full fit reports and simulation evidence are under [timing24/small](../../docs/perf/cpu66_20261022/timing24/small). All 185 CPU cases, four adapters, and the targeted signaling-true odd-target BSUN cases pass. Original disk images and the previously shared ZIP are preserved.
