#!/usr/bin/env python3
"""Independent P6 qualification; generated fixtures and logs stay under --out."""
from pathlib import Path
import argparse
import subprocess, sys
r = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=r/'scratch/pipeline_p6')
args = parser.parse_args()
root_out = args.out.resolve()
root_out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(r/'scripts/cpu'))
d=root_out;rtl=r/'rtl/ap68040/rtl';out=d/'negative_full';out.mkdir(exist_ok=True)
s=(r/'rtl/ap68040/experimental/ap040_pipeline_integer.sv').read_text()
mutations=[
 ('partial_merge','load_oracle','is_indexload(ex_opcode) ? old_dst : dst','is_indexload(ex_opcode) ? dst : dst'),
 ('store_base','store_oracle','is_indexstore(ex_opcode) ? old_dst +','is_indexstore(ex_opcode) ? dst +'),
 ('third_forward','store_oracle','wire [31:0] old_dst = wb_v && wb_we && wb_dst == ex_dst ? wb_data : rf_old_dst;','wire [31:0] old_dst = rf_old_dst;'),
 ('zero_rox_carry','alu_oracle',"ex_opcode[4:3] == 2 ? flags_in[4] : 1'b0", "1'b0"),
 ('lea_sign','alu_oracle','source_full + {{16{ex_extension[15]}},ex_extension}',"source_full + {16'd0,ex_extension}"),
 ('shift_forward','alu_oracle','(wb_v && wb_we && wb_dst == read_dst) ? wb_data : rf_b','rf_b'),
]
for name,fixture,before,after in mutations:
 assert s.count(before)==1,(name,s.count(before))
 module=out/(name+'.sv');module.write_text(s.replace(before,after));fdir=d/fixture
 code=(fdir/'instructions.hex').read_text().splitlines();rows=(fdir/'oracle.trace').read_text().splitlines()
 nreq=0 if fixture=='alu_oracle' else len((fdir/'requests.hex').read_text().splitlines())
 # All final instructions in these fixtures carry an extension.
 end=int(code[-1][:8],16)+4
 with (out/(name+'_compile.log')).open('w') as log:
  subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_pea','-o',str(out/(name+'.vvp')),str(fdir/'tb.sv'),str(module),str(rtl/'ap040_regfile.v'),str(rtl/'ap040_alu.v')],stdout=log,stderr=subprocess.STDOUT,check=True)
 cmd=['vvp',str(out/(name+'.vvp')),'+program='+str(fdir/'instructions.hex'),'+trace='+str(out/(name+'.trace')),'+count='+str(len(code)),'+registers=16','+mode=1','+delay=3','+stores='+str(fdir/'requests.hex'),'+requests='+str(nreq),'+supported='+str(fdir/'supported.hex'),f'+end_pc={end:x}']
 with (out/(name+'.log')).open('w') as log:ret=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 got=(out/(name+'.trace')).read_text().splitlines()
 # Require a semantic mismatch or a request assertion, not an unrelated timeout.
 mismatch=next(((i,a,b) for i,(a,b) in enumerate(zip(got,rows)) if a!=b),None)
 log=(out/(name+'.log')).read_text()
 assert mismatch is not None or ('FATAL' in log and ('request' in log or 'store' in log)),(name,ret.returncode,log[-1000:])
 print('PASS mutation detected:',name,'trace row '+str(mismatch[0]) if mismatch else log[-300:],flush=True)
