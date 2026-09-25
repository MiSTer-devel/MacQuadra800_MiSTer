#!/usr/bin/env python3
"""Check delayed brief admission and full-format indexed fallback."""
import argparse
from pathlib import Path
import subprocess
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, required=True, help='candidate ap040_core.v')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
args = parser.parse_args()
d = args.out.resolve()
d.mkdir(parents=True, exist_ok=True)
rtl = r/'rtl/ap68040/rtl'
exp = r/'rtl/ap68040/experimental'

def run(cmd,name):
 with (d/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
(d/'monitor.sv').write_text('''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module fallback_monitor;
integer waits=0,claims=0,expected=0;
initial if($value$plusargs("claims=%d",expected)) begin end
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce && `C.pc_i=='h60e) begin
 if(`C.pipe_pea_wait) waits++;
 if(`C.pipe_claim) claims++;
end
final begin
 $display("FALLBACK waits=%0d claims=%0d expected=%0d",waits,claims,expected);
 if(waits==0 || claims!=expected) $fatal(1,"missing delayed extension coverage");
end
endmodule
''')
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',exp/'ap040_pipeline_integer.sv',*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program','-s','fallback_monitor',*flags,'-o',d/'test.vvp',*sources],'compile.log')
for kind,opcode in [('load',0x3630),('store',0x3183),('cmp',0xb670),('tst',0x4a70)]:
 for full in (False,True):
  name=kind+('_full' if full else '_brief');ext=0x1910 if full else 0x1800
  result=0xabcd8001 if kind=='load' else 0xabcdefff
  value=0xefff if kind=='store' else 0x8001
  ccr=0x10 if kind=='cmp' else 0x18
  asm=' org 0\n dc.l $7000,start\n'+''.join(' dc.l failed\n' for _ in range(254))+f''' org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
 movea.l #$c000,a0
 moveq #8,d1
 move.l #$abcdefff,d3
 move.w #$8001,($c008).l
 clr.w -(a7)
 move.l #$60e,-(a7)
 move.w #$2710,-(a7)
 rte
 org $60e
 dc.w ${opcode:04x},${ext:04x}
 move.w sr,d6
 andi.w #$1f,d6
 cmpi.w #${ccr:x},d6
 bne failed
 cmpi.l #${result:x},d3
 bne failed
 cmpi.w #${value:x},($c008).l
 bne failed
 cmpa.l #$c000,a0
 bne failed
 cmpi.l #8,d1
 bne failed
 move.w #$600d,($f102).l
 stop #$2700
failed:
 move.w #$bad0,($f102).l
 stop #$2700
'''
  (d/(name+'.s')).write_text(asm)
  run([args.vasm,'-Fbin','-m68040','-no-opt','-o',d/(name+'.bin'),d/(name+'.s')],name+'_asm.log')
  run(['python3',r/'rtl/ap68040/tb/bin2hex.py',d/(name+'.bin'),d/(name+'.hex')],name+'_hex.log')
  run(['vvp',d/'test.vvp','+prog='+str(d/(name+'.hex')),'+claims='+str(0 if full else 3)],name+'.log')
  s=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in s and 'FAIL:' not in s,s[-2000:]
  print(name,'PASS',next(l for l in s.splitlines() if l.startswith('FALLBACK')),flush=True)
