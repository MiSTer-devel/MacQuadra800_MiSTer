`timescale 1ns/1ps
`include "ap040_defs.svh"
`define C tb_ap040_program.dut.core
module root_handoff_exact_monitor;
integer early=0, dm, required=0;
integer write_acks=0, checked=0;
reg pending=0; reg [31:0] owner_pc;
reg eligible;
initial if ($value$plusargs("require_early=%d",required)) begin end
always @(posedge tb_ap040_program.clk) begin
 if(!tb_ap040_program.nreset) pending=0;
 if(tb_ap040_program.nreset && `C.ce && pending) begin
  if(`C.pc_i != owner_pc) begin
   if(write_acks!=1) $fatal(1,"handoff destination write acknowledgements=%0d expected1 pc=%h",write_acks,owner_pc);
   checked=checked+1; pending=0;
  end else if(`C.mem_req && `C.mem_write && `C.d_ack && !`C.d_err) begin
   write_acks=write_acks+1;
   if(write_acks>1) $fatal(1,"duplicate handoff destination write acknowledgement");
  end
 end
 eligible=tb_ap040_program.nreset && `C.ce &&
 `C.state==`C.S_MRD && `C.m_issued && `C.d_ack && !`C.d_err &&
 `C.r_m_ret==`C.S_PIPE_SDONE && `C.p_src==`C.SK_MEM && `C.p_dst==`C.DK_MEM &&
 `C.exec_kind==`C.EK_ALU && `C.alu_op==`AP040_ALU_MOVE && !`C.p_rmw;
 dm=`C.dst_mode_r;
 #1;
 if(eligible && `C.state==`C.S_MWR && `C.m_issued && `C.mem_req && `C.mem_write) begin
  early=early+1;
  if(pending) $fatal(1,"previous handoff not retired");
  pending=1; owner_pc=`C.pc_i; write_acks=0;
  if(dm<2 || dm>4) $fatal(1,"unexpected handoff mode");
 end
end
always @(negedge tb_ap040_program.clk)
 if(tb_ap040_program.nreset && `C.mem_req && `C.mem_write && `C.mem_addr_q==32'hf102 && `C.mem_wdata[15:0]==16'h600d) begin
  if(required && early==0) $fatal(1,"actual read-to-write handoff not exercised");
 end
final $display("ROOT_MOVE_HANDOFF early=%0d checked=%0d",early,checked);
endmodule
