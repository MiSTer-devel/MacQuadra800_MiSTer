`timescale 1ns/1ps
`define M tb_ap040_program.dut.mmu
module mmu_copy_monitor;
integer full_cycles=0, flush_full=0, clear_checks=0, i;
reg clear_pending=0;
always @(posedge tb_ap040_program.clk) begin
 if (`M.u_valid[0] && `M.u_valid[1] && `M.u_valid[2] && `M.u_valid[3]) begin
  full_cycles++;
  if (`M.pf_req || `M.sweep_on) flush_full++;
 end
 clear_pending = !`M.nreset || `M.fill_we || `M.sweep_on || `M.pf_req || (`M.tc != `M.u_tc);
end
always @(negedge tb_ap040_program.clk) if(clear_pending) begin
 for(i=0;i<$size(`M.u_valid);i=i+1) if(`M.u_valid[i] !== 1'b0) $fatal(1,"retained stale translation copy %0d",i);
 clear_checks++;
end
final begin
 $display("MMU_COPY coverage full_cycles=%0d flush_full=%0d clear_checks=%0d",full_cycles,flush_full,clear_checks);
 if(full_cycles==0 || flush_full==0 || clear_checks==0) $fatal(1,"missing four-copy invalidation coverage");
end
endmodule
