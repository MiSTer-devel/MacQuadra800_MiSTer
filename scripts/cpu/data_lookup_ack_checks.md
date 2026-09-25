# P131 data-lookup acknowledgement checks

Reproduce the generic portable span bench in this order:

1. Generate the standard span bench with `scripts/cpu/cache_spanning_reads.py` using the same inputs/options as the P124 check.
2. Apply the existing `scripts/cpu/spanning_read_ack_checks.patch` to the generated `spans_tb.v`.
3. Apply `scripts/cpu/data_lookup_span_checks.patch` to the resulting portable bench (pass the generated file explicitly to `patch`, e.g. `patch /path/to/spans_tb.v < scripts/cpu/data_lookup_span_checks.patch`). The patch adds `P131_DATA_LOOKUP_ACK` conditionals for the two ordinary data-lookup latency checks. Compile the baseline without that macro (3 cycles); compile P131 with `-DP131_DATA_LOOKUP_ACK` (2 cycles). All data, residency, zero-memory-read, and acknowledgement assertions remain active.

The isolated D-cache probe is reproducible from `scripts/cpu/data_lookup_directed_checks.patch`, which creates `scripts/cpu/tb_p131_d_lookup.sv`. Compile it with the P124 or P131 cache and `rtl/ap68040/rtl/primitives/dpram.v`, top `tb_p131_d_lookup`. Define `P131_DLOOK` only for P131 so the probe measures `dut.fast_data_look`. It covers warm data lookup, no-gap BWL requests, one qualified ack after a CE pause, same-row admission/C_LOOK/paused D snoops, and bus-error no-early-ack behavior.

For the ordinary snoop bench, apply `patch -p0 < scripts/cpu/data_lookup_ack_checks.patch` from the repository root outside an active FPGA source freeze. Its candidate macro and baseline latency expectations are the same.
