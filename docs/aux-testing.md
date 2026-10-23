# A/UX 3.1 boot and shutdown (2026-10-22)

The supplied 1 GB A/UX image boots to the multiuser Finder and a responsive root CommandShell on both existing pipelined-040 bitstreams, with 32 MB RAM and Ethernet Off. Both builds complete `shutdown -h now` and display the explicit safe-to-switch-off screen.

No RTL changes or bitstream recompilation were needed for these tests. The hardware is MiSTer `10.0.2.192`; `.14` received the disk image while its Dorado session was left running.

| Build | ALMs | Bitstream MD5 | Boot and shell | `shutdown -h now` |
|---|---:|---|---|---|
| Minimal, `MacQuadra800_fix2.rbf`, seed 38 | 33,200 | `11580e654e9fa77e391c933b668f43c5` | Pass | Safe screen captured at ~157 s |
| Performance/options, `MacQuadra800_opts.rbf`, seed 40 | 35,648 | `916b27a3190c22fb6ed62480f6237a68` | Pass | Safe screen captured at ~134 s |

Shutdown times are rounded screenshot bounds, measured from the Return report in `/tmp/remote.log`; the halt may have completed before the captured frame. The [run record](perf/aux_20261022/runs.json) preserves timestamps and evidence hashes. A/UX takes substantially longer to shut down than the Mac OS 8.1 guest in the [earlier qualification](shutdown-testing.md).

## Test media

Source: `~/Downloads/AUX_3_1_1GB_Use_In_Shoebill.zip`. Member `AUX_3_1_1GB.dsk` was copied unchanged as `games/MacQuadra800/TestImages/AUX_3_1_1GB.hda` so the core's `.hda`/`.vhd` file filter can select it. Its initial raw SHA-256 is `ad743e781945f6df1cc4c0cc4fcfcc153534de34c09f6a65b651eec2c7e07708`.

Both destination copies passed transferred-byte-count, SHA-256, and file read-back SHA-256 checks before the first boot. The [verification record](perf/aux_20261022/image-verification.json) includes the source archive hash and results for each host. The `.192` copy was subsequently used as writable guest media, so its initial hash describes delivery before boot. The original Downloads ZIP and the archive on `misterubuntu:~/mister/q800_aux_20261022/archives/` remain available.

## Observations and evidence

Both boots reached Finder with the Unix `/` volume mounted and without a visible panic. Apple → CommandShell opened a root prompt. Both returned `A/UX localhos 3.1 SVR2 mc68040` from `uname -a`, plus normal `date` and `df` results. The guest date advanced between samples: minimal 17:06:26 → 17:08:00, options 17:15:10 → 17:16:39. Each shell remained responsive after idle.

| Evidence | Minimal | Performance/options |
|---|---|---|
| OSD, 32 MB | [RAM setting](perf/aux_20261022/min-osd-32mb.png) | [RAM setting](perf/aux_20261022/options-osd-32mb.png) |
| Unix Finder desktop | [Desktop](perf/aux_20261022/min-desktop.png) | [Desktop](perf/aux_20261022/options-desktop.png) |
| Kernel identity and filesystem | [Shell commands](perf/aux_20261022/min-uname-df.png) | [Shell commands](perf/aux_20261022/options-uname-df.png) |
| Clock after idle | [Later date](perf/aux_20261022/min-date-later.png) | [Later date](perf/aux_20261022/options-date-later.png) |
| Verified halt command | [Command](perf/aux_20261022/min-shutdown-command.png) | [Command](perf/aux_20261022/options-shutdown-command.png) |
| Safe-to-switch-off screen | [Halt](perf/aux_20261022/min-halted.png) | [Halt](perf/aux_20261022/options-halted.png) |

Input used the persistent websocket helper described in [shutdown testing](shutdown-testing.md). A/UX's mouse tracking differs from the Mac OS 8.1 image, so the CommandShell row was verified on screen before releasing the button. Each guest was shut down with `shutdown -h now` in CommandShell. The performance build was loaded only after the minimal build showed its explicit safe-to-switch-off message.

These results cover this supplied image at 32 MB. They do not qualify A/UX at 128 MB or the CD-audio release gate.

The test host is left at the A/UX safe-to-switch-off screen on the performance/options build, with `AUX_3_1_1GB.hda` still selected.
