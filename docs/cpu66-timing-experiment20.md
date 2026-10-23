# CPU66 timing experiment 20: select the maintenance write set before its tag match

Experiment17 balanced's worst path passes from a cache-maintenance tag compare through the valid/dirty write-set selector and a read of `lsw`. During E_M_SCAN2 the selected set is already known from the registered scan index; the tag match only decides whether any write/invalidation occurs.

The candidate selects `vp_set` unconditionally in that state and preserves every match, way mask, valid/dirty enable and value. WB fast writes are restricted to E_IDLE; the split store drains there before a scan may start; snooping freezes the engine. A simulation assertion at the scan's port selection also verifies that no earlier writer has enabled the port. When the match fails, the changed address is unused. No pipeline or engine state transition changes.

This prototype is experiment19 plus [scan-address.patch](perf/cpu66_20261022/timing20/scan-address.patch), still confined to scratch. All185 CPU cases and four adapters pass with exact experiment18 cycles, including split copyback, maintenance and snoop cases. No new register, cycle, array or timing exception is added. [Validation](perf/cpu66_20261022/timing20/validation.json). Fitting is required before any timing/area benefit can be claimed. No VRAM/DDR changes are included.
