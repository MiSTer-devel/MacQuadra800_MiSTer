# CPU66 timing experiment 17: append before shifting the fetch queue

Experiment16 balanced's worst path passes from a fetched instruction through D1's consume decision, count subtraction and shift/append selection into the fetch queue. This candidate constructs the old queue with the two F3 words appended at the registered count, then selects the shifted window. The append-position arithmetic therefore runs before the late consume input. Queue count is similarly calculated as `(count + append_count) - consume`.

Queue capacity, registers, append and consume rates, predecode ring, redirects and pipeline cycles remain unchanged. Unused entries retain their old contents too, preserving D1 lookahead behavior and exact cycle counts. An independent simulation observer implements the original shift-then-append rules and compares every valid instruction word and all four fault/demand/ATC/branch flags, including redirects and simultaneous append/consume. The existing predecode-head observer remains active.

All **185 CPU cases pass with exact experiment16 cycle counts**; all four machine bus adapter configurations pass. No register, cycle or timing exception is added. [Validation](perf/cpu66_20261022/timing17/validation.json).

Fits compare balanced and speed synthesis using pinned copies of the same RTL at66/33/99MHz, seed38, stamp261022. The main recipe remains balanced. Actual fitted timing and area will determine whether this change is retained. No DDR/VRAM changes are included.
