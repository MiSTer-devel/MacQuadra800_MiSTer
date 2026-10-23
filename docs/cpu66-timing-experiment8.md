# CPU66 timing experiment 8: registered engine transparency

The funnel-only fit exposes a 12-level ATC-entry selection → translation-address selection → cache tag → way path. This candidate retains the existing engine phases and ordinary two-slot queue.

Like DC1's existing `m1_tp`, one registered bit classifies the engine's stolen logical address as transparent (TTR match or translation disabled). It is ready before the registered ATC read is consumed. The engine compares tags directly against either that logical address or the ATC physical page, in parallel with translation permission checks. Hit remains qualified by valid translation and no fault. Way selection is consumed only with hit, so it need not wait for those permissions. The already registered split address/set replace repeated increments.

A simulation observer compares hit and every consumed way with the original combined lookup. All **185 CPU cases and four adapter tests pass**, including continuous-snoop split stores. All 185 cycle counts match experiment 5 exactly. [Validation](perf/cpu66_20261022/timing8/validation.json). This adds one bit, no wide bank, no cycle and no clock exception.

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fitted results are pending.
