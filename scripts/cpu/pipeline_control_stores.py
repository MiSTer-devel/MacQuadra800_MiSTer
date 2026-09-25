#!/usr/bin/env python3
from pathlib import Path
import argparse,subprocess
r=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description="Check pipeline branch conditions and cancellation of younger stores.")
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--core',type=Path,required=True)
parser.add_argument('--pipeline-module',type=Path,required=True)
parser.add_argument('--vasm',default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
args=parser.parse_args();d=args.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental' 
pairs=[(0,0),(1,0),(0,1),(0x80000000,1),(0x7fffffff,0xffffffff),(0xffffffff,0),(0x80000000,0x7fffffff),(0x7fffffff,0x80000000)]
names=['bra',None,'bhi','bls','bcc','bcs','bne','beq','bvc','bvs','bpl','bmi','bge','blt','bgt','ble']
asm=''' org 0
 dc.l $7000,start
 rept 254
 dc.l failed
 endr
 org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
 movea.l #$c000,a0
 movea.l #$c100,a1
 move.l #$55aa,d5
 moveq #0,d1
'''
k=0
for dst,src in pairs:
 v=(dst-src)&0xffffffff;n=bool(v&0x80000000);z=v==0;c=dst<src;o=bool(((dst^src)&(dst^v))&0x80000000)
 outcomes=[True,False,not c and not z,c or z,not c,c,not z,z,not o,o,not n,n,n==o,n!=o,not z and n==o,z or n!=o]
 for cc,name in enumerate(names):
  if name is None:continue
  asm+=f''' moveq #0,d7
 clr.w (a1)
 move.l #${dst:08x},d3
 move.l #${src:08x},($c000).l
 dc.w $2430,$1800
 dc.w $b6b0,$1800
 {name}.b taken{k}
 move.w d5,(a1)
 bra.b check{k}
taken{k}:
 moveq #1,d7
check{k}:
 cmpi.w #{int(outcomes[cc])},d7
 bne failed
 cmpi.w #${0 if outcomes[cc] else 0x55aa:04x},(a1)
 bne failed
''';k+=1
asm+=''' move.w #$600d,($f102).l
 stop #$2700
failed:
 move.w #$bad0,($f102).l
 stop #$2700
'''
(d/'test.s').write_text(asm)
(d/'monitor.sv').write_text('`timescale 1ns/1ps\n`define C tb_ap040_program.dut.core\nmodule drain_monitor;\ninteger count=0,taken=0,not_taken=0;\nalways @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce && `C.pipe_owner && `C.pipe_retire && `C.pipe_opcode[15:12]==6 && `C.pipe_opcode[7:0]==4) begin\n count++;\n if((`C.pipe_next_pc != `C.pipe_pc + 2)) taken++; else not_taken++;\nend\nfinal begin\n $display("BRANCH_PIPE count=%0d taken=%0d not_taken=%0d",count,taken,not_taken);\n if(count!=357 || taken!=192 || not_taken!=165) $fatal(1,"branch final-WB coverage missing");\nend\nendmodule\n')
def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/'test.bin',d/'test.s'],'asm.log')
run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/'test.bin',d/'test.hex'],'hex.log')
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',exp/'handoff_monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',args.pipeline_module.resolve(),*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN','-DAP040_PIPELINE_COMPARE']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','handoff_monitor','-s','drain_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
run(['vvp',d/'test.vvp','+prog='+str(d/'test.hex')],'run.log')
s=(d/'run.log').read_text();assert 'ALL TESTS PASSED' in s and 'FAIL:' not in s,s[-2000:];print(s[-1800:])
