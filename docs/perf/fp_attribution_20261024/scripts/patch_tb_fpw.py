#!/usr/bin/env python3
# fp_attribution 2026-10-24: extend tb_ap68040.sv's +pcprof (a scratch copy of
# rtl/ap68040_faster/tb, never the checkout) with the FPU background-wait
# accounting the old-core bench got: the dual core releases register-destination
# FP arithmetic to the background (ap68040_fpif bg) and the next FPU uop holds in
# EX with fp_hold until f_end.  Those cycles belong to the released operation, so
# they are moved off the waiting instruction's retire gap (PCPROF) and reported
# as PCFPW (charged to the released operation's address) and PCFPWW (the same
# cycles charged to the waiter, the naive view).
import sys
src = open(sys.argv[1]).read()

old_block = """always_ff @(posedge clk) if (rsti_n && pcprof && dut.be.adv_wb && dut.be.wb_u.last) begin
	pc_cyc[dut.be.wb_u.pc] += cycles - pc_last;
	pc_n[dut.be.wb_u.pc]   += 1;
	pc_last <= cycles;
end
"""
new_block = """// fp_attribution: cycles an FPU uop spends held in EX behind a released
// (background) operation are charged to that operation, not to the waiter
int   pc_fpw  [int unsigned];
int   pc_fpww [int unsigned];
int   fpw_in_gap = 0;
int   fpw_lost = 0;
logic [31:0] fp_bg_pc = 0;
logic        fp_bg_v = 0;
wire  fpbgwait = dut.be.ex_v && dut.be.ex_is_fp && dut.be.fp_hold && dut.be.fpif.bg && !dut.be.fpif.f_end && dut.be.fpif.safe;
always_ff @(posedge clk) if (rsti_n && pcprof) begin
	// the released operation is the last FPU uop that left EX: the waiter is
	// still in EX, and nothing that waits for bg can have left EX since
	if (fpbgwait) begin
		if (fp_bg_v) pc_fpw[fp_bg_pc] += 1; else fpw_lost += 1;
		pc_fpww[dut.be.ex_u.pc] += 1;
		fpw_in_gap += 1;
	end
	if (dut.be.adv_ex && dut.be.ex_is_fp) begin fp_bg_pc = dut.be.ex_u.pc; fp_bg_v = 1'b1; end
	if (dut.be.adv_wb && dut.be.wb_u.last) begin
		pc_cyc[dut.be.wb_u.pc] += cycles - pc_last - fpw_in_gap;
		pc_n[dut.be.wb_u.pc]   += 1;
		pc_last <= cycles;
		fpw_in_gap = 0;
	end
end
"""
assert src.count(old_block) == 1, "pcprof block not found"
src = src.replace(old_block, new_block)

old_dump = """	foreach (pc_cyc[a]) $display("PCPROF %08x %0d %0d", a, pc_n[a], pc_cyc[a]);
"""
new_dump = old_dump + """	foreach (pc_fpw[a]) $display("PCFPW %08x %0d", a, pc_fpw[a]);
	foreach (pc_fpww[a]) $display("PCFPWW %08x %0d", a, pc_fpww[a]);
	$display("PCFPW_LOST %0d", fpw_lost);
"""
assert src.count(old_dump) == 1, "pcprof_dump not found"
src = src.replace(old_dump, new_dump)
open(sys.argv[2], "w").write(src)
print("patched", sys.argv[2])
