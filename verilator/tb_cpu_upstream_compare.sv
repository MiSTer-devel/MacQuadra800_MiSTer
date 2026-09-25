// Same program and RAM responder for current Mac and upstream pipeline.
// Current Mac includes its real
// MMU/cache/store buffer. The RAM responder is a controlled-latency model,
// NOT quadra800's SDRAM controller; these cycles are not hardware Mix scores.
// Memory is byte-addressed, so word-aligned but non-longword-aligned stack
// transfers use the same unsplit 32-bit transaction contract as the platform.
`timescale 1ns/1ps
module tb_cpu_upstream_compare;
 reg clk=0; always #15 clk=~clk;
 reg nreset=0;
 wire req, wr, instr, walker_req, fault, halted;
 wire [1:0] size;
 wire [31:0] addr, wdata;
 reg ack=0;
 reg [31:0] rdata=0;
 reg [15:0] mem[0:32767];
 integer latency=1, waitleft=0, cycles=0, i, j, bytes, done=0;
 reg pending=0;
 reg [31:0] saved_addr, saved_data;
 reg [1:0] saved_size;
 reg saved_wr;
 string path; integer kernel=0; integer node,next_node,seen_nodes; integer fetches=0,reads=0,writes=0;
`ifdef UPSTREAM_PIPE
 ap040_pipe_sys #(.PC_RESET(32'h400),.PROG_WORDS(100000000)) dut(
 .clk(clk),.nreset(nreset),.ce(1'b1),.mem_req(req),.mem_write(wr),.mem_instr(instr),
 .mem_size(size),.mem_addr(addr),.mem_wdata(wdata),.mem_fc(),.mem_ack(ack),.mem_rdata(rdata));
 assign walker_req=0; assign fault=0; assign halted=0;
 wire [31:0] debug_pc=dut.u_cpu.dbg_ex_pc;
`else
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
 wire [31:0] debug_pc=dut.core.pc_i;
`endif
 function [7:0] readbyte(input integer a);
  if(a<0 || a>=65536) $fatal(1,"RAM address out of range %h",a);
  readbyte = a[0] ? mem[a>>1][7:0] : mem[a>>1][15:8];
 endfunction
 task writebyte(input integer a,input [7:0] value);
  if(a<0 || a>=65536) $fatal(1,"RAM write out of range %h",a);
  if(a[0]) mem[a>>1][7:0]=value; else mem[a>>1][15:8]=value;
 endtask
 initial begin
  if(!$value$plusargs("prog=%s",path)) $fatal(1,"missing program");
  if($value$plusargs("latency=%d",latency)) begin end
  for(i=0;i<32768;i=i+1) mem[i]=0;
  if(!$value$plusargs("kernel=%d",kernel)) $fatal(1,"missing kernel");
  $readmemh(path,mem);
  repeat(20) @(negedge clk);
`ifdef UPSTREAM_PIPE
  // The upstream CPU has no vector-loading reset. Match the fixture's ISP
  // explicitly; PC_RESET matches its entry point. This is test scaffolding.
  dut.u_cpu.u_regfile.isp={mem[0],mem[1]};
`endif
  nreset=1;
 end
 always @(posedge clk) if(nreset) begin
  cycles=cycles+1;
  if(walker_req || fault || halted) $fatal(1,"unexpected CPU fault/walker/halt pc=%h",debug_pc);
  if(cycles>100000000) $fatal(1,"timeout pc=%h",debug_pc);
  ack<=0;
  if(pending) begin
   if(!req || addr!==saved_addr || (saved_wr && wdata!==saved_data) || wr!==saved_wr || size!==saved_size)
    $fatal(1,"request changed before ack req=%b addr=%h/%h size=%h/%h wr=%b/%b data=%h/%h",req,addr,saved_addr,size,saved_size,wr,saved_wr,wdata,saved_data);
   if(waitleft>0) waitleft<=waitleft-1;
   else begin
    pending<=0;ack<=1;
    bytes=saved_size==0?1:(saved_size==1?2:4);
    rdata=0;
    for(j=0;j<bytes;j=j+1) begin
     if(saved_wr) writebyte(saved_addr+j,saved_data>>(8*(bytes-j-1)));
     else rdata=(rdata<<8)|readbyte(saved_addr+j);
    end
    if(saved_wr && saved_addr==32'hf102) begin
     case(kernel)
     0: begin
     if(saved_data[15:0]!=16'h600d) $fatal(1,"guest failed id=%h",mem['hf100>>1]);
     if(mem['hc000>>1]!==1) $fatal(1,"Queens did not find a solution");
     for(i=1;i<=8;i=i+1) begin
      if(mem[('hc0c0+2*i)>>1]<1 || mem[('hc0c0+2*i)>>1]>8) $fatal(1,"Queens column range row=%0d",i);
      for(j=1;j<i;j=j+1) begin
       if(mem[('hc0c0+2*i)>>1]==mem[('hc0c0+2*j)>>1]) $fatal(1,"Queens column collision");
       if(integer'(mem[('hc0c0+2*i)>>1])-integer'(mem[('hc0c0+2*j)>>1])==i-j || integer'(mem[('hc0c0+2*j)>>1])-integer'(mem[('hc0c0+2*i)>>1])==i-j) $fatal(1,"Queens diagonal collision");
      end
      $display("QUEEN row=%0d column=%0d",i,mem[('hc0c0+2*i)>>1]);
     end
     if(mem['hbffe>>1]!==16'ha55a || mem['hc002>>1]!==16'h5aa5 ||
        mem['hc01e>>1]!==16'ha55a || mem['hc042>>1]!==16'h5aa5 ||
        mem['hc05e>>1]!==16'ha55a || mem['hc072>>1]!==16'h5aa5 ||
        mem['hc07e>>1]!==16'ha55a || mem['hc09e>>1]!==16'h5aa5 ||
        mem['hc0be>>1]!==16'ha55a || mem['hc0d2>>1]!==16'h5aa5) $fatal(1,"Queens array guard changed");
     end
     1: begin
     if(saved_data[15:0]!=16'h600d) $fatal(1,"guest failed id=%h",mem['hf100>>1]);
     if(mem['hc000>>1]!==16'ha55a || mem['hc3ea>>1]!==16'h5aa5) $fatal(1,"bubble guards changed");
     for(i=0;i<500;i=i+1) if($signed(mem[('hc002+2*i)>>1]) != i-250) $fatal(1,"bubble result mismatch index=%0d value=%h",i,mem[('hc002+2*i)>>1]);
     end
     2: begin
     if(saved_data[15:0]!=16'h600d) $fatal(1,"guest failed id=%h",mem['hf100>>1]);
     if({mem['h5fa8>>1],mem['h5faa>>1]}!==32'd8660) $fatal(1,"bad recursion count");
     if(mem['h4000>>1]!==16'ha55a || mem['h4010>>1]!==16'h5aa5) $fatal(1,"bad guards");
     for(j=1;j<=7;j=j+1) if(mem[('h4000>>1)+j]!==j-1) $fatal(1,"bad permutation array");
     end
     3: begin
     if(saved_data[15:0]!=16'h600d) $fatal(1,"guest failed id=%h",mem['hf100>>1]);
     if(mem['h5fb6>>1]!==16'd16383 || mem['h6008>>1]!==0 || mem['h600c>>1]!==0) $fatal(1,"bad towers count/heads");
     if(mem['h5fb4>>1]!==16'ha55a || mem['h6010>>1]!==16'h5aa5) $fatal(1,"bad towers guards");
     seen_nodes=0;node=mem['h600a>>1];
     for(i=1;i<=14;i=i+1) begin
      if(node<1 || node>18 || (seen_nodes & (1<<node))) $fatal(1,"bad target node %0d",node);
      seen_nodes=seen_nodes|(1<<node);
      if(mem[('h5fba+4*node)>>1]!==i) $fatal(1,"bad target ordering");
      node=mem[('h5fbc+4*node)>>1];
     end
     if(node!=0) $fatal(1,"target list too long");
     node=mem['h5fb8>>1];
     for(i=0;i<4;i=i+1) begin
      if(node<1 || node>18 || (seen_nodes & (1<<node))) $fatal(1,"bad free node");
      seen_nodes=seen_nodes|(1<<node);node=mem[('h5fbc+4*node)>>1];
     end
     if(node!=0 || seen_nodes!='h7fffe) $fatal(1,"node partition failure");
     end
     default: $fatal(1,"unknown kernel");
     endcase
     $display("BENCH PASS kernel=%0d cycles=%0d latency=%0d fetches=%0d reads=%0d writes=%0d",kernel,cycles,latency,fetches,reads,writes);
     $finish;
    end
   end
  end else if(req && !ack) begin
`ifdef UPSTREAM_PIPE
   if(!instr && !wr && addr<32'h400)
    $fatal(1,"UPSTREAM EXCEPTION vector=%0d instruction_pc=%h opcode=%h cycles=%0d",addr>>2,dut.u_cpu.dbg_id_pc,mem[dut.u_cpu.dbg_id_pc>>1],cycles);
`endif
   if($test$plusargs("trace") && fetches+reads+writes<160)
    $display("BUS cycle=%0d instr=%b wr=%b addr=%h size=%d data=%h pc=%h",cycles,instr,wr,addr,size,wdata,debug_pc);
`ifdef UPSTREAM_PIPE
   if($test$plusargs("trace") && fetches+reads+writes<160)
    $display("PIPE sp=%h sr=%h id=%h op=%h",dut.u_cpu.u_regfile.isp,dut.u_cpu.dbg_sr,dut.u_cpu.dbg_id_pc,dut.u_cpu.if_opcode);
`endif
   if(instr) fetches++; else if(wr) writes++; else reads++;
   saved_addr<=addr;saved_data<=wdata;saved_wr<=wr;saved_size<=size;
   pending<=1;waitleft<=latency;
  end
 end
endmodule
