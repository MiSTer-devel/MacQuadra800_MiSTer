#!/usr/bin/env python3
"""Check MMU fault repair and RTE retry of simple memory MOVE destinations."""
import argparse
from pathlib import Path
import subprocess
R=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--displacement-destination',type=int,help='use d16(An) with this signed displacement instead of simple modes')
a=p.parse_args()
if a.displacement_destination is not None and not -32768<=a.displacement_destination<=32767: p.error('displacement must fit signed 16 bits')
d=a.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=R/'rtl/ap68040/rtl'
def run(cmd,name):
 with (d/name).open('w') as f:
  subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
units=['ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_regfile','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram']
flags=['-DAP040_EXPERIMENTAL_'+x for x in ['XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6']]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program',*flags,'-o',d/'bench.vvp',R/'rtl/ap68040/tb/tb_ap040_program.v',a.core.resolve(),R/'rtl/ap68040/experimental/ap040_pipeline_integer.sv',*[rtl/(u+'.v') for u in units]],'compile.log')
for suffix,n in [('b',1),('w',2),('l',4)]:
 for sm in (3,4):
  for dm in ((5,) if a.displacement_destination is not None else (2,3,4)):
   for fault in ('source','destination'):
    name=f'{suffix}_src{sm}_dst{dm}_{fault}'
    sa=0xb040+(n if sm==4 else 0);da=0xc100+(n if dm==4 else 0)
    if dm==5: da=0xc100-a.displacement_destination
    sf=sa+(n if sm==3 else -n);df=da+(n if dm==3 else -n if dm==4 else 0)
    page=11 if fault=='source' else 12;desc=0x4400+page*4
    fa=0xb040 if fault=='source' else 0xc100
    sr=0x271f if fault=='source' else 0x2718
    source='(a0)+' if sm==3 else '-(a0)';dest=f'({a.displacement_destination},a1)' if dm==5 else {2:'(a1)',3:'(a1)+',4:'-(a1)'}[dm]
    value=(1<<(n*8-1))|1
    asm=f''' org 0
 dc.l $3400,start,handler
 rept 253
 dc.l failed
 endr
 org $400
start:
 move.w #$2700,sr
 moveq #0,d0
 movec d0,tc
 movec d0,cacr
 clr.w ($3600).l
 lea ($4400).l,a0
 moveq #63,d1
setup:
 move.l d0,d3
 lsl.l #8,d3
 lsl.l #4,d3
 addq.l #3,d3
 move.l d3,(a0)+
 addq.l #1,d0
 dbra d1,setup
 move.l #$4203,($4000).l
 move.l #$4403,($4200).l
 move.l #$55555555,($c100).l
 move.{suffix} #${value:x},($b040).l
 clr.l (${desc:x}).l
 move.l #$4000,d0
 movec d0,srp
 movec d0,urp
 move.l #$8000,d0
 movec d0,tc
 pflusha
 movea.l #${sa:x},a0
 movea.l #${da:x},a1
 moveq #$66,d2
 move.w #$271f,sr
faulting:
 move.{suffix} {source},{dest}
 move.w sr,d6
 cmpi.w #$2718,d6
 bne failed
 cmpi.w #1,($3600).l
 bne failed
 cmpa.l #${sf:x},a0
 bne failed
 cmpa.l #${df:x},a1
 bne failed
 cmpi.{suffix} #${value:x},($c100).l
 bne failed
 cmpi.l #$66,d2
 bne failed
 move.w #$600d,($f102).l
 stop #$2700
handler:
 addq.w #1,($3600).l
 cmpi.w #1,($3600).l
 bne failed
 cmpi.w #${sr:x},(a7)
 bne failed
 cmpi.l #faulting,2(a7)
 bne failed
 cmpi.l #${fa:x},20(a7)
 bne failed
 move.w 6(a7),d0
 andi.w #$f000,d0
 cmpi.w #$7000,d0
 bne failed
 cmpa.l #${sa:x},a0
 bne failed
 cmpa.l #${da:x},a1
 bne failed
 cmpi.l #$66,d2
 bne failed
 move.l #${page*4096+3:x},(${desc:x}).l
 pflusha
 rte
failed:
 move.w #$bad0,($f102).l
 stop #$2700
'''
    (d/(name+'.s')).write_text(asm)
    run(['/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot','-Fbin','-m68040','-no-opt','-o',d/(name+'.bin'),d/(name+'.s')],name+'.asm.log')
    run(['python3',R/'rtl/ap68040/tb/bin2hex.py',d/(name+'.bin'),d/(name+'.hex')],name+'.hex.log')
    run(['vvp',d/'bench.vvp','+prog='+str(d/(name+'.hex'))],name+'.log')
    log=(d/(name+'.log')).read_text()
    assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log,log[-2000:]
    print(name,'PASS all three bus phases',flush=True)
