# Separate FPU benchmark comparison

Speedometer4.02 FPU Benchmarks, normalized to Quadra650=1.0. This is a
different workload from Performance Rating Math. Higher aggregate/rate is
better; lower Matrix/FFT time is better. The new runs use the exact saved
dual-issue R3 bitstreams from checkpoint43a5280, not the new memory port.

| Build/run | CPU MHz | KWhetstones/s | Matrix seconds | FFT seconds | FPU average |
|---|---:|---:|---:|---:|---:|
| Real Quadra800 photograph | 33 | 5456.609 | 0.713 | 0.288 | 1.011 |
| Older shipping20260930, first | 33 | — | — | — | 0.953 |
| Older shipping20260930, warm | 33 | — | — | — | 0.961–0.968 |
| Dual R3, first | 33 | 3504.934 | 0.836 | 0.406 | 0.741 |
| Dual R3, after Mix | 33 | 3503.977 | 0.828 | 0.406 | 0.744 |
| Dual R3, first | 66 | 7060.650 | 0.422 | 0.202 | 1.484 |
| Dual R3, after Mix | 66 | 7053.827 | 0.417 | 0.201 | 1.492 |

The after-Mix average scales2.005× from33 to66MHz. At33MHz it reaches
73.6% of the real-Quadra average and is about23% below the older shipping
warm reference. At66MHz it reaches147.6% of the photographed real average.
These are single suite observations per condition, not repeated-run
statistics. No cause for the33MHz deficit is established by this test.

## Method and artifact identity

Both new runs used the same disposable Dual040/QuadSquad8_dual.hda at32MB,
Ethernet Off, and baseline PRAM restored before each boot. Each first
FPU suite ran immediately after launching the app. The full ten-test Mix
then completed (33MHz1.801,66MHz3.614), followed by the second FPU suite.
All three FPU tests used one iteration. Completion dialogs, settings and
full results are preserved. Both guests cleanly shut down to the explicit
safe-to-switch-off screen. The board was returned to Menu and its original
S0/PRAM restored, preserving S2/CFG absences.

- 33MHz RBF MD5:467a90ca4793e68cf39981a7fea9f8ea; all-clock timing passes.
- 66MHz RBF MD5:45308760ed233a198ecdcbcd613836ef; CPU timing still fails−3.308ns.

The physical reference had120MB RAM; its disk/cache environment differs.
The older shipping reference is20260930, MD549951492d3576add9470bc1d1ef28e5d,
at32MB with Ethernet On and the write-buffer Main. These are not newly
measured numbers for the October2 shipping RBF.

## Evidence

- [33MHz results](perf/dual_20261023/33mhz/fpu/result.json), [completion screenshot](perf/dual_20261023/33mhz/fpu/after-mix-complete.png).
- [66MHz results](perf/dual_20261023/66mhz/fpu/result.json), [completion screenshot](perf/dual_20261023/66mhz/fpu/after-mix-complete.png).
- [Final board restoration](perf/dual_20261023/66mhz/fpu/final-state.json).
- [Real Quadra photograph](perf/dual_20261023/reference/speedometerrealquadra.png).
- [Older shipping report](perf/dual_20261023/reference/shipping-20260930-report.md), recovered from sibling refs/MacQuadra800_MiSTer.
- [Mix and PR comparison](dual-speedometer-comparison.md).
