# Hinted parallel-span directed checks

Apply `git apply scripts/cpu/hinted_parallel_span_checks.patch` after any active Quartus HDL freeze ends. It creates a standalone test of externally qualified P136 hints. Tested source SHA256: 105faaf92c803afcc6cfbde2bf79b1ecec6165cdf33cdaaeabdd96330acfdd65.

```bash
iverilog -g2012 -DP131_DATA_LOOKUP_ACK -Irtl/ap68040/rtl -s tb_ap040_cache_snoop -o /tmp/q800_hinted_pair.vvp scripts/cpu/tb_hinted_parallel_span.sv scratch/p136_hinted_parallel_span_20260921/ap040_cache.v rtl/ap68040/rtl/primitives/dpram.v
vvp /tmp/q800_hinted_pair.vvp
```

The test checks observed idle and lookup acknowledgement edges, wrong hints, lane eligibility, big-endian partial writes on both sides of the returned pair, a measured four-way mask from qualified hinted idle acknowledgements, snoop/refill, cold external bus error rejection, and paused C_LOOK completion. The memory model merges partial stores. Expected accepted run: idle8, look2, reject2, fault1, snoop1, paused3, way mask0xF, ALL P136 FOCUSED TESTS PASSED. Fatal assertions check data, exact acknowledgement counts, required coverage and timeout. This does not replace CPU/IRQ integration or hardware validation.

Additional root-audited P136 cache gates: P135-aware exact-span/no-gap bench (`parallel_span_checks.patch`), latency-aware snoop, XSTORE100, and posted-read matrix216. Evidence: `scratch/p136_hinted_parallel_span_20260921/{direct,smoke}`. Earlier failing experimental logs are preserved; only the final source hash above and identified terminal logs are accepted.
