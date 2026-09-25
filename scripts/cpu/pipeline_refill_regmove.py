#!/usr/bin/env python3
"""Check resident branch-target register MOVE values, aliases and CCRs."""
import argparse, subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser(description=__doc__)
a.add_argument('--core',type=Path,required=True)
a.add_argument('--pipeline-module',type=Path,required=True)
a.add_argument('--out',type=Path,required=True)
a.add_argument('--require-refill-move',action='store_true')
a.add_argument('--vasm',default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
args=a.parse_args();d=args.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=r/'rtl/ap68040/rtl'
def run(cmd,name):
 with (d/name).open('w') as f: subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
def reg(n):return ('d' if n<8 else 'a')+str(n%8)
asm=' org 0\n dc.l $7000,start\n rept 254\n dc.l failed\n endr\n org $400\nstart:\n move.w #$2700,sr\n move.l #$80008000,d0\n movec d0,cacr\n'
k=0
pairs=[(0,1),(2,2),(7,3),(6,7),(8,0),(15,6),(0,8),(7,15),(8,9),(15,15)]
for size,bits in [('b',8),('w',16),('l',32)]:
 for src,dst in pairs:
  if size=='b' and (src>=8 or dst>=8):continue
  for value in [0,0x80008080,0x7fff7f7f,0xffffffff]:
   k+=1;mask=(1<<bits)-1;initial=value if src==dst else 0xa5a55a5a
   result=((value&mask)|((~mask&0xffffffff)&initial)) if dst<8 else (value if size=='l' else ((value&0xffff)| (0xffff0000 if value&0x8000 else 0)))
   flags=0x1b if dst>=8 else 0x10|(4 if value&mask==0 else 0)|(8 if value&(1<<(bits-1)) else 0)
   counter=next(n for n in range(8) if n not in (src,dst))
   initdst='movea.l' if dst>=8 else 'move.l';initsrc='movea.l' if src>=8 else 'move.l'
   compare='cmpa.l' if dst>=8 else 'cmpi.l'
   asm+=f" move.w #{k},($f100).l\n {initdst} #$a5a55a5a,{reg(dst)}\n {initsrc} #${value:08x},{reg(src)}\n moveq #3,{reg(counter)}\n move.w #$271b,sr\n bra.w target{k}\n cnop 0,32\ntarget{k}:\n move.{size} {reg(src)},{reg(dst)}\n move.w sr,($c802).l\n nop\n nop\n dbra {reg(counter)},target{k}\n {compare} #${result:08x},{reg(dst)}\n bne failed\n cmpi.w #${0x2700|flags:04x},($c802).l\n bne failed\n"
# DBRA updates D0 on the same edge that dispatches its resident target.
# The target MOVE must observe that decrement through the pending-write bypass.
for size,bits,dst in [('b',8,1),('w',16,1),('l',32,1),('w',16,8),('l',32,8)]:
 k+=1;result=(0xa5a55a5a & ~((1<<bits)-1)) if dst<8 else 0
 flags=0x14 if dst<8 else 0x1b
 initdst='movea.l' if dst>=8 else 'move.l';compare='cmpa.l' if dst>=8 else 'cmpi.l'
 asm+=f" move.w #{k},($f100).l\n {initdst} #$a5a55a5a,{reg(dst)}\n moveq #3,d0\n move.w #$271b,sr\n bra.w target{k}\n cnop 0,32\ntarget{k}:\n move.{size} d0,{reg(dst)}\n move.w sr,($c802).l\n nop\n nop\n dbra d0,target{k}\n {compare} #${result:08x},{reg(dst)}\n bne failed\n cmpi.w #${0x2700|flags:04x},($c802).l\n bne failed\n"
asm+=' move.w #$600d,($f102).l\n stop #$2700\nfailed:\n move.w #$bad0,($f102).l\n stop #$2700\n'
(d/'test.s').write_text(asm)
run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/'test.bin',d/'test.s'],'asm.log')
assert (d/'test.bin').stat().st_size<0x7000
run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/'test.bin',d/'test.hex'],'hex.log')
(d/'monitor.sv').write_text('''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module refill_monitor;
reg [7:0] previous_state=0; integer direct=0,required=0,i; reg seen[0:CASECOUNT];
initial for(i=0;i<=CASECOUNT;i++) seen[i]=0;
initial if($value$plusargs("require_direct=%d",required)) begin end
always @(negedge tb_ap040_program.clk) begin
 if(tb_ap040_program.nreset && `C.ce && previous_state==`C.S_DBCC1 && `C.state==`C.S_PIPE_REGS && `C.ir[15:14]==0 && `C.ir[13:12]!=0) begin direct++; seen[tb_ap040_program.mem[16'hf100>>1]]=1; end
 previous_state=`C.state;
end
final begin
 $display("REFILL_REGMOVE direct=%0d",direct);
 if(required) for(i=1;i<=CASECOUNT;i++) if(!seen[i]) $fatal(1,"resident register MOVE case %0d not exercised",i);
end
endmodule
'''.replace('CASECOUNT',str(k)))
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',args.pipeline_module.resolve(),*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','refill_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
run(['vvp',d/'test.vvp','+prog='+str(d/'test.hex'),'+require_direct='+str(int(args.require_refill_move))],'run.log')
log=(d/'run.log').read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log,log[-2000:]
print(k,'fixtures PASS',log[-700:])
