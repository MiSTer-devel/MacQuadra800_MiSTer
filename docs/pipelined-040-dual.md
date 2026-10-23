# Ranzbak dual issue Quadra experiment

The new `pipelined-040-dual` branch preserves the saved CPU66 checkpoint
and replaces its CPU RTL with apolkosnik's current `faster` branch,
`eed15a0c7553d4bf220d2f9c164077d76ea69cb6`. This includes Ranzbak's
[faster-dual](https://github.com/ranzbak/AP68040/tree/fcb326be1d60d400ba4873fb68446a985429ec51)
work and newer [Minimig fixes](https://github.com/apolkosnik/AP68040/tree/eed15a0c7553d4bf220d2f9c164077d76ea69cb6).
The NeXT branch is still the older source we previously imported.

The measured baseline will use upstream's register/address-register dual
issue and BTB target-word cache, with 8 KB instruction and data caches.
Second-slot loads are disabled, matching upstream's latest hardware
default: intermittent bad load data corrupted Minimig disk contents with
that class enabled despite passing simulations. No original disk images
will be used as writable test media.

[Integration provenance](../rtl/ap68040_faster/UPSTREAM_QUADRA.md) lists
the local patches and retained bug fixes. In particular, the new faster
branch lacks two fixes already present in our old port; both are reapplied.
No old CPU66 timing optimization or DDR-VRAM change is included.

The working branch defaults to CPU/bus 33 MHz, SDRAM 99 MHz. The existing
CPU_AP68040_2X adapter selects the separate 66/33/99 MHz comparison. Each
fit will pin its inputs and keep a separate Quartus database. Mac hardware
qualification and Speedometer proceed at 33 MHz first, then 66 MHz.

Initial tag-RAM checks pass (8,192 cycles, 4,065 writes and 1,064
same-address collisions). All four Quadra adapter cases pass: 1x normal
34,851 cycles / 2,392 beats, 1x fast 33,707 / 2,389; 2x normal 28,311 /
2,357, 2x fast 27,320 / 2,355. These directed workload cycle counts are
not Speedometer performance measurements. The expanded CPU regression passes 225 cases: 45 programs under five bus
configurations. The original new PIO diagnostic failed test 2 in all five
configurations; an unmodified upstream control reproduced the same failure.
Its claimed noncacheable device mapping was absent. The corrected fixture
identity-maps RAM and marks only page F serialized/noncacheable, retaining a
cacheable destination buffer; all five cases pass. The original failure,
control, corrected results and exact upstream/local RTL patch are preserved
under [measurements](perf/dual_20261023).

Removing only the Quadra load-capture fix makes adapter test 11 fail again;
the retained fix passes. The t_ld1 event report also confirms actual paired
retirements with the chosen hardware parameters. No new FPGA timing or
hardware boot result is claimed yet.
