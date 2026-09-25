`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module fpu_continue_monitor;
integer beats=0,continued=0;
reg [31:0] nextaddr,value;
reg [3:0] oldn;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce &&
 `C.state==`C.S_MRD && `C.m_issued && `C.d_ack && !`C.d_err &&
 `C.r_m_ret==`C.S_FPU_RD &&
 ((`C.fp_nb==8 && `C.fp_n==1) || (`C.fp_nb==12 && (`C.fp_n==1 || `C.fp_n==2)))) begin
 beats++; nextaddr=`C.t_a+{26'd0,`C.fp_n,2'b00}; value=`C.mem_rdata; oldn=`C.fp_n;
 #1;
 if(`C.state==`C.S_MRD) begin
  continued++;
  if(`C.m_addr_r!=nextaddr || `C.fp_n!=oldn+1 || `C.r_m_ret!=`C.S_FPU_RD) $fatal(1,"bad continuation address/index");
  if((oldn==1 && `C.fpb[95:64]!=value) || (oldn==2 && `C.fpb[63:32]!=value)) $fatal(1,"bad continuation operand capture");
 end
end
final begin
 $display("FPU_CONTINUE beats=%0d continued=%0d",beats,continued);
 if(beats==0) $fatal(1,"no multiword beats covered");
 if($test$plusargs("require_continue") && continued!=beats) $fatal(1,"missing continuation");
 if($test$plusargs("require_baseline") && continued!=0) $fatal(1,"unexpected baseline continuation");
end
endmodule
