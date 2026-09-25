`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module forward_monitor;
integer early=0;
reg context_ready;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce) begin
 context_ready=(`C.state==`C.S_PIPE_REGS && `C.regs_alu_fire && !`C.p_wbsup && `C.p_dreg[3]);
 #1;
 if(context_ready && `C.state==`C.S_MRD && `C.r_m_ret==`C.S_PIPE_SDONE && `C.m_issued && `C.mem_req && !`C.mem_write) early++;
end
final begin
 $display("FORWARD_READ early=%0d",early);
 if($test$plusargs("require_early") && early==0) $fatal(1,"missing ALU-to-read forwarding");
 if($test$plusargs("require_baseline") && early!=0) $fatal(1,"baseline unexpectedly early");
end
endmodule
