`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module read_monitor;
integer early=0; reg final_read;
always @(posedge tb_ap040_program.clk) begin
 final_read=tb_ap040_program.nreset && `C.ce && `C.state==`C.S_MRD && `C.m_issued && `C.d_ack && !`C.d_err && `C.r_m_ret==`C.S_FPU_RD;
 #1;
 if(final_read && `C.state==`C.S_FPU_GO && `C.fpu_req) early=early+1;
end
final $display("ROOT_FPU_READ early=%0d",early);
endmodule
