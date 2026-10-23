# CPU66 timing experiment 6: circular two-slot micro-op queue

The first-slot pop control still misses timing by 1.314 ns in experiment 4. This comparison adds to the [integer funnel candidate](cpu66-timing-experiment5.md) a circular representation of the same two-entry micro-op queue. A pop toggles the read pointer; an emit writes the selected bank and toggles the write pointer. Neither wide bank depends on backend pop. Full occupancy still forbids emit even during a pop, preserving the original issue timing and capacity. Flush/exception entry reset both pointers with the count.

There are two additional single-bit pointers, no new wide bank and no extra issue cycle. The tradeoff is a wide head-selection mux controlled by the registered read pointer; FPGA area and that new data path must be measured. The target report script recognizes either the original slot registers or the new physical banks. The second-slot internal wire presents the logical second entry for the existing equivalence observer.

All **185 CPU runs** and **four adapter cases** pass with the original queue-content observer enabled; all 185 cycle counts match experiment 2. An [abstract exhaustive model](perf/cpu66_20261022/timing6/fifo_model.py) checks 72 reachable paired states and 2,052 transitions over three representative payload values, including empty/full, simultaneous push/pop, flush and exception entry. [Validation](perf/cpu66_20261022/timing6/validation.json).

The normal balanced recipe, 66/33/99 MHz and seed 38 are retained. No timing exception is added. An isolated fit will compare the funnel-only candidate with this queue variant. Timing and hardware qualification remain pending.
