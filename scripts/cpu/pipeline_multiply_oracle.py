#!/usr/bin/env python3
"""Check indexed word MULS/MULU full products and CCR against Python integers."""
import argparse, itertools, random, subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--pipeline-module',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args(); out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
rtl=root/'rtl/ap68040/rtl';rng=random.Random(20260920)
values=[0,1,0x7fff,0x8000,0xffff,0x8001]
pairs=list(itertools.product(values,repeat=2))+[(rng.randrange(65536),rng.randrange(65536)) for _ in range(28)]
asm=' org 0\n dc.l $e000,start\n rept 254\n dc.l failed\n endr\n org $400\nstart:\n move.w #$2700,sr\n move.l #$80008000,d0\n movec d0,cacr\n'
count=0
for signed in [False,True]:
 for left,right in pairs:
  def val(x): return x-65536 if signed and x&0x8000 else x
  result=(val(left)*val(right))&0xffffffff
  x=count&1; ccr=(x<<4)|((result>>31)<<3)|(4 if result==0 else 0)
  # Alternate word/long index and scale; both address c000 from c010.
  index='d1.w*2' if count&1 else 'd1.l'
  indexvalue=0xfffffff8 if count&1 else 0xfffffff0
  fullright=(rng.randrange(65536)<<16)|right
  asm+=f''' move.w #${left:04x},($c000).l
 movea.l #$c010,a0
 move.l #${indexvalue:08x},d1
 move.l #${fullright:08x},d3
 move.w #${0x270f|(x<<4):04x},sr
 cnop 0,16
 mul{'s' if signed else 'u'}.w (0,a0,{index}),d3
 move.w sr,d4
 cmpi.l #${result:08x},d3
 bne failed
 andi.w #$1f,d4
 cmpi.w #${ccr:04x},d4
 bne failed
'''
  count+=1
asm+=' move.w #$600d,($f102).l\n stop #$2700\nfailed:\n move.w #$bad0,($f102).l\n stop #$2700\n'
(out/'oracle.s').write_text(asm)
(out/'monitor.sv').write_text(f'''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module multiply_monitor;
integer launches=0, retires=0;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce) begin
 if(`C.pipe_load_launch && (`C.pipe_load_opcode & 16'hf0f8)==16'hc0f0) launches++;
 if(`C.pipe_retire && `C.pipe_we && (`C.pipe_opcode & 16'hf0f8)==16'hc0f0) retires++;
end
final begin
 $display("MULTIPLY coverage launches=%0d retires=%0d",launches,retires);
 if(launches!={3*count} || retires!={3*count}) $fatal(1,"multiply coverage missing");
end
endmodule
''')
def run(cmd,name):
 with (out/name).open('w') as f: subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
run(['/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot','-Fbin','-m68040','-no-opt','-o',out/'oracle.bin',out/'oracle.s'],'asm.log')
run(['python3',root/'rtl/ap68040/tb/bin2hex.py',out/'oracle.bin',out/'oracle.hex'],'hex.log')
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_regfile','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[root/'rtl/ap68040/tb/tb_ap040_program.v',out/'monitor.sv',a.core.resolve(),a.pipeline_module.resolve(),*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','multiply_monitor',*flags,'-o',out/'test.vvp',*sources],'compile.log')
run(['vvp',out/'test.vvp','+prog='+str(out/'oracle.hex')],'run.log')
log=(out/'run.log').read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log,log[-3000:]
print(f'PASS {count} signed/unsigned full-product and CCR cases in three bus/CE phases; '+next(l for l in log.splitlines() if l.startswith('MULTIPLY coverage')))
