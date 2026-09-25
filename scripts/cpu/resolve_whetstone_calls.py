#!/usr/bin/env python3
"""Resolve original Speedometer Whetstone calls using DATA0 and XREF3.

Loader evidence: CODE1 offsets 0x284..0x2da add A5, CODE1 base and current
segment base to three respective XREF groups. DATA0 is a length/offset/data
stream. A5 slots contain A9F0, a segment-relative long and a segment word;
CODE1 0x1d0..0x1ee rewrites these into absolute JMPs when loading a segment.
This reconstructs static destinations, not live guest trap-handler addresses.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mac_rsrc import Rsrc
import capstone

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('fork',type=Path)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
r=Rsrc(a.fork)
code3,_=r.get('CODE',3)
assert hashlib.sha256(code3).hexdigest()=='02123c6cb020961c79cbb66cbadef9247a1add4c480b421645d2a4a4c3fefc31'
data,_=r.get('DATA',0);xref,_=r.get('XREF',3)
mem={};pos=0
while True:
    n=struct.unpack_from('>I',data,pos)[0];pos+=4
    if n==0:break
    off=struct.unpack_from('>i',data,pos)[0];pos+=4
    assert pos+n<=len(data)
    mem.update((off+i,v) for i,v in enumerate(data[pos:pos+n]));pos+=n
assert pos==len(data)
groups={};pos=0
for kind in ['A5','CODE1','segment']:
    n=struct.unpack_from('>I',xref,pos)[0];pos+=4
    groups[kind]=set(struct.unpack_from('>'+str(n)+'I',xref,pos));pos+=4*n
assert pos==len(xref)
m=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_BIG_ENDIAN|capstone.CS_MODE_M68K_040)
calls=[];helpers={};listing=[]
for i in m.disasm(code3[8:0x836],8):
    if i.bytes[:2]!=bytes.fromhex('4eb9'):continue
    field=i.address+2;raw=int.from_bytes(i.bytes[2:],'big')
    kinds=[k for k,v in groups.items() if field in v]
    assert len(kinds)==1,(hex(field),kinds)
    call={'call_offset':hex(i.address),'raw_target':hex(raw),'relocation':kinds[0]}
    if kinds[0]=='segment':
        assert raw in (0x840,0x932)
        call.update(segment=3,offset=hex(raw))
    else:
        assert kinds==['A5']
        slot=bytes(mem[raw+j] for j in range(8))
        assert slot[:2]==bytes.fromhex('a9f0')
        off,seg=struct.unpack('>IH',slot[2:]);call.update(segment=seg,offset=hex(off))
        key=f'CODE{seg}:{off:04x}'
        if key not in helpers:
            b,_=r.get('CODE',seg);pc=off;traps=[];instructions=[]
            while pc<off+512:
                ins=next(m.disasm(b[pc:],pc,count=1),None)
                assert ins is not None
                word=int.from_bytes(b[pc:pc+2],'big')
                if word in (0xa9eb,0xa9ec):
                    assert b[pc-4:pc-2]==bytes.fromhex('3f3c')
                    traps.append({'offset':hex(pc),'trap':hex(word),'selector':hex(int.from_bytes(b[pc-2:pc],'big'))})
                instructions.append(f'{pc:04x} {ins.mnemonic:12s} {ins.op_str}')
                pc+=ins.size
                if ins.mnemonic=='rts':break
            else:raise AssertionError('helper boundary not found')
            helpers[key]={'start':hex(off),'end_exclusive':hex(pc),'sha256':hashlib.sha256(b[off:pc]).hexdigest(),'traps':traps}
            listing.extend([key,*instructions,''])
    calls.append(call)
assert len(calls)==15 and len(helpers)==6
(a.out/'resolved_calls.json').write_text(json.dumps({'scope':__doc__,'calls':calls,'helpers':helpers},indent=2)+'\n')
(a.out/'runtime_helpers.dis').write_text('\n'.join(listing)+'\n')
for key,h in helpers.items():print(key,h['traps'])
print('PASS all15 call sites have exactly one relocation;13 external sites resolve to6CODE6 helpers')
