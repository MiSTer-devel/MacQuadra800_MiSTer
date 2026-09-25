#!/usr/bin/env python3
"""Speedometer 4.02 Quick Sort / integer Matrix CPU fixtures, v2 (2026-09-22).

Revives scripts/cpu/profile_quick.py (Quick, Matrix kernels) against the
P171+ wombat_cpu.  Unchanged from v1: the extracted CODE3 kernel bytes, the
fixture scope, the independent oracles and the guard words, the checked
controlled-latency RAM responder and the optional real-MMU identity tables.
New in v2:
  * --rtl-root: the RTL comes from a snapshot tree (git archive HEAD rtl),
    never the live rtl/ another session may be editing.
  * the production build's macro set (COMPARE and EARLY_DRAIN included),
    plus $EXTRA_FLAGS; caches on.
  * a REQUIRED failing negative control: one input word is corrupted in a
    disposable copy of the program; the same verilated binary must stop with
    the oracle's mismatch message, or the fixture fails.
  * FIXTURE <kernel> PASS cycles=<N> latency=<L> lines; identity.json.
  * --profile: sequencer state occupancy by NAME (parsed from the snapshot's
    ap040_core.v), top opcodes by legacy active clocks (dut.core.ir), and
    fetch/read/write latency classes, written to profile_latency<L>.txt.
These cycles come from a controlled-latency RAM model, NOT quadra800's SDRAM
path; they are not hardware Speedometer scores.
"""
from pathlib import Path
import argparse, hashlib, json, os, random, re, subprocess, sys, time

repo = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('resource', type=Path, help='Speedometer 4.02 resource fork (sha256 af67113b...)')
parser.add_argument('--kernel', choices=('quick', 'matrix'), default='quick')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--rtl-root', type=Path, required=True,
                    help='snapshot directory containing rtl/ (e.g. from git archive HEAD rtl)')
parser.add_argument('--mmu', choices=('off', '4k', '8k'), default='off',
                    help='real MMU with identity page tables and shared physical RAM walker')
parser.add_argument('--latencies', type=int, nargs='+', default=[0, 3])
parser.add_argument('--control-latency', type=int, default=None,
                    help='latency of the negative-control run (default: the first latency)')
parser.add_argument('--no-control', action='store_true', help='skip the negative control (not a qualifying run)')
parser.add_argument('--core', type=Path, help='optional candidate ap040_core.v')
parser.add_argument('--pipeline-module', type=Path, help='optional candidate ap040_pipeline_integer.sv')
parser.add_argument('--profile', action='store_true', help='state/opcode/latency profile')
parser.add_argument('--top-states', type=int, default=20)
parser.add_argument('--top-opcodes', type=int, default=15)
parser.add_argument('--jobs', type=int, default=4, help='verilator -j (default 4)')
args = parser.parse_args()
if any(n < 0 for n in args.latencies): parser.error('latencies must be nonnegative')

d = args.out.resolve(); d.mkdir(parents=True, exist_ok=True)
root = args.rtl_root.resolve()
rtl = root / 'rtl/ap68040/rtl'
for p in (root / 'rtl/wombat_cpu.sv', rtl / 'ap040_core.v'):
    if not p.exists(): parser.error(f'--rtl-root has no {p}')
if root == repo: print('WARNING: --rtl-root is the live repository tree, not a snapshot', file=sys.stderr)

resource = args.resource.read_bytes()
assert hashlib.sha256(resource).hexdigest() == 'af67113bceb4eb906e973a9b747a0b1925b9d64c62f0f9a84bc6f0578839ca80'
start, end = {'quick': (0x93ce, 0x946e), 'matrix': (0x5dda, 0x5e2e)}[args.kernel]
kernel = resource[82 + 0x6250f + start:82 + 0x6250f + end]
(d / (args.kernel + '.bin')).write_bytes(kernel)

# Disassembly (for naming opcodes in the profile).
dis = {}
try:
    from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_040
    ins = list(Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_040).disasm(kernel, start))
    assert sum(i.size for i in ins) == len(kernel), 'incomplete disassembly'
    (d / 'kernel.dis').write_text(''.join(f'{i.address:04x} {i.bytes.hex():12} {i.mnemonic:10} {i.op_str}\n' for i in ins))
    for i in ins:
        dis.setdefault(int.from_bytes(i.bytes[:2], 'big'), []).append(f'{i.address:04x} {i.mnemonic} {i.op_str}')
except ImportError:
    pass

# ---------------------------------------------------------------- programs
def quick_asm(values, binpath):
    return ''' org 0
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
 incbin "''' + str(binpath) + '''"
 org $c000
 dc.w $a55a
''' + ''.join(' dc.w ' + ','.join('$%04x' % (x & 65535) for x in values[i:i + 20]) + '\n' for i in range(0, 500, 20)) + ' dc.w $5aa5\n'

def matrix_asm(a, b, binpath):
    asm = ''' org 0
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
 incbin "''' + str(binpath) + '''"
'''
    for table, base in ((0x7000, 0x8000), (0x7100, 0xa000)):
        asm += f' org ${table:x}\n' + ''.join(f' dc.l ${base + 82 * i:x}\n' for i in range(41))
    for base, rows in ((0x8000, a), (0xa000, b)):
        asm += f' org ${base:x}\n' + ' dc.w $a55a\n' * 41
        for row in rows: asm += ' dc.w $a55a,' + ','.join(f'${v & 65535:04x}' for v in row) + '\n'
        asm += ' dc.w $5aa5\n'
    asm += ' org $c000\n dc.w $a55a\n rept 1600\n dc.w $dead\n endr\n dc.w $5aa5\n'
    return asm

binpath = d / (args.kernel + '.bin')
if args.kernel == 'quick':
    values = list(range(-250, 250)); random.Random(20260919).shuffle(values)
    inputs = values
    asm = quick_asm(values, binpath)
    # Negative control: one input word changed (a duplicate appears, one
    # value disappears), so the sorted result can no longer be -250..249.
    bad = list(values); bad[0] = values[1]
    control_asm = quick_asm(bad, binpath)
    control_note = f'input[0] {values[0]} -> {values[1]} (duplicate of input[1])'
    control_expect = 'quick result mismatch'
    expected_text = None
else:
    rng = random.Random(20260920)
    a = [[rng.randrange(-32768, 32768) for _ in range(40)] for _ in range(40)]
    b = [[rng.randrange(-32768, 32768) for _ in range(40)] for _ in range(40)]
    expected = [sum(b[row][k] * a[k][col] for k in range(40)) & 65535 for row in range(40) for col in range(40)]
    expected_text = ''.join(f'{v:04x}\n' for v in expected)
    (d / 'expected.hex').write_text(expected_text)
    inputs = {'a': a, 'b': b, 'operation': 'B*A, signed word inputs, word results'}
    asm = matrix_asm(a, b, binpath)
    # Negative control: A[0][0] flipped in the program only; the oracle is
    # the untouched expected.hex.
    bad = [list(r) for r in a]; bad[0][0] = ((a[0][0] ^ 1) + 32768) % 65536 - 32768
    control_asm = matrix_asm(bad, b, binpath)
    control_note = f'A[0][0] {a[0][0]} -> {bad[0][0]} in the program; oracle unchanged'
    control_expect = 'matrix mismatch'

def mmu_patch(text):
    if args.mmu == 'off': return text
    return text.replace(' lea ($8000).l,a5', ' move.l #$4000,d0\n movec d0,urp\n movec d0,srp\n move.l #$'
                        + ('8000' if args.mmu == '4k' else 'c000') + ',d0\n movec d0,tc\n lea ($8000).l,a5')
asm = mmu_patch(asm); control_asm = mmu_patch(control_asm)

def run(cmd, path, check=True):
    with path.open('w') as f:
        return subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT, check=check).returncode

VASM = '/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot'
def build_program(sub, text):
    sd = d / sub; sd.mkdir(exist_ok=True)
    (sd / (args.kernel + '.s')).write_text(text)
    run([VASM, '-Fbin', '-m68040', '-no-opt', '-o', sd / 'program.bin', sd / (args.kernel + '.s')], sd / 'asm.log')
    assert (sd / 'program.bin').read_bytes()[start:end] == kernel, 'kernel bytes changed in program'
    run(['python3', root / 'rtl/ap68040/tb/bin2hex.py', sd / 'program.bin', sd / 'program.hex'], sd / 'hex.log')
    return sd
prog = build_program('program', asm)
ctrl = None if args.no_control else build_program('control', control_asm)
if ctrl:
    assert (ctrl / 'program.bin').read_bytes() != (prog / 'program.bin').read_bytes()

# ---------------------------------------------------------------- testbench
s = r'''// Original Speedometer kernel through wombat_cpu's real MMU/cache/store
// buffer. The RAM responder is a controlled-latency model, NOT quadra800's
// SDRAM controller; these cycles are not hardware Mix scores.
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
if args.kernel == 'matrix':
    s = s.replace('reg [15:0] mem[0:32767];', 'reg [15:0] mem[0:32767]; reg [15:0] expected[0:1599]; reg [15:0] initial_mem[0:32767];')
    s = s.replace('  $readmemh(path,mem);', '  $readmemh(path,mem);\n  $readmemh("' + str(d / 'expected.hex') + '",expected);\n  for(i=0;i<32768;i=i+1) initial_mem[i]=mem[i];')
    b0 = s.index("     if(mem['hc000>>1]")
    f0 = s.index('     for(j=0;j<256;', b0)
    s = s[:b0] + '''     if(mem['hc000>>1]!==16'ha55a || mem['hcc82>>1]!==16'h5aa5) $fatal(1,"matrix guards changed");
     for(i=0;i<1600;i=i+1) if(mem[('hc002+2*i)>>1]!==expected[i]) $fatal(1,"matrix mismatch index=%0d actual=%h expected=%h",i,mem[('hc002+2*i)>>1],expected[i]);
     for(i=('h7000>>1);i<('had24>>1);i=i+1) if(mem[i]!==initial_mem[i]) $fatal(1,"matrix input or guard changed addr=%h",i*2);
     $display("BUFFER_UPPER_BOUND hits=%0d saved_cycles=%0d",buffer_hits,buffer_saving);
     $display("MATRIX40 PASS cycles=%0d latency=%0d all_1600_results=PASS inputs_and_guards=PASS",cycles,latency);
''' + s[f0:]
if args.mmu != 'off':
    s = s.replace('reg ack=0;', '''reg ack=0;
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
    s = s.replace('.walker_we(),', '.walker_we(walker_we),').replace(".walker_addr(),.walker_wdat(),.walker_ack(1'b0),.walker_data(32'd0),", '.walker_addr(walker_addr),.walker_wdat(walker_wdat),.walker_ack(walker_ack),.walker_data(walker_data),')
    s = s.replace('walker_req || fault || halted', 'fault || halted')
    shift = 12 if args.mmu == '4k' else 13
    tables = "  mem['h4000>>1]=0; mem['h4002>>1]='h4203;\n  mem['h4200>>1]=0; mem['h4202>>1]='h4403;\n"
    for page in range(65536 >> shift):
        desc = (page << shift) | 3
        tables += f"  mem[{(0x4400 + 4 * page) // 2}]=16'h{desc >> 16:04x}; mem[{(0x4402 + 4 * page) // 2}]=16'h{desc & 65535:04x};\n"
    s = s.replace('  repeat(20)', tables + '  repeat(20)')
    s = s.replace('  ack<=0;', '  ack<=0; walker_ack<=0;')
    s = s.replace('if(!req || addr!==saved_addr || (saved_wr && wdata!==saved_data) || wr!==saved_wr || size!==saved_size)', 'if(!ram_req || ram_addr!==saved_addr || (saved_wr && ram_wdata!==saved_data) || ram_wr!==saved_wr || ram_size!==saved_size)')
    s = s.replace('pending<=0;ack<=1;', 'pending<=0; if(saved_walker) begin walker_ack<=1; if(saved_wr) walk_writes++; else walk_reads++; end else ack<=1;')
    s = s.replace("    if(saved_wr && saved_addr==32'hf102)", "    if(saved_walker) walker_data<=rdata;\n    if(!saved_walker && saved_wr && saved_addr==32'hf102)")
    s = s.replace('     $finish;', '''     if(!dut.core.tc[15] || walk_reads==0 || walk_writes==0) $fatal(1,"missing real MMU walk coverage");
     if((mem['h4002>>1]&16'h8)==0 || (mem['h4202>>1]&16'h8)==0) $fatal(1,"descriptor used bits missing");
     $display("MMU_WALKS reads=%0d writes=%0d tc=%h",walk_reads,walk_writes,dut.core.tc);
     $finish;''')
    s = s.replace('end else if(req && !ack) begin', 'end else if(ram_req && !ram_ack) begin')
    s = s.replace('saved_addr<=addr;saved_data<=wdata;saved_wr<=wr;saved_size<=size;', 'saved_addr<=ram_addr;saved_data<=ram_wdata;saved_wr<=ram_wr;saved_size<=ram_size;saved_walker<=ram_walker;')
if args.profile:
    # Legacy-sequencer opcode occupancy (cycles the pipeline does not own the
    # register file, attributed to dut.core.ir) and pipeline issue count.
    s = s.replace('integer states[0:255];', 'integer states[0:255]; integer opcycles[0:65535]; integer pipe_cycles=0,pipe_issues=0;')
    s = s.replace('for(i=0;i<256;i=i+1) states[i]=0;', 'for(i=0;i<256;i=i+1) states[i]=0; for(i=0;i<65536;i=i+1) opcycles[i]=0;')
    s = s.replace('cycles=cycles+1; states[dut.core.state]', """if(dut.core.pipe_rf_owner) pipe_cycles++; else opcycles[dut.core.ir]++;
  if(dut.core.pipe_input && dut.core.pipe_ready) pipe_issues++;
  cycles=cycles+1; states[dut.core.state]""")
    s = s.replace('$display("BUFFER_UPPER_BOUND', 'for(j=0;j<65536;j=j+1) if(opcycles[j]) $display("ACTIVE_IR opcode=%04h cycles=%0d",j[15:0],opcycles[j]); $display("PIPELINE cycles=%0d issues=%0d",pipe_cycles,pipe_issues); $display("BUFFER_UPPER_BOUND')
(d / 'tb.sv').write_text(s)

# ---------------------------------------------------------------- build
units = ('ap040_core', 'ap040_bus_timeout', 'ap040_regfile', 'ap040_alu', 'ap040_muldiv', 'ap040_mmu', 'ap040_cache', 'ap040_fpu', 'primitives/dpram')
flags = ['-DAP040_EXPERIMENTAL_' + x for x in ('XSTORE', 'LEA', 'PIPELINE', 'PIPELINE_LOADS', 'PIPELINE_STORES', 'PIPELINE_PEA', 'PIPELINE_P6')]
flags += ['-DAP040_PIPELINE_MEMORY_ENTRY', '-DAP040_PIPELINE_COMPARE', '-DAP040_PIPELINE_EARLY_DRAIN']
flags += os.environ.get('EXTRA_FLAGS', '').split()
core_v = args.core.resolve() if args.core else rtl / 'ap040_core.v'
pipe_v = args.pipeline_module.resolve() if args.pipeline_module else root / 'rtl/ap68040/experimental/ap040_pipeline_integer.sv'
sources = [d / 'tb.sv', root / 'rtl/wombat_cpu.sv', root / 'rtl/wombat_store_buffer.sv',
           *[(core_v if u == 'ap040_core' else rtl / (u + '.v')) for u in units], pipe_v]

# State names from the core actually compiled.
state_names = {}
for m in re.finditer(r"localparam\s+(S_[A-Z0-9_]+)\s*=\s*8'd(\d+)", core_v.read_text()):
    state_names.setdefault(int(m.group(2)), [])
    if m.group(1) not in state_names[int(m.group(2))]: state_names[int(m.group(2))].append(m.group(1))

commit = (root / 'HEAD_COMMIT').read_text().strip() if (root / 'HEAD_COMMIT').exists() else None
identity = {
    'fixture': args.kernel, 'script': 'scripts/cpu/profile_quick_v2.py',
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'rtl_root': str(root), 'rtl_snapshot_commit': commit,
    'sources': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    'flags': flags, 'mmu': args.mmu, 'caches': 'on (CACR $80008000)', 'latencies': args.latencies,
    'kernel_range': f'0x{start:04x}..0x{end - 1:04x}',
    'kernel_sha256': hashlib.sha256(kernel).hexdigest(), 'resource_sha256': hashlib.sha256(resource).hexdigest(),
    'program_sha256': hashlib.sha256((prog / 'program.bin').read_bytes()).hexdigest(),
    'oracle_sha256': hashlib.sha256(expected_text.encode()).hexdigest() if expected_text else None,
    'input': inputs,
    'scope': ('unchanged 0x93ce..0x946d recursive sort; fixed shuffled 500-word input (-250..249, seed 20260919); '
              'excludes initializer, allocation and original wrapper' if args.kernel == 'quick' else
              'unchanged 0x5dda..0x5e2d dot product; 1600 calls over fixed signed 40x40 matrices (seed 20260920); '
              'excludes original initialization, allocation, timing/UI'),
    'oracle': ('output must equal -250..249 in order (sorted permutation of the known input); guard words c000/c3ea'
               if args.kernel == 'quick' else
               'all 1600 word results equal Python B*A (word wrap); inputs, row tables and guards 7000..ad23 unchanged; guards c000/cc82'),
    'negative_control': None if args.no_control else {'mutation': control_note, 'expected_failure': control_expect},
    'memory_model': 'controlled-latency byte-addressed RAM responder (+latency wait cycles per transaction); shared physical walker when MMU on; NOT quadra800 SDRAM',
}
(d / 'identity.json').write_text(json.dumps(identity, indent=2))

t0 = time.time()
run(['/home/alans/verilator5/bin/verilator', '--binary', '--timing', '-Wno-fatal', '-Wno-BLKLOOPINIT', '-j', str(args.jobs),
     '--top-module', 'tb_cpu_quick', '--Mdir', d / 'obj', '-I' + str(rtl), *flags, *sources], d / 'compile.log')
print(f'compiled in {time.time() - t0:.0f}s', flush=True)
exe = d / 'obj/Vtb_cpu_quick'
tag = {'quick': 'QUICK500 PASS', 'matrix': 'MATRIX40 PASS'}[args.kernel]
results = {}

def profile_report(log, latency):
    out = []
    total = int(re.search(r'PASS cycles=(\d+)', log).group(1))
    st = [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r'^STATE (\d+) cycles=(\d+)', log, re.M)]
    st.sort(key=lambda x: -x[1])
    out.append(f'# {args.kernel} mmu={args.mmu} latency={latency} total_cycles={total}')
    out.append('## sequencer state occupancy (dut.core.state)')
    for v, c in st[:args.top_states]:
        out.append(f'STATE {"/".join(state_names.get(v, ["?"])):24s} {v:3d} {c:9d} {100 * c / total:6.2f}%')
    pm = re.search(r'^PIPELINE cycles=(\d+) issues=(\d+)', log, re.M)
    if pm:
        pc = int(pm.group(1))
        out.append(f'## pipeline owns the register file {pc} cycles ({100 * pc / total:.2f}%), issues={pm.group(2)}')
    ops = [(int(m.group(1), 16), int(m.group(2))) for m in re.finditer(r'^ACTIVE_IR opcode=([0-9a-f]+) cycles=(\d+)', log, re.M)]
    ops.sort(key=lambda x: -x[1])
    if ops:
        out.append('## legacy active clocks by dut.core.ir (cycles the pipeline does not own the register file)')
        for op, c in ops[:args.top_opcodes]:
            where = '; '.join(dis.get(op, ['(not a kernel instruction start: harness or stale ir)'])[:3])
            out.append(f'OPCODE {op:04x} {c:9d} {100 * c / total:6.2f}%  {where}')
    out.append('## RAM transaction latency classes (MMU-side mem_req..mem_ack, inclusive)')
    for m in re.finditer(r'^LATENCY class=(\d) count=(\d+) total=(\d+)', log, re.M):
        cl, n, t = int(m.group(1)), int(m.group(2)), int(m.group(3))
        out.append(f'LATENCY {("fetch", "read", "write")[cl]:5s} count={n} total={t} mean={t / n if n else 0:.2f}')
    for key in ('BUFFER_UPPER_BOUND', 'MMU_WALKS'):
        m = re.search('^' + key + '.*$', log, re.M)
        if m: out.append(m.group(0))
    return '\n'.join(out) + '\n'

for latency in args.latencies:
    logfile = d / f'run_latency{latency}.log'
    t1 = time.time()
    rc = run([exe, '+prog=' + str(prog / 'program.hex'), f'+latency={latency}'], logfile, check=False)
    wall = time.time() - t1
    log = logfile.read_text()
    m = re.search(tag + r' cycles=(\d+)', log)
    if rc != 0 or not m:
        print(log[-2000:]); print(f'FIXTURE {args.kernel} FAIL latency={latency} rc={rc}'); sys.exit(1)
    cyc = int(m.group(1)); results[latency] = {'cycles': cyc, 'wall_s': round(wall, 1)}
    walks = re.search(r'^MMU_WALKS.*$', log, re.M)
    print(f'FIXTURE {args.kernel} PASS cycles={cyc} latency={latency} mmu={args.mmu} wall={wall:.1f}s' + (f' {walks.group(0)}' if walks else ''), flush=True)
    if args.profile:
        rep = profile_report(log, latency)
        (d / f'profile_latency{latency}.txt').write_text(rep)
        print(rep, flush=True)

control = None
if ctrl:
    cl = args.control_latency if args.control_latency is not None else args.latencies[0]
    logfile = ctrl / f'run_latency{cl}.log'
    rc = run([exe, '+prog=' + str(ctrl / 'program.hex'), f'+latency={cl}'], logfile, check=False)
    log = logfile.read_text()
    ok = rc != 0 and control_expect in log and tag not in log
    line = next((l for l in log.splitlines() if control_expect in l), log.strip().splitlines()[-1] if log.strip() else '')
    control = {'latency': cl, 'rc': rc, 'mutation': control_note, 'message': line.strip(), 'failed_as_required': ok}
    if ok:
        print(f'CONTROL {args.kernel} control failed as required ({control_note}): {line.strip()}', flush=True)
    else:
        print(f'CONTROL {args.kernel} DID NOT FAIL AS REQUIRED rc={rc}: {line.strip()}', flush=True)

identity['results'] = results; identity['control'] = control
(d / 'identity.json').write_text(json.dumps(identity, indent=2))
if control is not None and not control['failed_as_required']:
    print(f'FIXTURE {args.kernel} FAIL negative control'); sys.exit(1)
