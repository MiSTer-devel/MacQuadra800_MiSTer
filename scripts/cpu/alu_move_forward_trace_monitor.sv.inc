`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module trace_forward_monitor;
integer producers=0,reads=0;
reg traced;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce) begin
 traced=(`C.state==`C.S_PIPE_REGS && `C.regs_alu_fire && `C.p_dreg[3] && `C.tr_t1);
 if(traced) producers++;
 #1;
 if(traced && `C.state==`C.S_MRD && `C.r_m_ret==`C.S_PIPE_SDONE) reads++;
end
final begin
 $display("TRACE_FORWARD producers=%0d reads=%0d",producers,reads);
 if(producers==0 || reads!=0) $fatal(1,"trace boundary coverage or ordering failed");
end
endmodule
