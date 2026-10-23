# Quartus17 pairing predicate reproduction

Use this branch's ap68040_pkg.sv and either original.sv or corrected.sv
as probe.sv. Set device5CSEBA6U23I7, top probe, SYSTEMVERILOG_FILE for
package then probe, and VIRTUAL_PIN ON to*. Run quartus_map probe.

The registered ok vector is {direct first-and-last, s0_ok, s1_indep}.
Original synthesis ties ok[1] to GND even though u is an unconstrained
input and direct ok[2] remains dynamic. With the identical first/last
bits passed as explicit function arguments, ok[1] remains dynamic.
All other predicate terms and the s1_indep function are unchanged.
The exact source and both reports are preserved here. The full-core
acceptance guard also requires all36 RF MLAB banks and rejects a
constant uq0s.v/uq1s.v/ex_s.v/wb_s.v, so another silent removal cannot
be accepted as a valid dual-issue comparison.
