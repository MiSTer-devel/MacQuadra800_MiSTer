module probe import ap68040_pkg::*; (
 input logic clk, input uop_t u, input s1_t c, input logic [15:0] w,
 output logic [2:0] ok, output s1_t pd
);
function automatic logic s0_ok(input uop_t u);
	s0_ok = u.first && u.last && (u.exc == 8'd0) && !u.ser &&
	        !u.upd2_v && (u.dyn == 3'd0) && !u.exr &&
	        (u.op != OP_FPU) && (u.op != OP_RTE) && (u.op != OP_RTEF) &&
	        (u.op != OP_MISC) && (u.op != OP_SRLOG) && (u.op != OP_SPW) &&
	        (u.op != OP_CHKSR) && (u.op != OP_IACKV);
endfunction
function automatic logic s1_indep(input uop_t u, input s1_t c);
	logic [4:0] r [3];
	logic       rv [3];
	s1_indep = 1'b1;
	r[0] = c.a_reg; rv[0] = c.a_v && !c.a_imm;
	r[1] = c.b_reg; rv[1] = c.b_v;
	r[2] = c.d_reg; rv[2] = c.d_v || c.agop;
	for (int i = 0; i < 3; i++)
		if (rv[i] && ((u.d_v && u.d_reg == r[i]) || (u.upd_v && u.upd_reg == r[i])))
			s1_indep = 1'b0;
endfunction
always_ff @(posedge clk) begin
 ok <= {u.first && u.last, s0_ok(u), s1_indep(u,c)};
 pd <= s1_dec(w);
end
endmodule
