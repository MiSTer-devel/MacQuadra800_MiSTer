#!/usr/bin/env python3
"""Shared runner for the v2 Speedometer 4.02 extracted-kernel CPU fixtures.

Used by profile_sieve_v2.py and profile_bubble_v2.py.  Revives the
2026-09-20 fixtures (profile_quick.py --kernel sieve, profile_bubble.py) on
the current CPU RTL:

- RTL comes from --rtl-root (a `git archive HEAD rtl` snapshot), never the
  live rtl/ by default, so another session's edits cannot leak in.
- Macros are the production .qsf's CPU set (plus EXTRA_FLAGS from the env);
  the wrapper keeps its defaults (FPU, cache, store buffer on) and the guest
  enables both caches through CACR, as before.
- Kernel bytes, scope, independent oracle and guards are the originals'.
- A required negative control patches one instruction in a disposable copy
  of the program image; the oracle must reject it.
- --profile compiles passive counters in and names sequencer states from the
  snapshot's ap040_core.v localparams.

The RAM responder is a controlled-latency model, NOT quadra800's SDRAM path;
cycles compare CPU variants, they are not hardware Speedometer scores.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, sys, time

REPO = Path(__file__).resolve().parents[2]
RESOURCE_SHA = 'af67113bceb4eb906e973a9b747a0b1925b9d64c62f0f9a84bc6f0578839ca80'
CODE_BASE = 82 + 0x6250f            # CODE3 offset inside the resource fork
VASM = '/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot'
VERILATOR = '/home/alans/verilator5/bin/verilator'
DEFAULT_RESOURCE = '/home/alans/mister/MacQuadra800_fixtures/Speedometer 4.02.rsrc'
DEFAULT_RTL_ROOT = REPO / 'scratch/fixture_sieve_bubble_20260922/tree'
PRODUCTION_FLAGS = ['-DAP040_EXPERIMENTAL_' + x for x in (
    'XSTORE', 'LEA', 'PIPELINE', 'PIPELINE_LOADS', 'PIPELINE_STORES',
    'PIPELINE_PEA', 'PIPELINE_P6')] + [
    '-DAP040_PIPELINE_MEMORY_ENTRY', '-DAP040_PIPELINE_COMPARE',
    '-DAP040_PIPELINE_EARLY_DRAIN']
UNITS = ('ap040_core', 'ap040_bus_timeout', 'ap040_regfile', 'ap040_alu',
         'ap040_muldiv', 'ap040_mmu', 'ap040_cache', 'ap040_fpu',
         'primitives/dpram')

# Responder, fault/timeout guards and latency classes are the 2026-09-20
# harness verbatim; @ORACLE@ is replaced by the kernel's result check.
TB = r'''// Original Speedometer kernel through wombat_cpu's real MMU/cache/store
// buffer. The RAM responder is a controlled-latency model, NOT quadra800's
// SDRAM controller; these cycles are not hardware Mix scores.
`timescale 1ns/1ps
module tb_cpu_fixture;
 reg clk=0; always #15 clk=~clk;
 reg nreset=0;
 wire req, wr, instr, walker_req, fault, halted;
 wire [1:0] size;
 wire [31:0] addr, wdata;
 reg ack=0;
 reg [31:0] rdata=0;
 reg [15:0] mem[0:32767];
 @DECLS@
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
 reg [1023:0] oracle_path;
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
  @INIT@
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
@ORACLE@
     $display("BUFFER_UPPER_BOUND hits=%0d saved_cycles=%0d",buffer_hits,buffer_saving);
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


def add_profile(s):
    """profile_quick.py's --profile counters, passive.  The profiler's own
    consistency checks print PROFILE_WARN instead of $fatal: a stale counter
    must not fail a run whose oracle passed."""
    s = s.replace('integer states[0:255];', '''integer states[0:255];
 integer opcycles[0:65535], ircycles[0:65535], exits[0:65535], regs_cycles[0:65535], admission_denied[0:65535];
 integer pipe_cycles=0,pipe_issues=0;
 integer fetch_empty=0,decode_ext_wait=0,pipe_ready_empty=0,data_prefetch_wait=0,data_setup=0,data_ack_wait=0,regs_queue_ready=0,regs_queue_empty=0;
 integer pr_count[0:32767],pr_cycles[0:32767],pr_max[0:32767];
 integer pr_retired[0:32767],pr_retire_gap[0:32767],pr_ack_cycle[0:32767];
 integer pr_prefetch[0:32767],pr_setup[0:32767],pr_wait[0:32767],pr_other[0:32767];
 integer pr_hint_miss[0:32767],pr_cache_busy[0:32767],pr_array_wait[0:32767],pr_tag_miss[0:32767];
 integer pr_start=-1,pr_pc=0,pr_index=0,pr_elapsed=0,profile_warn=0;''')
    s = s.replace('for(i=0;i<256;i=i+1) states[i]=0;', '''for(i=0;i<256;i=i+1) states[i]=0;
  for(i=0;i<65536;i=i+1) begin opcycles[i]=0;ircycles[i]=0;exits[i]=0;regs_cycles[i]=0;admission_denied[i]=0;end
  for(i=0;i<32768;i=i+1) begin
   pr_count[i]=0;pr_cycles[i]=0;pr_max[i]=0;pr_retired[i]=0;
   pr_retire_gap[i]=0;pr_ack_cycle[i]=-1;
   pr_prefetch[i]=0;pr_setup[i]=0;pr_wait[i]=0;pr_other[i]=0;
   pr_hint_miss[i]=0;pr_cache_busy[i]=0;pr_array_wait[i]=0;pr_tag_miss[i]=0;
  end''')
    s = s.replace('cycles=cycles+1; states[dut.core.state]', '''if(dut.core.state==dut.core.S_FETCH && !dut.core.epf_ready_pc) fetch_empty++;
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
  ircycles[dut.core.ir]++;
  if(dut.core.pipe_rf_owner) pipe_cycles++; else opcycles[dut.core.ir]++;
  if(dut.core.pipe_input && dut.core.pipe_ready) pipe_issues++;
  if(dut.core.pipe_owner && dut.core.pipe_exit_ready && !dut.core.pipe_input && dut.core.epf_ready_pc) exits[dut.core.epf_data[dut.core.epf_head]]++;
  if(pr_start>=0 && !dut.core.pipe_load_ack) begin
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
   if(pr_start>=0) profile_warn++;
   pr_start=cycles;pr_pc=dut.core.pipe_load_pc;
   if(pr_pc>=65536) begin profile_warn++; pr_pc=0; end
  end
  cycles=cycles+1; states[dut.core.state]''')
    s = s.replace('     $display("BUFFER_UPPER_BOUND', '''     for(j=0;j<65536;j=j+1) begin
      if(regs_cycles[j]) $display("REGS_IR opcode=%04h cycles=%0d",j[15:0],regs_cycles[j]);
      if(admission_denied[j]) $display("ENTRY_DENIED opcode=%04h cycles=%0d",j[15:0],admission_denied[j]);
      if(opcycles[j]) $display("ACTIVE_IR opcode=%04h cycles=%0d",j[15:0],opcycles[j]);
      if(ircycles[j]) $display("IR_ALL opcode=%04h cycles=%0d",j[15:0],ircycles[j]);
      if(exits[j]) $display("PIPE_EXIT opcode=%04h count=%0d",j[15:0],exits[j]);
     end
     $display("PIPELINE cycles=%0d issues=%0d",pipe_cycles,pipe_issues);
     $display("FETCH_PROFILE empty=%0d decode_extension_wait=%0d pipe_ready_empty=%0d data_prefetch_wait=%0d data_setup=%0d data_ack_wait=%0d regs_queue_ready=%0d regs_queue_empty=%0d",fetch_empty,decode_ext_wait,pipe_ready_empty,data_prefetch_wait,data_setup,data_ack_wait,regs_queue_ready,regs_queue_empty);
     for(j=0;j<32768;j=j+1) if(pr_count[j]) begin
      if(pr_count[j]!=pr_retired[j]) profile_warn++;
      if(pr_cycles[j] != pr_count[j]+pr_prefetch[j]+pr_setup[j]+pr_wait[j]+pr_other[j]) profile_warn++;
      $display("PIPE_READ pc=%04h reads=%0d response_cycles=%0d max_response=%0d retire_gap_cycles=%0d prefetch_wait=%0d setup=%0d ack_wait=%0d other=%0d",j*2,pr_count[j],pr_cycles[j],pr_max[j],pr_retire_gap[j],pr_prefetch[j],pr_setup[j],pr_wait[j],pr_other[j]);
      $display("PIPE_READ_BLOCKERS pc=%04h hint_mismatch=%0d cache_not_accepting=%0d array_unready=%0d tag_miss=%0d",j*2,pr_hint_miss[j],pr_cache_busy[j],pr_array_wait[j],pr_tag_miss[j]);
     end
     if(profile_warn) $display("PROFILE_WARN count=%0d (pipeline-read attribution inconsistent; oracle unaffected)",profile_warn);
     $display("BUFFER_UPPER_BOUND''')
    return s


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, log, check=True):
    with Path(log).open('w') as f:
        return subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT, check=check).returncode


def state_names(core_v):
    names = {}
    for m in re.finditer(r"localparam\s+(S_\w+)\s*=\s*8'd(\d+)", Path(core_v).read_text()):
        names.setdefault(int(m.group(2)), [])
        if m.group(1) not in names[int(m.group(2))]:
            names[int(m.group(2))].append(m.group(1))
    return {k: '/'.join(v) for k, v in names.items()}


def disasm(kernel, start):
    try:
        from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_040
    except ImportError:
        return []
    return [(i.address, i.bytes, f'{i.mnemonic} {i.op_str}'.strip()) for i in
            Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_040).disasm(kernel, start)]


def summarize(log, names, ops, top_states, top_ops):
    lines = log.splitlines()
    total = next(int(re.search(r'cycles=(\d+)', l).group(1)) for l in lines if ' PASS cycles=' in l)
    out = []
    st = sorted(((int(m.group(2)), int(m.group(1))) for m in
                 (re.match(r'STATE (\d+) cycles=(\d+)', l) for l in lines) if m), reverse=True)
    out.append(f'  sequencer states (top {top_states} of {len(st)}, % of {total} clocks):')
    for c, s in st[:top_states]:
        out.append(f'    {names.get(s, "S_%d" % s):28s} {s:3d} {c:10d} {100 * c / total:6.2f}%')

    def oplist(tag, title):
        rows = sorted(((int(m.group(2)), m.group(1)) for m in
                       (re.match(tag + r' opcode=([0-9a-f]{4}) cycles=(\d+)', l) for l in lines) if m), reverse=True)
        out.append(f'  {title} (top {top_ops}):')
        for c, o in rows[:top_ops]:
            out.append(f'    {o} {c:10d} {100 * c / total:6.2f}%  {ops.get(o, "")}')
    pipe = next((l for l in lines if l.startswith('PIPELINE ')), '')
    oplist('ACTIVE_IR', 'opcodes by legacy-sequencer clocks, dut.core.ir while !pipe_rf_owner')
    out.append(f'    {pipe}')
    oplist('IR_ALL', 'opcodes by all clocks, dut.core.ir (ir can be stale while the pipeline owns the register file)')
    ex = sorted(((int(m.group(2)), m.group(1)) for m in
                 (re.match(r'PIPE_EXIT opcode=([0-9a-f]{4}) count=(\d+)', l) for l in lines) if m), reverse=True)
    if ex:
        out.append('  pipeline exits by next opcode: ' + ', '.join(f'{o}({ops.get(o, "?")})x{c}' for c, o in ex[:8]))
    out.append('  memory request->ack latency at the wrapper core side (class: count, total, mean):')
    for l in lines:
        m = re.match(r'LATENCY class=(\d) count=(\d+) total=(\d+)', l)
        if m:
            n, t = int(m.group(2)), int(m.group(3))
            out.append(f"    {('fetch', 'read', 'write')[int(m.group(1))]:5s} {n:9d} {t:10d} {t / n if n else 0:6.2f}")
    for l in lines:
        if l.startswith(('FETCH_PROFILE', 'BUFFER_UPPER_BOUND', 'PROFILE_WARN', 'PIPE_READ')):
            out.append('  ' + l)
    return '\n'.join(out)


def main(spec):
    p = argparse.ArgumentParser(description=spec['description'])
    p.add_argument('resource', type=Path, nargs='?', default=Path(DEFAULT_RESOURCE))
    p.add_argument('--out', type=Path, default=REPO / f"scratch/fixture_sieve_bubble_20260922/{spec['name']}")
    p.add_argument('--rtl-root', type=Path, default=DEFAULT_RTL_ROOT,
                   help='directory containing rtl/ (a git archive snapshot); default the 2026-09-22 HEAD snapshot')
    p.add_argument('--latencies', type=int, nargs='+', default=[0, 3])
    p.add_argument('--profile', action='store_true', help='compile passive counters in and print named state/opcode/latency profiles')
    p.add_argument('--no-control', action='store_true', help='skip the negative control (it is required for a valid result)')
    p.add_argument('--top-states', type=int, default=15)
    p.add_argument('--top-ops', type=int, default=10)
    p.add_argument('-j', type=int, default=4, help='verilator build jobs (max 4 on this shared box)')
    a = p.parse_args()
    name = spec['name']
    d = a.out.resolve(); d.mkdir(parents=True, exist_ok=True)
    root = a.rtl_root.resolve()
    rtl = root / 'rtl/ap68040/rtl'
    resource = a.resource.read_bytes()
    assert hashlib.sha256(resource).hexdigest() == RESOURCE_SHA, 'Speedometer resource hash mismatch'
    start, end = spec['range']
    kernel = resource[CODE_BASE + start:CODE_BASE + end]
    kbin = d / f'{name}.bin'; kbin.write_bytes(kernel)
    dis = disasm(kernel, start)
    if dis:
        assert sum(len(b) for _, b, _ in dis) == len(kernel), 'incomplete disassembly'
        (d / 'kernel.dis').write_text(''.join(f'{ad:04x} {b.hex():12} {t}\n' for ad, b, t in dis))
    ops = {}
    for ad, b, t in dis:
        ops.setdefault(b[:2].hex(), f'{ad:04x}: {t}')
    asm, oracle_files, inputs = spec['build'](d, kbin)
    (d / f'{name}.s').write_text(asm)
    run([VASM, '-Fbin', '-m68040', '-no-opt', '-o', d / 'program.bin', d / f'{name}.s'], d / 'asm.log')
    prog = bytearray((d / 'program.bin').read_bytes())
    assert bytes(prog[start:end]) == kernel, 'kernel bytes changed in program image'
    bin2hex = root / 'rtl/ap68040/tb/bin2hex.py'
    run(['python3', bin2hex, d / 'program.bin', d / 'program.hex'], d / 'hex.log')
    # Negative control: one instruction replaced in a disposable copy.
    coff, cold, cnew = spec['control']
    assert bytes(prog[coff:coff + len(cold)]) == cold, 'control site does not hold the expected instruction'
    ctl = bytearray(prog); ctl[coff:coff + len(cnew)] = cnew
    (d / 'control_program.bin').write_bytes(ctl)
    run(['python3', bin2hex, d / 'control_program.bin', d / 'control_program.hex'], d / 'hex_control.log')

    tb = TB.replace('@DECLS@', spec['tb_decls']).replace('@INIT@', spec['tb_init']).replace('@ORACLE@', spec['tb_oracle'])
    if a.profile:
        tb = add_profile(tb)
    mode = 'profile' if a.profile else 'plain'
    (d / f'tb_{mode}.sv').write_text(tb)
    extra = os.environ.get('EXTRA_FLAGS', '').split()
    flags = PRODUCTION_FLAGS + extra
    sources = [d / f'tb_{mode}.sv', root / 'rtl/wombat_cpu.sv', root / 'rtl/wombat_store_buffer.sv',
               *[rtl / (u + '.v') for u in UNITS], root / 'rtl/ap68040/experimental/ap040_pipeline_integer.sv']
    head = (root / 'HEAD_COMMIT').read_text().strip() if (root / 'HEAD_COMMIT').exists() else None
    ident = {
        'fixture': name, 'rtl_root': str(root), 'rtl_head_commit': head,
        'sources': {str(s): sha(s) for s in sources}, 'verilog_flags': flags, 'extra_flags_env': extra,
        'wrapper_parameters': 'wombat_cpu defaults (AP040_HAS_FPU=1, AP040_ENABLE_CACHE=1, AP040_STORE_BUFFER=1); guest CACR=$80008000',
        'resource_sha256': RESOURCE_SHA, 'kernel_range': [hex(start), hex(end)], 'kernel_sha256': sha(kbin),
        'program_sha256': sha(d / 'program.bin'), 'control_program_sha256': sha(d / 'control_program.bin'),
        'control': {'offset': hex(coff), 'original': cold.hex(), 'replacement': cnew.hex(), 'why': spec['control_why'],
                    'expected_failure': spec['control_expect']},
        'oracle_sha256': {str(f): sha(f) for f in oracle_files}, 'input': inputs,
        'scope': spec['scope'], 'latencies': a.latencies, 'profile': a.profile,
        'memory_model': 'controlled-latency 64 KB byte-addressed responder; not quadra800 SDRAM; MMU off',
    }
    (d / f'identity_{mode}.json').write_text(json.dumps(ident, indent=2))
    (d / 'identity.json').write_text(json.dumps(ident, indent=2))
    obj = d / f'obj_{mode}'
    t0 = time.time()
    run([VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-BLKLOOPINIT', '-j', a.j, '--top-module', 'tb_cpu_fixture',
         '--Mdir', obj, '-I' + str(rtl), *flags, *sources], d / f'compile_{mode}.log')
    print(f'BUILD {name} {mode} {time.time() - t0:.1f}s', flush=True)
    names = state_names(rtl / 'ap040_core.v')
    ok = True
    for lat in a.latencies:
        log = d / f'run_{mode}_latency{lat}.log'
        t0 = time.time()
        rc = run([obj / 'Vtb_cpu_fixture', '+prog=' + str(d / 'program.hex'), f'+latency={lat}'], log, check=False)
        wall = time.time() - t0
        text = log.read_text()
        m = re.search(spec['pass_tag'] + r' PASS cycles=(\d+)', text)
        if rc or not m:
            ok = False
            print(f'FIXTURE {name} FAIL latency={lat} rc={rc}\n' + text[-1500:], flush=True)
            continue
        print(f'FIXTURE {name} PASS cycles={m.group(1)} latency={lat} wall={wall:.1f}s', flush=True)
        if a.profile:
            prof = summarize(text, names, ops, a.top_states, a.top_ops)
            (d / f'profile_latency{lat}.txt').write_text(prof + '\n')
            print(prof, flush=True)
    if not a.no_control:
        lat = 3 if 3 in a.latencies else a.latencies[0]
        log = d / f'run_{mode}_control_latency{lat}.log'
        rc = run([obj / 'Vtb_cpu_fixture', '+prog=' + str(d / 'control_program.hex'), f'+latency={lat}'], log, check=False)
        text = log.read_text()
        if rc and re.search(spec['control_expect'], text) and ' PASS cycles=' not in text:
            msg = re.search(spec['control_expect'] + r'[^\n]*', text).group(0)
            print(f'CONTROL {name} control failed as required: {msg}', flush=True)
        else:
            ok = False
            print(f'CONTROL {name} INVALID: negative control did not fail with the oracle (rc={rc})\n' + text[-1500:], flush=True)
    sys.exit(0 if ok else 1)
