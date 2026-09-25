`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module fault_correlation_monitor;
integer prepared=0,immediate=0,errors=0;
reg producer;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce) begin
 if(`C.state==`C.S_MRD && `C.m_issued && `C.d_err && `C.r_m_ret==`C.S_PIPE_SDONE && `C.m_addr_r==32'h2000) errors++;
 producer=(`C.state==`C.S_PIPE_REGS && `C.regs_alu_fire && !`C.p_wbsup && `C.p_dreg[3]);
 #1;
 if(producer && `C.state==`C.S_MRD && `C.r_m_ret==`C.S_PIPE_SDONE && `C.m_addr_r==32'h2000) begin
  prepared++; if(`C.m_issued && `C.mem_req && !`C.mem_write) immediate++;
 end
end
final begin
 $display("FAULT_FORWARD prepared=%0d immediate=%0d errors=%0d",prepared,immediate,errors);
 if($test$plusargs("require_fault") && (prepared==0 || errors==0)) $fatal(1,"missing forwarded fault correlation");
 if($test$plusargs("require_baseline") && (prepared!=0 || errors==0)) $fatal(1,"baseline fault correlation wrong");
end
endmodule
