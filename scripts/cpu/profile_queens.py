#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,subprocess
r=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description="Profile original Speedometer Queens recursive solver; not a hardware score.")
parser.add_argument('resource',type=Path)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--core',type=Path,help='optional isolated candidate CPU core')
parser.add_argument('--pipeline-module',type=Path,default=r/'rtl/ap68040/experimental/ap040_pipeline_integer.sv',help='pipeline module paired with --core')
parser.add_argument('--compare-module',type=Path,help='optional alternative pipeline module; core and entry policy remain identical')
parser.add_argument('--early-drain',action='store_true',help='enable final-WB pipeline handoff')
parser.add_argument('--compare',action='store_true',help='enable indexed CMP/TST and register TST')
parser.add_argument('--profile',action='store_true',help='report legacy opcode occupancy and pipeline exits')
args=parser.parse_args()
d=args.out.resolve();d.mkdir(parents=True,exist_ok=True);rtl=r/'rtl/ap68040/rtl' 
resource=args.resource.read_bytes()
assert hashlib.sha256(resource).hexdigest()=='af67113bceb4eb906e973a9b747a0b1925b9d64c62f0f9a84bc6f0578839ca80'
kernel=resource[82+0x6250f+0x91a4:82+0x6250f+0x9286];(d/'queens.bin').write_bytes(kernel)
asm=f''' org 0
 dc.l $e000,start
 rept 254
 dc.l unexpected
 endr
 org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
 lea ($8000).l,a5
 pea ($c0c0).l
 pea ($c080).l
 pea ($c060).l
 pea ($c020).l
 pea ($c000).l
 move.w #1,-(sp)
 jsr ($91a4).l
 lea 22(sp),sp
 cmpi.w #1,($c000).l
 bne unexpected
 move.w #$600d,($f102).l
 stop #$2700
unexpected:
 move.w #$bad0,($f102).l
 stop #$2700
 org $91a4
 incbin "{d/'queens.bin'}"
 org $bffe
 dc.w $a55a,0,$5aa5
 org $c01e
 dc.w $a55a
 rept 17
 dc.w 1
 endr
 dc.w $5aa5
 org $c05e
 dc.w $a55a
 rept 9
 dc.w 1
 endr
 dc.w $5aa5
 org $c07e
 dc.w $a55a
 rept 15
 dc.w 1
 endr
 dc.w $5aa5
 org $c0be
 dc.w $a55a
 rept 9
 dc.w 0
 endr
 dc.w $5aa5
'''
(d/'queens.s').write_text(asm)
def run(cmd,path):
 with path.open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
run(['/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot','-Fbin','-m68040','-no-opt','-o',d/'program.bin',d/'queens.s'],d/'asm.log')
assert (d/'program.bin').read_bytes()[0x91a4:0x9286]==kernel
run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/'program.bin',d/'program.hex'],d/'hex.log')
# Self-contained responder and independent column/diagonal/guard checks.
s=r'''// Original Speedometer Queens recursive solver through wombat_cpu's real
// MMU/cache/store buffer. The RAM responder is a controlled-latency model,
// NOT quadra800's SDRAM controller; these cycles are not hardware Mix scores.
// Memory is byte-addressed, so word-aligned but non-longword-aligned stack
// transfers use the same unsplit 32-bit transaction contract as the platform.
`timescale 1ns/1ps
module tb_cpu_queens;
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
  if(walker_req || fault || halted) $fatal(1,"unexpected CPU fault/walker/halt pc=%h",dut.core.pc_i);
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
     $display("BUFFER_UPPER_BOUND hits=%0d saved_cycles=%0d",buffer_hits,buffer_saving);
     $display("QUEENS PASS cycles=%0d latency=%0d nonattacking_board=PASS guards=PASS",cycles,latency);
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
'''
if args.profile:
 s=s.replace('integer states[0:255];', 'integer states[0:255]; integer opcycles[0:65535]; integer exits[0:65535]; integer pipe_cycles=0,pipe_issues=0;')
 s=s.replace('for(i=0;i<256;i=i+1) states[i]=0;', 'for(i=0;i<256;i=i+1) states[i]=0; for(i=0;i<65536;i=i+1) begin opcycles[i]=0;exits[i]=0;end')
 s=s.replace('cycles=cycles+1; states[dut.core.state]', """if(dut.core.pipe_rf_owner) pipe_cycles++; else opcycles[dut.core.ir]++;
  if(dut.core.pipe_input && dut.core.pipe_ready) pipe_issues++;
  if(dut.core.pipe_owner && dut.core.pipe_exit_ready && !dut.core.pipe_input && dut.core.epf_ready_pc) exits[dut.core.epf_data[dut.core.epf_head]]++;
  cycles=cycles+1; states[dut.core.state]""")
 s=s.replace('$display("BUFFER_UPPER_BOUND', 'for(j=0;j<65536;j=j+1) begin if(opcycles[j]) $display("ACTIVE_IR opcode=%04h cycles=%0d",j[15:0],opcycles[j]); if(exits[j]) $display("PIPE_EXIT opcode=%04h count=%0d",j[15:0],exits[j]); end $display("PIPELINE cycles=%0d issues=%0d",pipe_cycles,pipe_issues); $display("BUFFER_UPPER_BOUND')
(d/'tb.sv').write_text(s)
units=('ap040_core','ap040_bus_timeout','ap040_regfile','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','primitives/dpram')
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_MEMORY_ENTRY']
if args.compare: flags.append('-DAP040_PIPELINE_COMPARE')
if args.early_drain: flags.append('-DAP040_PIPELINE_EARLY_DRAIN')
for variant in (('current','compare') if args.compare_module else ('current',)):
 out=d/variant;out.mkdir(exist_ok=True)
 module=args.pipeline_module.resolve() if variant=='current' else args.compare_module.resolve()
 sources=[d/'tb.sv',r/'rtl/wombat_cpu.sv',r/'rtl/wombat_store_buffer.sv',*[(args.core.resolve() if u=='ap040_core' and args.core else rtl/(u+'.v')) for u in units],module]
 (out/'identity.json').write_text(json.dumps({'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'kernel_sha256':hashlib.sha256(kernel).hexdigest(),'resource_sha256':hashlib.sha256(resource).hexdigest(),'input':'eight queens, initially empty board','early_drain':args.early_drain,'compare':args.compare,'scope':'unchanged 0x91a4..0x9285 recursive Try routine; one eight-queen solve; excludes Queens 250-iteration wrapper and its initializer'},indent=2))
 run(['/home/alans/verilator5/bin/verilator','--binary','--timing','-Wno-fatal','-Wno-BLKLOOPINIT','-j','8','--top-module','tb_cpu_queens','--Mdir',out/'obj','-I'+str(rtl),*flags,*sources],out/'compile.log')
 run([out/'obj/Vtb_cpu_queens','+prog='+str(d/'program.hex'),'+latency=3'],out/'run.log')
 log=(out/'run.log').read_text();assert 'QUEENS PASS' in log,log[-2000:]
 print(variant,'\n'.join(l for l in log.splitlines() if l.startswith(('QUEENS','LATENCY','PIPELINE','PIPE_EXIT'))),flush=True)
