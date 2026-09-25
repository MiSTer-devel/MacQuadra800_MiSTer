#!/usr/bin/env python3
"""Inject an interrupt during indexed multiply and verify retirement/replay."""
import argparse, subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True);p.add_argument('--pipeline-module',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--indirect-add',action='store_true',help='test byte/word/long memory ADD instead of multiply')
a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental'
(d/'monitor.sv').write_text((exp/'irq_load_monitor.sv').read_text().replace("'h600","'h608"))
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_regfile','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',a.core.resolve(),a.pipeline_module.resolve(),*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN','-DAP040_PIPELINE_FORCE_DECODE']
def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','irq_load_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
cases=[('b',6,0x2011),('w',6,0x2011),('l',6,0x2011)] if a.indirect_add else [('s',0xffffffeb,0x2008),('u',0x6ffeb,0x2000)]
for kind,result,sr in cases:
 asm=(exp/'irq_load.s').read_text().replace('move.l #$55,($c000).l','move.w #$fffd,($c000).l').replace('moveq #0,d1','moveq #7,d1\n    moveq #0,d3').replace('move.l (a0),d1',f'mul{kind}.w (0,a0,d3.l),d1').replace('load_at:', '    rept 4\n    nop\n    endr\nload_at:').replace('cmpi.l #$602,2(a7)','cmpi.l #$60c,2(a7)').replace('cmpi.l #$55,d1',f'cmpi.l #${result:x},d1').replace('handler:\n',f'handler:\n    cmpi.w #${sr:x},(a7)\n    bne failed\n')
 if a.indirect_add:
  asm=asm.replace('move.w #$fffd,($c000).l','move.l #$ffffffff,($c000).l').replace(f'mul{kind}.w (0,a0,d3.l),d1',f'add.{kind} (a0),d1').replace('cmpi.l #$60c,2(a7)','cmpi.l #$60a,2(a7)')
 (d/f'mul{kind}.s').write_text(asm)
 run(['/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot','-Fbin','-m68040','-no-opt','-o',d/f'mul{kind}.bin',d/f'mul{kind}.s'],f'mul{kind}_asm.log')
 run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/f'mul{kind}.bin',d/f'mul{kind}.hex'],f'mul{kind}_hex.log')
 run(['vvp',d/'test.vvp','+prog='+str(d/f'mul{kind}.hex')],f'mul{kind}.log')
 log=(d/f'mul{kind}.log').read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log and 'coverage missing' not in log,log[-2500:]
 print(f'{"ADD." if a.indirect_add else "MUL"}{kind.upper()} IRQ PASS '+next(l for l in log.splitlines() if l.startswith('LOAD IRQ')),flush=True)
