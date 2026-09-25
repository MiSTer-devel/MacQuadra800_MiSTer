// P120 candidate-only boundary test; requires dut.direct_admit.
`timescale 1ns/1ps
module tb_pipeline_integer;
    reg clk = 0;
    always #5 clk = !clk;
    reg kill_younger = 0;
    wire idle;
    reg nreset = 0, ce = 1, flush = 0, in_valid = 0, retire_ready = 1;
    reg [31:0] in_pc = 0;
    reg [15:0] in_opcode = 0;
    wire in_ready, retire_valid, retire_we, fallback_valid;
    wire [31:0] retire_pc, retire_data, fallback_pc;
    wire [15:0] retire_opcode, fallback_opcode;
    wire [3:0] retire_dst;
    wire [4:0] retire_ccr;
    wire in_supported;
    ap040_pipeline_integer dut (.external_dst(32'd0), .read_old_dst(), .external_a(32'd0), .external_b(32'd0),
        .external_ccr(5'd0), .next_opcode(16'd0), .next_extension(16'd0), .next_valid(1'b0), .next_extension_valid(1'b0), .next_supported(), .external_sp(32'd0), .in_extension(16'd0), .in_extension_valid(1'b0), .in_words(), .retire_next_pc(), .read_src(), .read_dst(), .load_req(), .load_write(), .load_wdata(), .load_ccr(), .load_addr(), .load_size(), .load_pc(), .load_opcode(),
        .load_ack(1'b0), .load_fault(1'b0), .load_data(32'd0),
        .retire_fault(), .retire_fault_addr(), .empty_after_retire(), .retire_wb_valid(), .retire_branch_taken(), .*);

 integer retired=0, admissions=0;
 always @(posedge clk) begin
  if(nreset && dut.direct_admit) admissions=admissions+1;
  if(retire_valid && retire_ready) begin
   if(retire_pc!==32'h400 || retire_opcode!==16'h702a || !retire_we || retire_dst!==0 || retire_data!==42 || retire_ccr!==0)
    $fatal(1,"bad architectural retirement pc=%h op=%h data=%h ccr=%h",retire_pc,retire_opcode,retire_data,retire_ccr);
   retired=retired+1;
  end
 end
 task tick; begin @(posedge clk); #1; @(negedge clk); end endtask
 task reset_case; begin
  nreset=0; in_valid=0;ce=1;flush=0;kill_younger=0;retire_ready=1;
  tick;tick;nreset=1;in_pc=32'h400;in_opcode=16'h702a;
 end endtask
 task empty_check; begin
  if(retire_valid || dut.ex_v || dut.id_v || dut.wb_v) $fatal(1,"blocked input altered pipeline state");
 end endtask
 initial begin
  @(negedge clk);
  reset_case;
  in_valid=1;ce=0;repeat(3) begin tick;empty_check;end
  ce=1;flush=1;repeat(3) begin tick;empty_check;end
  flush=0;kill_younger=1;repeat(3) begin tick;empty_check;end
  kill_younger=0;retire_ready=0;
  #1;if(!in_ready) $fatal(1,"empty pipeline must accept under retirement backpressure");
  tick;in_valid=0;
  if(!dut.ex_v || dut.id_v) $fatal(1,"supported empty input did not bypass ID");
  repeat(5)tick;
  if(retired!=0 || !retire_valid) $fatal(1,"backpressure retirement violation");
  repeat(3)begin tick;if(retire_data!==42 || retire_pc!==32'h400) $fatal(1,"blocked retirement changed");end
  retire_ready=1;tick;repeat(4)tick;
  if(retired!=1 || admissions!=1) $fatal(1,"supported input must retire exactly once");
  reset_case;in_opcode=16'h4afc;in_valid=1;tick;in_valid=0;
  if(!fallback_valid || fallback_pc!==32'h400 || fallback_opcode!==16'h4afc || dut.ex_v || admissions!=1)
   $fatal(1,"unsupported empty input must use fallback without EX admission");
  flush=1;tick;flush=0;repeat(4)tick;
  if(retired!=1) $fatal(1,"unsupported input retired");
  $display("PASS P120 boundary: CE/flush/kill block valid empty input; unsupported fallback; backpressure stable; exactly one MOVEQ retirement; direct admissions=%0d",admissions);
  $finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
