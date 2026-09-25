#!/usr/bin/env python3
"""Prepare original Whetstone plus original ROM runtime state for a CPU fixture.

Not a resumable Mac checkpoint: selected private RAM is replaced, CPU starts
at a new supervisor stub, and original low-memory reset words are restored.
Execution and an independent numerical oracle remain separate requirements.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mac_rsrc import Rsrc

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('fork',type=Path); p.add_argument('ram',type=Path)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=True)
r=Rsrc(a.fork); original=a.ram.read_bytes(); ram=bytearray(original)
assert len(ram)==32*1024*1024
bases={3:0x600000,6:0x610000};a5=0x620000;stub=0x630000;stack=0x640000
code3,_=r.get('CODE',3)
assert hashlib.sha256(code3).hexdigest()=='02123c6cb020961c79cbb66cbadef9247a1add4c480b421645d2a4a4c3fefc31'
# Explicitly construct a private fixture arena; never write the live guest.
ram[0x600000:0x640000]=bytes(0x40000)
changes=[]
for segment,limit in [(3,0xb4e),(6,0x1476)]:
    code,_=r.get('CODE',segment); code=bytearray(code[:limit])
    xref,_=r.get('XREF',segment);pos=0
    for kind in ['A5','CODE1','segment']:
        n=struct.unpack_from('>I',xref,pos)[0];pos+=4
        for field in struct.unpack_from('>'+str(n)+'I',xref,pos):
            if field>=limit:continue
            assert field+4<=limit
            # CODE6 before the used wrappers contains unrelated routines.
            if segment==6 and field<0x12d2:continue
            assert kind!='CODE1','fixture unexpectedly needs custom loader'
            raw=int.from_bytes(code[field:field+4],'big')
            value=(raw+(a5 if kind=='A5' else bases[segment]))&0xffffffff
            code[field:field+4]=value.to_bytes(4,'big')
            changes.append({'segment':segment,'field':hex(field),'kind':kind,'before':hex(raw),'after':hex(value)})
        pos+=4*n
    assert pos==len(xref)
    ram[bases[segment]:bases[segment]+len(code)]=code
# Original DATA0 blocks, followed by the same JMP materialization as CODE1.
data,_=r.get('DATA',0);pos=0
while True:
    n=struct.unpack_from('>I',data,pos)[0];pos+=4
    if not n:break
    off=struct.unpack_from('>i',data,pos)[0];pos+=4
    assert 0x618000<=a5+off<a5+0x1000 and pos+n<=len(data)
    ram[a5+off:a5+off+n]=data[pos:pos+n];pos+=n
assert pos==len(data)
slots=[]
for offset in [0x50,0x58,0x60,0x68,0x70,0x78]:
    address=a5+offset
    assert ram[address:address+2]==bytes.fromhex('a9f0')
    target,segment=struct.unpack_from('>IH',ram,address+2)
    assert segment==6 and 0x12d2<=target<0x1476
    ram[address:address+6]=bytes.fromhex('4ef9')+(bases[6]+target).to_bytes(4,'big')
    slots.append({'a5_offset':hex(offset),'target':hex(bases[6]+target)})
# The snapshot's supervisor map must map the complete private arena identically.
def u32(addr):
    assert 0<=addr<=len(original)-4
    return int.from_bytes(original[addr:addr+4],'big')
for va in range(0x600000,0x642000,8192):
    root=u32(0x1ff6c00+((va>>25)&127)*4);assert root&2
    pointer=u32((root&~511)+((va>>18)&127)*4);assert pointer&2
    page=u32((pointer&~127)+((va>>13)&31)*4)
    assert page&3 in (1,3) and (page&~8191)==va
asm=f''' org ${stub:x}
start:
 move.w #$2700,sr
 move.l #${u32(0):x},($0).l
 move.l #${u32(4):x},($4).l
 move.l #$1ff6c00,d0
 movec d0,srp
 moveq #0,d0
 movec d0,urp
 move.l #$c000,d0
 movec d0,tc
 move.l #$80008000,d0
 movec d0,cacr
 lea (${a5:x}).l,a5
 move.w #1,($f108).l
 jsr (${bases[3]+8:x}).l
 move.w #2,($f108).l
 move.w #$600d,($f102).l
 stop #$2700
'''
(d/'entry.s').write_text(asm)
with (d/'assemble.log').open('w') as log:
    subprocess.run(['/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot','-Fbin','-m68040','-no-opt','-o',str(d/'entry.bin'),str(d/'entry.s')],stdout=log,stderr=subprocess.STDOUT,check=True)
entry=(d/'entry.bin').read_bytes();assert len(entry)<512
ram[stub:stub+len(entry)]=entry
ram[:8]=struct.pack('>II',stack,stub)
(d/'ram.bin').write_bytes(ram)
manifest={'scope':__doc__,'ram_input_sha256':hashlib.sha256(original).hexdigest(),
 'ram_output_sha256':hashlib.sha256(ram).hexdigest(),'fork_sha256':hashlib.sha256(a.fork.read_bytes()).hexdigest(),
 'code3_sha256':hashlib.sha256(code3).hexdigest(),'relocations':changes,'slots':slots,
 'code_bases':{str(k):hex(v) for k,v in bases.items()},'a5':hex(a5),'stack':hex(stack),'entry':hex(stub),
 'status':'prepared only; no execution or numerical validation',
 'runtime':'original installed SANE dispatchers; trap sites remain unchanged until ROM runtime rewrites them'}
(d/'identity.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Prepared',len(ram),'bytes;',len(changes),'relocations;',len(slots),'runtime slots; execution pending')
