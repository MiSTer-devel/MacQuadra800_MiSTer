#!/usr/bin/env python3
"""Run the original Speedometer 4.02 Puzzle test through wombat_cpu.

Extracted, unchanged CODE3 bytes 0x8a8a..0x919b (Fit, Place, Remove, the
Puzzle driver at 0x8be6 and the recursive Trial at 0x90e8, plus the
never-executed MacsBug names between them) are placed at their original
CODE-relative addresses.  The harness calls Puzzle exactly as doTheTests
does (CODE3 0x4df8: JSR $8be6, no arguments), so the measured window is one
complete timed Puzzle run: array allocation and initialization, the
2005-trial search, and the frees.

Puzzle calls two Memory Manager traps: _NewPtrClear (A31E, 17 calls) and
_DisposPtr (A01F, 17 calls).  The harness supplies them with an A-line
exception handler: a bump allocator laid out like the 32-bit Memory
Manager (12-byte block header, 4-byte-aligned data, size rounded to 4) that
clears each block, and a no-op DisposPtr that counts and sums the pointers.
Handler clocks are inside the window and are reported separately (by PC,
approximate); the real Memory Manager's cost is not modelled.

The RAM responder is a controlled-latency model, NOT quadra800's SDRAM
controller; cycles compare CPU variants, they are not hardware Mix scores.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, sys, time
from collections import Counter

r = Path(__file__).resolve().parents[2]
SNAP = r / 'scratch/fixture_puzzle_20260922/tree'
RSRC_SHA = 'af67113bceb4eb906e973a9b747a0b1925b9d64c62f0f9a84bc6f0578839ca80'
CODE3 = 82 + 0x6250f                  # CODE3 CODE-relative 0 inside the fork
KSTART, KEND = 0x8a8a, 0x919c         # Fit .. end of Trial (RTS at 0x919a)
PUZZLE, TRIAL = 0x8be6, 0x90e8
KOUNT_ADDR, N_ADDR = 0x8000 - 0x2054, 0x8000 - 0x2052   # A5 globals, A5=$8000
HEAP = 0xa000                         # first block header
JUNK_END = 0xe800                     # junk-filled, oracle-checked to here
SSP = 0xf000
CONTROL_PATCH = (0x910c, bytes.fromhex('5240'), bytes.fromhex('5440'))
# ^ Trial's kount increment ADDQ.W #1,D0 -> ADDQ.W #2,D0 (same search path)
VASM = '/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot'
VERILATOR = '/home/alans/verilator5/bin/verilator'
UNITS = ('ap040_core', 'ap040_bus_timeout', 'ap040_regfile', 'ap040_alu',
         'ap040_muldiv', 'ap040_mmu', 'ap040_cache', 'ap040_fpu',
         'primitives/dpram')
MACROS = ['-DAP040_EXPERIMENTAL_' + x for x in (
    'XSTORE', 'LEA', 'PIPELINE', 'PIPELINE_LOADS', 'PIPELINE_STORES',
    'PIPELINE_PEA', 'PIPELINE_P6')] + [
    '-DAP040_PIPELINE_MEMORY_ENTRY', '-DAP040_PIPELINE_COMPARE',
    '-DAP040_PIPELINE_EARLY_DRAIN']

ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
ap.add_argument('resource', type=Path, nargs='?',
                default=Path('/home/alans/mister/MacQuadra800_fixtures/Speedometer 4.02.rsrc'))
ap.add_argument('--out', type=Path, default=r / 'scratch/fixture_puzzle_20260922/run')
ap.add_argument('--rtl-root', type=Path, default=SNAP,
                help='tree containing rtl/ (default: the HEAD snapshot); never point at a tree being edited')
ap.add_argument('--latencies', type=int, nargs='+', default=[0, 3])
ap.add_argument('--mmu', choices=('off', '4k', '8k'), default='off',
                help='real MMU with identity page tables and the shared physical RAM walker')
ap.add_argument('--profile', action='store_true',
                help='state occupancy by name, top opcodes by active clocks, latency classes')
ap.add_argument('--jobs', type=int, default=4)
ap.add_argument('--top', type=int, default=15)
args = ap.parse_args()
if any(n < 0 for n in args.latencies): ap.error('latencies must be nonnegative')
d = args.out.resolve(); d.mkdir(parents=True, exist_ok=True)
rt = args.rtl_root.resolve()
rtl = rt / 'rtl/ap68040/rtl'

resource = args.resource.read_bytes()
assert hashlib.sha256(resource).hexdigest() == RSRC_SHA, 'unexpected resource fork'
code3 = resource[CODE3:CODE3 + 0x9a00]
kernel = code3[KSTART:KEND]
assert kernel[PUZZLE - KSTART:PUZZLE - KSTART + 4] == bytes.fromhex('4e56ffcc'), 'Puzzle LINK'
assert kernel[TRIAL - KSTART:TRIAL - KSTART + 4] == bytes.fromhex('4e560000'), 'Trial LINK'
assert code3[0x4df8:0x4dfe] == bytes.fromhex('4eb900008be6'), 'doTheTests call site'
assert kernel[CONTROL_PATCH[0] - KSTART:][:2] == CONTROL_PATCH[1]
(d / 'puzzle.bin').write_bytes(kernel)

# ---------------------------------------------------------------- oracle
# Independent model of Forest Baskett's Puzzle (Stanford suite constants),
# written from the published algorithm, not from the guest code.
def oracle():
    sys.setrecursionlimit(10000)
    SIZE, TYPEMAX, D = 511, 12, 8
    puzzl = [1] * 512
    for i in range(1, 6):
        for j in range(1, 6):
            for k in range(1, 6): puzzl[i + D * (j + D * k)] = 0
    p = [[0] * 512 for _ in range(13)]
    defs = [(3,1,0,0),(1,0,3,0),(0,3,1,0),(1,3,0,0),(3,0,1,0),(0,1,3,0),
            (2,0,0,1),(0,2,0,1),(0,0,2,1),(1,1,0,2),(1,0,1,2),(0,1,1,2),(1,1,1,3)]
    cls, pmax = [], []
    for t, (a, b, c, cl) in enumerate(defs):
        for i in range(a + 1):
            for j in range(b + 1):
                for k in range(c + 1): p[t][i + D * (j + D * k)] = 1
        cls.append(cl); pmax.append(a + D * b + D * D * c)
    pc = [13, 3, 1, 1]
    st = {'kount': 0, 'depth': 0, 'maxdepth': 0}
    def fit(i, j): return all(not (p[i][k] and puzzl[j + k]) for k in range(pmax[i] + 1))
    def place(i, j):
        for k in range(pmax[i] + 1):
            if p[i][k]: puzzl[j + k] = 1
        pc[cls[i]] -= 1
        for k in range(j, SIZE + 1):
            if not puzzl[k]: return k
        return 0
    def remove(i, j):
        for k in range(pmax[i] + 1):
            if p[i][k]: puzzl[j + k] = 0
        pc[cls[i]] += 1
    def trial(j):
        st['kount'] += 1; st['depth'] += 1
        st['maxdepth'] = max(st['maxdepth'], st['depth'])
        try:
            for i in range(TYPEMAX + 1):
                if pc[cls[i]] != 0 and fit(i, j):
                    k = place(i, j)
                    if trial(k) or k == 0: return 1
                    remove(i, j)
            return 0
        finally: st['depth'] -= 1
    m = 1 + D * (1 + D * 1)
    assert fit(0, m)
    n = place(0, m)
    ok = trial(n)
    return dict(success=ok, kount=st['kount'], n=n, maxdepth=st['maxdepth'],
                piececount=pc, cls=cls, piecemax=pmax, puzzl=puzzl, p=p)

o = oracle()
assert o['success'] == 1 and o['kount'] == 2005 and all(x == 1 for x in o['puzzl'])

# Expected memory: allocation order is fixed by the guest code:
# piececount(8), class(26), piecemax(26), puzzl(0x400), p[0..12](0x400 each).
exp = {}                                  # byte address -> expected byte
def put_w(a, v): exp[a] = (v >> 8) & 255; exp[a + 1] = v & 255
def put_l(a, v): put_w(a, v >> 16); put_w(a + 2, v & 65535)
blocks = []; hp = HEAP
for size, words in [(8, o['piececount']), (26, o['cls']), (26, o['piecemax']),
                    (0x400, o['puzzl'])] + [(0x400, o['p'][i]) for i in range(13)]:
    put_l(hp, size); put_l(hp + 4, 0xa55aa55a); put_l(hp + 8, 0x5aa5a55a)
    data = hp + 12; rounded = (size + 3) & ~3
    for i in range(rounded // 2): put_w(data + 2 * i, words[i] if i < len(words) else 0)
    blocks.append(data); hp = data + rounded
put_l(hp, 0xa55aa55a)                    # trailer guard after the last block
heap_end = hp + 4
for a in range(heap_end, JUNK_END, 2): put_w(a, 0xdead)
put_w(KOUNT_ADDR - 2, 0xa55a); put_w(KOUNT_ADDR, o['kount'])
put_w(N_ADDR, o['n']); put_w(N_ADDR + 2, 0x5aa5)
assert heap_end < JUNK_END and len(blocks) == 17
mask = [0] * 32768; expected = [0] * 32768
for a in range(0, 65536, 2):
    if a in exp:
        mask[a >> 1] = 1; expected[a >> 1] = (exp[a] << 8) | exp[a + 1]
(d / 'expected.hex').write_text(''.join(f'{v:04x}\n' for v in expected))
(d / 'mask.hex').write_text(''.join(f'{v:x}\n' for v in mask))
dispose_sum = sum(blocks) & 0xffffffff

# ---------------------------------------------------------------- program
vectors = ''.join(f' dc.l {"aline" if v == 10 else "unexpected"}\n' for v in range(2, 256))
mmu_setup = ''
tables = ''
if args.mmu != 'off':
    shift = 12 if args.mmu == '4k' else 13
    mmu_setup = (' move.l #$4000,d0\n movec d0,urp\n movec d0,srp\n'
                 f' move.l #${"8000" if shift == 12 else "c000"},d0\n movec d0,tc\n')
    tables = ' org $4000\n dc.l $4203\n org $4200\n dc.l $4403\n org $4400\n' + \
        ''.join(f' dc.l ${(pg << shift) | 3:x}\n' for pg in range(65536 >> shift))
asm = f''' org 0
 dc.l ${SSP:x},start
{vectors} org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
{mmu_setup} lea ($8000).l,a5
 move.l #$d3d3d3d3,d3
 move.l #$d4d4d4d4,d4
 move.l #$d5d5d5d5,d5
 move.l #$d6d6d6d6,d6
 move.l #$d7d7d7d7,d7
 move.l #$a2a2a2a2,a2
 move.l #$a3a3a3a3,a3
 move.l #$a4a4a4a4,a4
 move.l #$a6a6a6a6,a6
 move.w #1,($f104).l
 jsr (${PUZZLE:x}).l
 move.w #1,($f106).l
 cmpi.l #$d3d3d3d3,d3
 bne unexpected
 cmpi.l #$d4d4d4d4,d4
 bne unexpected
 cmpi.l #$d5d5d5d5,d5
 bne unexpected
 cmpi.l #$d6d6d6d6,d6
 bne unexpected
 cmpi.l #$d7d7d7d7,d7
 bne unexpected
 cmpa.l #$a2a2a2a2,a2
 bne unexpected
 cmpa.l #$a3a3a3a3,a3
 bne unexpected
 cmpa.l #$a4a4a4a4,a4
 bne unexpected
 cmpa.l #$a6a6a6a6,a6
 bne unexpected
 cmpa.l #$8000,a5
 bne unexpected
 cmpa.l #${SSP:x},sp
 bne unexpected
 move.w #$600d,($f102).l
 stop #$2700
unexpected:
 move.w #$bad0,($f102).l
 stop #$2700
; A-line: _NewPtrClear (A31E) and _DisposPtr (A01F) only.  Everything but
; A0/D0 is preserved; D0 returns noErr.
aline:
 movem.l d1/a1,-(sp)
 move.l 10(sp),a1
 move.w (a1),d1
 addq.l #2,10(sp)
 cmpi.w #$a31e,d1
 beq newptr
 cmpi.w #$a01f,d1
 bne unexpected
 addq.w #1,($f10a).l
 move.l a0,d1
 add.l d1,($f10c).l
 bra alinedone
newptr:
 cmpi.l #$400,d0
 bhi unexpected
 addq.w #1,($f108).l
 move.l ($f110).l,a1
 move.l d0,(a1)+
 move.l #$a55aa55a,(a1)+
 move.l #$5aa5a55a,(a1)+
 move.l a1,a0
 addq.l #3,d0
 lsr.l #2,d0
 bra clrtest
clrloop:
 clr.l (a1)+
clrtest:
 subq.l #1,d0
 bcc clrloop
 move.l #$a55aa55a,(a1)
 move.l a1,($f110).l
alinedone:
 moveq #0,d0
 movem.l (sp)+,d1/a1
 rte
alineend:
{tables} org ${KOUNT_ADDR - 2:x}
 dc.w $a55a,$1234,$4321,$5aa5
 org ${KSTART:x}
 incbin "{d / 'puzzle.bin'}"
 org ${HEAP:x}
 rept {(JUNK_END - HEAP) // 2}
 dc.w $dead
 endr
 org $f108
 dc.w 0,0
 dc.l 0,${HEAP:x}
'''
(d / 'puzzle.s').write_text(asm)

def run(cmd, path, check=True):
    with path.open('w') as f:
        return subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT, check=check).returncode
run([VASM, '-Fbin', '-m68040', '-no-opt', '-L', d / 'puzzle.lst', '-o', d / 'program.bin', d / 'puzzle.s'], d / 'asm.log')
prog = bytearray((d / 'program.bin').read_bytes())
assert prog[KSTART:KEND] == kernel, 'kernel bytes moved'
def sym(name):
    for line in (d / 'puzzle.lst').read_text().splitlines():
        mm = re.match(r'^' + name + r'\s+A:([0-9a-fA-F]+)$', line.strip())
        if mm: return int(mm.group(1), 16)
    raise SystemExit('symbol not in listing: ' + name)
ALINE, ALINE_END = sym('aline'), sym('alineend')
def hexfile(image, path):
    path.write_text(''.join(f'{image[i]:02x}{image[i+1]:02x}\n' for i in range(0, 65536, 2)))
prog += bytes(65536 - len(prog))
hexfile(prog, d / 'program.hex')
ctl = bytearray(prog)
a, before, after = CONTROL_PATCH
assert ctl[a:a + 2] == before
ctl[a:a + 2] = after
hexfile(ctl, d / 'program_control.hex')

# ---------------------------------------------------------------- testbench
tb = r'''// Original Speedometer 4.02 Puzzle through wombat_cpu's real MMU, caches and
// store buffer.  Controlled-latency RAM responder (NOT quadra800's SDRAM
// controller): cycles compare CPU variants, they are not hardware scores.
`timescale 1ns/1ps
module tb_cpu_puzzle;
 reg clk=0; always #15 clk=~clk;
 reg nreset=0;
 wire req, wr, instr, walker_req, fault, halted, walker_we;
 wire [1:0] size;
 wire [31:0] addr, wdata, walker_addr, walker_wdat;
 reg ack=0, walker_ack=0;
 reg [31:0] rdata=0, walker_data=0;
 reg [15:0] mem[0:32767];
 reg [15:0] expected[0:32767];
 reg mask[0:32767];
 integer latency=1, mmu=0, waitleft=0, cycles=0, i, j, bytes, bad=0;
 integer win_start=-1, win_end=-1, in_win=0;
 integer walk_reads=0, walk_writes=0, handler_cycles=0;
 integer lat_count[0:2], lat_total[0:2], lat_start=-1, lat_class;
 integer region[0:7];
 reg pending=0, saved_walker=0, saved_wr;
 reg [31:0] saved_addr, saved_data;
 reg [1:0] saved_size;
 reg [1023:0] path, expath, maskpath;
 wire ram_walker = pending ? saved_walker : walker_req;
 wire ram_req = ram_walker ? walker_req : req;
 wire ram_wr = ram_walker ? walker_we : wr;
 wire [31:0] ram_addr = ram_walker ? walker_addr : addr;
 wire [31:0] ram_wdata = ram_walker ? walker_wdat : wdata;
 wire [1:0] ram_size = ram_walker ? 2'd2 : size;
 wire ram_ack = ram_walker ? walker_ack : ack;
 wire [31:0] cur_pc = dut.core.pipe_rf_owner ? dut.core.pc : dut.core.pc_i;
`ifdef PROFILE
 integer states[0:255]; integer opcycles[0:65535]; integer exits[0:65535];
 integer pipe_cycles=0, pipe_issues=0;
`endif
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
 initial begin
  if(!$value$plusargs("prog=%s",path)) $fatal(1,"missing +prog");
  if(!$value$plusargs("expected=%s",expath)) $fatal(1,"missing +expected");
  if(!$value$plusargs("mask=%s",maskpath)) $fatal(1,"missing +mask");
  if($value$plusargs("latency=%d",latency)) begin end
  if($value$plusargs("mmu=%d",mmu)) begin end
  for(i=0;i<3;i=i+1) begin lat_count[i]=0;lat_total[i]=0;end
  for(i=0;i<8;i=i+1) region[i]=0;
`ifdef PROFILE
  for(i=0;i<256;i=i+1) states[i]=0;
  for(i=0;i<65536;i=i+1) begin opcycles[i]=0; exits[i]=0; end
`endif
  $readmemh(path,mem); $readmemh(expath,expected); $readmemh(maskpath,mask);
  repeat(20) @(negedge clk);
  nreset=1;
 end
 always @(posedge clk) if(nreset) begin
  cycles=cycles+1;
  if(fault || halted || (walker_req && !mmu)) $fatal(1,"unexpected CPU fault/walker/halt pc=%h",dut.core.pc_i);
  if(cycles>200000000) $fatal(1,"timeout pc=%h",dut.core.pc_i);
  if(in_win) begin
   if(cur_pc>=@ALINE@ && cur_pc<@ALINE_END@) begin handler_cycles++; region[0]++; end
   else if(cur_pc>=32'h8a8a && cur_pc<32'h8ad8) region[1]++;   // Fit
   else if(cur_pc>=32'h8ade && cur_pc<32'h8b6a) region[2]++;   // Place
   else if(cur_pc>=32'h8b72 && cur_pc<32'h8bdc) region[3]++;   // Remove
   else if(cur_pc>=32'h8be6 && cur_pc<32'h90de) region[4]++;   // Puzzle body
   else if(cur_pc>=32'h90e8 && cur_pc<32'h919c) region[5]++;   // Trial
   else region[6]++;
`ifdef PROFILE
   states[dut.core.state]=states[dut.core.state]+1;
   if(dut.core.pipe_rf_owner) pipe_cycles++; else opcycles[dut.core.ir]++;
   if(dut.core.pipe_input && dut.core.pipe_ready) pipe_issues++;
   if(dut.core.pipe_owner && dut.core.pipe_exit_ready && !dut.core.pipe_input && dut.core.epf_ready_pc) exits[dut.core.epf_data[dut.core.epf_head]]++;
`endif
   if(dut.mem_req && lat_start<0) begin
    lat_start=cycles;lat_class=dut.mem_instr?0:(dut.mem_write?2:1);
   end
   if(dut.mem_ack && lat_start>=0) begin
    lat_count[lat_class]=lat_count[lat_class]+1;
    lat_total[lat_class]=lat_total[lat_class]+cycles-lat_start+1;
    lat_start=-1;
   end
  end
  ack<=0; walker_ack<=0;
  if(pending) begin
   if(!ram_req || ram_addr!==saved_addr || (saved_wr && ram_wdata!==saved_data) || ram_wr!==saved_wr || ram_size!==saved_size)
    $fatal(1,"request changed before ack req=%b addr=%h/%h size=%h/%h wr=%b/%b data=%h/%h",ram_req,ram_addr,saved_addr,ram_size,saved_size,ram_wr,saved_wr,ram_wdata,saved_data);
   if(waitleft>0) waitleft<=waitleft-1;
   else begin
    pending<=0;
    if(saved_walker) begin walker_ack<=1; if(saved_wr) walk_writes++; else walk_reads++; end else ack<=1;
    bytes=saved_size==0?1:(saved_size==1?2:4);
    rdata=0;
    for(j=0;j<bytes;j=j+1) begin
     if(saved_wr) writebyte(saved_addr+j,saved_data>>(8*(bytes-j-1)));
     else rdata=(rdata<<8)|readbyte(saved_addr+j);
    end
    if(saved_walker) walker_data<=rdata;
    if(!saved_walker && saved_wr && saved_addr==32'hf104) begin win_start=cycles; in_win=1; end
    if(!saved_walker && saved_wr && saved_addr==32'hf106) begin win_end=cycles; in_win=0; end
    if(!saved_walker && saved_wr && saved_addr==32'hf102) begin
     if(saved_data[15:0]!=16'h600d) $fatal(1,"ORACLE FAIL guest harness check failed (callee-saved register, A5 or SP) marker=%h",saved_data[15:0]);
     if(win_start<0 || win_end<0) $fatal(1,"ORACLE FAIL window markers missing");
     $display("ORACLE kount=%0d n=%0d allocs=%0d disposes=%0d dispose_sum=%h",mem[@KOUNT@>>1],mem[@N@>>1],mem['hf108>>1],mem['hf10a>>1],{mem['hf10c>>1],mem['hf10e>>1]});
     if(mem[@KOUNT@>>1]!==16'd@EXP_KOUNT@) $fatal(1,"ORACLE FAIL kount=%0d expected @EXP_KOUNT@",mem[@KOUNT@>>1]);
     if(mem['hf108>>1]!==17 || mem['hf10a>>1]!==17) $fatal(1,"ORACLE FAIL allocation/dispose count");
     if({mem['hf10c>>1],mem['hf10e>>1]}!==32'h@DSUM@) $fatal(1,"ORACLE FAIL disposed pointers differ from allocated ones");
     for(i=0;i<32768;i=i+1) if(mask[i] && mem[i]!==expected[i]) begin
      if(bad<8) $display("MISMATCH addr=%h actual=%h expected=%h",i*2,mem[i],expected[i]);
      bad=bad+1;
     end
     if(bad) $fatal(1,"ORACLE FAIL %0d memory words differ from the Python model",bad);
     if(mmu) begin
      if(!dut.core.tc[15] || walk_reads==0) $fatal(1,"missing real MMU walk coverage");
      $display("MMU_WALKS reads=%0d writes=%0d tc=%h",walk_reads,walk_writes,dut.core.tc);
     end
     $display("REGIONS aline_handler=%0d fit=%0d place=%0d remove=%0d puzzle_body=%0d trial=%0d other=%0d",region[0],region[1],region[2],region[3],region[4],region[5],region[6]);
`ifdef PROFILE
     for(j=0;j<256;j=j+1) if(states[j]) $display("STATE %0d cycles=%0d",j,states[j]);
     for(j=0;j<65536;j=j+1) begin
      if(opcycles[j]) $display("ACTIVE_IR opcode=%04h cycles=%0d",j[15:0],opcycles[j]);
      if(exits[j]) $display("PIPE_EXIT opcode=%04h count=%0d",j[15:0],exits[j]);
     end
     $display("PIPELINE cycles=%0d issues=%0d",pipe_cycles,pipe_issues);
`endif
     for(j=0;j<3;j=j+1) $display("LATENCY class=%0d count=%0d total=%0d",j,lat_count[j],lat_total[j]);
     $display("FIXTURE puzzle PASS cycles=%0d latency=%0d total=%0d handler=%0d kount=@EXP_KOUNT@ memory_words=%0d",win_end-win_start,latency,cycles,handler_cycles,@NWORDS@);
     $finish;
    end
   end
  end else if(ram_req && !ram_ack) begin
   saved_addr<=ram_addr;saved_data<=ram_wdata;saved_wr<=ram_wr;saved_size<=ram_size;saved_walker<=ram_walker;
   pending<=1;waitleft<=latency;
  end
 end
endmodule
'''
for k, v in {'@ALINE@': f"32'h{ALINE:x}", '@ALINE_END@': f"32'h{ALINE_END:x}",
             '@KOUNT@': f"'h{KOUNT_ADDR:x}", '@N@': f"'h{N_ADDR:x}",
             '@EXP_KOUNT@': str(o['kount']), '@DSUM@': f'{dispose_sum:08x}',
             '@NWORDS@': str(sum(mask))}.items():
    tb = tb.replace(k, v)
(d / 'tb.sv').write_text(tb)

# ---------------------------------------------------------------- build + run
sources = [d / 'tb.sv', rt / 'rtl/wombat_cpu.sv', rt / 'rtl/wombat_store_buffer.sv',
           *[rtl / (u + '.v') for u in UNITS],
           rt / 'rtl/ap68040/experimental/ap040_pipeline_integer.sv']
flags = MACROS + os.environ.get('EXTRA_FLAGS', '').split()
if args.profile: flags.append('-DPROFILE')
obj = d / ('obj_profile' if args.profile else 'obj')
core_v = rtl / 'ap040_core.v'
identity = {
    'rtl_root': str(rt),
    'rtl_commit': (rt / 'HEAD_COMMIT').read_text().strip() if (rt / 'HEAD_COMMIT').exists() else None,
    'sources': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources[1:]},
    'testbench_sha256': hashlib.sha256((d / 'tb.sv').read_bytes()).hexdigest(),
    'program_sha256': hashlib.sha256(bytes(prog)).hexdigest(),
    'resource_sha256': RSRC_SHA,
    'kernel': {'code3_range': f'{KSTART:#x}..{KEND - 1:#x}', 'sha256': hashlib.sha256(kernel).hexdigest()},
    'flags': flags, 'mmu': args.mmu, 'latencies': args.latencies,
    'scope': ('one complete Puzzle call exactly as doTheTests makes it (CODE3 0x4df8 JSR $8be6): '
              '17 _NewPtrClear, array initialization, Fit/Place and the 2005-trial recursive search, '
              '17 _DisposPtr. The Memory Manager traps are served by a harness A-line handler '
              '(bump allocator with 12-byte headers, clears each block; DisposPtr is a counting no-op); '
              'handler clocks are inside the window. Excluded: Speedometer UI, timer start/stop, '
              'the real Memory Manager and trap dispatcher, interrupts.'),
    'window': 'bus acceptance of the harness write to $f104 (before JSR) to that of $f106 (after return)',
    'oracle': {'kount': o['kount'], 'n': o['n'], 'success': o['success'], 'max_trial_depth': o['maxdepth'],
               'checked_memory_words': sum(mask),
               'what': 'Python model of the published algorithm: every word of all 17 blocks '
                       '(final puzzl, piececount, class, piecemax, p[0..12]), block headers and trailer, '
                       'junk-filled RAM to 0xe800, A5 globals kount/n with guards, 17 allocs/17 disposes '
                       'and the sum of disposed pointers, callee-saved registers, A5 and SP'},
    'negative_control': f'CODE3 {CONTROL_PATCH[0]:#x} {CONTROL_PATCH[1].hex()} -> {CONTROL_PATCH[2].hex()} '
                        '(Trial kount ADDQ.W #1 -> #2), must fail the oracle',
}
(d / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
t0 = time.time()
run([VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-BLKLOOPINIT', '-j', str(args.jobs),
     '--top-module', 'tb_cpu_puzzle', '--Mdir', obj, '-I' + str(rtl), *flags, *sources], d / 'compile.log')
print(f'BUILD seconds={time.time() - t0:.1f}', flush=True)
exe = obj / 'Vtb_cpu_puzzle'
common = ['+expected=' + str(d / 'expected.hex'), '+mask=' + str(d / 'mask.hex'),
          '+mmu=' + ('0' if args.mmu == 'off' else '1')]

names = {}
for mm in re.finditer(r"localparam\s+(S_\w+)\s*=\s*8'd(\d+)", core_v.read_text()):
    names.setdefault(int(mm.group(2)), [])
    if mm.group(1) not in names[int(mm.group(2))]: names[int(mm.group(2))].append(mm.group(1))
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_040
cs = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_040)
sites = {}
for lo, hi in ((0x8a8a, 0x8ad8), (0x8ade, 0x8b6a), (0x8b72, 0x8bdc), (0x8be6, 0x90de), (0x90e8, 0x919c), (ALINE, ALINE_END)):
    pc = lo
    while pc < hi:
        if prog[pc] == 0xa3 or prog[pc] == 0xa0:     # A-line traps
            sites.setdefault((prog[pc] << 8) | prog[pc + 1], []).append((pc, f'dc.w ${prog[pc]:02x}{prog[pc+1]:02x} (trap)'))
            pc += 2; continue
        ins = next(cs.disasm(bytes(prog[pc:hi]), pc, count=1))
        sites.setdefault((prog[pc] << 8) | prog[pc + 1], []).append((pc, f'{ins.mnemonic} {ins.op_str}'))
        pc += ins.size

results = []
for lat in args.latencies:
    log = d / f'run_latency{lat}.log'
    t0 = time.time()
    rc = run([exe, '+prog=' + str(d / 'program.hex'), f'+latency={lat}', *common], log, check=False)
    wall = time.time() - t0
    text = log.read_text()
    line = next((l for l in text.splitlines() if l.startswith('FIXTURE puzzle PASS')), None)
    if rc != 0 or line is None: raise SystemExit(f'FIXTURE puzzle FAIL latency={lat} rc={rc}\n' + text[-3000:])
    print(line, f'wall={wall:.1f}s', flush=True)
    for l in text.splitlines():
        if l.startswith(('REGIONS', 'MMU_WALKS', 'ORACLE')): print(' ', l)
    cyc = int(re.search(r' cycles=(\d+)', line).group(1))
    results.append({'latency': lat, 'cycles': cyc, 'wall_seconds': round(wall, 1), 'line': line})
    if args.profile:
        st = {int(a): int(b) for a, b in re.findall(r'^STATE (\d+) cycles=(\d+)', text, re.M)}
        tot = sum(st.values())
        print(f'  STATES (window clocks {tot}; legacy sequencer state each clock)')
        for s, c in sorted(st.items(), key=lambda x: -x[1])[:args.top]:
            print(f'    {"/".join(names.get(s, ["?"])):28s} {s:3d} {c:10d} {100 * c / tot:6.2f}%')
        ops = {int(a, 16): int(b) for a, b in re.findall(r'^ACTIVE_IR opcode=([0-9a-f]+) cycles=(\d+)', text, re.M)}
        pipe = re.search(r'^PIPELINE cycles=(\d+) issues=(\d+)', text, re.M)
        print(f'  TOP OPCODES by legacy-owned clocks (dut.core.ir; pipeline-owned clocks={pipe.group(1)}, issues={pipe.group(2)})')
        for op, c in sorted(ops.items(), key=lambda x: -x[1])[:args.top]:
            where = sites.get(op, [])
            desc = where[0][1] if where else '(not in kernel/handler)'
            at = ','.join(f'{a:x}' for a, _ in where[:4]) + (',...' if len(where) > 4 else '')
            print(f'    {op:04x} {c:10d} {100 * c / tot:6.2f}%  {desc:34s} @{at}')
        for cl, n, t in re.findall(r'^LATENCY class=(\d) count=(\d+) total=(\d+)', text, re.M):
            n, t = int(n), int(t)
            print(f'  LATENCY {("fetch", "read", "write")[int(cl)]:5s} count={n} total={t} mean={t / max(n, 1):.2f}')

# Required negative control: must fail the oracle, and for the oracle reason.
lat = args.latencies[0]
log = d / 'control.log'
rc = run([exe, '+prog=' + str(d / 'program_control.hex'), f'+latency={lat}', *common], log, check=False)
text = log.read_text()
if rc != 0 and 'ORACLE FAIL kount=4010' in text and 'FIXTURE puzzle PASS' not in text:
    print(f'CONTROL puzzle FAILED-AS-REQUIRED (kount ADDQ #1->#2 at {CONTROL_PATCH[0]:#x}: oracle reported kount=4010)')
else:
    raise SystemExit('CONTROL puzzle DID NOT FAIL AS REQUIRED rc=%d\n%s' % (rc, text[-2000:]))
(d / 'results.json').write_text(json.dumps({'runs': results, 'control': 'failed as required'}, indent=2) + '\n')
