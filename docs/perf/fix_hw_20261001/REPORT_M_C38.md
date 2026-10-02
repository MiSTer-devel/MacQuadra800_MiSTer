# Mac OS 8.1 gate and CD transport on C38 (release candidate), 2026-10-01 23:17-23:33

Opus operator run from `scratch/hw_20261001/BRIEF_81.md`; report saved by
the main session. Screenshots and logs (`M_*`) are in `scratch/hw_20261001/`
(gitignored). `/media/fat/_Unstable/MacQuadra800_C38.rbf`, md5
`1928f231dd9ac9ef5935e69272d305a4` (commit `8c223c8`, seed 38, every clock
met, stamp 261002). Main `148d5679`. `.s0` = `QuadSquad8.hda`, `.s4` =
`ToneTest.cue`, CFG byte 0 `$50` (128 MB, Ethernet On).

| check | result |
|---|---|
| boot | **PASS**: `load_core` 23:17:24; Ticks from about t+52, straight through `$278` at about t+64 (`$1D3` at t+60.3, `$306` at t+65.4, `$42D` at t+70.3), 59-61 ticks/s on every 5 s read; extensions at t+76; Finder menu bar between t+76 and t+91; desktop fully drawn by t+108. No restart, no alert. |
| input | **PASS**: closed-loop pointer move (15,15) -> (300,220) exact; click + type-select "jou" selected Joust; Apple menu walk and Cmd-Q worked. |
| idle clock | **PASS**: 11:20, 11:21, 11:22, 11:23, 11:24 in frames a minute apart from 23:20:39 (the guest clock matches the wall clock); the guest's screen saver covered the sixth frame, a 2-px move woke it and the clock read 11:26 at 23:26:11. `tmcheck` at 23:23:10: moving. |
| CD mount | **PASS**: "Audio CD 1" on the desktop in the first fully drawn frame; AppleCD Audio Player (Apple menu) shows four tracks, 07:02. |
| Play | **PASS**: 00:01 at 23:28:24, 00:30 at 23:28:54. |
| Pause | **PASS**: 00:46 at 23:29:12 and at 23:29:24. |
| Resume | **PASS**: 00:48 at 23:29:43, 01:00 at 23:29:55. |
| Stop | **PASS**: Track 01 00:00 at 23:30:24 and 23:30:34. No "drive is not responding" dialog in any frame. |
| shutdown | **PASS**: `mac_shutdown.sh` 23:31:11-23:31:58, exit 0; "It is now safe to switch off your Macintosh" at 23:32:05. |
| configuration restored | **PASS**: `.s0`, `.s4` back from the `.gate_keep` copies (`cmp`), CFG untouched. |

Not verified: sound (the user's check, by ear); Main's `Mac CD: cmd` log
(Main was not relaunched); the 11:25 reading (screen saver).
