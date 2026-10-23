# CPU66 timing experiment 11: parallel stalls with circular queue

This compares experiment 10 with experiment 6's circular representation of the same two-slot micro-op FIFO. The old attempt predated the cache selector fix and regressed other paths. With that cache family now passing, this experiment measures whether the queue removes the late hold → wide FIFO head path that still limits experiment 8.

Two pointer bits select the same two storage banks. A pop moves only the read pointer; emit writes only the selected bank. There are no extra entries, wide banks or cycles. The existing FIFO observer compares all valid contents against the original queue every active clock. All **185 CPU cases and four adapters pass**, with exactly matching cycle counts to experiment 10. [Validation](perf/cpu66_20261022/timing11/validation.json), [queue model](perf/cpu66_20261022/timing6/fifo_model.py).

66/33/99 MHz, seed 38 and balanced synthesis remain fixed. Fitted results are pending. Neither this nor experiment 10 is promoted before the fitted area/setup/hold/crossing results are measured.
