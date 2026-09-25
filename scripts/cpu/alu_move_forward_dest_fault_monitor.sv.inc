`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module dest_fault_monitor;
integer prepared=0,errors=0,correlated=0;
reg producer,pending=0;
reg [31:0] prepared_pc;
always @(posedge tb_ap040_program.clk) begin
 if(!tb_ap040_program.nreset) pending=0;
 else if(`C.ce) begin
  if(pending && `C.pc_i!=prepared_pc) pending=0;
  if(`C.state==`C.S_MWR && `C.m_issued && `C.d_err && `C.m_addr_r==32'h2000) begin
   errors++;
   if(pending && `C.pc_i==prepared_pc) correlated++;
  end
  producer=(`C.state==`C.S_PIPE_REGS && `C.regs_alu_fire && !`C.p_wbsup && `C.p_dreg[3]);
  #1;
  if(producer && `C.state==`C.S_MRD && `C.r_m_ret==`C.S_PIPE_SDONE && `C.m_addr_r==32'hc000) begin
   prepared++; pending=1; prepared_pc=`C.pc_i;
  end
 end
end
final begin
 $display("DEST_FAULT prepared=%0d errors=%0d correlated=%0d",prepared,errors,correlated);
 if(errors!=3) $fatal(1,"expected three destination errors");
 if($test$plusargs("require_fault") && correlated!=3) $fatal(1,"faulting MOVE was not forwarded");
 if($test$plusargs("require_baseline") && (prepared!=0 || correlated!=0)) $fatal(1,"baseline unexpectedly forwarded");
end
endmodule
