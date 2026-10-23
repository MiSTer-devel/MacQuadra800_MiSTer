module probe(input logic clk, input logic [5:0] aa, ab,
 input logic we, input logic [21:0] wd, output logic [21:0] qa, qb, raw,
 output logic bv, output logic [21:0] bd);
 ap68040_tdp #(.AW(6), .DW(22)) tag(
 .clk(clk), .addr_a(aa), .we_a(1'b0), .wd_a(22'd0), .q_a(qa),
 .qa_raw(raw), .qa_bv(bv), .qa_bd(bd),
 .addr_b(ab), .we_b(we), .wd_b(wd), .q_b(qb));
endmodule
