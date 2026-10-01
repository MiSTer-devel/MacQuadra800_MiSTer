// rtl/via6522.sv: an interrupt event that lands on the same E clock as a CPU
// access which clears IFR bits must not be lost.
//
// On the Quadra the timers tick on the E falling edge and every CPU access
// is taken on it too (iosb.sv), and the ROM acknowledges the 60 Hz VBL with
// "move.b #$02,vIFR".  The IFR write used to be a full-vector assignment
// that discarded every event of its clock, and the port / SR / counter-low
// accesses overrode their own bit: a Timer 2 timeout on such a clock was
// erased, T2 is one-shot, and the Mac OS Time Manager re-arms it only from
// its interrupt -- Day of the Tentacle, DOOM II and Dracula Unleashed hung
// waiting for a Time Manager task (2026-10-01).  The same race dropped CA1,
// CA2 and the shift register's completion (ADB).
//
// Each row arms one event source, puts one access on the event's own E clock
// ("@evt") or one E clock later ("+1E", the control: the clear must still
// work), and checks the flag.  The two timer-restart writes (T1C-H, T2C-H)
// are the deliberate exception: the clear wins, and the new countdown raises
// the flag later.
//   make tb_via_irq_race
`timescale 1ns/1ps
module tb_via_irq_race;
reg clk = 0; always #5 clk = ~clk;
reg [3:0] div = 0; always @(posedge clk) div <= div + 4'd1;
wire e_fall = (div == 4'd15);
wire e_rise = (div == 4'd7);
reg reset = 1;
reg [3:0] addr = 0; reg wen = 0, ren = 0; reg [7:0] din = 0;
reg ca1 = 1, srx = 0;
wire [7:0] dout; wire [31:0] dbg;
via6522 v (.clock(clk), .rising(e_rise), .falling(e_fall), .timer_tick(e_fall), .reset(reset),
  .addr(addr), .wen(wen), .ren(ren), .data_in(din), .data_out(dout), .phi2_ref(),
  .port_a_o(), .port_a_t(), .port_a_i(8'h00), .port_b_o(), .port_b_t(), .port_b_i(8'h00),
  .ca1_i(ca1), .ca2_o(), .ca2_i(1'b0), .ca2_t(), .cb1_o(), .cb1_i(1'b0), .cb1_t(),
  .cb2_o(), .cb2_i(1'b0), .cb2_t(), .ca2_lvl_i(1'b0), .cb2_lvl_i(1'b0), .irq(),
  .dbg_irq_state(dbg), .sr_active(), .sr_ext_complete(srx), .sr_ext_load(1'b0), .sr_ext_data(8'h00));

localparam EV_T2 = 0, EV_T1 = 1, EV_T1FREE = 2, EV_CA1 = 3, EV_SR = 4;
localparam NONE = 0, WR = 1, RD = 2;
localparam X = 2;                       // late check: don't care

// Stimulus changes on the falling clock edge, in the middle of the cycle
// whose closing rising edge samples it, so nothing here races the model.
// to_div(n) returns in the middle of the cycle with div == n; E falls (and
// the timers tick) on the edge that closes the div == 15 cycle.
task to_div(input [3:0] n);
begin
  @(negedge clk); while (div != n) @(negedge clk);
end endtask

// one access, on the next E falling
task acc(input [3:0] a, input integer kind, input [7:0] d);
begin
  to_div(4'd15);
  addr = a; wen = (kind == WR); ren = (kind == RD); din = d;
  @(negedge clk);
  wen = 0; ren = 0;
end endtask

integer fails = 0, rows = 0;

// arm the source, put the access on the event's E clock (ofs 0) or `ofs` E
// clocks later, check the flag; `late` checks it again 12 E clocks on
task row(input [8*28-1:0] name, input integer ev, input integer flag,
         input [3:0] a, input integer kind, input [7:0] d, input integer ofs,
         input integer want, input integer late);
integer k; reg seen; reg got;
begin
  reset = 1; ca1 = 1; srx = 0; wen = 0; ren = 0;
  repeat (40) @(negedge clk);
  reset = 0;
  repeat (40) @(negedge clk);
  case (ev)
  EV_T2: begin
    acc(4'h8, WR, 8'h05);               // T2 latch low
    acc(4'h9, WR, 8'h00);               // T2C-H: start, count 5
  end
  EV_T1, EV_T1FREE: begin
    acc(4'hB, WR, (ev == EV_T1FREE) ? 8'h40 : 8'h00);
    acc(4'h4, WR, 8'h05);               // T1 latch low
    acc(4'h5, WR, 8'h00);               // T1C-H: start, count 5
  end
  default: ;
  endcase
  // stop in the middle of the div == 15 cycle that carries the event
  seen = 0;
  case (ev)
  EV_T2:
    for (k = 0; k < 40 && !seen; k = k + 1) begin
      to_div(4'd15);
      if (v.timer_b_timeout) seen = 1;
    end
  EV_T1, EV_T1FREE:
    for (k = 0; k < 40 && !seen; k = k + 1) begin
      to_div(4'd15);
      if (v.timer_a_reload && v.timer_a_may_interrupt) seen = 1;
    end
  EV_CA1: begin
    to_div(4'd14);
    ca1 = 0;                            // ca1_c takes it on the next edge:
    @(negedge clk);                     // the event is up in the div == 15 cycle
    seen = 1;
  end
  EV_SR: begin
    to_div(4'd15);
    srx = 1;
    seen = 1;
  end
  endcase
  if (!seen) begin
    $display("TB FAIL %0s: the event never came", name);
    fails = fails + 1;
  end
  if (ofs == 0 && kind != NONE) begin
    addr = a; wen = (kind == WR); ren = (kind == RD); din = d;
  end
  @(negedge clk);                       // past the E falling with the event
  wen = 0; ren = 0; srx = 0;
  if (ofs > 0 && kind != NONE) begin
    repeat (ofs - 1) to_div(4'd15);
    acc(a, kind, d);
  end
  repeat (6) @(negedge clk);
  got = v.irq_flags[flag];
  rows = rows + 1;
  if (got !== want[0]) begin
    fails = fails + 1;
    $display("TB FAIL %0s: IFR[%0d] = %b, expected %b%0s", name, flag, got, want[0],
             want[0] ? "  (the interrupt was LOST)" : "");
  end
  else $display("TB ok   %0s: IFR[%0d] = %b", name, flag, got);
  if (late != X) begin
    repeat (16*12) @(negedge clk);
    got = v.irq_flags[flag];
    if (got !== late[0]) begin
      fails = fails + 1;
      $display("TB FAIL %0s: IFR[%0d] = %b 12 E later, expected %b", name, flag, got, late[0]);
    end
  end
end endtask

initial begin
  //   name                           source     flag addr  kind  data  ofs want late
  row("T2  no access               ", EV_T2,     5, 4'h0, NONE, 8'h00, 0, 1, X);
  row("T2  IFR wr $02 @evt         ", EV_T2,     5, 4'hD, WR,   8'h02, 0, 1, X);
  row("T2  IFR wr $02 +1E          ", EV_T2,     5, 4'hD, WR,   8'h02, 1, 1, X);
  row("T2  IFR wr $20 @evt         ", EV_T2,     5, 4'hD, WR,   8'h20, 0, 1, X);
  row("T2  IFR wr $20 +1E          ", EV_T2,     5, 4'hD, WR,   8'h20, 1, 0, 0);
  row("T2  T2C-L rd @evt           ", EV_T2,     5, 4'h8, RD,   8'h00, 0, 1, X);
  row("T2  T2C-L rd +1E            ", EV_T2,     5, 4'h8, RD,   8'h00, 1, 0, 0);
  row("T2  IER wr $82 @evt         ", EV_T2,     5, 4'hE, WR,   8'h82, 0, 1, X);
  row("T2  ORB rd @evt             ", EV_T2,     5, 4'h0, RD,   8'h00, 0, 1, X);
  row("T2  T2C-H wr @evt (restart) ", EV_T2,     5, 4'h9, WR,   8'h00, 0, 0, 1);
  row("T1  no access               ", EV_T1,     6, 4'h0, NONE, 8'h00, 0, 1, X);
  row("T1  IFR wr $02 @evt         ", EV_T1,     6, 4'hD, WR,   8'h02, 0, 1, X);
  row("T1  T1C-L rd @evt           ", EV_T1,     6, 4'h4, RD,   8'h00, 0, 1, X);
  row("T1  T1C-L rd +1E            ", EV_T1,     6, 4'h4, RD,   8'h00, 1, 0, 0);
  row("T1  T1L-H wr @evt           ", EV_T1,     6, 4'h7, WR,   8'h00, 0, 1, X);
  row("T1  T1L-H wr +1E            ", EV_T1,     6, 4'h7, WR,   8'h00, 1, 0, 0);
  row("T1  T1C-H wr @evt (restart) ", EV_T1,     6, 4'h5, WR,   8'h00, 0, 0, 1);
  row("T1f IFR wr $40 @evt         ", EV_T1FREE, 6, 4'hD, WR,   8'h40, 0, 1, X);
  row("T1f IFR wr $40 +1E          ", EV_T1FREE, 6, 4'hD, WR,   8'h40, 1, 0, 1);
  row("CA1 no access               ", EV_CA1,    1, 4'h0, NONE, 8'h00, 0, 1, X);
  row("CA1 IFR wr $20 @evt         ", EV_CA1,    1, 4'hD, WR,   8'h20, 0, 1, X);
  row("CA1 IFR wr $02 @evt         ", EV_CA1,    1, 4'hD, WR,   8'h02, 0, 1, X);
  row("CA1 IFR wr $02 +1E          ", EV_CA1,    1, 4'hD, WR,   8'h02, 1, 0, 0);
  row("CA1 ORA rd @evt             ", EV_CA1,    1, 4'h1, RD,   8'h00, 0, 1, X);
  row("CA1 ORA rd +1E              ", EV_CA1,    1, 4'h1, RD,   8'h00, 1, 0, 0);
  row("SR  no access               ", EV_SR,     2, 4'h0, NONE, 8'h00, 0, 1, X);
  row("SR  IFR wr $02 @evt         ", EV_SR,     2, 4'hD, WR,   8'h02, 0, 1, X);
  row("SR  SR rd @evt              ", EV_SR,     2, 4'hA, RD,   8'h00, 0, 1, X);
  row("SR  IFR wr $04 +1E          ", EV_SR,     2, 4'hD, WR,   8'h04, 1, 0, 0);
  if (fails == 0) $display("TB PASS tb_via_irq_race: %0d rows", rows);
  else            $display("TB FAIL tb_via_irq_race: %0d failure(s) in %0d rows", fails, rows);
  $finish;
end
endmodule
