#!/usr/bin/env python3
"""Independent ordered-store oracle: all register pairs, sizes and modes."""
from pathlib import Path
import argparse
import subprocess
from pipeline_prototype import ROOT, workload, encode
import pipeline_address_oracle as address
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
r=ROOT;d=args.out.resolve();d.mkdir(parents=True,exist_ok=True)
rtl=r/'rtl/ap68040/rtl';exp=r/'rtl/ap68040/experimental'
regs=[0]*16;ccr=0;words=[];trace=[];stores=[]
def emit(kind,*a):
 global ccr
 pc=0x400+2*len(words)
 if kind=='q':
  dest,val=a;word=0x7000+dest*512+(val&255);regs[dest]=val&0xffffffff
  ccr=(ccr&16)|(8 if val<0 else 4 if val==0 else 0)
 elif kind=='a':
  src,dest=a;word=0x2040+dest*512+src;regs[8+dest]=regs[src]
 elif kind=='add':
  dest,=a;word=0x5280+dest;old=regs[dest];v=(old+1)&0xffffffff;regs[dest]=v
  ccr=(17 if old==0xffffffff else 0)|(8 if v&0x80000000 else 4 if v==0 else 0)|(2 if old==0x7fffffff else 0)
 else:
  src,dest,size,mode=a;sz={1:1,2:3,4:2}[size];word=(sz<<12)+(dest<<9)+(mode<<6)+src
  val=regs[src];base=regs[8+dest];step=2 if size==1 and dest==7 else size
  addr=(base-step)&0xffffffff if mode==4 else base
  stores.append((pc,addr,val,{1:0,2:1,4:2}[size]))
  if mode==4:regs[8+dest]=addr
  if mode==3:regs[8+dest]=(base+step)&0xffffffff
  v=val&((1<<(8*size))-1);ccr=(ccr&16)|(8 if v&(1<<(8*size-1)) else 4 if v==0 else 0)
 words.append(word);trace.append(f'{pc:08x} {word:04x} {ccr:02x}'+''.join(f' {v:08x}' for v in regs))
for src in range(16):
 for dest in range(8):
  for size in ((1,2,4) if src<8 else (2,4)):
   for mode in (2,3,4):
    emit('q',7,80);emit('a',7,dest)
    if src>=8:emit('a',7,src-8)
    else:emit('q',src,[-128,-1,0,1,127][(src+dest+size+mode)%5])
    emit('q',6,-1);emit('add',6) # establish X=1 before MOVE
    emit('s',src,dest,size,mode)
# Immediate pointer and source dependencies, with no setup between stores.
emit('q',0,96);emit('a',0,0);emit('q',1,17)
for _ in range(12):
 emit('s',1,0,4,3);emit('s',8,0,4,3);emit('s',1,0,4,4)
(d/'instructions.hex').write_text('\n'.join(f'{w:04x}' for w in words)+'\n')
(d/'oracle.trace').write_text('\n'.join(trace)+'\n')
(d/'stores.hex').write_text('\n'.join(f'{pc:08x}{addr:08x}{val:08x}{size:01x}' for pc,addr,val,size in stores)+'\n')
supported={encode(op) for op in workload()}|{address.encode(op) for op in address.workload()}|set(words)
# Probe only the same register map plus the complete legal store map.
(d/'supported.hex').write_text('\n'.join(str(int(w in supported)) for w in range(65536))+'\n')
units=[exp/'tb_pipeline_stores.sv',exp/'ap040_pipeline_integer.sv',rtl/'ap040_regfile.v',rtl/'ap040_alu.v']
with (d/'compile.log').open('w') as f:subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_stores','-o',str(d/'test.vvp'),*map(str,units)],stdout=f,stderr=subprocess.STDOUT,check=True)
for mode in (0,1):
 for delay in (0,1,3,8):
  name=f'm{mode}_d{delay}';cmd=['vvp',str(d/'test.vvp'),'+program='+str(d/'instructions.hex'),'+trace='+str(d/(name+'.trace')),'+count='+str(len(words)),'+registers=16','+mode='+str(mode),'+delay='+str(delay),'+stores='+str(d/'stores.hex'),'+requests='+str(len(stores)),'+supported='+str(d/'supported.hex')]
  with (d/(name+'.log')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  got=(d/(name+'.trace')).read_text().splitlines()
  assert got==trace, next(((i,x,y) for i,(x,y) in enumerate(zip(got,trace)) if x!=y),(len(got),len(trace)))
  print(name,len(words),'retirements',len(stores),'stores PASS',flush=True)

# A wrong address-register update must fail the independent retirement oracle.
poison=d/'bad_update.sv'
store_src=(exp/'ap040_pipeline_integer.sv').read_text()
store_old='wb_data <= ex_store ? store_update : (ex_load && ex_dst[3]) ?'
store_new="wb_data <= ex_store ? (store_update ^ 32'd1) : (ex_load && ex_dst[3]) ?"
if store_src.count(store_old) != 1:
 raise SystemExit(f'bad An-update mutation expected one target, found {store_src.count(store_old)}')
poison.write_text(store_src.replace(store_old,store_new,1))
with (d/'negative_compile.log').open('w') as f:
 subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_stores','-o',str(d/'negative.vvp'),
                 str(exp/'tb_pipeline_stores.sv'),str(poison),str(rtl/'ap040_regfile.v'),str(rtl/'ap040_alu.v')],stdout=f,stderr=subprocess.STDOUT,check=True)
cmd[1]=str(d/'negative.vvp'); cmd=[x if not x.startswith('+trace=') else '+trace='+str(d/'negative.trace') for x in cmd]
with (d/'negative.log').open('w') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
assert result.returncode != 0 or (d/'negative.trace').read_text().splitlines()!=trace, 'bad An update escaped oracle'
print('PASS: incorrect store An update rejected',flush=True)

with (d/'cancel_compile.log').open('w') as f:
 subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_store_cancel','-o',str(d/'cancel.vvp'),
                 str(exp/'tb_pipeline_store_cancel.sv'),str(exp/'ap040_pipeline_integer.sv'),
                 str(rtl/'ap040_regfile.v'),str(rtl/'ap040_alu.v')],stdout=f,stderr=subprocess.STDOUT,check=True)
with (d/'cancel.log').open('w') as f:
 subprocess.run(['vvp',str(d/'cancel.vvp')],stdout=f,stderr=subprocess.STDOUT,check=True)
assert 'STORE CANCEL PASS' in (d/'cancel.log').read_text()
print('PASS: older WB commits while younger store/register are cancelled',flush=True)

poison=d/'bad_cancel.sv'
src=(exp/'ap040_pipeline_integer.sv').read_text()
old='nreset && ce && !flush && !kill_younger &&\n        ex_v && ex_load'
if src.count(old) != 1:
 raise SystemExit(f'cancel-offer mutation expected one target, found {src.count(old)}')
poison.write_text(src.replace(old,'nreset && ce && !flush &&\n        ex_v && ex_load',1))
with (d/'cancel_negative_compile.log').open('w') as f:
 subprocess.run(['iverilog','-g2012','-I',str(rtl),'-s','tb_pipeline_store_cancel','-o',str(d/'cancel_negative.vvp'),
                 str(exp/'tb_pipeline_store_cancel.sv'),str(poison),str(rtl/'ap040_regfile.v'),str(rtl/'ap040_alu.v')],stdout=f,stderr=subprocess.STDOUT,check=True)
with (d/'cancel_negative.log').open('w') as f:
 result=subprocess.run(['vvp',str(d/'cancel_negative.vvp')],stdout=f,stderr=subprocess.STDOUT)
assert result.returncode != 0 and 'store offer escaped cancellation' in (d/'cancel_negative.log').read_text()
print('PASS: cancelled-store offer mutation rejected',flush=True)
