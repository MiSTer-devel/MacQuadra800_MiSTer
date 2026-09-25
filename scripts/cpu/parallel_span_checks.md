# P135 parallel-span checks

`parallel_span_checks.patch` adds the self-contained `scripts/cpu/tb_parallel_span.sv` bench. Keep it unapplied while a Quartus wrapper freezes tracked HDL. Apply with `git apply scripts/cpu/parallel_span_checks.patch` after the wrapper finishes.

This is the candidate-aware P135 cache bench, not a baseline latency test. It retains the cache snoop/error/store/cross-line matrix and asserts separate idle/lookup pair acknowledgements, actual lookup snoop/paused windows, correct data, exact acknowledgement counts, and fatal failures/timeouts. It instantiates external RAM models; it is not full-machine validation. P136's hinted idle path needs separately driven hint inputs and is not covered by merely swapping in P136.

Run from the repository root (CACHE must be the P135 snapshot):

```bash
CACHE=scratch/p135_parallel_span_read_20260921/ap040_cache.v
iverilog -g2012 -DAP040_EXPERIMENTAL_XSTORE -DP131_DATA_LOOKUP_ACK -Irtl/ap68040/rtl -s tb_ap040_cache_snoop -o /tmp/q800_parallel_span.vvp scripts/cpu/tb_parallel_span.sv "$CACHE" rtl/ap68040/rtl/primitives/dpram.v
vvp /tmp/q800_parallel_span.vvp
```

Expected pair coverage from the accepted run: idle=13, look=2, total=15, C_LOOK_snoop=2, C_LOOK_paused=7 and ALL TESTS PASSED. Counts are observations, not correctness oracles; the source contains the data/ack/coverage assertions. Root inspected the source and accepted log at `scratch/p135_cache_smoke_20260921/pair/run.log`. Error exclusion is asserted continuously; this does not prove all possible simultaneous-error stimuli were exercised.
