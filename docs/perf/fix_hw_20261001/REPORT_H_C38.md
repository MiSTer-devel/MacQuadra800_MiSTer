# Games on C38 (release candidate), 2026-10-01 23:36 - 2026-10-02 00:26

Opus operator run from `scratch/hw_20261001/BRIEF_GAMES.md`; report saved by
the main session. Screenshots and logs (`H_*`) are in `scratch/hw_20261001/`
(gitignored). `/media/fat/_Unstable/MacQuadra800_C38.rbf`, md5
`1928f231dd9ac9ef5935e69272d305a4` (commit `8c223c8`, seed 38, every clock
met, stamp 261002). Problem Games disk, 128 MB, Ethernet On.

**Verdict: no hangs. The Time Manager was "moving" at all 32 `tmcheck`
runs. Neither boot stalled.** No bombs, crashes or garbage.

## Boots

| | boot 1 (`.s4` = DRACULA.toast) | boot 2 (`.s4` = Day of the Tentacle.toast) |
|---|---|---|
| `load_core` | 23:36:14 | 00:09:24 |
| Ticks at t+55 / 60 / 65 / 70 | `$0A8` / `$1D4` / `$300` / `$42C` | `$0A9` / `$1D6` / `$301` / `$42C` |
| through `$278` | about t+63, 59-62 ticks/s on every 5 s read | the same |
| Finder menu bar | in the t+90 screenshot | in the t+90 screenshot |

## Games

| game | launched | result |
|---|---|---|
| DOOM II | 23:39:20 | **PASS**: title at t+45, attract demos for 20 minutes (24 shots, 22 distinct; the title page comes round again at t+1149). `tmcheck` moving at all 20 one-minute runs. Old build: frozen at about 3 minutes. |
| Dracula Unleashed | 00:01:42 | **PASS**: Viacom logo at t+0, "Presents" at t+10, title, credits, live video in the player at t+180 and t+240. `tmcheck` moving four times. Old build: frozen at the Viacom logo. |
| Day of the Tentacle | 00:11:58 | **PASS**: intro past the tunnel (house at t+24, sewer at t+60, canyon at t+211) into the first playable scene at t+308; all 17 frames differ; `tmcheck` moving six times; the game answered a mouse move ("Walk to window"). Old build: frozen in the tunnel at about 15 s. |

Finder afterwards: clock 12:19, 12:20, 12:22 in shots a minute apart, guest
time within 0.5 s of the box clock; `tmcheck` moving; Cmd-W and closed-loop
pointer moves worked. Both shutdowns (`mac_shutdown.sh`, exit 0) reached the
halt screen.

Not verified: sound; the tunnel frame itself (the shots fell at launch+6 s
and +19 s).
