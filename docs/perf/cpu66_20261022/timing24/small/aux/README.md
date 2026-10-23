# Timing24-small A/UX qualification and limits

Exact RBF MD5 `3e008b0c2c4a22c7dd6cde837cf12fcb`, 66/33/99 MHz, 32 MB, Ethernet Off. One initial boot on the previously used clone2 stopped at partial startup. It was observed for 452 seconds, then recovered under the user's prior authorization for failed boots on disposable test clones. That image is preserved; its specific failure cause is unknown. [Failure record](first-off-clone2/records.json).

A new disposable image was copied from the preserved original and read back verified: 1,048,576,000 bytes, SHA256 `f2e6d21992849ae9b9be7d968cdfa0a31e8f115e511e6b1e456ff1110f9e9819`. The previously qualified experiment12 RBF passed Unix Finder, root `uname -a`/`date`/`df`, an advancing clock, and clean shutdown on it. [Reference evidence](control12-fresh/records.json).

Timing24-small then used the **same image and PRAM**, with no intervening reset of a running guest. It passed Unix Finder, root commands, date advancing from 09:39:00 to 09:40:09, and clean shutdown to the explicit safe screen. [Matched candidate evidence](matched-control/records.json). The final capture bounds shutdown at about 172 seconds after Return; this is an observation bound, not an exact duration.

The debug CFG was absent throughout. Originals and earlier failed clones remain intact, and mouse buttons were explicitly released. This establishes one successful controlled qualification. It does not explain the earlier stall or establish repeated-boot reliability. CPU timing still fails, and CD audio remains unqualified on this RBF.
