# Games on F33 (fixes `e3fc1a0`, seed 33, CPU clock -0.378 ns), 2026-10-01 17:56-18:58

Opus operator run from `scratch/hw_20261001/BRIEF_GAMES.md`; report saved by
the main session. Screenshots and logs (`G_*`) are in `scratch/hw_20261001/`
(gitignored). rbf md5 `faf2eacdec2c680b29e88ffc735d2fe3`, Main `148d5679`,
disk `MacQuadra800_Problem_Games.hda`, 128 MB, Ethernet On.

**Verdict: none of the three games hung. The Time Manager was "moving" at
all 34 `tmcheck` runs.** One anomaly on the first boot (section 1).

## 1. Load and boot

- `load_core` 17:56:15; black RAM test until 17:57:04.
- **Stall:** "Starting Up..." appeared at 17:57:22 with no extension icons;
  the frame was byte-identical through 18:00:14. Ticks (`$16A`) stayed at
  `$0277` in every read from 17:59:14 to 18:01:05; Main's `write_bytes` and
  `read_bytes` were flat over 30 s.
- `pcsample` at 17:59:14 (3 s) and 18:01:12 (5 s): SR `$2400/$2404/$2408`
  about 99 % of the time (interrupt mask at level 4, VIA interrupts
  blocked). Hot PCs: `$3150-$319C` (the level-4 autovector `$70` ->
  `$3196`, the SCC dispatcher that reads RR2 through SCCRd `$50F0C020` and
  dispatches via Lvl2DT `$1B2`), `$40809B60-B90` (ROM interrupt entry/exit),
  and three channel-A handlers: external/status `$40809D40` (hot
  `$40809D42-5A`), Tx `$4086B276` (hot `$4086B14C-B29E`), and the RAM serial
  driver's receive/error path (hot `$2C094-$2C0FA`).
- **Recovery:** Ticks moved again by about 18:01:12 and ran at 63/s from
  18:01:27; the Finder was first seen at 18:02:07 (between 4 min 55 s and
  5 min 52 s after the load; normal is about 105 s). The stall ended within
  seconds of a 16 KB `gdump` of low memory; earlier 4-byte reads had not
  ended it. Coincidence or not is unknown.
- The guest clock lost the 3 min 53 s of the stall (the one-second interrupt
  was blocked too) and no more afterwards.
- No "not shut down properly" notice. Idle-Finder `tmcheck` 18:03:07: moving.
- **Second boot (18:45:19): no stall**, Ticks from about 47 s, Finder by
  92 s.

## 2. Day of the Tentacle: PASS (with its CD)

- As briefed (no CD): "Couldn't find the Day of the Tentacle CD" -- this
  copy needs the CD; not a hang (`tmcheck` moving five times; Return exits).
- Second run with `.s4` = `Day of the Tentacle.toast` (restored afterwards):
  launched 18:50:14, the LucasArts tunnel at t+12 s, on through the intro
  (sewer scene at t+60) into the first playable scene (Bernard in the motel
  lobby with the verb bar) at t+309. All 17 frames differ. `tmcheck` moving
  at 18:51:18, 18:52:14, 18:53:14, 18:54:15, 18:55:14. Cmd-Q, Return, back
  in the Finder 18:56:26. Observed 6 min. (Old build: frozen in the tunnel
  at about 15 s.)

## 3. DOOM II: PASS

Launched 18:11:54; title at t+45 s, attract demos for 20 minutes (24 shots,
22 distinct; the only repeat is the title page as the attract cycle comes
round). All 20 `tmcheck` runs moving, once a minute 18:12:57-18:31:57. (Old
build: frozen at about 3 minutes.) Cmd-Q, Return; Finder 18:33:05.

## 4. Dracula Unleashed: PASS

Launched 18:34:04; "Presents" at t+10 (already past the old Viacom-logo
hang), title at t+20, credits, live video in the player UI at t+208.
`tmcheck` moving at 18:35:04, 18:36:04, 18:37:04. Quit needed the player's
Stop button first; Finder 18:40:38. Alive about 6.5 min.

## 5. Finder afterwards: PASS

Menu-bar clock 6:37, 6:38, 6:39 across three screenshots a minute apart
(carrying the boot stall's lag); `tmcheck` moving; Cmd-W and a closed-loop
pointer move worked; `write_bytes` flat at idle.

## 6. Shutdown: PASS (twice)

`mac_shutdown.sh` 18:43:42 -> halt 18:44:18 (exit 0); again 18:56:43 ->
18:57:19. Menu core loaded after each.

## Not verified

Sound; the Viacom logo frame itself (between t+0 and t+10); the cause of the
SCC storm and what ended it.
