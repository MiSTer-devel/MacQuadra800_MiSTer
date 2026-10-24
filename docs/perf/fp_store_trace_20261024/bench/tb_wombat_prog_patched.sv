// tb_wombat_prog: a scratch program bench for the OLD core through
// rtl/wombat_cpu.sv (core + MMU + write-through cache + store buffer, the
// Quadra's 32-bit transaction port), derived from verilator/tb_cpu_permute.sv.
// RAM: 1 MB, byte addressed; the responder acks one transaction (any size,
// misaligned included) +latency clocks after accepting it (latency=0: the
// ack is seen by the CPU two clocks after the request rose).  No platform
// retained line, no SDRAM controller.
// Protocol (the new core's bench): $F102 <= $600D pass, $F108 cycle stamp.
//
// 2026-10-24 (fp_attribution): +pcprof -- the cycles between consecutive
// instruction dispatches (ap040_core's perf_dispatch_toggle; pc_i is the
// dispatched instruction's address), charged to the instruction that was
// dispatched first, dumped at PASS as "PCPROF <pc> <count> <cycles>" in the
// new core's tb_ap68040 format.  The sequencer dispatches in order, so the
// gap is the time the instruction held the front of the machine.
`timescale 1ns/1ps
module tb_wombat_prog;
 reg clk=0; always #15 clk=~clk;
 reg nreset=0;
 wire req, wr, instr, walker_req, fault, halted;
 wire [1:0] size;
 wire [31:0] addr, wdata;
 reg ack=0;
 reg [31:0] rdata=0;
 reg [15:0] mem[0:524287];
 integer latency=0, waitleft=0, cycles=0, i, j, bytes, timeout=20000000;
 integer stamp_prev=0, nacc=0;
 reg pending=0;
 reg [31:0] saved_addr, saved_data;
 reg [1:0] saved_size;
 reg saved_wr;
 reg [1023:0] path;
 wombat_cpu dut(.clk(clk),.nreset(nreset),.ce(1'b1),.ipl(3'b111),
 .ipl_autovector(1'b1),.berr(1'b0),.stall_hold(1'b0),.dbg_stall_flt(),
 .cache_line_valid(1'b0),.cache_line_tag(28'd0),.cache_line_data(128'd0),
 .store_buffer_ok(1'b1),.bus_req(req),.bus_write(wr),.bus_instr(instr),
 .bus_size(size),.bus_addr(addr),.bus_wdata(wdata),.bus_fc(),
 .bus_ack(ack),.bus_rdata(rdata),.walker_req(walker_req),.walker_we(),
 .walker_addr(),.walker_wdat(),.walker_ack(1'b0),.walker_data(32'd0),
 .walker_berr(1'b0),.snoop_stb(1'b0),.snoop_addr(32'd0),.nresetout(),
 .nmi_ack_toggle(),.cacr_out(),.vbr_out(),.debug_busy(),
 .debug_fault(fault),.debug_halted(halted),.debug_status(),.debug_status2());
 function [7:0] readbyte(input integer a);
  if(a<0 || a>=1048576) begin $display("FAIL: RAM read out of range %h pc=%h",a,dut.core.pc_i); $finish; end
  readbyte = a[0] ? mem[a>>1][7:0] : mem[a>>1][15:8];
 endfunction
 task writebyte(input integer a,input [7:0] value);
  if(a<0 || a>=1048576) begin $display("FAIL: RAM write out of range %h pc=%h",a,dut.core.pc_i); $finish; end
  if(a[0]) mem[a>>1][7:0]=value; else mem[a>>1][15:8]=value;
 endtask
 // +pcprof: dispatch-to-dispatch cycles by instruction address.
 // The ap040 releases register-destination FP arithmetic to the background
 // (fpu_bg) and keeps dispatching integer instructions; the next FP
 // instruction then waits for fpu_done in S_FPU_ISSUE (or in S_FPU_DEC for
 // the classes that do not overlap).  Those wait cycles belong to the
 // background operation, not to the instruction that happens to wait, so
 // they are counted separately: PCPROF carries the gap minus the wait,
 // PCFPW the wait charged to the background op's address, PCFPWW the same
 // wait charged to the waiting instruction (the naive view).
 reg pcprof=0;
 reg last_tog=0;
 reg pc_prev_v=0;
 reg [31:0] pc_prev=32'hFFFFFFFF;
 reg [31:0] fp_bg_pc=32'hFFFFFFFF;
 reg fpu_bg_last=0;
 integer pc_last_cyc=0;
 integer ndisp=0;
 integer fpw_in_gap=0;
 int pc_cyc [int unsigned];
 int pc_n   [int unsigned];
 int pc_fpw [int unsigned];
 int pc_fpww [int unsigned];
 wire fpwait = dut.core.fpu_bg && !dut.core.fpu_done &&
               (dut.core.state==dut.core.S_FPU_ISSUE || (dut.core.state==dut.core.S_FPU_DEC && !dut.core.fp_dec_overlap_ok));
 task automatic pcprof_dump();
  foreach (pc_cyc[a]) $display("PCPROF %08x %0d %0d", a, pc_n[a], pc_cyc[a]);
  foreach (pc_fpw[a]) $display("PCFPW %08x %0d", a, pc_fpw[a]);
  foreach (pc_fpww[a]) $display("PCFPWW %08x %0d", a, pc_fpww[a]);
 endtask
 always @(posedge clk) if(nreset && pcprof) begin
  // the released operation is the instruction dispatched before this edge
  // (fetch_next may dispatch the next one on the same edge fpu_bg rises)
  if(dut.core.fpu_bg && !fpu_bg_last) fp_bg_pc=pc_prev;
  fpu_bg_last=dut.core.fpu_bg;
  if(dut.core.perf_dispatch_toggle!==last_tog) begin
   if(pc_prev_v) begin pc_cyc[pc_prev]+=cycles-pc_last_cyc-fpw_in_gap; pc_n[pc_prev]+=1; end
   pc_prev=dut.core.pc_i; pc_prev_v=1; pc_last_cyc=cycles; ndisp=ndisp+1; fpw_in_gap=0;
  end
  last_tog=dut.core.perf_dispatch_toggle;
  if(fpwait) begin pc_fpw[fp_bg_pc]+=1; pc_fpww[pc_prev]+=1; fpw_in_gap=fpw_in_gap+1; end
 end
 // fp_store_trace: +fstag=<n>,+fslen=<cycles>: one line a cycle from the stamp
 integer fs_tag=-1, fs_len=400, fs_from=-1, fs_to=-1;
 initial begin
  if(!$value$plusargs("fstag=%d",fs_tag)) fs_tag=-1;
  if(!$value$plusargs("fslen=%d",fs_len)) fs_len=400;
 end
 always @(posedge clk) if(nreset && fs_from>=0 && cycles>=fs_from && cycles<fs_to)
  $display("%8d st=%0d pc=%08x | fp req=%b done=%b acc=%b bg=%b fst=%0d st=%b n=%0d | mgo=%b wr=%b | bus req=%b wr=%b a=%08x sz=%0d ack=%b | disp=%b",
   cycles, dut.core.state, dut.core.pc_i, dut.core.fpu_req, dut.core.fpu_done, dut.core.fpu_accepted,
   dut.core.fpu_bg, dut.core.g_fpu.fpu.fst, dut.core.fp_st, dut.core.fp_n, dut.core.mgo, dut.core.mgo_wr,
   req, wr, addr, size, ack, dut.core.perf_dispatch_toggle);
 initial begin
  if(!$value$plusargs("prog=%s",path)) begin $display("FAIL: missing +prog"); $finish; end
  if($value$plusargs("latency=%d",latency)) begin end
  if($value$plusargs("timeout=%d",timeout)) begin end
  pcprof=$test$plusargs("pcprof");
  for(i=0;i<524288;i=i+1) mem[i]=0;
  $readmemh(path,mem);
  repeat(20) @(negedge clk);
  nreset=1;
 end
 always @(posedge clk) if(nreset) begin
  cycles=cycles+1;
  if(walker_req || fault || halted) begin
   $display("FAIL: unexpected CPU fault/walker/halt walker=%b fault=%b halted=%b pc=%h cycles=%0d",walker_req,fault,halted,dut.core.pc_i,cycles); $finish;
  end
  if(cycles>timeout) begin $display("FAIL: timeout pc=%h",dut.core.pc_i); $finish; end
  ack<=0;
  if(pending) begin
   if(!req || addr!==saved_addr || (saved_wr && wdata!==saved_data) || wr!==saved_wr || size!==saved_size) begin
    $display("FAIL: request changed before ack req=%b addr=%h/%h size=%h/%h wr=%b/%b data=%h/%h",req,addr,saved_addr,size,saved_size,wr,saved_wr,wdata,saved_data); $finish;
   end
   if(waitleft>0) waitleft<=waitleft-1;
   else begin
    pending<=0;ack<=1;nacc=nacc+1;
    bytes=saved_size==0?1:(saved_size==1?2:4);
    rdata=0;
    for(j=0;j<bytes;j=j+1) begin
     if(saved_wr) writebyte(saved_addr+j,saved_data>>(8*(bytes-j-1)));
     else rdata=(rdata<<8)|readbyte(saved_addr+j);
    end
    if(saved_wr && saved_addr[19:0]==20'hf108) begin
     $display("STAMP tag=%04x cycles=%0d bus_transactions=%0d dispatches=%0d at=%0d",saved_data[15:0],cycles-stamp_prev,nacc,ndisp,cycles);
     if(fs_tag>=0 && fs_from<0 && saved_data[15:0]==fs_tag[15:0]) begin fs_from=cycles+1; fs_to=fs_from+fs_len; $display("%8d FSTRACE start: stamp tag %04x",cycles,fs_tag[15:0]); end
     stamp_prev=cycles;
    end
    if(saved_wr && saved_addr[19:0]==20'hf102) begin
     if(saved_data[15:0]!=16'h600d) begin $display("FAIL: program reports failure id=%h",mem['hf100>>1]); $finish; end
     if(pcprof) pcprof_dump();
     $display("PASS %0s cycles=%0d latency=%0d bus_transactions=%0d",path,cycles,latency,nacc);
     $finish;
    end
   end
  end else if(req && !ack) begin
   saved_addr<=addr;saved_data<=wdata;saved_wr<=wr;saved_size<=size;
   pending<=1;waitleft<=latency;
  end
 end
endmodule
