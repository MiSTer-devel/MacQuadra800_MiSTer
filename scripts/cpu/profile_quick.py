#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,random,subprocess
r=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description="Profile original Speedometer integer kernels on CPU/cache/RAM; not a hardware score.")
parser.add_argument('resource',type=Path)
parser.add_argument('--kernel',choices=('quick','sieve','matrix'),default='quick',help='original integer kernel; sieve runs one full pass without Mac allocation')
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--mmu-remap-buffer',action='store_true',help='Sieve translation control: move one virtual buffer page to different physical RAM')
parser.add_argument('--mmu',choices=('off','4k','8k'),default='off',help='real MMU with identity page tables and shared physical RAM walker')
parser.add_argument('--latencies',type=int,nargs='+',default=[3],help='controlled RAM latency values, default 3')
parser.add_argument('--alu',type=Path,help='optional isolated ALU; applies to both compared pipeline modules')
parser.add_argument('--mmu-module',type=Path,help='optional isolated MMU implementation')
parser.add_argument('--muldiv',type=Path,help='optional isolated multiply/divide unit')
parser.add_argument('--store-buffer',type=Path,help='optional isolated store-buffer module')
parser.add_argument('--core',type=Path,help='optional isolated candidate CPU core')
parser.add_argument('--compare-module',type=Path,help='optional alternative pipeline module; core and entry policy remain identical')
parser.add_argument('--early-drain',action='store_true',help='enable final-WB pipeline handoff')
parser.add_argument('--compare',action='store_true',help='enable indexed CMP/TST and register TST')
parser.add_argument('--disassemble',action='store_true',help='write kernel.dis using Python capstone')
parser.add_argument('--profile',action='store_true',help='report legacy opcode occupancy and pipeline exits')
args=parser.parse_args()
if args.mmu_remap_buffer and (args.mmu=='off' or args.kernel!='sieve'): parser.error('--mmu-remap-buffer requires Sieve and enabled MMU')
if any(n<0 for n in args.latencies): parser.error('latencies must be nonnegative')
d=args.out.resolve();d.mkdir(parents=True,exist_ok=True);rtl=r/'rtl/ap68040/rtl' 
resource=args.resource.read_bytes()
assert hashlib.sha256(resource).hexdigest()=='af67113bceb4eb906e973a9b747a0b1925b9d64c62f0f9a84bc6f0578839ca80'
start,end={'quick':(0x93ce,0x946e),'sieve':(0xb6a,0xbae),'matrix':(0x5dda,0x5e2e)}[args.kernel]
kernel=resource[82+0x6250f+start:82+0x6250f+end];(d/(args.kernel+'.bin')).write_bytes(kernel)
if args.disassemble:
 from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_040
 instructions=list(Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_040).disasm(kernel,start))
 assert sum(i.size for i in instructions)==len(kernel), 'incomplete disassembly'
 (d/'kernel.dis').write_text(''.join(f'{i.address:04x} {i.bytes.hex():12} {i.mnemonic:10} {i.op_str}\n' for i in instructions))
values=list(range(-250,250));random.Random(20260919).shuffle(values)
asm=''' org 0
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
 lea ($c000).l,a2
 move.w #500,-(sp)
 move.w #1,-(sp)
 move.l a2,-(sp)
 jsr ($93ce).l
 addq.w #8,sp
 move.w #$600d,($f102).l
 stop #$2700
unexpected:
 move.w #$bad0,($f102).l
 stop #$2700
 org $93ce
 incbin "'''+str(d/(args.kernel+'.bin'))+'''"
 org $c000
 dc.w $a55a
'''+''.join(' dc.w '+','.join('$%04x'%(x&65535) for x in values[i:i+20])+'\n' for i in range(0,500,20))+' dc.w $5aa5\n'
if args.kernel=='sieve':
 # Every flag denotes the odd integer 2*i+3. Trial division is independent
 # of the guest's sieve algorithm and checks all output bytes, not just count.
 def prime(n):
  return n>=2 and all(n%k for k in range(2,__import__('math').isqrt(n)+1))
 expected=[int(prime(2*i+3)) for i in range(8191)]
 (d/'expected.hex').write_text(''.join(f'{v:02x}\n' for v in expected))
 values={'odd_first':3,'odd_last':16383,'count':sum(expected),'flags':8191}
 asm=''' org 0
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
 lea ($9000).l,a2
 jsr ($0b6a).l
 move.w d7,($f100).l
 move.w #$600d,($f102).l
 stop #$2700
unexpected:
 move.w #$bad0,($f102).l
 stop #$2700
 org $0b6a
 incbin "'''+str(d/(args.kernel+'.bin'))+'''"
 rts
 org $8ffe
 dc.w $a55a
 org $afff
 dc.b $5a,$a5
'''
if args.kernel=='matrix':
 # Signed 16-bit input, independently calculated B*A with word wraparound.
 # The original routine computes one 40-term dot product per call.
 rng=random.Random(20260920)
 a=[[rng.randrange(-32768,32768) for _ in range(40)] for _ in range(40)]
 b=[[rng.randrange(-32768,32768) for _ in range(40)] for _ in range(40)]
 expected=[sum(b[row][k]*a[k][col] for k in range(40))&65535 for row in range(40) for col in range(40)]
 (d/'expected.hex').write_text(''.join(f'{v:04x}\n' for v in expected))
 values={'a':a,'b':b,'operation':'B*A, signed word inputs, word results'}
 asm=''' org 0
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
 lea ($c002).l,a3
 moveq #1,d7
row_loop:
 moveq #1,d6
column_loop:
 move.w d6,-(sp)
 move.w d7,-(sp)
 move.l #$7000,-(sp)
 move.l #$7100,-(sp)
 move.l a3,-(sp)
 jsr ($5dda).l
 lea 16(sp),sp
 addq.l #2,a3
 addq.w #1,d6
 cmpi.w #40,d6
 ble column_loop
 addq.w #1,d7
 cmpi.w #40,d7
 ble row_loop
 move.w #$600d,($f102).l
 stop #$2700
unexpected:
 move.w #$bad0,($f102).l
 stop #$2700
 org $5dda
 incbin "'''+str(d/'matrix.bin')+'''"
'''
 for table,base,rows in ((0x7000,0x8000,a),(0x7100,0xa000,b)):
  asm+=f' org ${table:x}\n'+''.join(f' dc.l ${base+82*i:x}\n' for i in range(41))
 for base,rows in ((0x8000,a),(0xa000,b)):
  asm+=f' org ${base:x}\n'+ ' dc.w $a55a\n'*41
  for row in rows: asm+=' dc.w $a55a,'+','.join(f'${v&65535:04x}' for v in row)+'\n'
  asm+=' dc.w $5aa5\n'
 asm+=' org $c000\n dc.w $a55a\n rept 1600\n dc.w $dead\n endr\n dc.w $5aa5\n'
if args.mmu!='off':
 asm=asm.replace(' lea ($8000).l,a5', ' move.l #$4000,d0\n movec d0,urp\n movec d0,srp\n move.l #$'+('8000' if args.mmu=='4k' else 'c000')+',d0\n movec d0,tc\n lea ($8000).l,a5')
(d/(args.kernel+'.s')).write_text(asm)
def run(cmd,path):
 with path.open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
run(['/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot','-Fbin','-m68040','-no-opt','-o',d/'program.bin',d/(args.kernel+'.s')],d/'asm.log')
assert (d/'program.bin').read_bytes()[start:end]==kernel
run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/'program.bin',d/'program.hex'],d/'hex.log')
# Self-contained responder and independent sorted-permutation checks.
s=r'''// Original Speedometer Quick Sort recursive routine through wombat_cpu's real
// MMU/cache/store buffer. The RAM responder is a controlled-latency model,
// NOT quadra800's SDRAM controller; these cycles are not hardware Mix scores.
// Memory is byte-addressed, so word-aligned but non-longword-aligned stack
// transfers use the same unsplit 32-bit transaction contract as the platform.
`timescale 1ns/1ps
module tb_cpu_quick;
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
     if(mem['hc000>>1]!==16'ha55a || mem['hc3ea>>1]!==16'h5aa5) $fatal(1,"quick guards changed");
     for(i=0;i<500;i=i+1) if($signed(mem[('hc002+2*i)>>1]) != i-250) $fatal(1,"quick result mismatch index=%0d value=%h",i,mem[('hc002+2*i)>>1]);
     $display("BUFFER_UPPER_BOUND hits=%0d saved_cycles=%0d",buffer_hits,buffer_saving);
     $display("QUICK500 PASS cycles=%0d latency=%0d sorted_permutation=PASS guards=PASS",cycles,latency);
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
if args.kernel=='sieve':
 s=s.replace('reg [15:0] mem[0:32767];','reg [15:0] mem[0:32767]; reg [7:0] expected[0:8190];')
 s=s.replace('  $readmemh(path,mem);', '  $readmemh(path,mem);\n  $readmemh("'+str(d/'expected.hex')+'",expected);')
 begin=s.index('     if(mem[\'hc000>>1]')
 finish=s.index('     for(j=0;j<256;',begin)
 s=s[:begin]+'''     if(readbyte('h8ffe)!==8'ha5 || readbyte('h8fff)!==8'h5a || readbyte('hafff)!==8'h5a || readbyte('hb000)!==8'ha5) $fatal(1,"sieve guards changed");
     if(mem['hf100>>1]!==16'd'''+str(sum(expected))+''') $fatal(1,"sieve count mismatch %0d",mem['hf100>>1]);
     for(i=0;i<8191;i=i+1) if(readbyte('h9000+i)!==expected[i]) $fatal(1,"sieve flag mismatch index=%0d",i);
     $display("BUFFER_UPPER_BOUND hits=%0d saved_cycles=%0d",buffer_hits,buffer_saving);
     $display("SIEVE8191 PASS cycles=%0d latency=%0d prime_flags=PASS guards=PASS",cycles,latency);
'''+s[finish:]
if args.kernel=='matrix':
 s=s.replace('reg [15:0] mem[0:32767];','reg [15:0] mem[0:32767]; reg [15:0] expected[0:1599]; reg [15:0] initial_mem[0:32767];')
 s=s.replace('  $readmemh(path,mem);', '  $readmemh(path,mem);\n  $readmemh("'+str(d/'expected.hex')+'",expected);\n  for(i=0;i<32768;i=i+1) initial_mem[i]=mem[i];')
 begin=s.index("     if(mem['hc000>>1]")
 finish=s.index('     for(j=0;j<256;',begin)
 s=s[:begin]+'''     if(mem['hc000>>1]!==16'ha55a || mem['hcc82>>1]!==16'h5aa5) $fatal(1,"matrix guards changed");
     for(i=0;i<1600;i=i+1) if(mem[('hc002+2*i)>>1]!==expected[i]) $fatal(1,"matrix mismatch index=%0d actual=%h expected=%h",i,mem[('hc002+2*i)>>1],expected[i]);
     for(i=('h7000>>1);i<('had24>>1);i=i+1) if(mem[i]!==initial_mem[i]) $fatal(1,"matrix input or guard changed addr=%h",i*2);
     $display("BUFFER_UPPER_BOUND hits=%0d saved_cycles=%0d",buffer_hits,buffer_saving);
     $display("MATRIX40 PASS cycles=%0d latency=%0d all_1600_results=PASS inputs_and_guards=PASS",cycles,latency);
'''+s[finish:]
if args.mmu!='off':
 s=s.replace('reg ack=0;', '''reg ack=0;
 wire walker_we; wire [31:0] walker_addr,walker_wdat;
 reg walker_ack=0; reg [31:0] walker_data=0;
 reg saved_walker=0;
 integer walk_reads=0,walk_writes=0;
 wire ram_walker=pending?saved_walker:walker_req;
 wire ram_req=ram_walker?walker_req:req;
 wire ram_wr=ram_walker?walker_we:wr;
 wire [31:0] ram_addr=ram_walker?walker_addr:addr;
 wire [31:0] ram_wdata=ram_walker?walker_wdat:wdata;
 wire [1:0] ram_size=ram_walker?2'd2:size;
 wire ram_ack=ram_walker?walker_ack:ack;''')
 s=s.replace('.walker_we(),', '.walker_we(walker_we),').replace('.walker_addr(),.walker_wdat(),.walker_ack(1\'b0),.walker_data(32\'d0),', '.walker_addr(walker_addr),.walker_wdat(walker_wdat),.walker_ack(walker_ack),.walker_data(walker_data),')
 s=s.replace('walker_req || fault || halted','fault || halted')
 # Initialize resident identity tables physically, before releasing reset.
 shift=12 if args.mmu=='4k' else 13
 tables="  mem['h4000>>1]=0; mem['h4002>>1]='h4203;\n  mem['h4200>>1]=0; mem['h4202>>1]='h4403;\n"
 for page in range(65536>>shift):
  desc=(page<<shift)|3
  if args.mmu_remap_buffer and page==(0x9000>>shift): desc=(0x5000 if shift==12 else 0x6000)|3
  tables+=f"  mem[{(0x4400+4*page)//2}]=16'h{desc>>16:04x}; mem[{(0x4402+4*page)//2}]=16'h{desc&65535:04x};\n"
 if args.mmu_remap_buffer:
  virtual_base=0x9000 if shift==12 else 0x8000
  physical_base=0x5000 if shift==12 else 0x6000
  tables+=f"  for(i=0;i<{(1<<shift)//2};i=i+1) begin mem[{physical_base//2}+i]=mem[{virtual_base//2}+i]; mem[{virtual_base//2}+i]=16'hdead; end\n"
  # Only oracle reads translate; bus and walker always access physical RAM.
  function=f''' function [7:0] readguestbyte(input integer a);
  readguestbyte=readbyte((a>={virtual_base} && a<{virtual_base+(1<<shift)}) ? a-{virtual_base}+{physical_base} : a);
 endfunction
'''
  s=s.replace(' initial begin',function+' initial begin',1)
  s=s.replace("if(readbyte('h8ffe)","if(readguestbyte('h8ffe)").replace("readbyte('h8fff)","readguestbyte('h8fff)").replace("readbyte('hafff)","readguestbyte('hafff)").replace("readbyte('hb000)","readguestbyte('hb000)").replace("readbyte('h9000+i)","readguestbyte('h9000+i)")
  s=s.replace('     $finish;',f'''     for(i=0;i<{(1<<shift)//2};i=i+1) if(mem[{virtual_base//2}+i]!==16'hdead) $fatal(1,"MMU bypass wrote unmapped physical page");
     $display("MMU_REMAP PASS virtual=%h physical=%h",32'd{virtual_base},32'd{physical_base});
     $finish;''')
 s=s.replace('  repeat(20)',tables+'  repeat(20)')
 s=s.replace('  ack<=0;', '  ack<=0; walker_ack<=0;')
 s=s.replace('if(!req || addr!==saved_addr || (saved_wr && wdata!==saved_data) || wr!==saved_wr || size!==saved_size)', 'if(!ram_req || ram_addr!==saved_addr || (saved_wr && ram_wdata!==saved_data) || ram_wr!==saved_wr || ram_size!==saved_size)')
 s=s.replace('pending<=0;ack<=1;', 'pending<=0; if(saved_walker) begin walker_ack<=1; if(saved_wr) walk_writes++; else walk_reads++; end else ack<=1;')
 s=s.replace("    if(saved_wr && saved_addr==32'hf102)", "    if(saved_walker) walker_data<=rdata;\n    if(!saved_walker && saved_wr && saved_addr==32'hf102)")
 s=s.replace('     $finish;', '''     if(!dut.core.tc[15] || walk_reads==0 || walk_writes==0) $fatal(1,"missing real MMU walk coverage");
     if((mem['h4002>>1]&16'h8)==0 || (mem['h4202>>1]&16'h8)==0) $fatal(1,"descriptor used bits missing");
     $display("MMU_WALKS reads=%0d writes=%0d tc=%h",walk_reads,walk_writes,dut.core.tc);
     $finish;''')
 s=s.replace('end else if(req && !ack) begin', 'end else if(ram_req && !ram_ack) begin')
 s=s.replace('saved_addr<=addr;saved_data<=wdata;saved_wr<=wr;saved_size<=size;', 'saved_addr<=ram_addr;saved_data<=ram_wdata;saved_wr<=ram_wr;saved_size<=ram_size;saved_walker<=ram_walker;')
if args.profile:
 s=s.replace('integer states[0:255];', 'integer states[0:255]; integer opcycles[0:65535]; integer exits[0:65535]; integer regs_cycles[0:65535]; integer admission_denied[0:65535]; integer pipe_cycles=0,pipe_issues=0; integer fetch_empty=0,decode_ext_wait=0,pipe_ready_empty=0,data_prefetch_wait=0,data_setup=0,data_ack_wait=0,regs_queue_ready=0,regs_queue_empty=0;')
 s=s.replace('for(i=0;i<256;i=i+1) states[i]=0;', 'for(i=0;i<256;i=i+1) states[i]=0; for(i=0;i<65536;i=i+1) begin opcycles[i]=0;exits[i]=0;regs_cycles[i]=0;admission_denied[i]=0;end')
 s=s.replace('cycles=cycles+1; states[dut.core.state]', """if(dut.core.state==dut.core.S_FETCH && !dut.core.epf_ready_pc) fetch_empty++;
  if(dut.core.pipe_pea_wait) decode_ext_wait++;
  if(dut.core.pipe_rf_owner && dut.core.pipe_ready && !dut.core.epf_ready_pc) pipe_ready_empty++;
  if(dut.core.state==dut.core.S_MRD || dut.core.state==dut.core.S_MWR) begin
   if(!dut.core.m_issued && dut.core.epf_pend) data_prefetch_wait++;
   else if(!dut.core.m_issued) data_setup++;
   else if(!dut.core.d_ack) data_ack_wait++;
  end
  if(dut.core.state==dut.core.S_DECODE && dut.core.pipe_supported && !dut.core.pipe_entry_ok) admission_denied[dut.core.ir]++;
  if(dut.core.state==dut.core.S_PIPE_REGS) begin
   regs_cycles[dut.core.ir]++;
   if(dut.core.epf_ready_pc) regs_queue_ready++;else regs_queue_empty++;
  end
  if(dut.core.pipe_rf_owner) pipe_cycles++; else opcycles[dut.core.ir]++;
  if(dut.core.pipe_input && dut.core.pipe_ready) pipe_issues++;
  if(dut.core.pipe_owner && dut.core.pipe_exit_ready && !dut.core.pipe_input && dut.core.epf_ready_pc) exits[dut.core.epf_data[dut.core.epf_head]]++;
  cycles=cycles+1; states[dut.core.state]""")
 s=s.replace('$display("BUFFER_UPPER_BOUND', 'for(j=0;j<65536;j=j+1) begin if(regs_cycles[j]) $display("REGS_IR opcode=%04h cycles=%0d",j[15:0],regs_cycles[j]); if(admission_denied[j]) $display("ENTRY_DENIED opcode=%04h cycles=%0d",j[15:0],admission_denied[j]); if(opcycles[j]) $display("ACTIVE_IR opcode=%04h cycles=%0d",j[15:0],opcycles[j]); if(exits[j]) $display("PIPE_EXIT opcode=%04h count=%0d",j[15:0],exits[j]); end $display("PIPELINE cycles=%0d issues=%0d",pipe_cycles,pipe_issues); $display("FETCH_PROFILE empty=%0d decode_extension_wait=%0d pipe_ready_empty=%0d data_prefetch_wait=%0d data_setup=%0d data_ack_wait=%0d regs_queue_ready=%0d regs_queue_empty=%0d",fetch_empty,decode_ext_wait,pipe_ready_empty,data_prefetch_wait,data_setup,data_ack_wait,regs_queue_ready,regs_queue_empty); $display("BUFFER_UPPER_BOUND')
if args.profile:
 # Attribute actual pipeline read handshakes by issued PC, never legacy IR.
 s=s.replace('integer states[0:255];', '''integer states[0:255];
 integer pr_count[0:32767],pr_cycles[0:32767],pr_max[0:32767];
 integer pr_retired[0:32767],pr_retire_gap[0:32767],pr_ack_cycle[0:32767];
 integer pr_prefetch[0:32767],pr_setup[0:32767],pr_wait[0:32767],pr_other[0:32767];
 integer pr_hint_miss[0:32767],pr_cache_busy[0:32767],pr_array_wait[0:32767],pr_tag_miss[0:32767];
 integer pr_start=-1,pr_pc=0,pr_index=0,pr_elapsed=0;
''')
 s=s.replace('for(i=0;i<256;i=i+1) states[i]=0;', '''for(i=0;i<256;i=i+1) states[i]=0;
  for(i=0;i<32768;i=i+1) begin
   pr_count[i]=0;pr_cycles[i]=0;pr_max[i]=0;pr_retired[i]=0;
   pr_retire_gap[i]=0;pr_ack_cycle[i]=-1;
   pr_prefetch[i]=0;pr_setup[i]=0;pr_wait[i]=0;pr_other[i]=0;
   pr_hint_miss[i]=0;pr_cache_busy[i]=0;pr_array_wait[i]=0;pr_tag_miss[i]=0;
  end''')
 s=s.replace('cycles=cycles+1; states[dut.core.state]', '''if(pr_start>=0 && !dut.core.pipe_load_ack) begin
   pr_index=pr_pc>>1;
   if(dut.core.state==dut.core.S_MRD && !dut.core.m_issued && dut.core.epf_pend) pr_prefetch[pr_index]++;
   else if(dut.core.state==dut.core.S_MRD && !dut.core.m_issued) pr_setup[pr_index]++;
   else if(dut.core.state==dut.core.S_MRD && dut.core.m_issued) begin
    pr_wait[pr_index]++;
    if(!dut.mm_hint_match) pr_hint_miss[pr_index]++;
    if(!dut.g_cache.cache.fast_accept) pr_cache_busy[pr_index]++;
    if(!dut.g_cache.cache.idle_data_valid || !dut.g_cache.cache.idle_tag_valid ||
       dut.g_cache.cache.idle_data_idx != {1'b0,dut.g_cache.cache.hq_lo[dut.g_cache.cache.SETW+3:2]} ||
       dut.g_cache.cache.idle_tag_idx != {1'b0,dut.g_cache.cache.hq_lo[dut.g_cache.cache.SETW+3:4]}) pr_array_wait[pr_index]++;
    if(!dut.g_cache.cache.hint_look_hit) pr_tag_miss[pr_index]++;
   end
   else pr_other[pr_index]++;
  end
  if(dut.core.pipe_load_ack && pr_start>=0) begin
   pr_index=pr_pc>>1;pr_elapsed=cycles-pr_start;
   pr_count[pr_index]++;pr_cycles[pr_index]+=pr_elapsed;
   if(pr_elapsed>pr_max[pr_index]) pr_max[pr_index]=pr_elapsed;
   pr_ack_cycle[pr_index]=cycles;pr_start=-1;
  end
  if(dut.core.pipe_retire && (dut.core.pipe_owner || dut.core.pipe_read_retire)) begin
   pr_index=dut.core.pipe_pc>>1;
   if(pr_index<32768 && pr_ack_cycle[pr_index]>=0) begin
    pr_retired[pr_index]++;pr_retire_gap[pr_index]+=cycles-pr_ack_cycle[pr_index];
    pr_ack_cycle[pr_index]=-1;
   end
  end
  if(dut.core.pipe_load_launch && !dut.core.pipe_load_write) begin
   if(pr_start>=0) $fatal(1,"overlapping pipeline read attribution");
   pr_start=cycles;pr_pc=dut.core.pipe_load_pc;
   if(pr_pc>=65536) $fatal(1,"pipeline PC outside fixture");
  end
  cycles=cycles+1; states[dut.core.state]''')
 s=s.replace('$display("BUFFER_UPPER_BOUND', '''for(j=0;j<32768;j=j+1) if(pr_count[j]) begin
      if(pr_count[j]!=pr_retired[j]) $fatal(1,"pipeline read retirement count mismatch pc=%h",j*2);
      if(pr_cycles[j] != pr_count[j]+pr_prefetch[j]+pr_setup[j]+pr_wait[j]+pr_other[j]) $fatal(1,"pipeline read timing accounting mismatch");
      $display("PIPE_READ pc=%04h reads=%0d response_cycles=%0d max_response=%0d retire_gap_cycles=%0d prefetch_wait=%0d setup=%0d ack_wait=%0d other=%0d",j*2,pr_count[j],pr_cycles[j],pr_max[j],pr_retire_gap[j],pr_prefetch[j],pr_setup[j],pr_wait[j],pr_other[j]);
      $display("PIPE_READ_BLOCKERS pc=%04h hint_mismatch=%0d cache_not_accepting=%0d array_unready=%0d tag_miss=%0d",j*2,pr_hint_miss[j],pr_cache_busy[j],pr_array_wait[j],pr_tag_miss[j]);
     end
     $display("BUFFER_UPPER_BOUND''')
(d/'tb.sv').write_text(s)
units=('ap040_core','ap040_bus_timeout','ap040_regfile','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','primitives/dpram')
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_MEMORY_ENTRY']
if args.compare: flags.append('-DAP040_PIPELINE_COMPARE')
if args.early_drain: flags.append('-DAP040_PIPELINE_EARLY_DRAIN')
for variant in (('current','compare') if args.compare_module else ('current',)):
 out=d/variant;out.mkdir(exist_ok=True)
 module=r/'rtl/ap68040/experimental/ap040_pipeline_integer.sv' if variant=='current' else args.compare_module.resolve()
 sources=[d/'tb.sv',r/'rtl/wombat_cpu.sv',r/'rtl/wombat_store_buffer.sv',*[rtl/(u+'.v') for u in units],module]
 sources=[args.core.resolve() if args.core and p==rtl/'ap040_core.v' else p for p in sources]
 sources=[args.store_buffer.resolve() if args.store_buffer and p==r/'rtl/wombat_store_buffer.sv' else p for p in sources]
 sources=[args.alu.resolve() if args.alu and p==rtl/'ap040_alu.v' else p for p in sources]
 sources=[args.mmu_module.resolve() if args.mmu_module and p==rtl/'ap040_mmu.v' else p for p in sources]
 sources=[args.muldiv.resolve() if args.muldiv and p==rtl/'ap040_muldiv.v' else p for p in sources]
 (out/'identity.json').write_text(json.dumps({'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'kernel_sha256':hashlib.sha256(kernel).hexdigest(),'resource_sha256':hashlib.sha256(resource).hexdigest(),'input':values,'latencies':args.latencies,'early_drain':args.early_drain,'compare':args.compare,'scope':('unchanged 0x93ce..0x946d recursive sort; fixed shuffled input; excludes initializer, allocation and original wrapper' if args.kernel=='quick' else 'unchanged 0x5dda..0x5e2d dot product; 1600 calls over fixed signed 40x40 matrices; excludes original initialization, allocation, timing/UI' if args.kernel=='matrix' else 'unchanged 0xb6a..0xbad Sieve inner pass including initialization; original addresses; excludes allocation, disposal, outer 100-pass repetition and timing/UI'), 'kernel':args.kernel, 'mmu':args.mmu, 'mmu_remap_buffer':args.mmu_remap_buffer, 'memory_model':'shared physical RAM responder and walker; see mmu and mmu_remap_buffer for mapping', 'program_sha256':hashlib.sha256((d/'program.bin').read_bytes()).hexdigest(), 'oracle_sha256':hashlib.sha256((d/'expected.hex').read_bytes()).hexdigest() if args.kernel in ('sieve','matrix') else None},indent=2))
 run(['/home/alans/verilator5/bin/verilator','--binary','--timing','-Wno-fatal','-Wno-BLKLOOPINIT','-j','8','--top-module','tb_cpu_quick','--Mdir',out/'obj','-I'+str(rtl),*flags,*sources],out/'compile.log')
 for latency in args.latencies:
  logfile=out/f'run_latency{latency}.log'
  run([out/'obj/Vtb_cpu_quick','+prog='+str(d/'program.hex'),f'+latency={latency}'],logfile)
  log=logfile.read_text();assert {'quick':'QUICK500 PASS','sieve':'SIEVE8191 PASS','matrix':'MATRIX40 PASS'}[args.kernel] in log,log[-2000:]
  print(variant,'\n'.join(l for l in log.splitlines() if l.startswith(('QUICK500','SIEVE8191','MATRIX40','MMU_WALKS','MMU_REMAP','LATENCY','PIPELINE','PIPE_EXIT','PIPE_READ','FETCH_PROFILE'))),flush=True)
