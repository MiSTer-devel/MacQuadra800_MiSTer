#!/usr/bin/env python3
"""Check CPU stores invalidate resident branch targets outside the fetch queue."""
import argparse, subprocess, re
from pathlib import Path
r=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--pipeline-module',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--vasm',default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=True);rtl=r/'rtl/ap68040/rtl'
def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
tag_width=re.search(r'reg\s*\[(\d+):0\]\s+brf_tag',a.core.read_text())
assert tag_width, 'refill tag declaration not found'
sector_shift=31-int(tag_width[1])
(d/'monitor.sv').write_text(r'''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module coherence_monitor;
integer target=0,patch=0,covered=0;
localparam SHIFT=SECTOR_SHIFT;
initial begin
 if($value$plusargs("target=%h",target)) begin end
 if($value$plusargs("patch=%h",patch)) begin end
end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce &&
 `C.state==`C.S_MWR && `C.d_ack && `C.mem_write && `C.mem_addr_q==patch) begin
 if(`C.brf_tag != (target>>SHIFT) || !`C.brf_valid[(target>>1)&((1<<(SHIFT-1))-1)])
  $fatal(1,"patch missed resident target tag=%h valid=%h shift=%0d target=%h",`C.brf_tag,`C.brf_valid,SHIFT,target);
 if(!(`C.epf_next>target+3 || `C.epf_ftail<=target))
  $fatal(1,"patch overlaps queue; refill-only invalidation not isolated");
 covered++;
end
final begin
 $display("REFILL_COHERENCE patches=%0d",covered);
 if(covered!=3) $fatal(1,"missing patch coverage across bus phases");
end
endmodule
'''.replace('SECTOR_SHIFT',str(sector_shift)))
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',a.core.resolve(),rtl/'ap040_regfile.v',a.pipeline_module.resolve(),*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','coherence_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
sector_bytes=1<<sector_shift
upper=0x800+sector_bytes//2;cross=0x800+sector_bytes
for name,target,patch,size,value in [('upper',upper,upper,'w',0x702a),('cross',cross,cross-2,'l',0x4e71702a)]:
 asm=f''' org 0
 dc.l $7000,start
 rept 254
 dc.l failed
 endr
 org $400
start:
 move.w #$2700,sr
 moveq #0,d0
 movec d0,cacr
 moveq #1,d6
 moveq #3,d7
 jmp (${target:x}).l
 org ${target:x}
target:
 moveq #1,d0
 nop
 nop
 dbra d7,target
 tst.b d6
 beq.s finished
 moveq #0,d6
 move.{size} #${value:x},(${patch:x}).l
 moveq #1,d7
 bra.s target
finished:
 cmpi.l #42,d0
 bne failed
 move.w #$600d,($f102).l
 stop #$2700
failed:
 move.w #$bad0,($f102).l
 stop #$2700
'''
 (d/(name+'.s')).write_text(asm)
 run([a.vasm,'-Fbin','-m68040','-no-opt','-o',d/(name+'.bin'),d/(name+'.s')],name+'.asm.log')
 run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/(name+'.bin'),d/(name+'.hex')],name+'.hex.log')
 run(['vvp',d/'test.vvp','+prog='+str(d/(name+'.hex')),f'+target={target:x}',f'+patch={patch:x}'],name+'.log')
 log=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log,log[-2000:]
 print(name,'PASS',log.split('REFILL_COHERENCE')[-1].strip(),flush=True)
