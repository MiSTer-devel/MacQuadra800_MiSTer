// Original complete Speedometer Whetstone fixture through wombat_cpu's real
// MMU/cache/store buffer. The RAM responder is a controlled-latency model,
// NOT quadra800's SDRAM controller; these cycles are not hardware Mix scores.
// Memory is byte-addressed, so word-aligned but non-longword-aligned stack
// transfers use the same unsplit 32-bit transaction contract as the platform.
`timescale 1ns/1ps
module tb_cpu_whetstone;
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
 reg [7:0] mem[0:33554431]; reg [7:0] rom[0:1048575];
 integer fd, count, patch_writes=0; reg [1023:0] rompath;
 integer pc_cycles[0:65535];
 integer mem_setup=0, mem_prefetch=0, mem_issued=0, read_shape;
 integer read_cache[0:2][0:15];
 integer write_cache[0:15];
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
  if(a>=0 && a<33554432) readbyte=mem[a];
  else if(a>='h40800000 && a<'h40900000) readbyte=rom[a-'h40800000];
  else $fatal(1,"unmodeled read addr=%h pc=%h",a,dut.core.pc_i);
 endfunction
 task writebyte(input integer a,input [7:0] value);
  if(a<0 || a>=33554432) $fatal(1,"unmodeled write addr=%h pc=%h",a,dut.core.pc_i);
  mem[a]=value;
  if(a>='h600000 && a<'h600b4e) patch_writes++;
 endtask
 initial begin
  if(!$value$plusargs("prog=%s",path) || !$value$plusargs("rom=%s",rompath)) $fatal(1,"missing image/ROM");
  if($value$plusargs("latency=%d",latency)) begin end
  for(i=0;i<256;i++) states[i]=0;
  for(i=0;i<16;i++) begin
   write_cache[i]=0;
   for(j=0;j<3;j++) read_cache[j][i]=0;
  end
  for(i=0;i<65536;i++) pc_cycles[i]=0;
  for(i=0;i<3;i++) begin lat_count[i]=0;lat_total[i]=0;end
  fd=$fopen(path,"rb");if(!fd) $fatal(1,"RAM open failed");
  count=$fread(mem,fd);$fclose(fd);if(count!=33554432) $fatal(1,"short RAM image");
  fd=$fopen(rompath,"rb");if(!fd) $fatal(1,"ROM open failed");
  count=$fread(rom,fd);$fclose(fd);if(count!=1048576) $fatal(1,"short ROM image");
  if({mem[0],mem[1],mem[2],mem[3]}!=32'h640000 ||
     {mem[4],mem[5],mem[6],mem[7]}!=32'h630000) $fatal(1,"unexpected fixture vectors");
  repeat(20) @(negedge clk);
  nreset=1;
 end
 always @(posedge clk) if(nreset) begin
  if(dut.core.state==dut.core.S_MRD || dut.core.state==dut.core.S_MWR) begin
   if(!dut.core.m_issued) begin
    if(dut.core.epf_pend) mem_prefetch++; else mem_setup++;
   end else begin
    mem_issued++;
    if(dut.core.state==dut.core.S_MWR) write_cache[dut.g_cache.cache.cst]++;
    else begin
     read_shape=0;
     if((dut.core.m_size==2 && dut.core.m_addr_r[1:0]!=0) ||
        (dut.core.m_size==1 && dut.core.m_addr_r[1:0]==3))
      read_shape=(dut.core.m_addr_r[3:2]==3)?2:1;
     read_cache[read_shape][dut.g_cache.cache.cst]++;
    end
   end
  end
  pc_cycles[dut.core.pc_i[23:8]]++;
  if(cycles%1000000==0) $display("HEARTBEAT cycle=%0d pc=%h state=%0d",cycles,dut.core.pc_i,dut.core.state);
  cycles=cycles+1; states[dut.core.state]=states[dut.core.state]+1;
  if(fault || halted) $fatal(1,"unexpected CPU fault/walker/halt pc=%h",dut.core.pc_i);
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
     else if(saved_data[15:0]==2) $display("WHETSTONE_LOOP cycles=%0d latency=%0d",cycles-stamp_start,latency);
    end
    if(!saved_walker && saved_wr && saved_addr==32'hf102) begin
     if(saved_data[15:0]!=16'h600d) $fatal(1,"guest failure marker");
     $display("WHETSTONE RETURNED cycles=%0d latency=%0d code_patch_bytes=%0d walk_reads=%0d walk_writes=%0d",cycles,latency,patch_writes,walk_reads,walk_writes);
     $display("NUMERICAL_ORACLE_PENDING: return is not a correctness verdict");
     if(mem_setup+mem_prefetch+mem_issued!=states[dut.core.S_MRD]+states[dut.core.S_MWR]) $fatal(1,"memory attribution accounting mismatch");
     $display("MEMORY_PHASE setup=%0d prefetch_wait=%0d issued=%0d",mem_setup,mem_prefetch,mem_issued);
     for(i=0;i<16;i++) begin
      if(write_cache[i]) $display("WRITE_CACHE state=%0d cycles=%0d",i,write_cache[i]);
      for(j=0;j<3;j++) if(read_cache[j][i]) $display("READ_CACHE shape=%0d state=%0d cycles=%0d",j,i,read_cache[j][i]);
     end
     for(j=0;j<256;j++) if(states[j]) $display("STATE %0d cycles=%0d",j,states[j]);
     for(j=0;j<65536;j++) if(pc_cycles[j]) $display("PC_BUCKET %06h cycles=%0d",j*256,pc_cycles[j]);
     $writememh("whet_stack.hex",mem,'h63fc00,'h63ffff);
     $writememh("whet_globals.hex",mem,'h61df90,'h61dfa3);
     $writememh("whet_code.hex",mem,'h600000,'h600b4d);
     $finish;
    end
   end
  end else if(ram_req && !ram_ack) begin
   saved_addr<=ram_addr;saved_data<=ram_wdata;saved_wr<=ram_wr;saved_size<=ram_size;saved_walker<=ram_walker;
   pending<=1;waitleft<=latency;
  end
 end
endmodule
