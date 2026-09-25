#!/usr/bin/env python3
"""Independent brief-index PEA oracle with variable PCs and stack forwarding."""
import argparse
from pathlib import Path
import subprocess
from pipeline_prototype import ROOT, workload, encode
import pipeline_address_oracle as address
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args();d=args.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=ROOT/'rtl/ap68040/rtl';exp=ROOT/'rtl/ap68040/experimental'
regs=[0]*16;ccr=0;pc=0x400;code=[];trace=[];stores=[]
def emit(kind,*a):
 global pc,ccr
 at=pc;ext=0;pc+=2
 if kind=='q':
  dest,val=a;word=0x7000+dest*512+(val&255);regs[dest]=val&0xffffffff
  ccr=(ccr&16)|(8 if val<0 else 4 if val==0 else 0)
 elif kind=='a':
  src,dest=a;word=0x2040+dest*512+src;regs[8+dest]=regs[src]
 elif kind in ('double','one'):
  dest,=a;old=regs[dest];other=old if kind=='double' else 1
  word=(0xd080+dest*512+dest) if kind=='double' else 0x5280+dest
  wide=old+other;v=wide&0xffffffff;regs[dest]=v
  ccr=(17 if wide>0xffffffff else 0)|(8 if v&0x80000000 else 4 if v==0 else 0)
  if (~(old^other)&(v^old))&0x80000000:ccr|=2
 elif kind=='pea':
  base,index,long,scale,disp=a;word=0x4870+base
  ext=(index<<12)+(long<<11)+(scale<<9)+(disp&255);pc+=2
  idx=regs[index] if long else ((regs[index]&65535)^32768)-32768
  value=(regs[8+base]+idx*(1<<scale)+disp)&0xffffffff
  regs[15]=(regs[15]-4)&0xffffffff
  stores.append((at,regs[15],value,2))
 else:raise AssertionError(kind)
 code.append((at,word,ext));trace.append(f'{at:08x} {word:04x} {ccr:02x}'+''.join(f' {x:08x}' for x in regs))
def constant(dest,value):
 emit('q',dest,0)
 for bit in range(31,-1,-1):
  emit('double',dest)
  if value&(1<<bit):emit('one',dest)
for i,val in enumerate((0x8001,0x10001,0xdead8001,0x80000000,0xffffffff,0x7fffffff,0x1234ffff,0)):
 constant(i,val)
for base in range(8):
 for index in range(16):
  for long in (0,1):
   for scale in range(4):
    # Source values include word/long sign differences; A7 aliases and same
    # base/index cases are interpreted from actual preceding instructions.
    emit('a',(base+index)%8,base)
    if index>=8:emit('a',(index+scale)%8,index-8)
    emit('q',7,96);emit('a',7,7)
    emit('pea',base,index,long,scale,(-128,-1,0,127)[(base+index+scale+long)%4])
# Consecutive pushes must forward newly committed A7, including A7 as index/base.
for i in range(32):emit('pea',7,15,i%2,i%4,(i%7)-3)
(d/'instructions.hex').write_text('\n'.join(f'{at:08x}{op:04x}{ext:04x}' for at,op,ext in code)+'\n')
(d/'oracle.trace').write_text('\n'.join(trace)+'\n')
(d/'stores.hex').write_text('\n'.join(f'{at:08x}{addr:08x}{val:08x}{size:01x}' for at,addr,val,size in stores)+'\n')
supported={encode(op) for op in workload()}|{address.encode(op) for op in address.workload()}|set(range(0x4870,0x4878))
for src in range(16):
 for dst in range(8):
  for sz in ((1,2,3) if src<8 else (2,3)):
   for mode in (2,3,4):supported.add((sz<<12)+(dst<<9)+(mode<<6)+src)
(d/'supported.hex').write_text('\n'.join(str(int(w in supported)) for w in range(65536))+'\n')
units=[exp/'tb_pipeline_pea.sv',exp/'ap040_pipeline_integer.sv',rtl/'ap040_regfile.v',rtl/'ap040_alu.v']
with (d/'compile.log').open('w') as f:
 subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_pea','-o',str(d/'test.vvp'),*map(str,units)],stdout=f,stderr=subprocess.STDOUT,check=True)
for mode in (0,1):
 for delay in (0,1,3,8):
  name=f'm{mode}_d{delay}'
  cmd=['vvp',str(d/'test.vvp'),'+program='+str(d/'instructions.hex'),'+trace='+str(d/(name+'.trace')),
       '+count='+str(len(code)),'+registers=16','+mode='+str(mode),'+delay='+str(delay),'+stores='+str(d/'stores.hex'),
       '+requests='+str(len(stores)),'+supported='+str(d/'supported.hex'),f'+end_pc={pc:x}']
  with (d/(name+'.log')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  got=(d/(name+'.trace')).read_text().splitlines()
  assert got==trace,next(((i,x,y) for i,(x,y) in enumerate(zip(got,trace)) if x!=y),(len(got),len(trace)))
  print(name,len(code),'retirements',len(stores),'PEA requests PASS',flush=True)

# These mutations must be rejected by the independent request/next-PC checks.
source=(exp/'ap040_pipeline_integer.sv').read_text()
mutations={
 'next_pc':("id_next_pc <= in_pc + {29'd0, in_words, 1'b0};", "id_next_pc <= in_pc + 32'd2;"),
 'stack_forward':('wire [31:0] stack_value = wb_v && wb_we && wb_dst == 15 ? wb_data : rf_sp;',
                  'wire [31:0] stack_value = rf_sp;')}
for name,(before,after) in mutations.items():
 assert before in source
 poison=d/(name+'.sv');poison.write_text(source.replace(before,after))
 with (d/(name+'_compile.log')).open('w') as f:
  subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_pea','-o',str(d/(name+'.vvp')),
                  str(exp/'tb_pipeline_pea.sv'),str(poison),str(rtl/'ap040_regfile.v'),str(rtl/'ap040_alu.v')],stdout=f,stderr=subprocess.STDOUT,check=True)
 badcmd=cmd.copy();badcmd[1]=str(d/(name+'.vvp'))
 badcmd=[x if not x.startswith('+trace=') else '+trace='+str(d/(name+'.trace')) for x in badcmd]
 with (d/(name+'.log')).open('w') as f:result=subprocess.run(badcmd,stdout=f,stderr=subprocess.STDOUT)
 assert result.returncode!=0 or (d/(name+'.trace')).read_text().splitlines()!=trace, name+' escaped oracle'
 print('PASS: '+name+' mutation rejected',flush=True)
