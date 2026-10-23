# Experimental CPU66 A/UX-compatible checkpoint

Exact tested RBF from source `f8aa787`, seed38, OSD stamp261022, CPU/bus/SDRAM **66/33/99 MHz**. MD5 `08612014fe6dfc822f33a031d3328a2b`; SHA256 `d70a64afd67a533809bbd990c8caabd0b5a07b13772ad1ad00686cc7a9c80c51`.

The existing DBcc minimum is four CPU clocks in the 2× configuration, avoiding A/UX's `SetUpTimeK` 16-bit calibration overflow. The 1× configuration retains floor zero. A/UX on clone2 passes Unix Finder, root uname/date/df and clean shutdown with Ethernet On, then again Off, at32MB. One earlier clone4 run stalled after partial UI; the specific cause is unknown and repeated-boot reliability is not established. [A/UX evidence](../../docs/perf/cpu66_20261022/timing12/aux/README.md).

MacOS8.1 boots to Finder, advances its clock and completes Mix **3.160** (originalCPU66 3.162; minimal33 1.611). CPU PR **3.474**, graphics1.399, math26.610; the first PR run returned no disk result, so no complete overall PR is claimed. The user performed clean shutdown and the safe-to-switch-off screen was visually verified. [Mac results](../../docs/perf/cpu66_20261022/timing12/mac/result.json).

**Timing is not closed:** CPU setup −1.667ns, CPU TNS −196.113ns, 33,335ALMs. SDRAM +0.366ns, bus +0.830ns, HDMI +0.329ns and minimum hold +0.130ns pass. [Fit](../../docs/perf/cpu66_20261022/timing12/fit/artifact.json). This is an experimental checkpoint, not a release. Original disk images, the frozen minimal branch and the previous Dani/Elle ZIP are preserved.
