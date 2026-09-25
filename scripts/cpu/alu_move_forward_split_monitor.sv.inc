`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module split_forward_monitor;
integer prepared=0,split=0,immediate=0;
reg producer;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce) begin
 if(`C.state==`C.S_MRD_B && `C.r_m_ret==`C.S_PIPE_SDONE && `C.m_addr_r==32'h1ffe) split++;
 producer=(`C.state==`C.S_PIPE_REGS && `C.regs_alu_fire && !`C.p_wbsup && `C.p_dreg[3]);
 #1;
 if(producer && `C.state==`C.S_MRD && `C.r_m_ret==`C.S_PIPE_SDONE && `C.m_addr_r==32'h1ffe) begin
  prepared++; if(`C.m_issued && `C.mem_req && !`C.mem_write) immediate++;
 end
end
final begin
 $display("SPLIT_FORWARD prepared=%0d immediate=%0d split=%0d",prepared,immediate,split);
 if(split==0) $fatal(1,"missing split source read");
 if($test$plusargs("require_early") && prepared==0) $fatal(1,"missing forwarded preparation");
 if($test$plusargs("require_baseline") && prepared!=0) $fatal(1,"baseline unexpectedly forwarded");
end
endmodule
