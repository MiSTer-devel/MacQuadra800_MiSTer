// Directed check: a VIA1 Timer 2 timeout that lands on the same E clock as a
// CPU access that clears OTHER IFR bits must still raise IFR[5].
//   case A: IFR write of $02 (VBL handler clearing CA1) on the event clock
//   case B: control -- the same IFR write one E clock later
//   case C: read of T2C-L on the event clock (architecturally clears IFR[5],
//           but the 6522 sets the flag at the timeout -- the event should win)
`timescale 1ns/1ps
module tb;
reg clk = 0; always #5 clk = ~clk;
reg [3:0] div = 0; always @(posedge clk) div <= div + 1;
wire e_fall = (div == 4'd15);
wire e_rise = (div == 4'd7);
reg reset = 1;
reg [3:0] addr = 0; reg wen = 0, ren = 0; reg [7:0] din = 0;
wire [7:0] dout; wire [31:0] dbg;
via6522 v (.clock(clk), .rising(e_rise), .falling(e_fall), .timer_tick(e_fall), .reset(reset),
  .addr(addr), .wen(wen), .ren(ren), .data_in(din), .data_out(dout), .phi2_ref(),
  .port_a_o(), .port_a_t(), .port_a_i(8'h00), .port_b_o(), .port_b_t(), .port_b_i(8'h00),
  .ca1_i(1'b0), .ca2_o(), .ca2_i(1'b0), .ca2_t(), .cb1_o(), .cb1_i(1'b0), .cb1_t(),
  .cb2_o(), .cb2_i(1'b0), .cb2_t(), .ca2_lvl_i(1'b0), .cb2_lvl_i(1'b0), .irq(),
  .dbg_irq_state(dbg), .sr_active(), .sr_ext_complete(1'b0), .sr_ext_load(1'b0), .sr_ext_data(8'h00));

task acc(input [3:0] a, input w, input [7:0] d);   // one access, held across one E falling
begin
  @(posedge clk); while (!(div == 4'd14)) @(posedge clk);
  addr <= a; wen <= w; ren <= !w; din <= d;
  @(posedge clk); @(posedge clk);
  wen <= 0; ren <= 0;
end endtask

integer fails = 0;
// run one case: arm T2 with count N; access at E-falling number `at` after the arm
task run(input [8*16-1:0] name, input [3:0] a, input w, input [7:0] d, input integer at_ofs);
integer k; reg seen;
begin
  reset = 1; repeat (40) @(posedge clk); reset = 0; repeat (40) @(posedge clk);
  acc(4'hE, 1, 8'hA0);              // IER: enable T2
  acc(4'h8, 1, 8'h05);              // T2 latch lo = 5
  acc(4'h9, 1, 8'h00);              // T2C-H: start, count 5
  // the timeout event is presented on the E falling where timer_b_event is high:
  // find it, then place the access on that same E falling (at_ofs = 0) or later
  seen = 0;
  for (k = 0; k < 400 && !seen; k = k + 1) begin
    @(posedge clk);
    if (v.timer_b_timeout && div == 4'd14) seen = 1;   // next E falling carries the event
  end
  if (at_ofs > 0) repeat (16*at_ofs) @(posedge clk);
  addr <= a; wen <= w; ren <= !w; din <= d;   // asserted for the coming E falling
  @(posedge clk); @(posedge clk);
  wen <= 0; ren <= 0;
  repeat (40) @(posedge clk);
  $display("%0s: IFR[5] (T2) = %b  %0s", name, v.irq_flags[5],
           v.irq_flags[5] ? "ok" : "LOST");
  if (!v.irq_flags[5] && !(a == 4'h8 && !w && at_ofs > 0)) fails = fails + 1;
end endtask

initial begin
  reset = 1; repeat (40) @(posedge clk); reset = 0; repeat (40) @(posedge clk);
  acc(4'hE, 1, 8'hA0); acc(4'h8, 1, 8'h05); acc(4'h9, 1, 8'h00);
  repeat (16*12) begin @(posedge clk); if (e_fall) $display("  E: t2cnt=%h trig=%b tmo=%b evt=%b ifr=%b", v.timer_b_count, v.timer_b_oneshot_trig, v.timer_b_timeout, v.timer_b_event, v.irq_flags); end
  $display("baseline (no access): IFR[5] = %b", v.irq_flags[5]);
  run("A IFR wr $02 @evt", 4'hD, 1, 8'h02, 0);
  run("B IFR wr $02 +1E ", 4'hD, 1, 8'h02, 1);
  run("C T2C-L rd @evt  ", 4'h8, 0, 8'h00, 0);
  run("D IER wr @evt    ", 4'hE, 1, 8'h82, 0);
  $display("%0d case(s) lost the T2 interrupt", fails);
  $finish;
end
endmodule
