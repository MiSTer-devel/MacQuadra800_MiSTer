# Dual issue AP68040 in the Quadra

The `pipelined-040-dual` experiment imports apolkosnik/AP68040 `faster` at
`eed15a0c7553d4bf220d2f9c164077d76ea69cb6` (2026-10-23). It contains
Ranzbak's dual issue work (`ranzbak/AP68040` `faster-dual` at
`fcb326be1d60d400ba4873fb68446a985429ec51`) and subsequent Minimig fixes,
including stale-BTB refetch handling and corrected second-slot decoding.
The NeXT `pipelined_040` head remains `f8e9591`, the source of our older
scalar port. The new CPU is imported afresh; our local CPU66 timing
experiments are not carried into its RTL.

The wrapper explicitly enables DUAL and BTIC with S1_CLASSES=3'b011:
register and address-register companions, with second-slot loads disabled.
This is upstream's current hardware default following intermittent
Minimig disk corruption with second-slot loads. Both caches are 8 KB
(CSB=7). The optional FPU pipeline, loop predictor, early results,
DC1 ATC port and skid register stay off.

Local integration patches are limited to:

- Physical I/O serialization/cacheability parameters, unchanged from the
  Quadra port: only RAM and ROM are cacheable.
- The load-capture boot fix, adapted to both older dual-issue writers:
  a same-clock younger DC2 load capture must not be marked stale.
- DBcc floor input and counter for A/UX calibration; zero at 33 MHz and
  four clocks at 66 MHz, using the existing bus/clock adapter.
- Quartus 17 byte-enabled RAM slices and read-only-port-A D-cache tag
  template. The upstream Xilinx-oriented templates are not used for those
  memories. A fit must verify four tag M10Ks, data slices, and 36 RF MLABs.
- Quartus17 pairing predicate workaround: pass first/last as explicit
  function arguments, since reading those structure members inside s0_ok
  synthesizes to constant zero. The compiler reproduction and full-core
  RF/companion-valid guards document this.
- Upstream main fixes 190ea48 (IPEND claim against the committing SR mask)
  and 6d146df (discarded DC2 job kill mark survives a snoop freeze).
  The faster branch diverged before these landed; its two-cycle table-walk
  tag compare is already present.

The testbench merges the older functional tests with upstream's new dual
issue tests. All 45 programs run under five bus configurations, with
AP_S1C=3'b011 to match hardware. The ADDX-loop test names its branch label
at the unchanged ORG address for compatibility with the installed vasm.
The runner uses NUL-separated xargs input on macOS and Linux. The previous
scalar timing-rewrite observers are optional rather than bound to this
new implementation.

Area figures for an isolated CPU or another host core cannot establish
Quadra area or timing. The requested 33 and 66 MHz results must come from
this complete integration and matched Speedometer hardware runs.

Memory-performance follow-up (`pipelined-040-dual-memory`): the optional
PA_VRAM_POST parameter defaults off upstream and is enabled by the Quadra
wrapper. A validated, cache-inhibited, non-locked VRAM store within one
bus word can retire when captured in the existing DMU bus registers. The
engine remains occupied until the write finishes. Faults, cache hits,
locked/RMW operations, crossing accesses and MOVE16 retain the precise
path. See docs/dual-memory-performance.md for controls and qualification.
