// Simulation-only observers: compare valid queue contents and consumed
// redirect addresses against the pre-optimization assignment rules.
module cpu66_uqueue_check
 import ap68040_pkg::*;
(
 input logic clk, nreset, flush, exc_go, emit, pop,
 input logic [1:0] count,
 input uop_t slot0, slot1, incoming
);
 logic reset_seen = 0;
 logic [1:0] ref_count;
 uop_t ref0, ref1;
 integer empty_pushes = 0, single_pushes = 0, full_pops = 0, simultaneous = 0;
 always @(posedge clk) begin
  if (nreset && reset_seen) begin
   if (count !== ref_count || (count != 0 && slot0 !== ref0) ||
       (count == 2 && slot1 !== ref1))
    $fatal(1, "FAIL: timing rewrite changed valid micro-op FIFO contents");
   if (emit && count == 2)
    $fatal(1, "FAIL: full micro-op FIFO emitted a new entry");
   if (emit && count == 0) empty_pushes <= empty_pushes + 1;
   if (emit && count == 1) single_pushes <= single_pushes + 1;
   if (pop && count == 2) full_pops <= full_pops + 1;
   if (emit && pop && count != 0) simultaneous <= simultaneous + 1;
  end
  if (!nreset) begin
   reset_seen <= 1;
   ref_count <= 0;
   ref0 <= '0;
   ref1 <= '0;
  end else begin
   if (pop && ref_count != 0) begin
    ref0 <= (emit && ref_count == 1) ? incoming : ref1;
    ref1 <= (emit && ref_count == 2) ? incoming : ref1;
    ref_count <= emit ? ref_count : ref_count - 2'd1;
   end else begin
    ref0 <= (emit && ref_count == 0) ? incoming : ref0;
    ref1 <= (emit && ref_count == 1) ? incoming : ref1;
    ref_count <= emit ? ref_count + 2'd1 : ref_count;
   end
   if (flush || exc_go) ref_count <= 0;
  end
 end
 final $display("TIMING_FIFO: empty_pushes=%0d single_pushes=%0d full_pops=%0d simultaneous=%0d",
                empty_pushes, single_pushes, full_pops, simultaneous);
endmodule

bind ap68040_useq cpu66_uqueue_check timing_fifo_check (
 .clk(clk), .nreset(nreset), .flush(flush), .exc_go(exc_go),
 .emit(emit), .pop(uq_pop), .count(uq_n), .slot0(uq0), .slot1(uq1), .incoming(nu)
);

module cpu66_redirect_check (
 input logic clk, nreset, advance, early, redirect_valid,
 input logic wb_commit, wb_redirect, wb_early, refetch,
 input logic [31:0] next_pc, wb_next_pc, wb_pc, redirect_pc
);
 logic reset_seen = 0;
 logic [31:0] ref_pc;
 integer ex_redirects = 0, wb_redirects = 0, refetches = 0, overlapping = 0;
 always @(posedge clk) begin
  if (nreset && reset_seen) begin
   if (redirect_valid && redirect_pc !== ref_pc)
    $fatal(1, "FAIL: timing rewrite changed redirect PC: %h expected %h", redirect_pc, ref_pc);
   if (advance && early) ex_redirects <= ex_redirects + 1;
   if (wb_commit && wb_redirect && !wb_early) wb_redirects <= wb_redirects + 1;
   if (refetch) refetches <= refetches + 1;
   if (advance && ((wb_commit && wb_redirect && !wb_early) || refetch))
    overlapping <= overlapping + 1;
  end
  if (!nreset) begin
   reset_seen <= 1;
   ref_pc <= 0;
  end else begin
   if (advance && early) ref_pc <= next_pc;
   if (wb_commit && wb_redirect && !wb_early) ref_pc <= wb_next_pc;
   if (refetch) ref_pc <= wb_pc;
  end
 end
 final $display("TIMING_REDIRECT: ex=%0d wb=%0d refetch=%0d overlapping=%0d",
                ex_redirects, wb_redirects, refetches, overlapping);
endmodule

bind ap68040_backend cpu66_redirect_check timing_redirect_check (
 .clk(clk), .nreset(nreset), .advance(adv_ex), .early(ex_early),
 .redirect_valid(redir_v), .wb_commit(wb_commit), .wb_redirect(wb_redir),
 .wb_early(wb_eredir), .refetch(wb_refetch), .next_pc(ex_next),
 .wb_next_pc(wb_redir_pc), .wb_pc(wb_u.pc), .redirect_pc(redir_pc)
);
