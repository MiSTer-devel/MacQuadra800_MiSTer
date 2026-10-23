# Timing24-small A/UX qualification and limits

ExactRBF MD5 `3e008b0c2c4a22c7dd6cde837cf12fcb`,66/33/99MHz,32MB,EthernetOff. One initial boot on the previously used clone2 stopped at partial startup. It was observed for452seconds, then recovered under the user's prior failed-test-clone authorization. That image is preserved; its specific failure cause is unknown. [Failure record](first-off-clone2/records.json).

A new disposable image was copied from the preserved original and read-back verified:1048576000bytes,SHA256 `f2e6d21992849ae9b9be7d968cdfa0a31e8f115e511e6b1e456ff1110f9e9819`. The previously qualified12RBF passed UnixFinder, rootuname/date/df, advancing clock and clean shutdown on it. [Reference evidence](control12-fresh/records.json).

Timing24-small then used the **same image and PRAM**, with no intervening reset of a running guest. It passed UnixFinder, rootuname/date/df, date09:39:00→09:40:09 and clean shutdown to the explicit safe screen. [Matched candidate evidence](matched-control/records.json). The final capture bounds shutdown at about172seconds after Return; this is an observation bound, not an exact duration.

The debugCFG was absent throughout, originals and earlier failed clones remain intact, and mouse buttons were explicitly released. This establishes one successful controlled qualification; it does not explain the earlier stall or establish repeated-boot reliability. CPU timing still fails and CD audio remains unqualified on this RBF.
