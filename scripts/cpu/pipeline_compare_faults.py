#!/usr/bin/env python3
"""Compare extension qualification; generated fixtures and logs stay under --out."""
from pathlib import Path
import argparse
import subprocess, sys
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=r/'scratch/pipeline_compare')
parser.add_argument("--vasm", default="/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot")
parser.add_argument('--core',type=Path,default=r/'rtl/ap68040/rtl/ap040_core.v')
parser.add_argument('--pipeline-module',type=Path,default=r/'rtl/ap68040/experimental/ap040_pipeline_integer.sv')
parser.add_argument('--indirect-tst',action='store_true')
parser.add_argument('--sequencer-read',action='store_true',help='test early brief-indexed sequencer MUL/DIV reads with shortcut coverage')
parser.add_argument('--displacement-read',action='store_true',help='use d16 sequencer source reads; requires --sequencer-read')
parser.add_argument('--pc-relative-read',action='store_true',help='use d16(PC); requires --displacement-read')
parser.add_argument('--multiply',action='store_true',help='test indexed MULS/MULU in an isolated pipeline module')
parser.add_argument('--indirect-add',action='store_true',help='also test byte/word/long ADD (An),Dn pipeline source faults')
args = parser.parse_args()
if args.multiply and args.sequencer_read: parser.error('--multiply and --sequencer-read are separate paths')
if args.pc_relative_read and not args.displacement_read: parser.error('--pc-relative-read requires --displacement-read')
if args.displacement_read and not args.sequencer_read: parser.error('--displacement-read requires --sequencer-read')
root_out = args.out.resolve()
root_out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(r/'scripts/cpu'))
d=root_out/'faults';d.mkdir(exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental'
(d/'monitor.sv').write_text('''`timescale 1ns/1ps
module indexed_fault_monitor;
integer count=0;
always @(posedge tb_ap040_program.clk)
 if(tb_ap040_program.nreset && tb_ap040_program.dut.core.ce && tb_ap040_program.dut.core.pipe_load_launch && tb_ap040_program.dut.core.pipe_load_pc==32'h600) count=count+1;
final begin
 $display("INDEXED FAULT launches=%0d",count);
 if(count!=3) $fatal(1,"indexed fault coverage missing");
end
endmodule
''')
if args.sequencer_read:
 (d/'monitor.sv').write_text('''`timescale 1ns/1ps
`define C tb_ap040_program.dut.core
module indexed_fault_monitor;
integer count=0;
reg check_read=0;
always @(posedge tb_ap040_program.clk) if(tb_ap040_program.nreset && `C.ce) begin
 if(check_read && (`C.state!=`C.S_MRD || `C.r_m_ret!=`C.S_PIPE_SDONE)) $fatal(1,"indexed shortcut did not enter read directly");
 check_read=0;
 if(`C.hint_indexed_read && `C.pc_i==32'h600) begin count=count+1;check_read=1;end
end
final begin
 $display("INDEXED FAULT launches=%0d",count);
 if(count!=3) $fatal(1,"indexed sequencer fault coverage missing");
end
endmodule
''')
if args.displacement_read:
 monitor=d/'monitor.sv'
 monitor.write_text(monitor.read_text().replace('hint_indexed_read','hint_displacement_read').replace('integer count=0;', '''// Withhold the resident-extension offer only at this instruction's
// operand dispatch. Release it for S_IMMF so the actual displacement is
// fetched normally; this selects the fallback EA path under test.
always @(negedge tb_ap040_program.clk) begin
 if(tb_ap040_program.nreset && `C.pc_i==32'h600 && `C.state==`C.S_PIPE_START)
  force `C.epf_ready_pc=1'b0;
 else release `C.epf_ready_pc;
end
integer count=0;'''))
if args.pc_relative_read:
 monitor=d/'monitor.sv'
 monitor.write_text(monitor.read_text().replace("32'h600", "32'he000"))
units=('ap040_tg68k_compat','ap040_bus16_adapter','ap040_bus_timeout','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','ap040_walker_cdc','primitives/dpram')
sources=[r/'rtl/ap68040/tb/tb_ap040_program.v',d/'monitor.sv',exp/'handoff_monitor.sv',args.core.resolve(),rtl/'ap040_regfile.v',args.pipeline_module.resolve(),*[rtl/(u+'.v') for u in units]]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
# Direct ADD joins an already-owned pipeline; force admission for fault coverage.
if args.indirect_add: flags.append('-DAP040_PIPELINE_FORCE_DECODE')
with (d/'compile.log').open('w') as f:subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_ap040_program','-s','handoff_monitor','-s','indexed_fault_monitor',*flags,'-o',str(d/'test.vvp'),*map(str,sources)],stdout=f,stderr=subprocess.STDOUT,check=True)
cases=[('cmp_word',0xb670,0x271f),('tst_word',0x4a70,0x271f)]
if args.multiply: cases=[('muls_word',0xc7f0,0x271f),('mulu_word',0xc6f0,0x271f)]
if args.sequencer_read: cases=[('muls_word',0xc7f0,0x271f),('mulu_word',0xc6f0,0x271f),('divs_word',0x87f0,0x271f),('divu_word',0x86f0,0x271f)]
if args.indirect_add:cases += [(f'indirect_add_{size}',0xd610+(size<<6),0x271f) for size in range(3)]
if args.indirect_tst:cases += [(f'indirect_tst_{size}',0x4a10+(size<<6),0x271f) for size in range(3)]
for name,opcode,sr in cases:
 if args.displacement_read: opcode += 10 if args.pc_relative_read else -8
 baseaddr=0xf140 if name.startswith('indirect') else 0xf100
 words=f'${opcode:04x}' if name.startswith('indirect') else f'${opcode:04x},$1800'
 if args.displacement_read: words=f'${opcode:04x},$'+('113e' if args.pc_relative_read else '0040')
 asm=f'''    org 0
    dc.l $7000,start
    dc.l handler
    rept 29
    dc.l failed
    endr
    dc.l $600
    rept 223
    dc.l failed
    endr
    org $400
start:
    move.w #$2700,sr
    move.l #$80008000,d0
    movec d0,cacr
    movea.l #${baseaddr:x},a0
    movea.l #$deadbeef,a3
    move.l #$fedcba98,d3
    moveq #$40,d1
    moveq #$66,d2
    move.w #$271f,sr
    trap #0
    org $600
faulting:
    dc.w {words}
    moveq #7,d2
    bra failed
handler:
    cmpi.w #${sr:04x},(a7)
    bne failed
    cmpi.l #faulting,2(a7)
    bne failed
    cmpi.l #$f140,20(a7)
    bne failed
    cmpa.l #${baseaddr:x},a0
    bne failed
    cmpa.l #$deadbeef,a3
    bne failed
    cmpi.l #$fedcba98,d3
    bne failed
    cmpi.l #$40,d1
    bne failed
    cmpi.l #$66,d2
    bne failed
    move.w 6(a7),d0
    andi.w #$f000,d0
    cmpi.w #$7000,d0
    bne failed
    move.w #$600d,($f102).l
    stop #$2700
failed:
    move.w #$6fad,($f100).l
    move.w #$bad0,($f102).l
    stop #$2700
'''
 if args.pc_relative_read: asm=asm.replace('dc.l $600','dc.l $e000').replace('org $600','org $e000')
 p=d/(name+'.s');p.write_text(asm)
 with (d/(name+'_assemble.log')).open('w') as f:
  subprocess.run([args.vasm,'-Fbin','-m68040','-no-opt','-o',str(d/(name+'.bin')),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
 subprocess.run(['python3',str(r/'rtl/ap68040/tb/bin2hex.py'),str(d/(name+'.bin')),str(d/(name+'.hex'))],capture_output=True,check=True)
 with (d/(name+'.log')).open('w') as f:subprocess.run(['vvp',str(d/'test.vvp'),'+prog='+str(d/(name+'.hex'))],stdout=f,stderr=subprocess.STDOUT,check=True)
 log=(d/(name+'.log')).read_text();assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log and 'INDEXED FAULT launches=3' in log,log[-3000:]
 print(name,'PASS',next(l for l in log.splitlines() if l.startswith('HANDOFF')),flush=True)
