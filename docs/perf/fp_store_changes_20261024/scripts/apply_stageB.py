import re, sys, os

root = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/mister/q800_fpchg_20261024/stageB")
fpu_path = os.path.join(root, "rtl/ap68040_faster/rtl/fpu/ap040_fpu.v")

s = open(fpu_path).read()

# 1. Add st_norm and st_sE definitions near round_up
p1 = """// IEEE round-up decision from {lsb, G, R|S} and sign
function round_up;"""

rep1 = """// P255: normal register store in dispatch clock
wire        st_norm = fr_src_m[63] && (fr_src_e != 15'h7FFF);
wire signed [17:0] st_sE = $signed({3'd0, fr_src_e}) - 18'sd16383;

// IEEE round-up decision from {lsb, G, R|S} and sign
function round_up;"""

assert p1 in s, "round_up function header not found in ap040_fpu.v"
s = s.replace(p1, rep1, 1)

# 2. Update rd_mi and sd_out to use eff_* when fst == F_IDLE
p2 = """// One incrementer for the roundings of a_m at a precision's last kept bit:
// F_ROUND's (the operation's precision) and a single or double register
// store's (F_SRC, by the store format), in states of their own.
wire  [1:0] rd_pr   = (fst == F_SRC) ? ((r_fmt == 3'd1) ? 2'd1 : 2'd2) : prec_of(r_op);
wire [63:0] rd_mask = (rd_pr == 2'd1) ? 64'hFFFF_FF00_0000_0000 :
                      (rd_pr == 2'd2) ? 64'hFFFF_FFFF_FFFF_F800 : 64'hFFFF_FFFF_FFFF_FFFF;
wire [64:0] rd_mi   = {1'b0, a_m & rd_mask} +
                      ((rd_pr == 2'd1) ? 65'h100_0000_0000 : (rd_pr == 2'd2) ? 65'h800 : 65'd1);

// The single and double stores, in one form (F_SRC: a register's value
// rounded to the format, or its special value; F_PACKS: a denormal after
// the staged shift): the exponent field sd_E and the fraction sd_F as a
// double's, the single's being their upper bits -- one exponent subtract,
// one overflow test, one output multiplexer for both formats.  The
// rounding takes the shared incrementer (rd_mi: rd_pr is the format's).
reg        sd_isS, sd_den, sd_up, sd_inx, sd_ov, sd_tomax, sd_pr;
reg signed [17:0] sd_sE;
reg [17:0] sd_eun;
reg [16:0] sd_enc;
reg [63:0] sd_m;
reg [10:0] sd_E;
reg [51:0] sd_F;
reg [95:0] sd_out;
always @* begin
	sd_isS = (r_fmt == 3'd1);
	sd_sE  = $signed({a_e[16], a_e}) - 18'sd16383;
	sd_den = sd_isS ? (sd_sE < -18'sd126) : (sd_sE < -18'sd1022);
	sd_up  = sd_isS ? round_up(a_m[40], a_m[39], (a_m[38:0] != 0), a_s) :
	                  round_up(a_m[11], a_m[10], (a_m[9:0] != 0), a_s);
	sd_inx = sd_isS ? (a_m[39:0] != 0) : (a_m[10:0] != 0);
	// (a rounding carry out of the significand leaves sd_m zero: the
	// minimum of the next exponent)
	sd_m   = sd_up ? rd_mi[63:0] : (a_m & rd_mask);
	sd_eun = {1'b0, a_e} + {17'd0, sd_up && rd_mi[64]};
	sd_ov  = sd_eun > (sd_isS ? 18'd16510 : 18'd17406);
	sd_enc = sd_eun[16:0] - (sd_isS ? 17'd16256 : 17'd15360);
	sd_tomax = (rnd_mode == 2'b01) || (rnd_mode == 2'b10 && !a_s) || (rnd_mode == 2'b11 && a_s);
	// F_PACKS: the denormal's rounding at the format's last bit
	sd_pr  = sd_isS ? round_up(sh_v[43], sh_v[42], sh_v[41:0] != 0, a_s) :
	                  round_up(sh_v[14], sh_v[13], sh_v[12:0] != 0, a_s);
	if (fst == F_PACKS) begin
		sd_E = {10'd0, sd_pr ? shk_i[63] : shk[63]};
		sd_F = sd_pr ? shk_i[62:11] : shk[62:11];
	end
	else if (a_t != T_NUM) begin
		sd_E = (a_t == T_ZERO) ? 11'd0 : 11'h7FF;
		sd_F = (a_t == T_NAN) ? (a_m[62:11] | 52'h8_0000_0000_0000) : 52'd0;
	end
	else if (sd_ov) begin
		sd_E = sd_tomax ? 11'h7FE : 11'h7FF;
		sd_F = sd_tomax ? {52{1'b1}} : 52'd0;
	end
	else begin
		sd_E = sd_enc[10:0];
		sd_F = sd_m[62:11];
	end
	sd_out = sd_isS ? {a_s, sd_E[7:0], sd_F[51:29], 64'd0} : {a_s, sd_E, sd_F, 32'd0};
end"""

rep2 = """// One incrementer for the roundings of a_m at a precision's last kept bit:
// F_ROUND's (the operation's precision), single/double register stores
// (F_SRC, by the store format), and P255 dispatch-clock stores (F_IDLE).
wire        sd_idle = (fst == F_IDLE);
wire  [2:0] eff_fmt = sd_idle ? src_fmt : r_fmt;
wire        eff_s   = sd_idle ? fr_src_s : a_s;
wire [16:0] eff_e   = sd_idle ? {2'd0, fr_src_e} : a_e;
wire [63:0] eff_m   = sd_idle ? fr_src_m : a_m;

wire  [1:0] rd_pr   = ((fst == F_SRC) || sd_idle) ? ((eff_fmt == 3'd1) ? 2'd1 : 2'd2) : prec_of(r_op);
wire [63:0] rd_mask = (rd_pr == 2'd1) ? 64'hFFFF_FF00_0000_0000 :
                      (rd_pr == 2'd2) ? 64'hFFFF_FFFF_FFFF_F800 : 64'hFFFF_FFFF_FFFF_FFFF;
wire [64:0] rd_mi   = {1'b0, eff_m & rd_mask} +
                      ((rd_pr == 2'd1) ? 65'h100_0000_0000 : (rd_pr == 2'd2) ? 65'h800 : 65'd1);

// The single and double stores, in one form (F_SRC: a register's value
// rounded to the format, or its special value; F_PACKS: a denormal after
// the staged shift; F_IDLE: P255 dispatch-clock store): the exponent field sd_E
// and the fraction sd_F as a double's, the single's being their upper bits --
// one exponent subtract, one overflow test, one output multiplexer for both formats.
// The rounding takes the shared incrementer (rd_mi: rd_pr is the format's).
reg        sd_isS, sd_den, sd_up, sd_inx, sd_ov, sd_tomax, sd_pr;
reg signed [17:0] sd_sE;
reg [17:0] sd_eun;
reg [16:0] sd_enc;
reg [63:0] sd_m;
reg [10:0] sd_E;
reg [51:0] sd_F;
reg [95:0] sd_out;
always @* begin
	sd_isS = (eff_fmt == 3'd1);
	sd_sE  = $signed({eff_e[16], eff_e}) - 18'sd16383;
	sd_den = sd_isS ? (sd_sE < -18'sd126) : (sd_sE < -18'sd1022);
	sd_up  = sd_isS ? round_up(eff_m[40], eff_m[39], (eff_m[38:0] != 0), eff_s) :
	                  round_up(eff_m[11], eff_m[10], (eff_m[9:0] != 0), eff_s);
	sd_inx = sd_isS ? (eff_m[39:0] != 0) : (eff_m[10:0] != 0);
	// (a rounding carry out of the significand leaves sd_m zero: the
	// minimum of the next exponent)
	sd_m   = sd_up ? rd_mi[63:0] : (eff_m & rd_mask);
	sd_eun = {1'b0, eff_e} + {17'd0, sd_up && rd_mi[64]};
	sd_ov  = sd_eun > (sd_isS ? 18'd16510 : 18'd17406);
	sd_enc = sd_eun[16:0] - (sd_isS ? 17'd16256 : 17'd15360);
	sd_tomax = (rnd_mode == 2'b01) || (rnd_mode == 2'b10 && !eff_s) || (rnd_mode == 2'b11 && eff_s);
	// F_PACKS: the denormal's rounding at the format's last bit
	sd_pr  = sd_isS ? round_up(sh_v[43], sh_v[42], sh_v[41:0] != 0, a_s) :
	                  round_up(sh_v[14], sh_v[13], sh_v[12:0] != 0, a_s);
	if (fst == F_PACKS) begin
		sd_E = {10'd0, sd_pr ? shk_i[63] : shk[63]};
		sd_F = sd_pr ? shk_i[62:11] : shk[62:11];
	end
	else if (!sd_idle && a_t != T_NUM) begin
		sd_E = (a_t == T_ZERO) ? 11'd0 : 11'h7FF;
		sd_F = (a_t == T_NAN) ? (a_m[62:11] | 52'h8_0000_0000_0000) : 52'd0;
	end
	else if (sd_ov) begin
		sd_E = sd_tomax ? 11'h7FE : 11'h7FF;
		sd_F = sd_tomax ? {52{1'b1}} : 52'd0;
	end
	else begin
		sd_E = sd_enc[10:0];
		sd_F = sd_m[62:11];
	end
	sd_out = sd_isS ? {eff_s, sd_E[7:0], sd_F[51:29], 64'd0} : {eff_s, sd_E, sd_F, 32'd0};
end"""

assert p2 in s, "rd_mi / sd_out block not found in ap040_fpu.v"
s = s.replace(p2, rep2, 1)

# 3. Add dispatch-clock store branches in F_IDLE op_class == 3'b011
p3 = """					else if (fr_src_unsup) begin
						cap_cmd <= {op_class, src_fmt, dst_r, opmode};
						cap_unimp <= 0; cap_t <= 1; cap_e1 <= 0; cap_pk <= 0;   // T, not packed
						begin fst <= F_CAP; wb_r <= (F_CAP == F_WB); acc_r <= 1'b0; end
					end
					else begin
						{a_s, a_e, a_m, a_t} <=
							unpack_x(fr_src_s, fr_src_e, fr_src_m);
						begin fst <= F_SRC; wb_r <= (F_SRC == F_WB); acc_r <= 1'b0; end   // F_SRC routes stores via r_op = STORE
						r_op <= 7'h7F;  // internal: store
					end"""

rep3 = """					else if (fr_src_unsup) begin
						cap_cmd <= {op_class, src_fmt, dst_r, opmode};
						cap_unimp <= 0; cap_t <= 1; cap_e1 <= 0; cap_pk <= 0;   // T, not packed
						begin fst <= F_CAP; wb_r <= (F_CAP == F_WB); acc_r <= 1'b0; end
					end
					else if (src_fmt == 3'd2) begin
						// P222: raw extended store dispatch-clock pass-through
						dout <= {fr_src_s, fr_src_e, 16'd0, fr_src_m};
						done <= 1; fpu_used <= 1;
						r_op <= 7'h7F;
					end
					else if (src_fmt == 3'd1 && st_norm && (st_sE >= -18'sd126) &&
					         !sd_ov && !(sd_inx && fpcr[9])) begin
						// P255: normal single store dispatch-clock
						dout <= sd_out;
						if (sd_inx) begin fpsr[9] <= 1; fpsr[3] <= 1; end
						done <= 1; fpu_used <= 1;
						r_op <= 7'h7F;
					end
					else if (src_fmt == 3'd5 && st_norm && (st_sE >= -18'sd1022) &&
					         !sd_ov && !(sd_inx && fpcr[9])) begin
						// P255: normal double store dispatch-clock
						dout <= sd_out;
						if (sd_inx) begin fpsr[9] <= 1; fpsr[3] <= 1; end
						done <= 1; fpu_used <= 1;
						r_op <= 7'h7F;
					end
					else begin
						{a_s, a_e, a_m, a_t} <=
							unpack_x(fr_src_s, fr_src_e, fr_src_m);
						begin fst <= F_SRC; wb_r <= (F_SRC == F_WB); acc_r <= 1'b0; end   // F_SRC routes stores via r_op = STORE
						r_op <= 7'h7F;  // internal: store
					end"""

assert p3 in s, "F_IDLE op_class 011 block not found in ap040_fpu.v"
s = s.replace(p3, rep3, 1)

with open(fpu_path, "w") as f:
    f.write(s)

print(f"Successfully applied Stage B patch to {fpu_path}")
