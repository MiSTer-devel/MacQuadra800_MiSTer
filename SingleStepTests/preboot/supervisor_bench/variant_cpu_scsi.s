| variant_cpu_scsi.s — per-variant constants for CPU bench on SCSI.
| Linked alongside bench_main.c + payload_entry_cpu.s.

    .data
    .global g_results_offset
    .global g_results_max_bytes
| 8-byte magic tag the build script can grep for in the assembled .bin
| to patch the next two longs at link/build time. Lets us avoid hard-
| coding the /Results.jsonl partition offset — it varies with payload
| size and disk layout.
g_results_marker:    .ascii  "RJSNLTAG"   | findable signature
g_results_offset:    .long 0xDEADBEEF     | patched by build script
g_results_max_bytes: .long 409600         | 400 KB pre-allocation

| Chain-loader hook (all-in-one disks): partition offset + read length of
| the next suite's payload. Zero offset (the default, and what per-suite
| disks keep) = last suite, hang at DONE as always.
    .global g_next_offset
    .global g_next_length
g_next_marker:       .ascii  "NEXTPAYL"   | findable signature
g_next_offset:       .long 0              | partition byte offset; 0 = none
g_next_length:       .long 0              | bytes to _Read (512-rounded)
