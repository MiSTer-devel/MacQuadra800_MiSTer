# Minimal pipelined AP68040 checkpoint, 2026-10-22

The `pipelined-040-min` CPU port and boot fix are complete. This branch preserves a small baseline for subsequent clock and performance experiments. Its checkpoint artifact is the exact bitstream that passed the hardware tests below.

## Artifact and build

| Item | Value |
|---|---|
| Bitstream | [`releases/MacQuadra800_20261022.rbf`](../releases/MacQuadra800_20261022.rbf) |
| Size | 4,320,812 bytes |
| MD5 | `11580e654e9fa77e391c933b668f43c5` |
| SHA-256 | `2fc6bd6b55b2b0448697e7dc69ced840b630baac04ea76cd374915299e0254b6` |
| Build stamp | `261022` |
| Hardware source | `6e1b795ac3ed925c69135f7f20112e9f7dc3f17c` |
| Documentation/test-helper head before packaging | `6181423e9913ff444858e37b323d389d6f8fad0b` |
| Tool | Quartus Prime Lite 17.0.0 build 595 |
| Seed | 38 |
| Device | Cyclone V 5CSEBA6U23I7 |
| Clocks | CPU/machine 33 MHz; SDRAM 99 MHz |
| Logic | 33,200 / 41,910 ALMs (79%) |
| RAM and DSP | 487 / 553 M10K blocks; 38 / 112 DSP blocks |
| Setup slack | CPU +1.324 ns; SDRAM +1.022 ns; HDMI **−0.043 ns**, TNS −0.072 ns |
| Minimum hold slack | +0.132 ns |

The artifact was recovered from `misterubuntu:~/mister/q800_fix2/output_files/MacQuadra800.rbf`; it matches the tested `/media/fat/_Development/MacQuadra800_fix2.rbf` on `.192`. It was preserved without recompilation. The [source audit](perf/pipelined_min_20261022/source-audit.json) compared 155 build-source/configuration files: all HDL, clock definitions, constraints, and source lists match this branch. The only QSF difference is `LAST_QUARTUS_VERSION` metadata (17.0.0 in the build, 17.0.2 in the source).

The related-clock SDRAM crossing audit also passes: system → RAM +1.994 ns and RAM → system +1.324 ns. Detailed [system-to-RAM](perf/pipelined_min_20261022/cross_sys2ram_min_release_20261022.txt) and [RAM-to-system](perf/pipelined_min_20261022/cross_ram2sys_min_release_20261022.txt) reports are archived.

Saved evidence: [artifact identity](perf/pipelined_min_20261022/artifact.json), [fitter summary](perf/pipelined_min_20261022/MacQuadra800.fit.summary), [timing summary](perf/pipelined_min_20261022/MacQuadra800.sta.summary), and [build stamp](perf/pipelined_min_20261022/build_id.v).

## Scope

The branch contains the upstream pipelined AP68040 and its Quadra bus integration, serialized device reads, and the load-ordering boot fix in `6e1b795`. The CPU uses its small default configuration (`FPU_PIPE`, `LOOP_PRED`, `EARLY_RES`, `DC1_ATC`, and `SKID` off). CPU performance experiments remain on `pipelined-040`.

Mac OS 8.1 boots to Finder, completes Speedometer Mix and Performance Rating, and reaches the safe-to-switch-off screen after shutdown. A/UX 3.1 boots to multiuser Finder, runs responsive root-shell commands, advances its clock at idle, and completes `shutdown -h now`. These tests used 32 MB RAM and Ethernet Off. See the [Mac OS report](shutdown-testing.md) and [A/UX report](aux-testing.md), with screenshots and bitstream identities.

The apparent Finder shutdown hang was resolved by correcting the remote input sequence. No shutdown RTL patch was needed.

## Checkpoint limits

The HDMI setup miss remains in this hardware-tested artifact. Audible CD output and the CD-player transport gate have not been qualified on it. It is a completed CPU-port baseline on this development branch; the full general-release gate remains open.

Keep Ethernet Off: the pipelined CPU's SONIC cache-coherency integration is not implemented. A/UX qualification covers the supplied 1 GB image at 32 MB. Use a Main binary with MacQuadra800 support and the Mac disk write buffer, as described in the project documentation.

Future frequency experiments should retain this 33 MHz artifact as the reference. A 66 MHz CPU with the machine bus kept at 33 MHz is a separate adapter/clocking experiment; frequency support must be established by timing analysis and hardware tests before it becomes an OSD option.
