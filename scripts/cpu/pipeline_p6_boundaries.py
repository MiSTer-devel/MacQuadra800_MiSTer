#!/usr/bin/env python3
"""Independent P6 qualification; generated fixtures and logs stay under --out."""
from pathlib import Path
import argparse
import subprocess, sys
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=r/'scratch/pipeline_p6')
parser.add_argument("--vasm", default="/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot")
parser.add_argument("--memory-entry", action="store_true")
parser.add_argument("--early-drain", action="store_true")
args = parser.parse_args()
root_out = args.out.resolve()
root_out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(r/'scripts/cpu'))
d=root_out/'boundaries';d.mkdir(exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental'
(d/'monitor.sv').write_text('''`timescale 1ns/1ps
module indexed_monitor;
integer count=0,expected=3;
initial if($value$plusargs("launches=%d",expected)) begin end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && tb_ap040_program.dut.core.ce && tb_ap040_program.dut.core.pipe_load_launch && (tb_ap040_program.dut.core.pipe_load_opcode==16'h3630 || tb_ap040_program.dut.core.pipe_load_opcode==16'h3183)) count=count+1;
final begin
 $display("INDEXED launches=%0d expected=%0d",count,expected);
 if(count!=expected) $fatal(1,"indexed operation coverage missing");
end
endmodule
''')
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',exp/'handoff_monitor.sv',rtl/'ap040_core.v',rtl/'ap040_regfile.v',exp/'ap040_pipeline_integer.sv',*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+(['-DAP040_PIPELINE_MEMORY_ENTRY'] if args.memory_entry else ['-DAP040_PIPELINE_FORCE_DECODE'])
if args.early_drain: flags.append('-DAP040_PIPELINE_EARLY_DRAIN')
for irq in (False,True):
 name='irq' if irq else 'plain'
 with (d/(name+'_compile.log')).open('w') as f:subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_ap040_program','-s','handoff_monitor','-s','indexed_monitor',*(['-s','irq_load_monitor',str(exp/'irq_load_monitor.sv')] if irq else []),*flags,'-o',str(d/(name+'.vvp')),*map(str,sources)],stdout=f,stderr=subprocess.STDOUT,check=True)
for kind in ('load','store'):
 opcode=0x3630 if kind=='load' else 0x3183
 expected_d3=0xabcd8001 if kind=='load' else 0xabcdefff
 for boundary in ('extension','trace','irq'):
  name=kind+'_'+boundary
  if boundary=='extension':
   asm=(r/'rtl/ap68040/tb/asm/t_pipeline_pea_ext_fault.s').read_text()
   asm=asm.replace('    dc.w $4870', f'    dc.w ${opcode:04x}')
   asm=asm.replace('    moveq #0,d2', '    move.l #$abcdefff,d3\n    moveq #0,d2')
   asm=asm.replace('handler:\n', '''handler:
    cmpi.l #$abcdefff,d3
    bne failed
    cmpi.l #$2000,20(a7)
    bne failed
''')
  elif boundary=='trace':
   asm=(r/'rtl/ap68040/tb/asm/t_pipeline_pea_trace.s').read_text()
   asm=asm.replace('movea.l #$1000,a0','movea.l #$c000,a0').replace('moveq #7,d1', 'moveq #8,d1\n    move.l #$abcdefff,d3\n    move.w #$8001,($c008).l')
   asm=asm.replace('dc.w $4870,$1801',f'dc.w ${opcode:04x},$1800')
   asm=asm.replace('cmpi.w #$a71f,(a7)','cmpi.w #$a718,(a7)')
   asm=asm.replace('cmpi.l #$1008,($6ffc).l',f'cmpi.l #${expected_d3:08x},d3')
   if kind=='store':asm=asm.replace('    move.w #$600d,($f102).l', '    cmpi.w #$efff,($c008).l\n    bne failed\n    move.w #$600d,($f102).l')
  else:
   asm=(exp/'irq_pea.s').read_text()
   asm=asm.replace('moveq #$55,d1', 'moveq #8,d1\n    move.l #$abcdefff,d3\n    move.w #$8001,($c008).l')
   asm=asm.replace('    trap #0', '    move.w #$201f,sr\n    trap #0',1)
   asm=asm.replace('dc.w $4870,$1801',f'dc.w ${opcode:04x},$1800')
   asm=asm.replace('cmpi.l #$c056,($6ff4).l',f'cmpi.l #${expected_d3:08x},d3').replace('cmpi.l #$55,d1','cmpi.l #8,d1')
   asm=asm.replace('handler:\n','handler:\n    cmpi.w #$2018,(a7)\n    bne failed\n')
   if kind=='store':asm=asm.replace('    tst.l d2', '    cmpi.w #$efff,($c008).l\n    bne failed\n    tst.l d2')
  p=d/(name+'.s');p.write_text(asm)
  with (d/(name+'_assemble.log')).open('w') as f:subprocess.run([args.vasm,'-Fbin','-m68040','-no-opt','-o',str(d/(name+'.bin')),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['python3',str(r/'rtl/ap68040/tb/bin2hex.py'),str(d/(name+'.bin')),str(d/(name+'.hex'))],capture_output=True,check=True)
  launches=0 if boundary=='extension' else 3
  with (d/(name+'.log')).open('w') as f:subprocess.run(['vvp',str(d/('irq.vvp' if boundary=='irq' else 'plain.vvp')),'+prog='+str(d/(name+'.hex')),f'+launches={launches}'],stdout=f,stderr=subprocess.STDOUT,check=True)
  log=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log and f'INDEXED launches={launches} expected={launches}' in log,log[-3000:]
  if boundary=='irq':assert 'LOAD IRQ injections=3' in log and 'killed=0' not in log,log[-3000:]
  print(name,'PASS',next(l for l in log.splitlines() if l.startswith('HANDOFF')),flush=True)
