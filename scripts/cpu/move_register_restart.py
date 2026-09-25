#!/usr/bin/env python3
"""Check early register/immediate MOVE stores and MMU repair/RTE retry."""
import argparse
from pathlib import Path
import subprocess
R=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True);p.add_argument('--out',type=Path,required=True)

a=p.parse_args()

d=a.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=R/'rtl/ap68040/rtl'
def run(cmd,name):
 with (d/name).open('w') as f:
  subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
units=['ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_regfile','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram']
flags=['-DAP040_EXPERIMENTAL_'+x for x in ['XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6']]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program',*flags,'-o',d/'bench.vvp',R/'rtl/ap68040/tb/tb_ap040_program.v',a.core.resolve(),R/'rtl/ap68040/experimental/ap040_pipeline_integer.sv',*[rtl/(u+'.v') for u in units]],'compile.log')
for suffix,n in [('b',1),('w',2),('l',4)]:
 for source in ('d2','immediate','a0'):
  if source=='a0' and n==1: continue
  for mode in (2,3,4,5):
   for fault in ('none','write'):
    name=f'{source}_{suffix}_mode{mode}_{fault}'
    initial=0x55555555 & ((1<<(8*n))-1)
    base=0xc100+(n if mode==4 else -16 if mode==5 else 0)
    value=(base if source=='a0' else (1<<(n*8-1))|1)
    expected=value & ((1<<(n*8))-1)
    flags=0x2710 | (8 if expected&(1<<(8*n-1)) else 0) | (4 if expected==0 else 0)
    final=base+(n if mode==3 else -n if mode==4 else 0)
    operand={2:'(a0)',3:'(a0)+',4:'-(a0)',5:'(16,a0)'}[mode]
    desc=0xc003 if fault=='none' else 0xc007
    stacked=flags
    source_operand=f'#${value:x}' if source=='immediate' else source
    exceptions=0 if fault=='none' else 1
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
 move.{suffix} #${initial:x},($c100).l
 move.l #${desc:x},($4430).l
 move.l #$4000,d0
 movec d0,srp
 movec d0,urp
 move.l #$8000,d0
 movec d0,tc
 pflusha
 movea.l #${base:x},a0
 move.l #${value:x},d2
 move.w #$271f,sr
faulting:
 move.{suffix} {source_operand},{operand}
 move.w sr,d6
 cmpi.w #${flags:x},d6
 bne failed
 cmpi.w #{exceptions},($3600).l
 bne failed
 cmpa.l #${final:x},a0
 bne failed
 cmpi.{suffix} #${expected:x},($c100).l
 bne failed
 cmpi.l #${value:x},d2
 bne failed
 move.w #$600d,($f102).l
 stop #$2700
handler:
 addq.w #1,($3600).l
 cmpi.w #{exceptions},($3600).l
 bne failed
 cmpi.w #${stacked:x},(a7)
 bne failed
 cmpi.l #faulting,2(a7)
 bne failed
 cmpi.l #$c100,20(a7)
 bne failed
 move.w 6(a7),d0
 andi.w #$f000,d0
 cmpi.w #$7000,d0
 bne failed
 cmpa.l #${base:x},a0
 bne failed
 cmpi.l #${value:x},d2
 bne failed
 move.l #$c003,($4430).l
 pflusha
 cmpi.{suffix} #${initial:x},($c100).l
 bne failed
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
