#!/usr/bin/env python3
"""Compare identical Whetstone fixtures differing only in CPU core source.

Bitwise differential captures are not an independent numerical oracle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
b=json.loads((a.baseline/'identity.json').read_text());c=json.loads((a.candidate/'identity.json').read_text())
for key in ['image_sha256','rom_sha256','flags','latency']:
    if b[key]!=c[key]: raise ValueError('comparison changes '+key)
def supporting_sources(identity):
    files={Path(path).name:digest for path,digest in identity['sources'].items() if Path(path).name!='ap040_core.v'}
    if len(files)!=len(identity['sources'])-1: raise ValueError('ambiguous source names')
    return files
if supporting_sources(b)!=supporting_sources(c): raise ValueError('comparison changes non-core sources')
result={'scope':__doc__,'captures':{}}
for name in ['whet_stack.hex','whet_globals.hex','whet_code.hex']:
    x=(a.baseline/name).read_bytes();y=(a.candidate/name).read_bytes()
    result['captures'][name]={'equal':x==y,'baseline_sha256':hashlib.sha256(x).hexdigest(),'candidate_sha256':hashlib.sha256(y).hexdigest()}
    if x!=y: raise ValueError('differential output mismatch: '+name)
counts=[]
for path in [a.baseline,a.candidate]:
    log=(path/'run.log').read_text()
    if 'WHETSTONE RETURNED' not in log or 'Fatal' in log: raise ValueError('run incomplete or failed')
    counts.append(int(re.search(r'WHETSTONE_LOOP cycles=(\d+)',log)[1]))
result.update(baseline_cycles=counts[0],candidate_cycles=counts[1],reduction_percent=100*(counts[0]-counts[1])/counts[0],controlled_latency=b['latency'])
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
print('Differential captures match; loop clocks',*counts,'reduction %.3f%%'%result['reduction_percent'])
