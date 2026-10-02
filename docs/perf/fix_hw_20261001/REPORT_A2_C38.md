# A/UX 3.1 gate at 32 MB on C38 (release candidate), 2026-10-02 00:28-01:04

Opus operator run from `scratch/hw_20261001/BRIEF_AUX.md`; report saved by
the main session. Screenshots and logs (`A2_*`) are in
`scratch/hw_20261001/` (gitignored). `/media/fat/_Unstable/MacQuadra800_C38.rbf`,
md5 `1928f231dd9ac9ef5935e69272d305a4` (commit `8c223c8`, seed 38, every
clock met, stamp 261002). Main `148d5679`. `.s0` = the A/UX image (restored
from the backup zip on 10-01, one boot and one clean shutdown since), `.s4`
all zeros, `.s1` unmounted, CFG byte 0 `$40` (32 MB, Ethernet On).

**Verdict: the gate passes.**

| check | result |
|---|---|
| boot to multiuser | **PASS**: load 00:28:58 (T0); A/UX Startup at t+24 s; the root shell's login stamp is t+63 s (10-01: t+62 s); the Finder's menu bar with the "unreadable" dialog at t+84 s (frame identical to 10-01's). No panic, no garbled console, no streaks, no login dialog. |
| CommandShell | **PASS**: `uname -a` = `A/UX localhos 3.1 SVR2 mc68040`; `ls -l /etc | head -20` as on 10-01 (`total 6414`); `df` = `/ /dev/dsk/c0d0s0 3695490 blocks 961639 i-nodes`. |
| idle | **PASS**: 00:53:10-00:57:10; `date` 00:52:45 then 00:57:16, 271 s of guest time over 271 s. |
| `shutdown -h now` | **PASS**: typed 00:57:29; `callrpc RPC: Port mapper failure` by +85 s; "You may now switch off your Macintosh safely." at +125 s, the frame byte-identical to 10-01's. |
| configuration restored | **PASS**: `.s0`, `.s4`, CFG byte 0 `$50` back from the `.gate_keep` copies (`cmp`). |

## The "This disk is unreadable" dialog (open, not from these fixes)

As on 10-01 it comes up at t+84 s with nothing in slots 1 and 4, and the
desktop behind it is drawn only after a click. This time Return did not
close it (four tries); a 7 s press on Cancel did, at t+1133 s. On 10-01 a
long press had not closed it and a Return did. In both runs the A/UX
Finder acted on input late and inconsistently while the dialog was up; the
guest itself was alive throughout (about 20k PC updates/s, disk writes).
Which device the dialog means is not known (its icon is a hard disk; the
CD-ROM target with no medium and the unmounted second disk are the
candidates). The 2026-09-18 gate saw the dialog with an audio CD in slot 4;
whether it appeared with empty slots before the 2026-09-19 gate is not
recorded. Initialize was never approached.

Not verified: the kernel console text during boot (20 s sampling); the real
HDMI output.
