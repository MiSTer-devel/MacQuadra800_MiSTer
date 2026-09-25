`timescale 1ns/1ps
`include "ap040_defs.svh"
`define C tb_ap040_program.dut.core
module store_cov_monitor;
reg prep,fall; reg [1:0] sz; reg [2:0] mode,rn; reg isalias;
reg [11:0] classes=0; reg [1:0] a7=0;
integer early=0,fallback=0,alias_count=0;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce) begin
 prep=(`C.state==`C.S_PIPE_START && `C.exec_kind==`C.EK_ALU && `C.alu_op==`AP040_ALU_MOVE && `C.p_src==`C.SK_REG && `C.p_dst==`C.DK_MEM && !`C.p_rmw && !`C.p_wbsup && !`C.p_dst_mem_bit && `C.rr_b==`C.p_sreg && `C.epf_ready_pc2);
 fall=(`C.state==`C.S_PIPE_START && `C.exec_kind==`C.EK_ALU && `C.alu_op==`AP040_ALU_MOVE && `C.p_src==`C.SK_REG && `C.p_dst==`C.DK_MEM && !`C.p_rmw && !`C.p_wbsup && !`C.p_dst_mem_bit && `C.rr_b==`C.p_sreg && !`C.epf_ready_pc2);
 sz=`C.p_dsize; mode=`C.dst_mode_r; rn=`C.dst_rn_r; isalias=(`C.p_sreg=={1'b1,rn});
 #1;
 if(fall && `C.state==`C.S_EXEC) fallback++;
 if(prep && `C.state==`C.S_MWR && `C.m_issued && `C.mem_req && `C.mem_write && !`C.mem_instr_q) begin
  early++; if(sz<=2&&mode>=2&&mode<=5) classes[sz*4+mode-2]=1;
  if(sz==0&&rn==7&&mode==3) a7[0]=1;
  if(sz==0&&rn==7&&mode==4) a7[1]=1;
  if(isalias) alias_count++;
 end
end
always @(negedge tb_ap040_program.clk) if(tb_ap040_program.nreset&&`C.mem_req&&`C.mem_write&&!`C.mem_instr_q&&`C.mem_addr_q==32'hf102&&`C.mem_wdata[15:0]==16'h600d) begin
 $display("ROOT_STORE_COV classes=%h a7=%b alias=%0d fallback=%0d early=%0d",classes,a7,alias_count,fallback,early);
 if($test$plusargs("require_early") && (classes!==12'hfff || a7!==2'b11 || alias_count==0 || fallback==0 || early==0)) $fatal(1,"missing store coverage");
 if($test$plusargs("require_baseline") && early!=0) $fatal(1,"baseline unexpectedly early");
end
endmodule
