#!/usr/bin/env python3
"""Execute the complete constructed Whetstone fixture; numerical oracle pending."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
R=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('image',type=Path);p.add_argument('--rom',type=Path,default=R/'releases/quadra800.rom')
p.add_argument('--pipeline-module',type=Path,default=R/'rtl/ap68040/experimental/ap040_pipeline_integer.sv')
p.add_argument('--bench',type=Path,default=R/'scripts/cpu/tb_cpu_whetstone.sv')
p.add_argument('--cache',type=Path,help='isolated cache candidate override');
p.add_argument('--core',type=Path);p.add_argument('--out',type=Path,required=True)
p.add_argument('--latency',type=int,default=3)
a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=R/'rtl/ap68040/rtl'
units=['ap040_core','ap040_bus_timeout','ap040_regfile','ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu','primitives/dpram']
sources=[a.bench.resolve(),R/'rtl/wombat_cpu.sv',R/'rtl/wombat_store_buffer.sv',a.pipeline_module.resolve()]
sources += [a.core.resolve() if u=='ap040_core' and a.core else a.cache.resolve() if u=='ap040_cache' and a.cache else rtl/(u+'.v') for u in units]
flags=['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]+['-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_EARLY_DRAIN']
(d/'identity.json').write_text(json.dumps({'scope':__doc__,'sources':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources},'image_sha256':hashlib.sha256(a.image.read_bytes()).hexdigest(),'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(),'flags':flags,'latency':a.latency},indent=2)+'\n')
def run(cmd,log):
 with (d/log).open('w') as f:
  result=subprocess.run(list(map(str,cmd)),cwd=d,stdout=f,stderr=subprocess.STDOUT)
 text=(d/log).read_text()
 if result.returncode: raise RuntimeError(text[-3000:])
 return text
run(['/home/alans/verilator5/bin/verilator','--binary','--timing','-Wno-fatal','-Wno-BLKLOOPINIT','-j','4','--top-module','tb_cpu_whetstone','--Mdir',d/'obj','-I'+str(rtl),*flags,*sources],'compile.log')
result=run(['stdbuf','-oL',d/'obj/Vtb_cpu_whetstone','+prog='+str(a.image.resolve()),'+rom='+str(a.rom.resolve()),f'+latency={a.latency}'],'run.log')
assert 'WHETSTONE RETURNED' in result,result[-3000:]
print('\n'.join(l for l in result.splitlines() if l.startswith(('WHETSTONE','NUMERICAL'))))
