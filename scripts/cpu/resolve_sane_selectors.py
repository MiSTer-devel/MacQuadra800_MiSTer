#!/usr/bin/env python3
"""Resolve Whetstone-used selectors through the installed Quadra ROM dispatchers.

FP68K decoder follows 408E9A3A..408E9A7C; Elems68K follows 408EDD0E..408EDD18.
This is static dispatch resolution, not dynamic frequency or runtime cost.
"""
import argparse
import hashlib
import json
from pathlib import Path
from resolve_sane_rom import ROM_SHA

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('rom', type=Path)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args(); rom = a.rom.read_bytes()
if hashlib.sha256(rom).hexdigest() != ROM_SHA: p.error('unexpected ROM identity')
# Pin the dispatch bytes themselves, including the full PC-relative extension.
assert rom[0xe9a6e:0xe9a80].hex() == 'e158e508ebc0048a303b012002c441fb00ae'
assert rom[0xedd0e:0xedd1c].hex() == '323c003ec200323b10064efb10f4'

def fp68k(selector):
    if selector == 0: return 0x408eaa4c, None
    # ROL.W #8, LSL.B #2, BFEXTS D0{18:10}; index is a signed word.
    word = ((selector & 255) << 8) | (selector >> 8)
    word = (word & 0xff00) | ((word << 2) & 255)
    index = (word >> 4) & 1023
    if index & 512: index -= 1024
    table = 0xe9d3c + index
    return 0x408e9a2c + int.from_bytes(rom[table:table+2], 'big', signed=True), table

records = []
for name, selectors in [('FP68K', [0,2,4,6,8,13,18,8206]),
                        ('Elems68K', [0,8,0x18,0x1a,0x1e])]:
    for selector in selectors:
        if name == 'FP68K': target, table = fp68k(selector)
        else:
            table = 0xedd1c + (selector & 0x3e)
            target = 0x408edd0e + int.from_bytes(rom[table:table+2], 'big', signed=True)
        offset = target - 0x40800000
        assert 0 <= offset < len(rom)-16
        records.append({'trap': name, 'selector': hex(selector), 'target': hex(target),
                        'table_entry': hex(0x40800000+table) if table is not None else None,
                        'first_16_bytes': rom[offset:offset+16].hex()})
result = {'scope': __doc__, 'rom_sha256': ROM_SHA, 'selectors': records,
          'fp68k_callsite_rewrite': {'recognition': 'A9EB preceded by MOVE.W #selector,-(SP)',
              'replacement': 'six-byte JSR absolute to selected handler',
              'rom_code': '408E9A80..408E9A9A',
              'cache_maintenance': '408E9AD2..408E9B3A',
              'limit': 'conditional runtime rewrite; this tool does not modify guest code'}}
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(json.dumps(result, indent=2)+'\n')
for r in records: print(r['trap'], r['selector'], r['target'])
