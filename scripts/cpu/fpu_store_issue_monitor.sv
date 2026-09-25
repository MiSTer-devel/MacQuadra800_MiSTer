`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module root_issue_monitor;
integer fpu_early=0, movem_early=0, which;
always @(posedge tb_ap040_program.clk) begin
 which=0;
 if (tb_ap040_program.nreset && `C.ce) begin
  if (`C.state==`C.S_FPU_WR) which=1;
  if (`C.state==`C.S_FPU_MVM2 && `C.fp_st) which=2;
 end
 #1;
 if (which!=0 && `C.state==`C.S_MWR && `C.m_issued && `C.mem_req && `C.mem_write) begin
  if (which==1) fpu_early=fpu_early+1;
  else movem_early=movem_early+1;
 end
end
final $display("ROOT_FPU_ISSUE fpu=%0d movem=%0d", fpu_early,movem_early);
endmodule
