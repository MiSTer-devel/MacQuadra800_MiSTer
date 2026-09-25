#!/usr/bin/env python3
"""Speedometer 4.02 Towers (Towers of Hanoi) through wombat_cpu; not a hardware score.

Runs the UNCHANGED original CODE3 bytes 0x95f0..0x9887 (MakeNull, Getelement,
Push, Init, Pop, MoveThem, Tower, Towers and their MacsBug names) at their
original CODE-relative addresses.  The harness calls Towers (CODE3+0x9818)
exactly as Speedometer's test dispatcher does (CODE3+0x4dd0 `jsr $9818.l`), so
the scope is the whole timed Towers work: three passes of {free list of 18
cells, Init(peg 1, 14 discs), MakeNull(2), MakeNull(3), movesdone:=0,
Tower(1,2,14)} = 3 x 16,383 moves.  Excluded: the dispatcher's jump table,
Speedometer's timer/Ticks bracketing and UI.

The CPU is wombat_cpu (real AP68040 core, MMU, caches, store buffer, pipeline)
from an RTL SNAPSHOT (--rtl-root), never the live rtl/.  RAM is a 64 KB
controlled-latency responder that fatals if a request changes before its ack;
it is NOT quadra800's SDRAM path, so cycles compare CPU variants only.

Oracle (independent, Python): an executable model of the Stanford Towers
Pascal semantics over a copy of the initial memory image predicts the final
64 KB image byte for byte (A5 globals poisoned with $DEAD before the call so
every write is visible); the only unchecked window is the stack below $E000.
The caller also checks SP, A5 and the callee-saved registers after return, and
the testbench counts bus writes to movesdone (3 x (16,383 + 1 clear)).
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, sys, time

REPO = Path(__file__).resolve().parents[2]
RESOURCE_SHA = 'af67113bceb4eb906e973a9b747a0b1925b9d64c62f0f9a84bc6f0578839ca80'
CODE3 = 0x62561                  # file offset of CODE 3's resource data (byte 0)
LO, HI, ENTRY = 0x95f0, 0x9888, 0x9818
A5, SP0 = 0x8000, 0xe000
STACK_LO = 0xdc00                # unchecked stack window [STACK_LO, SP0); run uses $dd91..$dfff
POISON = 0xdead
GLOB_LO, GLOB_HI = 0x5fb4, 0x6012  # poisoned A5-global window (incl. guards)
DONE = 0xf102
VASM = '/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot'
VERILATOR = os.environ.get('VERILATOR', '/home/alans/verilator5/bin/verilator')
FLAGS = ['-DAP040_EXPERIMENTAL_' + x for x in
         ('XSTORE', 'LEA', 'PIPELINE', 'PIPELINE_LOADS', 'PIPELINE_STORES',
          'PIPELINE_PEA', 'PIPELINE_P6')] + \
        ['-DAP040_PIPELINE_MEMORY_ENTRY', '-DAP040_PIPELINE_COMPARE',
         '-DAP040_PIPELINE_EARLY_DRAIN']
UNITS = ('ap040_core', 'ap040_bus_timeout', 'ap040_regfile', 'ap040_alu',
         'ap040_muldiv', 'ap040_mmu', 'ap040_cache', 'ap040_fpu',
         'primitives/dpram')
# Negative controls: (CODE3 address, original word, mutated word, meaning)
NEGATIVE = {
    'input': (0x9868, 0x000e, 0x000d, 'Towers calls Tower(1,2,13) instead of Tower(1,2,14) (move.w #$e,-(a7) -> #$d at 0x9866)'),
    'instr': (0x979a, 0x5240, 0x5440, 'MoveThem counts +2 per move (addq.w #1,d0 -> addq.w #2,d0)'),
}
SCOPE = ('unchanged CODE3 0x95f0..0x9887; one call of Towers (0x9818) as the '
         'Speedometer dispatcher (CODE3 0x4dd0) makes it: 3 passes x 14 discs '
         '= 49,149 moves; excludes dispatcher, timer bracketing and UI')

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument('resource', type=Path)
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--rtl-root', type=Path,
                default=REPO / 'scratch/fixture_towers_20260922/tree/rtl',
                help='RTL snapshot root (git archive HEAD rtl | tar -x); never the live rtl/')
ap.add_argument('--latencies', type=int, nargs='+', default=[0, 3])
ap.add_argument('--profile', action='store_true',
                help='state occupancy by name, top opcodes, latency classes')
ap.add_argument('--negative-control', action='store_true',
                help='also run the mutated copies; each must FAIL the oracle')
ap.add_argument('--jobs', type=int, default=4, help='verilator -j (max 4 here)')
ap.add_argument('--top', type=int, default=25)
args = ap.parse_args()

out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
rtl = args.rtl_root.resolve()
if rtl == (REPO / 'rtl').resolve():
    sys.exit('refusing the live rtl/: pass a snapshot (git archive HEAD rtl | tar -x -C <dir>)')
resource = args.resource.read_bytes()
assert hashlib.sha256(resource).hexdigest() == RESOURCE_SHA, 'unexpected Speedometer resource fork'
assert resource[CODE3 - 4:CODE3] == (0x993c).to_bytes(4, 'big'), 'CODE 3 length word'
kernel = resource[CODE3 + LO:CODE3 + HI]
assert kernel[ENTRY - LO:ENTRY - LO + 4] == bytes.fromhex('4e560000'), 'Towers entry'
# The dispatcher's call, proving the entry and that one call is the timed unit.
assert resource[CODE3 + 0x4dd0:CODE3 + 0x4dd6] == bytes.fromhex('4eb900009818')
(out / 'towers.bin').write_bytes(kernel)


def run(cmd, log, check=True):
    with open(log, 'w') as f:
        return subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT, check=check)


# ----------------------------------------------------------------- program
def build_program(tag, kern):
    kb = out / f'towers_{tag}.bin'; kb.write_bytes(kern)
    asm = f''' org 0
 dc.l ${SP0:x},start
 rept 254
 dc.l unexpected
 endr
 org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
 lea (${A5:x}).l,a5
 move.l #$d3d3d3d3,d3
 move.l #$d4d4d4d4,d4
 move.l #$d5d5d5d5,d5
 move.l #$d6d6d6d6,d6
 move.l #$d7d7d7d7,d7
 move.l #$a2a2a2a2,a2
 move.l #$a3a3a3a3,a3
 move.l #$a4a4a4a4,a4
 jsr (${ENTRY:x}).l
 cmpa.l #${SP0:x},sp
 bne fail
 cmpa.l #${A5:x},a5
 bne fail
 cmpi.l #$d3d3d3d3,d3
 bne fail
 cmpi.l #$d4d4d4d4,d4
 bne fail
 cmpi.l #$d5d5d5d5,d5
 bne fail
 cmpi.l #$d6d6d6d6,d6
 bne fail
 cmpi.l #$d7d7d7d7,d7
 bne fail
 cmpa.l #$a2a2a2a2,a2
 bne fail
 cmpa.l #$a3a3a3a3,a3
 bne fail
 cmpa.l #$a4a4a4a4,a4
 bne fail
 move.w #$600d,(${DONE:x}).l
 stop #$2700
fail:
 move.w #$0001,($f100).l
 move.w #$bad0,(${DONE:x}).l
 stop #$2700
unexpected:
 move.w #$0002,($f100).l
 move.w #$bad0,(${DONE:x}).l
 stop #$2700
 org ${GLOB_LO:x}
 rept {(GLOB_HI - GLOB_LO) // 2}
 dc.w ${POISON:x}
 endr
 org ${LO:x}
 incbin "{kb}"
'''
    (out / f'towers_{tag}.s').write_text(asm)
    pb = out / f'program_{tag}.bin'
    run([VASM, '-Fbin', '-m68040', '-no-opt', '-o', pb, out / f'towers_{tag}.s'], out / f'asm_{tag}.log')
    img = bytearray(pb.read_bytes())
    assert bytes(img[LO:HI]) == kern, 'kernel not at its original address'
    assert len(img) <= 0x10000
    img += bytes(0x10000 - len(img))
    with open(out / f'program_{tag}.hex', 'w') as f:
        for i in range(0, 0x10000, 2):
            f.write('%02x%02x\n' % (img[i], img[i + 1]))
    return img


# ------------------------------------------------------------------ oracle
def oracle(initial):
    """Stanford Towers (Pascal) semantics on a copy of the memory image."""
    m = bytearray(initial)
    rd = lambda a: int.from_bytes(m[a:a + 2], 'big')
    def wr(a, v): m[a:a + 2] = (v & 0xffff).to_bytes(2, 'big')
    cell = lambda n: A5 - 0x2046 + 4 * n     # discsize at +0, next at +2
    stack = lambda s: A5 - 0x1ffa + 2 * s
    FREE, MOVES = A5 - 0x2048, A5 - 0x204a
    sw = lambda v: v - 0x10000 if v & 0x8000 else v
    moves_writes = [0]
    def getelement():
        assert sw(rd(FREE)) > 0, 'free list empty'
        t = rd(FREE); wr(FREE, rd(cell(t) + 2)); return t
    def push(i, s):
        if sw(rd(stack(s))) > 0 and i >= sw(rd(cell(rd(stack(s))))):
            raise AssertionError('disc size error')
        e = getelement(); wr(cell(e) + 2, rd(stack(s))); wr(stack(s), e); wr(cell(e), i)
    def pop(s):
        top = rd(stack(s))
        assert sw(top) > 0, 'nothing to pop'
        t = rd(cell(top)); t1 = rd(cell(top) + 2)
        wr(cell(top) + 2, rd(FREE)); wr(FREE, top); wr(stack(s), t1); return t
    def move(s1, s2):
        push(pop(s1), s2); wr(MOVES, rd(MOVES) + 1); moves_writes[0] += 1
    def tower(i, j, k):
        if k == 1: move(i, j); return
        o = 6 - i - j; tower(i, o, k - 1); move(i, j); tower(o, j, k - 1)
    passes = []
    for _ in range(3):
        for i in range(1, 19): wr(cell(i) + 2, i - 1)
        wr(FREE, 18)
        wr(stack(1), 0)
        for d in range(14, 0, -1): push(d, 1)
        wr(stack(2), 0); wr(stack(3), 0)
        wr(MOVES, 0); moves_writes[0] += 1
        tower(1, 2, 14)
        passes.append(rd(MOVES))
    # Independent end-state facts (not derived from the model's memory writes).
    assert passes == [2 ** 14 - 1] * 3, passes
    wr(DONE, 0x600d)
    return m, {'passes': passes, 'moves_total': sum(passes), 'moves_bus_writes': moves_writes[0]}


def check(initial, dump, moves_writes, expect_writes):
    exp, info = oracle(initial)
    bad = [a for a in range(0, 0x10000) if not (STACK_LO <= a < SP0) and dump[a] != exp[a]]
    errs = []
    if bad:
        errs.append('%d bytes differ, first %s' % (len(bad), ', '.join(
            '%04x:%02x/%02x' % (a, dump[a], exp[a]) for a in bad[:8])))
    # Peg 2 must hold discs 1..14 top-down, pegs 1 and 3 empty, 4 cells free.
    rd = lambda a: int.from_bytes(dump[a:a + 2], 'big')
    node, seen, discs = rd(A5 - 0x1ffa + 4), set(), []
    while node and len(discs) < 20:
        seen.add(node); discs.append(rd(A5 - 0x2046 + 4 * node)); node = rd(A5 - 0x2046 + 4 * node + 2)
    if discs != list(range(1, 15)): errs.append('peg 2 holds %s' % discs)
    if rd(A5 - 0x1ffa + 2) or rd(A5 - 0x1ffa + 6): errs.append('peg 1/3 not empty')
    if rd(A5 - 0x204a) != 16383: errs.append('movesdone=%d' % rd(A5 - 0x204a))
    if moves_writes != expect_writes: errs.append('movesdone bus writes %d != %d' % (moves_writes, expect_writes))
    return errs, info


# -------------------------------------------------------------- testbench
TB = r'''// Speedometer 4.02 Towers (unchanged CODE3 bytes) through wombat_cpu's real
// MMU/cache/store buffer/pipeline.  Controlled-latency RAM responder, NOT
// quadra800's SDRAM controller: cycles compare CPU variants, not Mix scores.
`timescale 1ns/1ps
module tb_cpu_towers;
 reg clk=0; always #15 clk=~clk;
 reg nreset=0;
 wire req, wr, instr, walker_req, fault, halted;
 wire [1:0] size;
 wire [31:0] addr, wdata;
 reg ack=0;
 reg [31:0] rdata=0;
 reg [7:0] mem[0:65535];
 integer latency=1, waitleft=0, i, j, bytes;
 longint cycles=0;
 longint states[0:255];
 longint lat_count[0:2], lat_total[0:2], lat_start=-1; integer lat_class;
 longint moves_writes=0;
 reg pending=0;
 reg [31:0] saved_addr, saved_data;
 reg [1:0] saved_size;
 reg saved_wr;
 reg [1023:0] path, dumppath;
 //PROFILE_DECL
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
 initial begin
  if(!$value$plusargs("prog=%s",path)) $fatal(1,"missing +prog");
  if(!$value$plusargs("dump=%s",dumppath)) $fatal(1,"missing +dump");
  if($value$plusargs("latency=%d",latency)) begin end
  for(i=0;i<256;i=i+1) states[i]=0;
  for(i=0;i<3;i=i+1) begin lat_count[i]=0;lat_total[i]=0;end
  //PROFILE_INIT
  begin : load
   reg [15:0] w[0:32767];
   $readmemh(path,w);
   for(i=0;i<32768;i=i+1) begin mem[2*i]=w[i][15:8]; mem[2*i+1]=w[i][7:0]; end
  end
  repeat(20) @(negedge clk);
  nreset=1;
 end
 always @(posedge clk) if(nreset) begin
  //PROFILE_CYCLE
  cycles=cycles+1; states[dut.core.state]=states[dut.core.state]+1;
  if(walker_req || fault || halted) $fatal(1,"unexpected CPU fault/walker/halt pc=%h",dut.core.pc_i);
  if(cycles>200000000) $fatal(1,"timeout pc=%h",dut.core.pc_i);
  if(dut.mem_req && lat_start<0) begin
   lat_start=cycles;lat_class=dut.mem_instr?0:(dut.mem_write?2:1);
  end
  if(dut.mem_ack && lat_start>=0) begin
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
    if(saved_addr>32'hffff || saved_addr+bytes>32'h10000) $fatal(1,"RAM access out of range %h",saved_addr);
    rdata=0;
    for(j=0;j<bytes;j=j+1) begin
     if(saved_wr) mem[saved_addr+j]=8'(saved_data>>(8*(bytes-j-1)));
     else rdata=(rdata<<8)|mem[saved_addr+j];
    end
    if(saved_wr && saved_addr==32'h5fb6 && saved_size==2'd1) moves_writes=moves_writes+1;
    if(saved_wr && saved_addr==32'hf102) begin
     $writememh(dumppath,mem);
     $display("DONE word=%04h reason=%04h cycles=%0d latency=%0d moves_writes=%0d",saved_data[15:0],{mem['hf100],mem['hf101]},cycles,latency,moves_writes);
     for(j=0;j<256;j=j+1) if(states[j]!=0) $display("STATE %0d cycles=%0d",j,states[j]);
     for(j=0;j<3;j=j+1) $display("LATENCY class=%0d count=%0d total=%0d",j,lat_count[j],lat_total[j]);
     //PROFILE_REPORT
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
PROFILE = {
    '//PROFILE_DECL': 'longint opcycles[0:65535]; longint pipe_cycles=0, pipe_issues=0;',
    '//PROFILE_INIT': 'for(i=0;i<65536;i=i+1) opcycles[i]=0;',
    '//PROFILE_CYCLE': 'if(dut.core.pipe_rf_owner) pipe_cycles=pipe_cycles+1; else opcycles[dut.core.ir]=opcycles[dut.core.ir]+1;\n'
                       '  if(dut.core.pipe_input && dut.core.pipe_ready) pipe_issues=pipe_issues+1;',
    '//PROFILE_REPORT': 'for(j=0;j<65536;j=j+1) if(opcycles[j]!=0) $display("ACTIVE_IR opcode=%04h cycles=%0d",j[15:0],opcycles[j]);\n'
                        '     $display("PIPELINE cycles=%0d issues=%0d",pipe_cycles,pipe_issues);',
}


def build_tb(profile):
    tag = 'profile' if profile else 'plain'
    s = TB
    if profile:
        for k, v in PROFILE.items(): s = s.replace(k, v)
    tbp = out / f'tb_{tag}.sv'; tbp.write_text(s)
    sources = [tbp, rtl / 'wombat_cpu.sv', rtl / 'wombat_store_buffer.sv',
               *[rtl / 'ap68040/rtl' / (u + '.v') for u in UNITS],
               rtl / 'ap68040/experimental/ap040_pipeline_integer.sv']
    for p in sources: assert p.exists(), p
    flags = FLAGS + os.environ.get('EXTRA_FLAGS', '').split()
    t = time.time()
    run([VERILATOR, '--binary', '--timing', '-O3', '-Wno-fatal', '-Wno-BLKLOOPINIT',
         '-j', str(min(args.jobs, 4)), '--top-module', 'tb_cpu_towers',
         '--Mdir', out / f'obj_{tag}', '-I' + str(rtl / 'ap68040/rtl'), *flags, *sources],
        out / f'compile_{tag}.log')
    print(f'built {tag} in {time.time() - t:.0f}s', flush=True)
    return out / f'obj_{tag}/Vtb_cpu_towers', sources, flags


def simulate(binary, tag, latency):
    log = out / f'run_{tag}_lat{latency}.log'; dump = out / f'dump_{tag}_lat{latency}.hex'
    t = time.time()
    run([binary, f'+prog={out / f"program_{tag}.hex"}', f'+dump={dump}', f'+latency={latency}'], log, check=False)
    wall = time.time() - t
    text = log.read_text()
    m = re.search(r'^DONE word=(\w+) reason=(\w+) cycles=(\d+) latency=(\d+) moves_writes=(\d+)', text, re.M)
    if not m: return None, text, wall
    mem = bytearray(0x10000); a = 0
    for tok in dump.read_text().split():
        if tok.startswith('@'): a = int(tok[1:], 16); continue
        mem[a] = int(tok, 16); a += 1
    return {'word': m[1], 'reason': m[2], 'cycles': int(m[3]), 'moves_writes': int(m[5]),
            'mem': mem, 'text': text}, text, wall


results = {}
img = build_program('orig', kernel)
_, oinfo = oracle(img)
EXPECT_WRITES = oinfo['moves_bus_writes']   # 3 x (16,383 moves + 1 clear)
binary, sources, flags = build_tb(False)
ok = True
for lat in args.latencies:
    r, text, wall = simulate(binary, 'orig', lat)
    if r is None or r['word'] != '600d':
        print(f'FIXTURE towers FAIL latency={lat} (no completion or guest check failed)\n' + text[-1500:]); ok = False; continue
    errs, info = check(img, r['mem'], r['moves_writes'], EXPECT_WRITES)
    status = 'PASS' if not errs else 'FAIL'
    ok &= not errs
    print(f'FIXTURE towers {status} cycles={r["cycles"]} latency={lat} moves={info["moves_total"]} '
          f'movesdone_writes={r["moves_writes"]} wall={wall:.1f}s' + ('' if not errs else ' :: ' + '; '.join(errs)), flush=True)
    results[f'lat{lat}'] = {'status': status, 'cycles': r['cycles'], 'wall_s': round(wall, 1),
                            'moves_writes': r['moves_writes'], 'errors': errs}

neg = {}
if args.negative_control:
    for name, (addr, old, new, what) in NEGATIVE.items():
        k = bytearray(kernel)
        assert int.from_bytes(k[addr - LO:addr - LO + 2], 'big') == old
        k[addr - LO:addr - LO + 2] = new.to_bytes(2, 'big')
        nimg = build_program('neg_' + name, bytes(k))
        lat = args.latencies[0]
        r, text, wall = simulate(binary, 'neg_' + name, lat)
        # The oracle is always the unmutated specification with the original image.
        if r is None or r['word'] != '600d':
            errs = ['did not complete cleanly']
        else:
            errs, _ = check(img, r['mem'], r['moves_writes'], EXPECT_WRITES)
            errs = errs or []
        failed = bool(errs)
        ok &= failed
        print(f'NEGATIVE {name} ({what}): oracle {"FAILED as required" if failed else "PASSED -- CONTROL BROKEN"}'
              + (' :: ' + '; '.join(errs)[:300] if errs else ''), flush=True)
        neg[name] = {'mutation': f'CODE3+0x{addr:04x} {old:04x}->{new:04x}', 'meaning': what,
                     'oracle_failed': failed, 'errors': errs[:5]}

prof = {}
if args.profile and ok:
    pbin, psources, _ = build_tb(True)
    core = (rtl / 'ap68040/rtl/ap040_core.v').read_text()
    names = {}
    for n, v in re.findall(r"localparam\s+(S_\w+)\s*=\s*8'd(\d+)", core):
        names.setdefault(int(v), []);
        if n not in names[int(v)]: names[int(v)].append(n)
    try:
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_040)
    except Exception:
        md = None
    def describe(op):
        if md is None: return ''
        for a in range(0, len(kernel) - 1, 2):
            if int.from_bytes(kernel[a:a + 2], 'big') == op:
                for ins in md.disasm(kernel[a:a + 10], LO + a):
                    return f'{ins.mnemonic} {ins.op_str}  (e.g. 0x{LO + a:04x})'
        return '(harness)'
    for lat in args.latencies:
        r, text, wall = simulate(pbin, 'orig', lat)
        assert r and r['word'] == '600d', text[-1500:]
        errs, _ = check(img, r['mem'], r['moves_writes'], EXPECT_WRITES)
        assert not errs, errs
        cyc = r['cycles']
        lines = [f'PROFILE latency={lat} cycles={cyc} (profile build, wall {wall:.1f}s)']
        st = sorted(((int(c), int(s)) for s, c in re.findall(r'^STATE (\d+) cycles=(\d+)', text, re.M)), reverse=True)
        lines.append('-- sequencer state occupancy (dut.core.state) --')
        for c, s in st[:args.top]:
            lines.append(f'  {"/".join(names.get(s, ["?"])):28s} {s:3d} {c:10d} {100 * c / cyc:6.2f}%')
        ops = sorted(((int(c), int(o, 16)) for o, c in re.findall(r'^ACTIVE_IR opcode=(\w+) cycles=(\d+)', text, re.M)), reverse=True)
        pm = re.search(r'^PIPELINE cycles=(\d+) issues=(\d+)', text, re.M)
        lines.append(f'-- clocks by legacy IR (pipeline-owned clocks counted separately: {pm[1]} = '
                     f'{100 * int(pm[1]) / cyc:.2f}%, {pm[2]} pipeline issues) --')
        for c, o in ops[:args.top]:
            lines.append(f'  {o:04x} {c:10d} {100 * c / cyc:6.2f}%  {describe(o)}')
        lines.append('-- bus latency classes (request to ack, inclusive) --')
        for cls, n, tot in re.findall(r'^LATENCY class=(\d) count=(\d+) total=(\d+)', text, re.M):
            n, tot = int(n), int(tot)
            lines.append(f'  {("fetch", "read", "write")[int(cls)]:5s} count={n:9d} clocks={tot:10d} '
                         f'avg={tot / max(n, 1):.2f} share={100 * tot / cyc:.2f}%')
        rep = '\n'.join(lines); print(rep, flush=True)
        (out / f'profile_lat{lat}.txt').write_text(rep + '\n')
        prof[f'lat{lat}'] = {'cycles': cyc, 'report': f'profile_lat{lat}.txt'}

commit = (rtl.parent / 'HEAD_COMMIT').read_text().strip() if (rtl.parent / 'HEAD_COMMIT').exists() else None
(out / 'identity.json').write_text(json.dumps({
    'fixture': 'towers', 'scope': SCOPE, 'rtl_root': str(rtl), 'rtl_snapshot_commit': commit,
    'resource_sha256': RESOURCE_SHA, 'kernel_region': f'CODE3[0x{LO:04x}:0x{HI:04x}]', 'entry': f'0x{ENTRY:04x}',
    'kernel_sha256': hashlib.sha256(kernel).hexdigest(),
    'program_sha256': hashlib.sha256((out / 'program_orig.bin').read_bytes()).hexdigest(),
    'caller': f'A5=${A5:x}, SP=${SP0:x}, CACR=$80008000, SR=$2700, MMU off, A5 globals ${GLOB_LO:x}..${GLOB_HI - 1:x} poisoned ${POISON:x}',
    'oracle': 'Python Stanford-Towers model predicts the full 64 KB image except the stack window '
              f'${STACK_LO:x}..${SP0 - 1:x}; peg-2 order 1..14, pegs 1/3 empty; movesdone bus writes {EXPECT_WRITES}; '
              'caller checks SP/A5/D3-D7/A2-A4',
    'verilator_flags': flags, 'sources': {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
    'results': results, 'negative_controls': neg, 'profile': prof,
}, indent=2))
sys.exit(0 if ok else 1)
