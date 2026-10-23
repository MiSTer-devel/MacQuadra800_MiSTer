`timescale 1ns/1ps
module tb_tag_ram;
 logic clk = 0;
 always #5 clk = !clk;
 logic [5:0] aa = 0, ab = 0;
 logic we = 0;
 logic [21:0] wd = 0;
 wire [21:0] qa, qb, raw, bd;
 wire bv;
 ap68040_tdp #(.AW(6), .DW(22), .WRITE_A(0)) dut (
  .clk(clk), .addr_a(aa), .we_a(1'b0), .wd_a(22'd0), .q_a(qa),
  .qa_raw(raw), .qa_bv(bv), .qa_bd(bd),
  .addr_b(ab), .we_b(we), .wd_b(wd), .q_b(qb)
 );
 logic [21:0] model [64];
 logic [31:0] rng = 32'h13a597cb;
 logic [21:0] expected_raw, expected_a, expected_b;
 logic expected_bypass;
 integer collisions = 0, writes = 0;
 initial begin
  // Initialize every address through the actual write port.
  for (int i = 0; i < 64; i++) begin
   @(negedge clk);
   aa = 6'(i); ab = 6'(i); we = 1; wd = 22'(i) ^ 22'h2a5a5a;
   model[i] = wd;
   @(posedge clk); #0.001;
  end
  for (int i = 0; i < 8192; i++) begin
   @(negedge clk);
   rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5);
   aa = rng[5:0]; ab = (i % 4 == 0) ? aa : rng[11:6];
   we = rng[12]; wd = rng[31:10];
   expected_raw = model[aa];
   expected_bypass = we && aa == ab;
   expected_a = expected_bypass ? wd : model[aa];
   expected_b = we ? wd : model[ab];
   if (we) begin model[ab] = wd; writes++; end
   if (expected_bypass) collisions++;
   @(posedge clk); #0.001;
   if (raw !== expected_raw || qa !== expected_a || qb !== expected_b ||
       bv !== expected_bypass || bd !== (expected_bypass ? wd : 22'd0))
    $fatal(1, "FAIL: tag RAM latency/bypass at step %0d: raw=%h qa=%h qb=%h", i, raw, qa, qb);
  end
  $display("PASS: tag RAM 8192 cycles, %0d writes, %0d same-address collisions", writes, collisions);
  $finish;
 end
endmodule
