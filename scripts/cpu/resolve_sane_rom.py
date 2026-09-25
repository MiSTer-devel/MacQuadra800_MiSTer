#!/usr/bin/env python3
"""Resolve Quadra ROM SANE entries from its compressed Toolbox trap table.

This reports boot-ROM defaults, not the handlers installed by a running OS.
Decoder follows ROM 40809a96..40809adc; dispatch uses 408099b0..408099ec.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROM_SHA = '7d9cb8c3bae0e26171adf9f24bedf10bf6371ae3c9bdbcdfd3b94e5350099fb6'
BASE = 0x40800000


def toolbox_entries(rom):
    if hashlib.sha256(rom).hexdigest() != ROM_SHA:
        raise ValueError('unsupported ROM: decoder is verified for the Quadra 800 ROM only')
    pos = int.from_bytes(rom[0x22:0x26], 'big')
    target = BASE
    entries = []
    for _ in range(1024):
        value = rom[pos]
        pos += 1
        if value == 0x80:
            entries.append(BASE + 0x9ae6)  # unimplemented trap, 40809ae6
            continue
        if value == 0xff:
            target = BASE + int.from_bytes(rom[pos:pos+4], 'big')
            pos += 4
        else:
            if value < 0x80:
                value = (value << 8) | rom[pos]
                pos += 1
            else:
                value &= 0x7f
            if value == 0:
                raise ValueError('trap stream ended before all Toolbox entries')
            # ADD.W followed by ADDA.W sign-extends the doubled 16-bit delta.
            delta = (value * 2) & 0xffff
            target = (target + (delta if delta < 0x8000 else delta - 0x10000)) & 0xffffffff
        entries.append(target)
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    entries = toolbox_entries(rom)
    result = {'rom_sha256': ROM_SHA, 'scope': __doc__, 'traps': []}
    for trap, name, hook, fallback in [(0xa9eb, 'FP68K', 0xac8, 0x408262ae),
                                       (0xa9ec, 'Elems68K', 0xacc, 0x408262b0)]:
        entry = entries[trap & 0x3ff]
        off = entry - BASE
        # Verify the ROM entry actually reads the named low-memory hook.
        expected = bytes.fromhex('48e780c02038') + hook.to_bytes(2, 'big')
        if rom[off:off+len(expected)] != expected:
            raise ValueError(f'{name}: decoded entry does not match hook prologue')
        result['traps'].append({'trap': hex(trap), 'name': name,
            'table_address': hex(0xe00 + 4 * (trap & 0x3ff)),
            'rom_entry': hex(entry), 'low_memory_handle': hex(hook),
            'rom_fallback': hex(fallback),
            'dispatch': 'nonzero hook and nonzero handle contents dispatch to *hook; otherwise resource loader fallback',
            'entry_bytes': rom[off:off+34].hex()})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    for entry in result['traps']:
        print(entry['name'], 'table', entry['table_address'], 'ROM', entry['rom_entry'],
              'handle', entry['low_memory_handle'])


if __name__ == '__main__':
    main()
