import os, sys

def patch_file(path, old, new):
    with open(path, 'r') as f:
        content = f.read()
    if old not in content:
        print(f"ERROR: Target string not found in {path}")
        print("OLD target was:")
        print(repr(old))
        sys.exit(1)
    content = content.replace(old, new, 1)
    with open(path, 'w') as f:
        f.write(content)
    print(f"Patched {path}")

E = os.path.expanduser("~/mister/q800_fpchg_20261024/stageE")
RTL = os.path.join(E, "rtl/ap68040_faster/rtl")

# 1. rtl/ap68040_fpif.sv
fpif_path = os.path.join(RTL, "ap68040_fpif.sv")

old_port = """\tinput  logic        kill,
\tinput  logic  [2:0] dynk,"""

new_port = """\tinput  logic        kill,
\tinput  logic  [2:0] dynk,
\tinput  logic        dc2_disp,"""
patch_file(fpif_path, old_port, new_port)

old_nclass = """\t\tFC_CHK: if (fuse && !go && !(bg && !f_end) && !chk_pend && !chk_x) begin
\t\t\tn_srcr  = ext[12:10];
\t\t\tn_dstr  = ext[9:7];
\t\t\tn_class = ocl;
\t\t\tn_opm   = opm;
\t\t\tn_fmt   = fmt;
\t\tend
\t\tFC_DISP: if (!go) begin"""

new_nclass = """\t\tFC_CHK: if (fuse && !go && !(bg && !f_end) && !chk_pend && !chk_x) begin
\t\t\tn_srcr  = ext[12:10];
\t\t\tn_dstr  = ext[9:7];
\t\t\tn_class = ocl;
\t\t\tn_opm   = opm;
\t\t\tn_fmt   = fmt;
\t\tend
\t\telse if (ocl == 3'b011 && !chk_pend && !chk_x && dc2_disp) begin
\t\t\tn_srcr  = ext[9:7];
\t\t\tn_dstr  = ext[9:7];
\t\t\tn_class = 3'b011;
\t\t\tn_opm   = opm;
\t\t\tn_fmt   = fmt;
\t\tend
\t\tFC_DISP: if (!go) begin"""
patch_file(fpif_path, old_nclass, new_nclass)

old_chk_adv = """\t\t\t\tsx_v  <= 1'b0;
\t\t\t\tsx_kill <= 1'b0;
\t\t\t\tgo    <= 1'b0;
\t\t\t\tdone_q <= 1'b0;"""

new_chk_adv = """\t\t\t\tsx_v  <= 1'b0;
\t\t\t\tsx_kill <= 1'b0;
\t\t\t\tdone_q <= 1'b0;
\t\t\t\tif (ocl == 3'b011 && !chk_pend && !chk_x && dc2_disp) begin
\t\t\t\t\tgo     <= 1'b1;
\t\t\t\t\tf_req  <= 1'b1;
\t\t\t\t\tf_iawe <= 1'b1;
\t\t\t\t\tf_iapc <= pc;
\t\t\t\tend
\t\t\t\telse begin
\t\t\t\t\tgo     <= 1'b0;
\t\t\t\tend"""
patch_file(fpif_path, old_chk_adv, new_chk_adv)

old_kill = """\t\tif (kill) begin
\t\t\tgo <= 1'b0; mvr_wait <= 1'b0; crr_wait <= 1'b0;
\t\tend"""

new_kill = """\t\tif (kill) begin
\t\t\tgo <= 1'b0; done_q <= 1'b0; mvr_wait <= 1'b0; crr_wait <= 1'b0;
\t\tend"""
patch_file(fpif_path, old_kill, new_kill)

# 2. rtl/ap68040_backend.sv
be_path = os.path.join(RTL, "ap68040_backend.sv")

old_be_fpif = """ap68040_fpif #(.FPU_REVISION(FPU_REVISION), .FPU_PIPE(FPU_PIPE)) fpif (
\t.clk(clk), .nreset(nreset),
\t.ex_v(ex_v && ex_is_fp && !ex_fault && ex_u.exc == 8'd0), .sub(ex_u.cond),
\t.fuse(ex_u.sz == SZ_W), .eal(ex_u.sz == SZ_B),
\t.imm(ex_u.imm[7:0]), .immb(ex_u.imm_b[7:0]),
\t.av(ex_av), .bv(ex_bv), .aw(ex_a[15:0]), .bw(ex_b[15:0]),
\t.dw_a(dc2_a[15:0]), .dw_b(dc2_b[15:0]), .dw_ld(!stall_ex), .latch(ex_latch), .ea(ex_ea), .pc(ex_u.pc),
\t.safe(!wb_v || wb_fpchk), .adv(adv_ex), .kill(kill_now), .dynk(ex_u.dynk[2:0]),"""

new_be_fpif = """wire dc2_disp = adv_dc2 && (dc2_u.op == OP_FPU) && (dc2_u.cond == 4'd1) &&
                (dc2_u.pc == ex_u.pc) && (dc2_u.exc == 8'd0);

ap68040_fpif #(.FPU_REVISION(FPU_REVISION), .FPU_PIPE(FPU_PIPE)) fpif (
\t.clk(clk), .nreset(nreset),
\t.ex_v(ex_v && ex_is_fp && !ex_fault && ex_u.exc == 8'd0), .sub(ex_u.cond),
\t.fuse(ex_u.sz == SZ_W), .eal(ex_u.sz == SZ_B),
\t.imm(ex_u.imm[7:0]), .immb(ex_u.imm_b[7:0]),
\t.av(ex_av), .bv(ex_bv), .aw(ex_a[15:0]), .bw(ex_b[15:0]),
\t.dw_a(dc2_a[15:0]), .dw_b(dc2_b[15:0]), .dw_ld(!stall_ex), .latch(ex_latch), .ea(ex_ea), .pc(ex_u.pc),
\t.safe(!wb_v || wb_fpchk), .adv(adv_ex), .kill(kill_now), .dynk(ex_u.dynk[2:0]), .dc2_disp(dc2_disp),"""
patch_file(be_path, old_be_fpif, new_be_fpif)

print("STAGE E (CHANGE 3) PATCHES APPLIED SUCCESSFULLY!")
