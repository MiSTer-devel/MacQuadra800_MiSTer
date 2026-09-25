`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module fpu_split_monitor;
integer splits=0;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce && `C.state==`C.S_MRD_B && `C.r_m_ret==`C.S_FPU_RD) splits++;
final begin
 $display("FPU_SPLIT cycles=%0d",splits);
 if(splits==0) $fatal(1,"ordinary FPU split path not covered");
end
endmodule
