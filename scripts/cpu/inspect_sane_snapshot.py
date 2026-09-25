#!/usr/bin/env python3
"""Read SANE slots and handles using captured supervisor page tables.

This is a physical RAM snapshot, not an architectural checkpoint. Translation
is a read-only page-table walk matching ap040_mmu.v; it does not model ATC or
transparent-translation registers. Low-memory identity results are consistent
with transparent translation as well. Nonidentity results need that caveat.
"""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('ram', type=Path)
p.add_argument('--tc', type=lambda s: int(s, 0), required=True)
p.add_argument('--srp', type=lambda s: int(s, 0), required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args(); ram = a.ram.read_bytes()

def read32(addr):
    if not 0 <= addr <= len(ram)-4:
        raise ValueError(f'physical address {addr:08x} outside captured RAM')
    return int.from_bytes(ram[addr:addr+4], 'big')

def translate(addr):
    if not a.tc & 0x8000:
        return addr, []
    trace = []
    def descriptor(location):
        value = read32(location)
        trace.append({'address': hex(location), 'value': hex(value)})
        return value
    root = descriptor((a.srp & ~511) + ((addr >> 25) & 127)*4)
    if not root & 2: raise ValueError('invalid root descriptor')
    pointer = descriptor((root & ~511) + ((addr >> 18) & 127)*4)
    if not pointer & 2: raise ValueError('invalid pointer descriptor')
    shift = 13 if a.tc & 0x4000 else 12
    table_mask = 127 if shift == 13 else 255
    page = descriptor((pointer & ~table_mask) + ((addr >> shift) & ((1 << (18-shift))-1))*4)
    if page & 3 == 2:
        page = descriptor(page & ~3)
    if page & 3 not in (1, 3): raise ValueError('invalid page descriptor')
    mask = (1 << shift)-1
    return (page & ~mask) | (addr & mask), trace

def inspect(addr):
    physical, walk = translate(addr)
    return {'virtual': hex(addr), 'physical': hex(physical),
            'value': hex(read32(physical)), 'walk': walk}

result = {'scope': __doc__, 'ram_sha256': hashlib.sha256(ram).hexdigest(),
          'ram_bytes': len(ram), 'tc': hex(a.tc), 'srp': hex(a.srp),
          'aline_vector': inspect(0x28), 'traps': []}
for name, slot, hook in [('FP68K', 0x15ac, 0xac8), ('Elems68K', 0x15b0, 0xacc)]:
    record = {'name': name, 'slot': inspect(slot), 'hook': inspect(hook)}
    handle = int(record['hook']['value'], 16)
    if handle: record['handle'] = inspect(handle)
    result['traps'].append(record)
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(json.dumps(result, indent=2)+'\n')
for t in result['traps']:
    print(t['name'], 'slot target', t['slot']['value'], 'handle target', t.get('handle', {}).get('value'))
