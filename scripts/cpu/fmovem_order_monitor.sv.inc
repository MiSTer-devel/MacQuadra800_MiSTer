`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module mvm_order_monitor;
integer read_ack=0,store_ack=0,early_read=0,early_store=0;
reg is_read;
always @(posedge tb_ap040_program.clk) begin
 if(tb_ap040_program.nreset && `C.ce && `C.m_issued && `C.d_ack && !`C.d_err && `C.r_m_ret==`C.S_FPU_MVM3 && (`C.state==`C.S_MRD || `C.state==`C.S_MWR)) begin
  is_read=(`C.state==`C.S_MRD);
  if(is_read) read_ack++; else store_ack++;
  #1;
  if(`C.state==`C.S_FPU_MVM2) begin
   if(is_read) early_read++; else early_store++;
  end
 end
end
final begin
 $display("FMOVEM_ORDER read=%0d store=%0d early_read=%0d early_store=%0d",read_ack,store_ack,early_read,early_store);
 if($test$plusargs("require_early") && (early_read==0 || early_store==0)) $fatal(1,"missing FMOVEM early completion");
end
endmodule
