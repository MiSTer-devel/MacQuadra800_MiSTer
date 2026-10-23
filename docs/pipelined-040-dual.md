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

## What changes in the CPU

The companion slot handles independent one-word integer operations (move,
add/subtract, compare, bitwise operations, clear/negate, extend and swap),
plus supported address-register moves and quick arithmetic. Pairing checks
register dependencies; both slots move through the backend together and
the younger slot commits only when the older instruction commits without
a redirect. Trace mode issues instructions individually. Complex
microcoded and floating-point operations still run alone. This is a
limited second integer slot, rather than a second complete memory/FPU
pipeline. Its sixth RF read port and third backend write port increase
the replicated MLAB bank count from 25 to 36.

BTIC caches two words at a predicted branch target, allowing fetch to
supply them while the instruction-cache lookup catches up. Its valid
state and target tags must survive neither invalidation nor discarded
refetches; the newer D1 hold fix addresses a stale-BTB livelock. The cache
set count grows from 64 to 128, yielding 8 KB per I/D cache. The byte
enable and tag templates remain explicit for Quartus17 inference. Final
M10K use, area and timing must be measured after fitting.

The upstream README's published out-of-context numbers describe the
earlier scalar core, and the dual-issue design notes report Xilinx LUTs
and slices. Neither establishes the quoted approximately26k ALM result
for a complete Quadra build. The comparison here keeps our peripherals,
VRAM, bus adapter and default feature selection, and reports whole-core
ALMs as well as actual Mac benchmark results.

## Initial synthesis rejection

Both first analysis/synthesis runs stopped at the RF inference guard:
30 MLAB banks were present instead of the required 36. The backend's
third write bank disappeared and Quartus reports uq0s.v, uq1s.v, ex_s.v
and wb_s.v tied low. This would silently remove actual paired issue on
hardware despite passing RTL simulations. No fit or hardware test used
these netlists.

Separately, synthesis reported 102,891/102,895 total registers and an
estimated78,207 ALMs: the two framework OSD buffers (32,768 data bits
each) and MT32 LCD buffer (8,192 data bits) mapped into registers. CPU
cache slices, tag RAMs, predecoder ROM and BTIC word RAMs did infer as
block RAM. The compiler probe and mapping investigation precede any
replacement fit.

The isolated [compiler reproduction](perf/dual_20261023/compiler-probe)
shows s0_ok's registered output stuck at zero when it reads first/last
through its structure argument, while a direct first/last expression
remains dynamic. Passing those same two bits as explicit scalar arguments
retains a dynamic predicate. The integration applies this representation
change to the pairing function and its diagnostic caller. Separately,
explicit M10K attributes on the two OSD buffers and MT32 LCD buffer replace
automatic resource selection. The next A&S must verify those memories,
36 RF MLAB banks, and nonconstant companion-valid state before fitting.
No VRAM storage or guest-visible pipeline behavior is changed.

All225 CPU cases pass again after the predicate representation change,
with identical cycle counts in every case. Both1x and2x adapter variants
also retain identical cycles and beat counts under normal and fast
acknowledgements. The exact R2 inputs and mapping checks are pinned before
restarting full synthesis.

## Compiler RAM-budget comparison

After the pairing fix, R2 preserves all36 RF banks and nonconstant
companion-valid state. Its forced OSD/LCD memories infer correctly, but
the automatic RAM-budget heuristic instead puts both scaler polyphase
coefficient memories (10,240 bits each) into registers. The 33 MHz fitter
reports needing4,429 LABs where the device provides4,191.

R3 keeps every RTL file identical and disables
SYNTH_RESOURCE_AWARE_INFERENCE_FOR_BLOCK_RAM in its isolated QSF. This
setting name was obtained from the installed17.0 project API. The
[Standard Edition guide](https://docs.altera.com/r/docs/683283/18.1/design-compilation-user-guide-quartus-prime-standard-edition/resource-aware-ram-rom-and-shift-register-inference?contentId=qyeeXMpVNhjBnX13_IsAxQ)
describes this budget-driven RAM-to-logic fallback; the actual fit still
must verify physical RAM availability.

The 33 MHz R3 synthesis has29,315 registers and3,722,339 block-memory bits,
compared with49,811 registers and3,701,859 bits in R2. The20,480-bit
coefficient-memory difference accounts for the20,496-register reduction
(including16 auxiliary registers). This is a compiler mapping comparison;
CPU behavior, clocks and video architecture are unchanged. A matching
66 MHz R3 build is pinned separately. Main's recipe is frozen while the
isolated flows run.
