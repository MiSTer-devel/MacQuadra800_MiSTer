import re, sys, os

root = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/mister/q800_fpchg_20261024/stageA")
fpif_path = os.path.join(root, "rtl/ap68040_faster/rtl/ap68040_fpif.sv")
backend_path = os.path.join(root, "rtl/ap68040_faster/rtl/ap68040_backend.sv")
ucode_path = os.path.join(root, "rtl/ap68040_faster/tools/ucode.py")

# 1. Patch ap68040_fpif.sv
s = open(fpif_path).read()
p1 = "output logic  [4:0] rs_words        // FRESTORE frame long words"
if p1 not in s:
    p1 = [line for line in s.splitlines() if "rs_words" in line and "output logic" in line][0]
rep1 = "	output logic  [4:0] rs_words,        // FRESTORE frame long words\n	output logic [31:0] get_w1,\n	output logic [31:0] get_w2"
assert p1 in s, "rs_words not found in fpif"
s = s.replace(p1, rep1, 1)

p2 = "wire nosafe = (sub == FC_GET) || (sub == FC_END && !sx_v && !fsr_q);"
rep2 = """assign get_w1 = get_q[63:32];
assign get_w2 = get_q[31:0];
wire live_done = go && f_done && !f_excreq && !f_unimp && !f_unsupp;
wire [95:0] store_dout = done_q ? get_q : f_dout;

wire nosafe = (sub == FC_GET) || (sub == FC_END && !sx_v && !fsr_q);"""
assert p2 in s, "nosafe not found in fpif"
s = s.replace(p2, rep2, 1)

p3 = "if (!done_q) hold = 1'b1;"
rep3 = "if (!(done_q || live_done)) hold = 1'b1;"
assert p3 in s, "if (!done_q) hold not found in fpif"
s = s.replace(p3, rep3, 1)

# In FC_DISP res_g:
old_res_g = """					if (ea_dn) begin
						case (fmt)
							3'd4:    res_g = {bv[31:16], f_dout[95:80]};
							3'd6:    res_g = {bv[31:8], f_dout[95:88]};
							default: res_g = f_dout[95:64];
						endcase
						dkill = sx_kill;
					end
					else case (fmt)
						3'd4:    res_g = {16'd0, f_dout[95:80]};
						3'd6:    res_g = {24'd0, f_dout[95:88]};
						default: res_g = f_dout[95:64];
					endcase"""

new_res_g = """					if (ea_dn) begin
						case (fmt)
							3'd4:    res_g = {bv[31:16], store_dout[95:80]};
							3'd6:    res_g = {bv[31:8], store_dout[95:88]};
							default: res_g = store_dout[95:64];
						endcase
						dkill = sx_kill;
					end
					else case (fmt)
						3'd4:    res_g = {16'd0, store_dout[95:80]};
						3'd6:    res_g = {24'd0, store_dout[95:88]};
						default: res_g = store_dout[95:64];
					endcase"""
assert old_res_g in s, "FC_DISP res_g not found in fpif"
s = s.replace(old_res_g, new_res_g, 1)

old_res = """		FC_DISP: if (ocl == 3'b011) begin
			if (ea_dn) case (fmt)
				3'd4:    res = {bv[31:16], f_dout[95:80]};
				3'd6:    res = {bv[31:8], f_dout[95:88]};
				default: res = f_dout[95:64];
			endcase
			else case (fmt)
				3'd4:    res = {16'd0, f_dout[95:80]};
				3'd6:    res = {24'd0, f_dout[95:88]};
				default: res = f_dout[95:64];
			endcase
		end"""

new_res = """		FC_DISP: if (ocl == 3'b011) begin
			if (ea_dn) case (fmt)
				3'd4:    res = {bv[31:16], store_dout[95:80]};
				3'd6:    res = {bv[31:8], store_dout[95:88]};
				default: res = store_dout[95:64];
			endcase
			else case (fmt)
				3'd4:    res = {16'd0, store_dout[95:80]};
				3'd6:    res = {24'd0, store_dout[95:88]};
				default: res = store_dout[95:64];
			endcase
		end"""
assert old_res in s, "FC_DISP res not found in fpif"
s = s.replace(old_res, new_res, 1)

open(fpif_path, "w").write(s)
print("ap68040_fpif.sv patched successfully")

# 2. Patch ap68040_backend.sv
sb = open(backend_path).read()
p6 = "logic  [4:0] fp_svwords, fp_rswords;"
rep6 = "logic  [4:0] fp_svwords, fp_rswords;\nlogic [31:0] fp_get1, fp_get2;"
assert p6 in sb, "fp_svwords not found in backend"
sb = sb.replace(p6, rep6, 1)

p7 = ".sv_words(fp_svwords), .rs_words(fp_rswords)"
rep7 = ".sv_words(fp_svwords), .rs_words(fp_rswords),\n\t.get_w1(fp_get1), .get_w2(fp_get2)"
assert p7 in sb, "fpif ports not found in backend"
sb = sb.replace(p7, rep7, 1)

p8 = """	case (ex_u.op)
		OP_CAS:  ex_st = cas_eq ? ex_av : ex_bv;
		OP_CAS2W: begin
			ex_st     = (ex_u.cond[0] && !cas2_eq) ? ex_bv : ex_av;
			ex_stkill = !ex_u.cond[0] && !cas2_eq;
		end
		default: ex_st = ex_res;
	endcase"""

rep8 = """	case (ex_u.op)
		OP_CAS:  ex_st = cas_eq ? ex_av : ex_bv;
		OP_CAS2W: begin
			ex_st     = (ex_u.cond[0] && !cas2_eq) ? ex_bv : ex_av;
			ex_stkill = !ex_u.cond[0] && !cas2_eq;
		end
		OP_MOV: begin
			if (ex_u.mem == M_ST && ex_u.cond == 4'd1) ex_st = fp_get1;
			else if (ex_u.mem == M_ST && ex_u.cond == 4'd2) ex_st = fp_get2;
			else ex_st = ex_res;
		end
		default: ex_st = ex_res;
	endcase"""
assert p8 in sb, "ex_st case not found in backend"
sb = sb.replace(p8, rep8, 1)

open(backend_path, "w").write(sb)
print("ap68040_backend.sv patched successfully")

# 3. Patch ucode.py
su = open(ucode_path).read()

p9 = "R('FPU_OUT8', F('GET', a='CONST', const=1, d='T1'), _fst('T0', 0), _fst('T1', 4),\n  F('END', ag='FUPD', last=1))"
rep9 = "R('FPU_OUT8', _fst('T0', 0), _fst('ZERO', 4, cond=1),\n  F('END', ag='FUPD', last=1))"
assert p9 in su, "FPU_OUT8 not found in ucode.py"
su = su.replace(p9, rep9, 1)

p10 = "R('FPU_OUT12', F('GET', a='CONST', const=1, d='T1'), F('GET', a='CONST', const=2, d='T2'),\n  _fst('T0', 0), _fst('T1', 4), _fst('T2', 8), F('END', ag='FUPD', last=1))"
rep10 = "R('FPU_OUT12', _fst('T0', 0), _fst('ZERO', 4, cond=1), _fst('ZERO', 8, cond=2),\n  F('END', ag='FUPD', last=1))"
assert p10 in su, "FPU_OUT12 not found in ucode.py"
su = su.replace(p10, rep10, 1)

p11 = """R('FPU_K_OUT8', FCHKEA(), F('DISP', d='T0'),
  F('GET', a='CONST', const=1, d='T1'), _fst('T0', 0), _fst('T1', 4),
  F('END', ag='FUPD', last=1))"""
rep11 = """R('FPU_K_OUT8', FCHKEA(), F('DISP', d='T0'),
  _fst('T0', 0), _fst('ZERO', 4, cond=1),
  F('END', ag='FUPD', last=1))"""
assert p11 in su, "FPU_K_OUT8 not found in ucode.py"
su = su.replace(p11, rep11, 1)

p12 = """R('FPU_K_OUT12', FCHKEA(), F('DISP', d='T0'),
  F('GET', a='CONST', const=1, d='T1'), F('GET', a='CONST', const=2, d='T2'),
  _fst('T0', 0), _fst('T1', 4), _fst('T2', 8), F('END', ag='FUPD', last=1))"""
rep12 = """R('FPU_K_OUT12', FCHKEA(), F('DISP', d='T0'),
  _fst('T0', 0), _fst('ZERO', 4, cond=1), _fst('ZERO', 8, cond=2),
  F('END', ag='FUPD', last=1))"""
assert p12 in su, "FPU_K_OUT12 not found in ucode.py"
su = su.replace(p12, rep12, 1)

p13 = """R('FPU_MVS',
  *[u for k in range(8) for u in (
      F('MVR', d='T2'), F('GET', a='CONST', const=1, d='T3'),
      F('GET', a='CONST', const=2, d='T4'),
      _fst('T2', 0, dyn=1, dynk=k), _fst('T3', 4, dyn=1, dynk=k),
      _fst('T4', 8, dyn=1, dynk=k),
      U(ag='ADDC', agb='T11', agw='T11', const=12, dyn=1, dynk=k))],
  U(jc='EA0_APD', jt='FPU_MVE.0'),
  F('END', last=1))"""
rep13 = """R('FPU_MVS',
  *[u for k in range(8) for u in (
      F('MVR', d='T2'),
      _fst('T2', 0, dyn=1, dynk=k), _fst('ZERO', 4, dyn=1, dynk=k, cond=1),
      _fst('ZERO', 8, dyn=1, dynk=k, cond=2),
      U(ag='ADDC', agb='T11', agw='T11', const=12, dyn=1, dynk=k))],
  U(jc='EA0_APD', jt='FPU_MVE.0'),
  F('END', last=1))"""
assert p13 in su, "FPU_MVS not found in ucode.py"
su = su.replace(p13, rep13, 1)

open(ucode_path, "w").write(su)
print("ucode.py patched successfully")
