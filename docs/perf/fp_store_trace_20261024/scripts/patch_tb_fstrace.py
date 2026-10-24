#!/usr/bin/env python3
# fp_store_trace 2026-10-24: add a per-cycle FP-store trace to a SCRATCH copy
# of rtl/ap68040_faster/tb/tb_ap68040.sv (never the checkout's).  Nothing
# under rtl/ changes: every probe is a hierarchical reference from the bench.
#
#   +fstag=<n> +fslen=<cycles>   from the cycle after the stamp whose tag is
#                                <n> (decimal), one line a cycle for <cycles>:
#     the fetch queue (Q words, R records, U uops), the uop in each of AG,
#     DC1, DC2, EX, WB (pc, op[.FPU sub], L/S, result register, AG update,
#     * = the instruction's last uop), the stage holds, adv_ex/adv_wb (+1:
#     a second slot committed beside WB), the FPU interface's handshake (the
#     sub-operation in EX, safe, hold, go, done_q, bg, f_req, the FPU's rq,
#     f_done, f_accepted, f_pbusy, the FPU state fst, mvr_wait), and the DMU's
#     store path (wb_st, wb_fast, st_rdy, e_st, dw, dc2_rdy, m2.fast, m2 hit)
#   STAMP lines also print the absolute cycle (at=).
import sys
src = open(sys.argv[1]).read()

old_stamp = '''					$display("STAMP tag=%04x cycles=%0d instructions=%0d", w, cycles - stamp_prev,
					         insns - insn_prev);
'''
new_stamp = '''					$display("STAMP tag=%04x cycles=%0d instructions=%0d at=%0d", w, cycles - stamp_prev,
					         insns - insn_prev, cycles);
'''
assert src.count(old_stamp) == 1, "STAMP display not found"
src = src.replace(old_stamp, new_stamp)

anchor = "// exception entries\n"
assert src.count(anchor) == 1, "anchor not found"
block = r'''// fp_store_trace 2026-10-24: +fstag=<n>,+fslen=<cycles>: the whole pipeline,
// the FPU interface's handshake and the DMU's store path, one line a cycle
// from the stamp with tag <n>
int fs_tag, fs_len, fs_from, fs_to;
initial begin
	if (!$value$plusargs("fstag=%d", fs_tag)) fs_tag = -1;
	if (!$value$plusargs("fslen=%d", fs_len)) fs_len = 400;
	fs_from = -1; fs_to = -1;
end
function automatic string fs_reg(input logic [4:0] r);
	if (r < 5'd8) return $sformatf("D%0d", r);
	else if (r < 5'd15) return $sformatf("A%0d", r - 5'd8);
	else if (r == 5'd15) return "USP";
	else if (r == 5'd16) return "ISP";
	else if (r == 5'd17) return "MSP";
	else return $sformatf("T%0d", r - 5'd18);
endfunction
function automatic string fs_sub(input logic [3:0] c);
	case (c)
		4'd0: return "CHK";  4'd1: return "DISP"; 4'd2: return "GET";  4'd3: return "END";
		4'd4: return "CRR";  4'd5: return "CRW";  4'd6: return "LIST"; 4'd7: return "MVR";
		4'd8: return "MVW";  4'd9: return "COND"; 4'd10: return "DBCC"; 4'd11: return "SV0";
		4'd12: return "SVW"; 4'd13: return "RS0"; 4'd14: return "RSW"; default: return "EAL";
	endcase
endfunction
function automatic string fs_uop(input logic v, input ap68040_pkg::uop_t u);
	string s;
	if (!v) return "----                      ";
	case (u.op)
		7'd55: s = $sformatf("FPU.%s", fs_sub(u.cond));
		7'd0:  s = "MOV";
		7'd1:  s = "ADD";
		7'd3:  s = "SUB";
		7'd5:  s = "CMP";
		7'd35: s = "EA";
		7'd36: s = "BCC";
		7'd37: s = "DBCC";
		7'd46: s = "LATCH";
		7'd54: s = "MISC";
		default: s = $sformatf("op%0d", u.op);
	endcase
	if (u.mem == 2'd1) s = {s, " L"};
	else if (u.mem == 2'd2) s = {s, " S"};
	else if (u.mem == 2'd3) s = {s, " RMW"};
	if (u.d_v) s = {s, ">", fs_reg(u.d_reg)};
	if (u.ag && u.upd_v) s = {s, " ag>", fs_reg(u.upd_reg)};
	if (u.last) s = {s, "*"};
	return $sformatf("%04x %-21s", u.pc[15:0], s);
endfunction
always_ff @(posedge clk) begin
	if (fs_tag >= 0 && fs_from < 0 && ev && !ev_rd && !ev_err && ev_tt == 2'd0 &&
	    (ev_addr[15:0] & 16'hFFFE) == 16'hF108 && ev_word(ev_addr, ev_data) == 16'(fs_tag)) begin
		fs_from = cycles + 1;
		fs_to   = fs_from + fs_len;
		$display("%8d FSTRACE start: stamp tag %04x", cycles, fs_tag[15:0]);
	end
	if (fs_from >= 0 && cycles >= fs_from && cycles < fs_to)
		$display("%8d Q%0d R%0d U%0d | AG %s| D1 %s| D2 %s| EX %s| WB %s| h a%b d1%b d2%b e%b w%b adv e%b w%b%s%s | FP %s sf%b h%b go%b dq%b bg%b rq%b/%b dn%b ac%b pb%b fst%0d mw%b | DM st%b fa%b rdy%b e%0d dw%b d2r%b m2f%b hit%b",
		         cycles, dut.fetch.cnt, dut.rq_n, dut.uq_n,
		         fs_uop(dut.be.ag_v, dut.be.ag_u), fs_uop(dut.be.dc1_v, dut.be.dc1_u),
		         fs_uop(dut.be.dc2_v, dut.be.dc2_u), fs_uop(dut.be.ex_v, dut.be.ex_u),
		         fs_uop(dut.be.wb_v, dut.be.wb_u),
		         dut.be.ag_hold, dut.dm_hold1, dut.be.dc2_hold, dut.be.ex_hold, dut.be.wb_hold,
		         dut.be.adv_ex, dut.be.adv_wb, dut.be.wb1_commit ? "+1" : "  ",
		         dut.redir_v ? " REDIR" : (dut.d_redir_v ? " DREDIR" : ""),
		         (dut.be.ex_v && dut.be.ex_is_fp) ? fs_sub(dut.be.ex_u.cond) : "-",
		         dut.be.fpif.safe, dut.be.fpif.hold, dut.be.fpif.go, dut.be.fpif.done_q, dut.be.fpif.bg,
		         dut.be.fpif.f_req, dut.be.fpif.fpu.rq, dut.be.fpif.f_done, dut.be.fpif.f_accepted,
		         dut.be.fpif.f_pbusy, dut.be.fpif.fpu.fst, dut.be.fpif.mvr_wait,
		         dut.dmu.wb_st, dut.dmu.wb_fast, dut.dmu.st_rdy, dut.dmu.e_st, dut.dmu.dw,
		         dut.dmu.dc2_rdy, dut.dmu.m2.fast, dut.dmu.m2.x.hit);
end

'''
src = src.replace(anchor, block + anchor)
open(sys.argv[2], "w").write(src)
print("patched", sys.argv[2])
