#!/usr/bin/env python3
"""Inventory unchanged Speedometer CODE3 Whetstone and its local helpers.

Static call-site counts are NOT dynamic frequencies or runtime costs.
External raw JSR targets still require relocation/runtime resolution.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import capstone

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('code3', type=Path)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
b = a.code3.read_bytes()
expected = '02123c6cb020961c79cbb66cbadef9247a1add4c480b421645d2a4a4c3fefc31'
assert hashlib.sha256(b).hexdigest() == expected, 'unexpected CODE3 resource'
m = capstone.Cs(capstone.CS_ARCH_M68K,
                capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_040)
a.out.mkdir(parents=True, exist_ok=True)
result = {'code3_sha256': expected, 'scope': __doc__, 'routines': []}
listing = []
for name, start, end in [('WStone', 0x8, 0x836),
                         ('helper_0840', 0x840, 0x92c),
                         ('helper_0932', 0x932, 0xb4e)]:
    assert b[start:start+2] == bytes.fromhex('4e56')
    assert b[end-2:end] == bytes.fromhex('4e75')
    pc = start
    traps, calls, histogram = [], [], Counter()
    while pc < end:
        if b[pc:pc+2] == bytes.fromhex('a9eb'):
            selector = (int.from_bytes(b[pc-2:pc], 'big')
                        if b[pc-4:pc-2] == bytes.fromhex('3f3c') else None)
            traps.append({'offset': hex(pc), 'stack_selector': selector})
            listing.append(f'{pc:04x}  a9eb          _FP68K selector={selector}')
            histogram['_FP68K'] += 1
            pc += 2
            continue
        instruction = next(m.disasm(b[pc:end], pc, count=1), None)
        assert instruction is not None, f'undecoded instruction at {pc:x}'
        assert instruction.mnemonic != 'dc.w', f'invalid word at {pc:x}'
        raw = b[pc:pc+instruction.size]
        if raw[:2] == bytes.fromhex('4eb9'):
            target = int.from_bytes(raw[2:], 'big')
            calls.append({'offset': hex(pc), 'raw_target': hex(target),
                          'local_code3_target': target in (0x840, 0x932)})
        listing.append(f'{pc:04x}  {raw.hex():14s} {instruction.mnemonic:12s} {instruction.op_str}')
        histogram[instruction.mnemonic] += 1
        pc += instruction.size
    assert pc == end
    result['routines'].append({'name': name, 'start': hex(start), 'end_exclusive': hex(end),
        'sha256': hashlib.sha256(b[start:end]).hexdigest(),
        'static_instruction_counts': dict(histogram.most_common()),
        'sane_calls': traps, 'absolute_jsr_calls': calls})
(a.out/'inventory.json').write_text(json.dumps(result, indent=2)+'\n')
(a.out/'routines.dis').write_text('\n'.join(listing)+'\n')
for r in result['routines']:
    print(r['name'], 'instructions=', sum(r['static_instruction_counts'].values()),
          'SANE sites=', len(r['sane_calls']), 'JSR sites=', len(r['absolute_jsr_calls']),
          'selectors=', dict(Counter(str(t['stack_selector']) for t in r['sane_calls'])))
