# CPU66 timing experiment 7: rejected extra cache-lookup phase

An isolated simulation candidate split successful slow-engine translation and tag comparison into consecutive phases, reusing `e_x` and adding one cycle. It passed four adapter tests and 180 CPU cases, but failed all five `t_cbsplit` configurations. Under continuous snoops, zero-wait runs repeatedly allocated and lost the second line rather than completing the store; a trace at one million cycles showed 98% DC2 wait and 37,728 invalidations. Half-bus-clock runs also lost the existing required split-store fallback coverage.

This candidate was **rejected before fitting**. No regression assertions were weakened. The [patch](perf/cpu66_20261022/timing7/rejected-slow-tag-phase.patch), [test results](perf/cpu66_20261022/timing7/cpu-regression.log) and [trace](perf/cpu66_20261022/timing7/split-store-trace.log) preserve the failed approach. The next candidate retains the existing timing of engine operations and registers only the transparency selector ahead of tag comparison.

The circular queue from experiment 6 is also removed from the active RTL, following its measured area/CPU-TNS/SDRAM regressions. Its source, reports and tests remain in history.
