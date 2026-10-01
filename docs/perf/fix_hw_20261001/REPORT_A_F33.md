# A/UX 3.1 gate at 32 MB on F33 (fixes `e3fc1a0`, seed 33), 2026-10-01 19:07-19:31

Opus operator run from `scratch/hw_20261001/BRIEF_AUX.md`; report saved by
the main session. Screenshots and logs (`A_*`) are in `scratch/hw_20261001/`
(gitignored). rbf md5 `faf2eacdec2c680b29e88ffc735d2fe3`, Main `148d5679`.
Image `HD60_512-AUX3.1-Installed.hda` restored from the backup zip at 17:35.
`.s0` = the A/UX image, `.s4` all zeros (no CD), `.s1` unmounted, CFG byte 0
`$40` (32 MB, Ethernet On).

**Verdict: the gate passes. The `copyout of icode failed` panic is gone.**

| check | result |
|---|---|
| boot to multiuser | **PASS**: load 19:07:18 (T0); A/UX Startup at t+26 s; "Welcome ... Checking root file system" at t+46 s (past the old panic point); Finder menu bar at t+86 s; "/", "MacPartition" and Trash icons by about t+317 s. No panic, no garbled console, no streaks, no login dialog. |
| CommandShell | **PASS**: Apple menu -> CommandShell, prompt `localhost.root #`. `uname -a` = `A/UX localhos 3.1 SVR2 mc68040`; `ls -l /etc | head -20` and `df` (`/ /dev/dsk/c0d0s0 3695452 blocks 961639 i-nodes`) sane. |
| idle | **PASS**: 19:20:47-19:25:10; `date` answered 12:20:45 then 12:25:10 guest time, in step with real time. |
| `shutdown -h now` | **PASS**: typed 19:25:24; "You may now switch off your Macintosh safely." at +125 s (19:27:35). `shutdown: callrpc RPC: Port mapper failure` was printed at +85 s and did not stop it. |
| configuration restored | **PASS**: `.s0`, `.s4`, CFG byte 0 `$50` back from the `.gate_keep` copies, byte-identical. |

No stall and no SCC interrupt storm: every 20 s PC sample showed about
17-21k updates/s, SR mostly user, `$20xx` or `$00xx`, never sitting at IPL 4.

## Anomaly: "This disk is unreadable" with nothing mounted

At t+86 s the A/UX Finder put up "This disk is unreadable: Do you want to
initialize it?" (Cancel / Initialize) although slot 4 and slot 1 were empty;
Main had only the A/UX image and the `.nvr` open. Mouse clicks on Cancel did
not close it (the button inverted while held, three tries); Return (the
default, Cancel) closed it at t+439 s and it did not come back. Which device
it refers to is unknown (the CD-ROM target with no medium is the likely
one). The 2026-09-18 gate saw the same dialog with an audio CD in slot 4.
Initialize was never approached.

## Not verified

Which device the dialog means; whether mouse clicks can activate dialog
buttons in A/UX at all; the real HDMI output (screenshots only).
