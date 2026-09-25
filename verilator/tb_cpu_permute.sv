// Exact Speedometer Permute computational routine through wombat_cpu's real
// MMU/cache/store buffer. The RAM responder is a controlled-latency model,
// NOT quadra800's SDRAM controller; these cycles are not hardware Mix scores.
// Memory is byte-addressed, so word-aligned but non-longword-aligned stack
// transfers use the same unsplit 32-bit transaction contract as the platform.
`timescale 1ns/1ps
module tb_cpu_permute;
 reg clk=0; always #15 clk=~clk;
 reg nreset=0;
 wire req, wr, instr, walker_req, fault, halted;
 wire [1:0] size;
 wire [31:0] addr, wdata;
 reg ack=0;
 reg [31:0] rdata=0;
 reg [15:0] mem[0:32767];
 integer latency=1, waitleft=0, cycles=0, i, j, bytes, done=0;
 integer states[0:255];
`ifdef AP040_EXPERIMENTAL_PIPELINE
 integer pipe_issues=0, pipe_loads=0, pipe_stores=0;
`endif
 integer lat_count[0:2], lat_total[0:2], lat_start=-1, lat_class;
 integer buffer_hits=0, buffer_saving=0;
 reg shadow_valid=0; reg [27:0] shadow_tag=0;
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
  for(i=0;i<256;i=i+1) states[i]=0;
  for(i=0;i<3;i=i+1) begin lat_count[i]=0;lat_total[i]=0;end
  $readmemh(path,mem);
  repeat(20) @(negedge clk);
  nreset=1;
 end
 always @(posedge clk) if(nreset) begin
  cycles=cycles+1; states[dut.core.state]=states[dut.core.state]+1;
`ifdef AP040_EXPERIMENTAL_PIPELINE
  if(dut.core.pipe_input && dut.core.pipe_ready) pipe_issues=pipe_issues+1;
  if(dut.core.pipe_owner && dut.core.pipe_load_req && !dut.core.pipe_load_active)
   if(dut.core.pipe_load_write) pipe_stores=pipe_stores+1; else pipe_loads=pipe_loads+1;
`endif
  if(walker_req || fault || halted) $fatal(1,"unexpected CPU fault/walker/halt pc=%h",dut.core.pc_i);
  if(cycles>20000000) $fatal(1,"timeout pc=%h",dut.core.pc_i);
  if(dut.mem_req && lat_start<0) begin
   lat_start=cycles;lat_class=dut.mem_instr?0:(dut.mem_write?2:1);
  end
  if(dut.mem_ack && lat_start>=0) begin
   if(!dut.mem_instr) begin
    if(dut.mem_write) shadow_valid=0;
    else begin
     if(shadow_valid && shadow_tag==dut.mem_addr[31:4] &&
        ({1'b0,dut.mem_addr[3:0]} + (dut.mem_size==0?1:(dut.mem_size==1?2:4)))<=16) begin
      buffer_hits=buffer_hits+1;buffer_saving=buffer_saving+cycles-lat_start;
     end
     shadow_valid=1;shadow_tag=dut.mem_addr[31:4];
    end
   end
   lat_count[lat_class]=lat_count[lat_class]+1;
   lat_total[lat_class]=lat_total[lat_class]+cycles-lat_start+1;
   lat_start=-1;
  end
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
     if(saved_data[15:0]!=16'h600d) $fatal(1,"guest failed id=%h",mem['hf100>>1]);
     if({mem['h5fa8>>1],mem['h5faa>>1]}!==32'd8660) $fatal(1,"bad recursion count");
     if(mem['h4000>>1]!==16'ha55a || mem['h4010>>1]!==16'h5aa5) $fatal(1,"bad guards");
     for(j=1;j<=7;j=j+1) if(mem[('h4000>>1)+j]!==j-1) $fatal(1,"bad permutation array");
     $display("BUFFER_UPPER_BOUND hits=%0d saved_cycles=%0d",buffer_hits,buffer_saving);
     `ifdef AP040_EXPERIMENTAL_PIPELINE
     $display("PIPELINE issues=%0d loads=%0d stores=%0d",pipe_issues,pipe_loads,pipe_stores);
`endif
     $display("KERNEL32 PASS cycles=%0d latency=%0d calls=8660 array=PASS guards=PASS",cycles,latency);
     for(j=0;j<256;j=j+1) if(states[j]) $display("STATE %0d cycles=%0d",j,states[j]);
     for(j=0;j<3;j=j+1) $display("LATENCY class=%0d count=%0d total=%0d",j,lat_count[j],lat_total[j]);
     $finish;
    end
   end
  end else if(req && !ack) begin
   saved_addr<=addr;saved_data<=wdata;saved_wr<=wr;saved_size<=size;
   pending<=1;waitleft<=latency;
  end
 end
endmodule
