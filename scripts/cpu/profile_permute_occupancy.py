#!/usr/bin/env python3
"""Profile the Permute kernel fixture; controlled RAM latency is not a hardware score."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--program', type=Path, required=True, help='existing Permute program.hex fixture')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--core', type=Path, default=root/'rtl/ap68040/rtl/ap040_core.v')
args = parser.parse_args()
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
rtl = root/'rtl/ap68040/rtl'
bench = (root/'verilator/tb_cpu_permute.sv').read_text()
replacements = [
 ('integer states[0:255];', 'integer states[0:255]; integer opcycles[0:65535]; integer pipe_cycles=0; integer exits[0:65535];'),
 ('for(i=0;i<256;i=i+1) states[i]=0;', 'for(i=0;i<256;i=i+1) states[i]=0; for(i=0;i<65536;i=i+1) begin opcycles[i]=0;exits[i]=0;end'),
 ('cycles=cycles+1;', '''if(dut.core.pipe_rf_owner) pipe_cycles++; else opcycles[dut.core.ir]++;
  if(dut.core.pipe_owner && dut.core.pipe_exit_ready && !dut.core.pipe_input && dut.core.epf_ready_pc) exits[dut.core.epf_data[dut.core.epf_head]]++;
  cycles=cycles+1;'''),
 ('$display("KERNEL32 PASS', 'for(j=0;j<65536;j++) begin if(opcycles[j]) $display("ACTIVE_IR opcode=%04h cycles=%0d",j[15:0],opcycles[j]); if(exits[j]) $display("PIPE_EXIT opcode=%04h count=%0d",j[15:0],exits[j]); end $display("PIPE_OWN cycles=%0d",pipe_cycles); $display("KERNEL32 PASS'),
]
for before, after in replacements:
    assert bench.count(before) == 1, before
    bench = bench.replace(before, after)
(out/'tb.sv').write_text(bench)
units = ('ap040_bus_timeout','ap040_regfile','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','primitives/dpram')
sources = [out/'tb.sv',root/'rtl/wombat_cpu.sv',root/'rtl/wombat_store_buffer.sv',args.core.resolve(),*[rtl/(unit+'.v') for unit in units],root/'rtl/ap68040/experimental/ap040_pipeline_integer.sv']
flags = ['-DAP040_EXPERIMENTAL_'+name for name in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]
flags += ['-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_EARLY_DRAIN']
inputs = [*sources,args.program.resolve()]
(out/'identity.json').write_text(json.dumps({'sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},'flags':flags,'latency':3,'scope':'instruction-state occupancy includes fetch and handoff; not retired-instruction latency or a hardware Mix score'},indent=2))
def run(command, log):
    with (out/log).open('w') as stream:
        subprocess.run(list(map(str,command)),stdout=stream,stderr=subprocess.STDOUT,check=True)
run(['/home/alans/verilator5/bin/verilator','--binary','--timing','-Wno-fatal','-Wno-BLKLOOPINIT','-j','8','--top-module','tb_cpu_permute','--Mdir',out/'obj','-I'+str(rtl),*flags,*sources],'compile.log')
run([out/'obj/Vtb_cpu_permute','+prog='+str(args.program.resolve()),'+latency=3'],'run.log')
log = (out/'run.log').read_text()
assert 'KERNEL32 PASS' in log and 'FAIL:' not in log
rows = [line for line in log.splitlines() if line.startswith('ACTIVE_IR')]
rows.sort(key=lambda line:int(line.split('cycles=')[1]),reverse=True)
summary = '\n'.join(line for line in log.splitlines() if line.startswith(('KERNEL32','PIPE_OWN','PIPELINE','PIPE_EXIT'))) + '\n' + '\n'.join(rows) + '\n'
(out/'summary.txt').write_text(summary)
print(summary)
