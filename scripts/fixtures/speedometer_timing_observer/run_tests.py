#!/usr/bin/env python3
import argparse,hashlib,pathlib,re,subprocess,tempfile
here=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--resource',type=pathlib.Path,default=pathlib.Path('/tmp/speedo402-unar/Speedometer 4.02.rsrc'))
args=parser.parse_args()
resource=args.resource.read_bytes()
assert hashlib.sha256(resource).hexdigest()=='af67113bceb4eb906e973a9b747a0b1925b9d64c62f0f9a84bc6f0578839ca80'
for sig,offset in [('3b7c0004beaa3b7c0092beac',0x6571d),('3b7c0004beaa3b7c00e2beac',0x65ba5)]:
    pattern=bytes.fromhex(sig)
    assert resource.count(pattern)==1 and resource[offset:offset+12]==pattern
header=(here/'speedometer_observer.h').read_text()
points=re.findall(r'\{(0x657[0-9a-f]+),(0x[0-9a-f]+),"',header)
assert len(points)==20
for offset,opcode in points:
    for delta in (0,0x494):
        i=int(offset,16)+delta
        assert int.from_bytes(resource[i:i+2],'big')==int(opcode,16),(offset,opcode,hex(delta))
out=pathlib.Path(tempfile.mkdtemp(prefix='speedometer-observer-test.'))
subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-O2',str(here/'test_observer.cpp'),'-o',str(out/'test')],check=True)
with (out/'test.log').open('w') as f:subprocess.run([str(out/'test')],check=True,stdout=f,stderr=subprocess.STDOUT)
print((out/'test.log').read_text().splitlines()[-1]);print('PASS immutable signatures +40 event-opcode checks');print('OUT',out)
