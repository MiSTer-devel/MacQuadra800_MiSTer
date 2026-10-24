# Separate FPU benchmark comparison

Speedometer 4.02 FPU Benchmarks, normalized to Quadra 650=1.0. This is a
different workload from Performance Rating Math. Higher aggregate/rate is
better; lower Matrix/FFT time is better. The R3 runs use exact saved
bitstreams from checkpoint `43a5280`.
The memory and FPU_PIPE rows below are a later matched comparison at
33 MHz on the memory-performance core.

| Build/run | CPU MHz | KWhetstones/s | Matrix seconds | FFT seconds | FPU average |
|---|---:|---:|---:|---:|---:|
| Real Quadra 800 photograph | 33 | 5456.609 | 0.713 | 0.288 | 1.011 |
| Older shipping 20260930, first | 33 | 4589.450 | 0.690 | 0.301 | 0.953 |
| Older shipping 20260930, after Mix | 33 | 4600.260 | 0.723 | 0.281 | 0.961 |
| Older shipping 20260930, extra warm | 33 | 4621.136 | 0.711 | 0.280 | 0.968 |
| Dual R3, first | 33 | 3504.934 | 0.836 | 0.406 | 0.741 |
| Dual R3, after Mix | 33 | 3503.977 | 0.828 | 0.406 | 0.744 |
| Dual R3, first | 66 | 7060.650 | 0.422 | 0.202 | 1.484 |
| Dual R3, after Mix | 66 | 7053.827 | 0.417 | 0.201 | 1.492 |
| Memory, first | 33 | 3505.131 | 0.836 | 0.406 | 0.741 |
| Memory, after Mix | 33 | 3508.624 | 0.829 | 0.406 | 0.744 |
| Memory + FPU_PIPE, first | 33 | 3635.266 | 0.835 | 0.406 | 0.750 |
| Memory + FPU_PIPE, after Mix | 33 | 3573.164 | 0.827 | 0.406 | 0.749 |

The after-Mix average scales 2.005× from 33 to 66 MHz. At 33 MHz it reaches
73.6% of the real-Quadra average and is about 23% below the older shipping
warm reference. At 66 MHz it reaches 147.6% of the photographed real average.
These are single suite observations per condition, not repeated-run
statistics. No cause for the 33 MHz deficit is established by this test.

## Method and artifact identity

Both new runs used the same disposable Dual040/QuadSquad8_dual.hda at 32 MB,
Ethernet Off, and baseline PRAM restored before each boot. Each first
FPU suite ran immediately after launching the app. The full ten-test Mix
then completed (33 MHz 1.801, 66 MHz 3.614), followed by the second FPU suite.
All three FPU tests used one iteration. Completion dialogs, settings and
full results are preserved. Both guests cleanly shut down to the explicit
safe-to-switch-off screen. The board was returned to Menu and its original
S0/PRAM restored, preserving S2/CFG absences.

- 33 MHz RBF MD5: 467a90ca4793e68cf39981a7fea9f8ea; all-clock timing passes.
- 66 MHz RBF MD5: 45308760ed233a198ecdcbcd613836ef; CPU timing still fails −3.308 ns.

The physical reference had 120 MB RAM; its disk/cache environment differs.
The older shipping reference is 20260930, MD5 49951492d3576add9470bc1d1ef28e5d,
at 32 MB with Ethernet On and the write-buffer Main. These are not newly
measured numbers for the October 2 shipping RBF.

## Evidence

- [33 MHz results](perf/dual_20261023/33mhz/fpu/result.json), [completion screenshot](perf/dual_20261023/33mhz/fpu/after-mix-complete.png).
- [66 MHz results](perf/dual_20261023/66mhz/fpu/result.json), [completion screenshot](perf/dual_20261023/66mhz/fpu/after-mix-complete.png).
- [Final board restoration](perf/dual_20261023/66mhz/fpu/final-state.json).
- [Real Quadra photograph](perf/dual_20261023/reference/speedometerrealquadra.png).
- [Older shipping report](perf/dual_20261023/reference/shipping-20260930-report.md), recovered from sibling refs/MacQuadra 800_MiSTer.
- [Mix and PR comparison](dual-speedometer-comparison.md).

The [isolated FPU_PIPE experiment](fpu-pipe-experiment.md) measures only
0.67–1.21% higher FPU scores at a cost of 1,077 ALMs (3.12%). PR Math
remains 13.313. The smaller memory core keeps FPU_PIPE off; the tested
experimental bitstream is preserved independently.
