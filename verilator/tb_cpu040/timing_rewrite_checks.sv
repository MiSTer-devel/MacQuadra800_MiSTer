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

module cpu66_class_check (
 input logic clk, nreset, active,
 input logic is_md, is_fp, slow, expected_md, expected_fp, expected_slow
);
 integer checked = 0;
 always @(posedge clk) if (nreset && active) begin
  if ({is_md, is_fp, slow} !== {expected_md, expected_fp, expected_slow})
   $fatal(1, "FAIL: registered EX classification differs from its opcode");
  checked <= checked + 1;
 end
 final $display("TIMING_CLASS: checked=%0d", checked);
endmodule

bind ap68040_backend cpu66_class_check timing_class_check (
 .clk(clk), .nreset(nreset), .active(ex_v),
 .is_md(ex_is_md), .is_fp(ex_is_fp), .slow(ex_slow),
 .expected_md((ex_u.op == OP_MUL) || (ex_u.op == OP_DIV)),
 .expected_fp(ex_u.op == OP_FPU), .expected_slow(is_slow(ex_u.op))
);

module cpu66_stall_check(input logic clk,nreset,input logic[4:0] valid,hold,actual);
 logic[4:0] expected;
 always_comb begin
  expected[0]=valid[0]&&hold[0];
  for(int i=1;i<5;i++)expected[i]=valid[i]&&(hold[i]||expected[i-1]);
 end
 always @(posedge clk)if(nreset && actual !== expected)
  $fatal(1,"FAIL: parallel stalls differ from original serial equations");
endmodule
bind ap68040_backend cpu66_stall_check timing_stall_check(
 .clk(clk),.nreset(nreset),.valid({ag_v,dc1_v,dc2_v,ex_v,wb_v}),
 .hold({ag_hold,dm_hold1,dc2_hold,ex_hold,wb_hold}),
 .actual({stall_ag,stall_dc1,stall_dc2,stall_ex,stall_wb}));

// Independent shifting model of the fetch queue before append-before-shift.
// Invalid entries are not part of the interface; every valid word and all
// four of its fault/prediction flags must agree, including across redirects.
module cpu66_fetch_queue_check(
 input logic clk,nreset,redirect,
 input logic[4:0] count,
 input logic[2:0] consume,
 input logic[1:0] append_count,
 input logic[15:0] words[8],append_words[2],
 input logic[7:0] fault,demand,atc,branch,
 input logic append_fault,append_demand,append_atc,
 input logic[1:0] append_branch
);
 logic seen=0;
 logic[4:0] ref_count;
 logic[19:0] ref_words[8];
 integer checked=0,simultaneous=0,redirects=0;
 integer shifts[8]='{default:0};
 always @(posedge clk)begin
  if(nreset && seen)begin
   if(count !== ref_count || consume>count || count>8 ||
      count-consume+append_count>8)
    $fatal(1,"FAIL: fetch queue count/consume contract");
   for(integer i=0;i<8;i=i+1)
    if(i<count && {words[i],fault[i],demand[i],atc[i],branch[i]} !== ref_words[i])
     $fatal(1,"FAIL: fetch queue valid entry %0d differs",i);
   checked<=checked+1;
   shifts[consume]<=shifts[consume]+1;
   if(consume!=0 && append_count!=0)simultaneous<=simultaneous+1;
   if(redirect)redirects<=redirects+1;
  end
  if(!nreset)begin
   seen<=1; ref_count<=0;
   for(integer i=0;i<8;i=i+1)ref_words[i]<=0;
  end else begin
   for(integer i=0;i<8;i=i+1)begin
    if(i<ref_count-consume)ref_words[i]<=ref_words[i+consume];
    else if(i-(ref_count-consume)<append_count)
     ref_words[i]<={append_words[(i-(ref_count-consume))%2],
                     append_fault,append_demand,append_atc,
                     append_branch[(i-(ref_count-consume))%2]};
   end
   ref_count<=redirect ? 5'd0 : ref_count-consume+append_count;
  end
 end
 final $display("TIMING_FETCH_QUEUE: checked=%0d simultaneous=%0d redirects=%0d shifts=%p",
                checked,simultaneous,redirects,shifts);
endmodule
bind ap68040_fetch cpu66_fetch_queue_check timing_fetch_queue_check(
 .clk(clk),.nreset(nreset),.redirect(redir_any),.count(cnt),.consume(consume),
 .append_count(f3_n),.words(qw),.append_words(f3_w),
 .fault(qf),.demand(qd),.atc(qa),.branch(qb),
 .append_fault(f3_f),.append_demand(f3_d),.append_atc(f3_a),.append_branch(f3_b));
