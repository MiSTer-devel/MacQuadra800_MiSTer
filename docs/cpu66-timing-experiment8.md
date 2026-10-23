# CPU66 timing experiment 8: registered engine transparency

The funnel-only fit exposes a 12-level ATC-entry selection → translation-address selection → cache tag → way path. This candidate retains the existing engine phases and ordinary two-slot queue.

Like DC1's existing `m1_tp`, one registered bit classifies the engine's stolen logical address as transparent (TTR match or translation disabled). It is ready before the registered ATC read is consumed. The engine compares tags directly against either that logical address or the ATC physical page, in parallel with translation permission checks. Hit remains qualified by valid translation and no fault. Way selection is consumed only with hit, so it need not wait for those permissions. The already registered split address/set replace repeated increments.

A simulation observer compares hit and every consumed way with the original combined lookup. All **185 CPU cases and four adapter tests pass**, including continuous-snoop split stores. All 185 cycle counts match experiment 5 exactly. [Validation](perf/cpu66_20261022/timing8/validation.json). This adds one bit, no wide bank, no cycle and no clock exception.

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fit complete: **33,323 ALMs**, CPU setup **-1.648 ns**, CPU TNS **-397.008 ns**. SDRAM +0.783 ns, bus +0.521 ns, HDMI +0.130 ns and minimum hold +0.098 ns pass. [Reports and RBF hashes](perf/cpu66_20261022/timing8/fit/artifact.json). This is not timing qualified and has not been hardware tested.

The targeted cache-tag and cache-way paths now pass at +2.166 ns and +0.394 ns. The remaining worst path is `m4.split` → write-back store hold → serial pipeline stalls → sequencer `uq0.imm[21]` (12 logic levels). The first-FIFO target report covers `.disp`, which passes; it does not cover every FIFO field. Flattening the stall equations is the next structural experiment.
