// Unchanged Quadra ROM SANE extended-add routine through wombat_cpu's real
// MMU/cache/store buffer. The RAM responder is a controlled-latency model,
// NOT quadra800's SDRAM controller; these cycles are not hardware Mix scores.
// Memory is byte-addressed, so word-aligned but non-longword-aligned stack
// transfers use the same unsplit 32-bit transaction contract as the platform.
`timescale 1ns/1ps
module tb_cpu_sane;
 reg clk=0; always #15 clk=~clk;
 reg nreset=0;
 wire req, wr, instr, walker_req, fault, halted;
 wire [1:0] size;
 wire [31:0] addr, wdata;
 reg ack=0;
 wire walker_we; wire [31:0] walker_addr,walker_wdat;
 reg walker_ack=0; reg [31:0] walker_data=0;
 reg saved_walker=0;
 integer walk_reads=0,walk_writes=0,mmu_shift=0,remap=0,desc;
 wire ram_walker=pending?saved_walker:walker_req;
 wire ram_req=ram_walker?walker_req:req;
 wire ram_wr=ram_walker?walker_we:wr;
 wire [31:0] ram_addr=ram_walker?walker_addr:addr;
 wire [31:0] ram_wdata=ram_walker?walker_wdat:wdata;
 wire [1:0] ram_size=ram_walker?2'd2:size;
 wire ram_ack=ram_walker?walker_ack:ack;
 reg [31:0] rdata=0;
 reg [15:0] mem[0:32767];
 integer latency=1, waitleft=0, cycles=0, i, j, bytes, done=0;
 integer states[0:255]; integer fpu_crossings=0, require_cross=0, fpu_reads=0; reg [7:0] previous_state=0;
 integer lat_count[0:2], lat_total[0:2], lat_start=-1, lat_class;
 integer buffer_hits=0, buffer_saving=0; integer stamp_start=0;
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
 .bus_ack(ack),.bus_rdata(rdata),.walker_req(walker_req),.walker_we(walker_we),
 .walker_addr(walker_addr),.walker_wdat(walker_wdat),.walker_ack(walker_ack),.walker_data(walker_data),
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
 function [15:0] guestword(input integer a);
  guestword=mem[((remap && a>='h2000 && a<('h2000+(1<<mmu_shift))) ? a+'h4000 : a)>>1];
 endfunction
 initial begin
  if(!$value$plusargs("prog=%s",path)) $fatal(1,"missing program");
  if($value$plusargs("latency=%d",latency)) begin end
  for(i=0;i<32768;i=i+1) mem[i]=0;
  for(i=0;i<256;i=i+1) states[i]=0;
  for(i=0;i<3;i=i+1) begin lat_count[i]=0;lat_total[i]=0;end
  $readmemh(path,mem);
  if($value$plusargs("require_cross=%d",require_cross)) begin end
  if($value$plusargs("mmu=%d",mmu_shift)) begin end
  if($value$plusargs("remap=%d",remap)) begin end
  if(mmu_shift!=0 && mmu_shift!=12 && mmu_shift!=13) $fatal(1,"invalid page size");
  if(remap && mmu_shift==0) $fatal(1,"remap requires MMU");
  if(mmu_shift!=0) begin
   mem['h4000>>1]=0; mem['h4002>>1]='h4203;
   mem['h4200>>1]=0; mem['h4202>>1]='h4403;
   for(i=0;i<(65536>>mmu_shift);i++) begin
    desc=((remap && i==('h2000>>mmu_shift)) ? 'h6000 : (i<<mmu_shift)) | 3;
    mem[('h4400+4*i)>>1]=desc>>16; mem[('h4402+4*i)>>1]=desc;
   end
   if(remap) for(i=0;i<(1<<mmu_shift)/2;i++) begin
    mem[('h6000>>1)+i]=mem[('h2000>>1)+i];mem[('h2000>>1)+i]=16'hdead;
   end
  end
  repeat(20) @(negedge clk);
  nreset=1;
 end
 always @(posedge clk) if(nreset) begin
  if(dut.core.state==dut.core.S_MRD && dut.core.d_ack && !dut.core.d_err &&
     (dut.core.r_m_ret==dut.core.S_FPU_RD || dut.core.r_m_ret==dut.core.S_FPU_MVM3)) begin
   if(require_cross && fpu_reads<6) $display("FPU_ADDRESS %h",dut.core.m_addr_r);
   fpu_reads++;

  end
  if(dut.core.state==dut.core.S_MRD_B && previous_state!=dut.core.S_MRD_B &&
     (dut.core.r_m_ret==dut.core.S_FPU_RD || dut.core.r_m_ret==dut.core.S_FPU_MVM3) &&
     dut.core.m_cross) fpu_crossings++;
  previous_state=dut.core.state;
  cycles=cycles+1; states[dut.core.state]=states[dut.core.state]+1;
  if(fault || halted || (walker_req && mmu_shift==0)) $fatal(1,"unexpected CPU fault/walker/halt pc=%h",dut.core.pc_i);
  if(cycles>100000000) $fatal(1,"timeout pc=%h",dut.core.pc_i);
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
  ack<=0; walker_ack<=0;
  if(pending) begin
   if(!ram_req || ram_addr!==saved_addr || (saved_wr && ram_wdata!==saved_data) || ram_wr!==saved_wr || ram_size!==saved_size)
    $fatal(1,"request changed before ack req=%b addr=%h/%h size=%h/%h wr=%b/%b data=%h/%h",req,addr,saved_addr,size,saved_size,wr,saved_wr,wdata,saved_data);
   if(waitleft>0) waitleft<=waitleft-1;
   else begin
    pending<=0; if(saved_walker) begin walker_ack<=1; if(saved_wr) walk_writes++; else walk_reads++; end else ack<=1;
    bytes=saved_size==0?1:(saved_size==1?2:4);
    rdata=0;
    for(j=0;j<bytes;j=j+1) begin
     if(saved_wr) writebyte(saved_addr+j,saved_data>>(8*(bytes-j-1)));
     else rdata=(rdata<<8)|readbyte(saved_addr+j);
    end
    if(saved_walker) walker_data<=rdata;
    if(!saved_walker && saved_wr && saved_addr==32'hf108) begin
     if(saved_data[15:0]==1) stamp_start=cycles;
     else if(saved_data[15:0]==2) $display("SANE_LOOP cycles=%0d latency=%0d",cycles-stamp_start,latency);
    end
    if(!saved_walker && saved_wr && saved_addr==32'hf102) begin
     if(saved_data[15:0]!=16'h600d) $fatal(1,"guest failed id=%h",mem['hf100>>1]);
     if(guestword('h2022)!==16'h4005 || guestword('h2024)!==16'hcc00 || guestword('h2026)!==0 || guestword('h2028)!==0 || guestword('h202a)!==0) $fatal(1,"SANE result mismatch");
     if(guestword('h2002)!==16'h3fff || guestword('h2004)!==16'h8000 || guestword('h2006)!==0 || guestword('h2008)!==0 || guestword('h200a)!==0) $fatal(1,"SANE source changed");
     if(guestword('h2000)!==16'ha55a || guestword('h2020)!==16'ha55a || guestword('h200c)!==16'h5aa5 || guestword('h202c)!==16'h5aa5) $fatal(1,"SANE guards changed");
     $display("SANE_ADD PASS cycles=%0d latency=%0d result102=PASS source_guards=PASS",cycles,latency);
     for(j=0;j<256;j=j+1) if(states[j]) $display("STATE %0d cycles=%0d",j,states[j]);
     for(j=0;j<3;j=j+1) $display("LATENCY class=%0d count=%0d total=%0d",j,lat_count[j],lat_total[j]);
     if(mmu_shift!=0) begin
      if(!dut.core.tc[15] || walk_reads==0 || walk_writes==0) $fatal(1,"missing MMU walk coverage");
      if((mem['h4002>>1]&16'h8)==0 || (mem['h4202>>1]&16'h8)==0) $fatal(1,"missing used bits");
      if(remap) for(i=0;i<(1<<mmu_shift)/2;i++) if(mem[('h2000>>1)+i]!==16'hdead) $fatal(1,"translation bypass wrote poisoned page");
      $display("MMU PASS shift=%0d remap=%0d reads=%0d writes=%0d",mmu_shift,remap,walk_reads,walk_writes);
     end
     if(require_cross && fpu_crossings==0) $fatal(1,"missing FPU page-crossing read");
     $display("FPU_CROSS reads=%0d",fpu_crossings);
     $finish;
    end
   end
  end else if(ram_req && !ram_ack) begin
   saved_addr<=ram_addr;saved_data<=ram_wdata;saved_wr<=ram_wr;saved_size<=ram_size;saved_walker<=ram_walker;
   pending<=1;waitleft<=latency;
  end
 end
endmodule
