`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module mvm_split_monitor;
integer reads=0, stores=0;
always @(posedge tb_ap040_program.clk) begin
 if(tb_ap040_program.nreset && `C.ce && `C.r_m_ret==`C.S_FPU_MVM3) begin
  if(`C.state==`C.S_MRD_B) reads=reads+1;
  if(`C.state==`C.S_MWR_B) stores=stores+1;
 end
end
final begin
 $display("ROOT_FMOVEM_SPLIT read=%0d store=%0d",reads,stores);
 if($test$plusargs("read_split") && reads==0) $fatal(1,"missing split read");
 if($test$plusargs("store_split") && stores==0) $fatal(1,"missing split store");
end
endmodule
