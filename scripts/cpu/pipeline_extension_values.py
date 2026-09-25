#!/usr/bin/env python3
from pathlib import Path
import argparse,subprocess
r=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description="Check pipeline EXT, EXTB and SWAP values, flags and forwarding for all data registers.")
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--core',type=Path,required=True)
parser.add_argument('--pipeline-module',type=Path,required=True)
parser.add_argument('--vasm',default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
args=parser.parse_args();d=args.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental' 
values=[0,1,0x7f,0x80,0xff,0x7fff,0x8000,0xffff,0x12345678,0x89abcdef,0xffff0000,0x80000000]
asm=" org 0\n dc.l $f000,start\n rept 254\n dc.l failed\n endr\n org $400\nstart:\n move.w #$2700,sr\n move.l #$80008000,d0\n movec d0,cacr\n movea.l #$e000,a0\n suba.l a1,a1\n clr.l (a0)\n"
k=0
for opcode in [0x4880,0x48c0,0x49c0,0x4840]:
 for reg in range(8):
  for value in values:
   for x in [0,1]:
    if opcode==0x4880:
     low=(value&255) if not value&128 else (value&255)|0xff00
     expected=(value&0xffff0000)|low; n=bool(low&0x8000);z=low==0
    elif opcode==0x48c0:
     expected=(value&65535) if not value&0x8000 else (value&65535)|0xffff0000
     n=bool(expected&0x80000000);z=expected==0
    elif opcode==0x49c0:
     expected=(value&255) if not value&128 else (value&255)|0xffffff00
     n=bool(expected&0x80000000);z=expected==0
    else:
     expected=((value<<16)|(value>>16))&0xffffffff;n=bool(expected&0x80000000);z=expected==0
    sr=0x2700|(x<<4)|(int(n)<<3)|(int(z)<<2)
    asm+=f" move.w #${0x2700|(x<<4):04x},sr\n move.l #${value:08x},(a0)\n dc.w ${0x2030|(reg<<9):04x},$9800\n dc.w ${opcode|reg:04x}\n move.w sr,($e100).l\n cmpi.l #${expected:08x},d{reg}\n bne.l failed\n cmpi.w #${sr:04x},($e100).l\n bne.l failed\n"
    k+=1
asm+=" move.w #$600d,($f102).l\n stop #$2700\nfailed:\n move.w #$bad0,($f102).l\n stop #$2700\n"
(d/'test.s').write_text(asm)
(d/'monitor.sv').write_text(f'''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module drain_monitor;
integer count=0;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce && `C.pipe_owner && `C.pipe_retire && ((`C.pipe_opcode & 16'hfff8)==16'h4880 || (`C.pipe_opcode & 16'hfff8)==16'h48c0 || (`C.pipe_opcode & 16'hfff8)==16'h49c0 || (`C.pipe_opcode & 16'hfff8)==16'h4840)) count++;
final begin $display("EXT_PIPE count=%0d",count); if(count!={k*3}) $fatal(1,"extension pipeline coverage missing");end
endmodule
''')
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
