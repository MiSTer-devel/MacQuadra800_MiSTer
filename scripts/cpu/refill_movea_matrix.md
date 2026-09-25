# MOVEA branch-refill matrix

`refill_movea_matrix.s` is the 11-case program used with `rtl/ap68040/tb/tb_ap040_program.v`. It verifies W/L forms of (An), (An)+, -(An), d16(An), A7 source updates, source/destination aliasing, word sign extension, exact An updates and unchanged CCR=0x1F. Each loop is aligned and branches repeatedly to the MOVEA. The F100/F102 result protocol and three memory timing phases come from the existing bench.

Assemble with vasm `-Fbin -m68040 -no-opt -o OUTPUT.bin scripts/cpu/refill_movea_matrix.s`, then run `python3 rtl/ap68040/tb/bin2hex.py OUTPUT.bin OUTPUT.hex` (both arguments required). Use explicit P109 and P137 cores with P136 cache and the standard program-bench source list. The directed run used the ordinary sequencer; the separate full CPU/IRQ integration covers enabled P120 pipeline behavior.

Apply `refill_movea_coverage.patch` ONLY to a scratch copy of the P137 core. It adds observation-only log counters to the existing refill arm, without changing control or data. Actual new-path evidence requires log opcodes to have destination mode001, source modes010/011/100/101, and sizes10/11; require all eight combinations. A generic branch counter does not prove this coverage.

Run with `+prog=OUTPUT.hex +dump=OUTPUT.dump.hex`; require ALL TESTS PASSED with no FAIL/ERROR/FATAL and byte-identical baseline/candidate dumps. The program itself asserts expected values before declaring PASS. Root-audited evidence: `scratch/p137_movea_refill_focus_20260921/root_matrix_{p109,p137}.log` and `.dump.hex`. Matching dump SHA2569cf8dc4e3680cf31d000f575b7e5f576b9939331c2c03639eca8bf7c3cca79c5. This matrix does not inject trace or bus faults into the new path.
