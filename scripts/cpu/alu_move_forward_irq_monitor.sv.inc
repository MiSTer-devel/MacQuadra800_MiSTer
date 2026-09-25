`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module irq_forward_monitor;
reg injected=0,checking=0;
integer injections=0,accepted=0,reads=0;
always @(negedge tb_ap040_program.clk) begin
 if(!tb_ap040_program.nreset) begin injected=0; checking=0; release `C.irq_lvl_live; end
 else if(!injected && `C.ce && `C.state==`C.S_PIPE_REGS && `C.regs_alu_fire && !`C.p_wbsup && `C.p_dreg[3] && `C.sr[10:8]==0) begin
  tb_ap040_program.ipl_lvl=3'd2;
  force `C.irq_lvl_live=3'd2;
  injected=1; checking=1; injections++;
 end
end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce && checking) begin
 #1;
 if(`C.state==`C.S_MRD) reads++;
 if(`C.state==`C.S_POST_EXC && `C.exc_is_irq && `C.exc_vec==26) accepted++;
 else $fatal(1,"pending IRQ not accepted at producer retirement");
 checking=0;
 release `C.irq_lvl_live;
end
final begin
 $display("IRQ_FORWARD injections=%0d accepted=%0d reads=%0d",injections,accepted,reads);
 if(injections!=3 || accepted!=3 || reads!=0) $fatal(1,"IRQ boundary coverage failed");
end
endmodule
