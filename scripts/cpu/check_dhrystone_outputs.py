#!/usr/bin/env python3
"""Validate the original Speedometer Dhrystone fixture against derived end state.

This is the 16-bit Speedometer implementation, not a substituted Dhrystone 2.1.
No simulated baseline output supplies expected values.
"""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('image', type=Path)
p.add_argument('run', type=Path)
a = p.parse_args()
ram = a.image.read_bytes()
assert len(ram) == 33554432

def capture(name, length):
    values = [int(t, 16) for line in (a.run / name).read_text().splitlines()
              for t in line.split('//')[0].split()]
    assert len(values) == length, (name, len(values), length)
    return bytes(values)

# Proc5/Func2/Proc8 establish these globals on each iteration. Proc8's
# array address arithmetic uses 102-byte rows (51 16-bit columns).
globals_expected = bytearray(ram[0x61c000:0x620000])
def put(address, width, value):
    offset = address - 0x61c000
    globals_expected[offset:offset + width] = value.to_bytes(width, 'big')

for offset, width, value in [(-0x3536, 4, 0x638000), (-0x3532, 4, 0x638100),
                            (-0x2072, 2, 5), (-0x2073, 1, 1),
                            (-0x2074, 1, ord('A')), (-0x2075, 1, ord('B'))]:
    put(0x620000 + offset, width, value)
for index, value in [(8, 7), (9, 7), (38, 8)]:
    put(0x620000 - 0x20dc + 2 * index, 2, value)
counter = 0x620000 - 0x352e + 8 * 102 + 7 * 2
initial = int.from_bytes(ram[counter:counter + 2], 'big')
for row, col, value in [(8, 7, (initial + 50000) & 0xffff),
                         (8, 8, 8), (8, 9, 8), (28, 8, 7)]:
    put(0x620000 - 0x352e + row * 102 + col * 2, 2, value)
assert capture('dhry_globals.hex', 0x4000) == globals_expected, 'global/array mismatch'

# Proc1 copies the original record, then Proc3/Proc7 produce primary 17
# and secondary 18; Proc6 maps primary enumeration 2 to secondary 1.
records = bytearray(ram[0x638000:0x638128])
for offset, enumeration, integer in [(0, 1, 18), (0x100, 2, 17)]:
    record = (0x638000).to_bytes(4, 'big') + bytes([0, enumeration])
    record += integer.to_bytes(2, 'big') + b'DHRYSTONE PROGRAM, SOME STRING\0'
    records[offset:offset + len(record)] = record
assert capture('dhry_records.hex', 0x128) == records, 'record/guard mismatch'

regs = capture('dhry_regs.hex', 16)
assert int.from_bytes(regs[:2], 'big') == 50000, 'iteration counter'
# Original d72..d94 computes 7*(9 - 9/3) - 3 = 39.
assert int.from_bytes(regs[4:8], 'big') == 39, 'final D4'
assert int.from_bytes(regs[8:12], 'big') == ord('C'), 'final character loop'
a6 = int.from_bytes(regs[12:16], 'big')
assert a6 == 0x63fffc, 'frame address'
stack = capture('dhry_stack.hex', 0x400)
for offset, value in [(-2, 7), (-4, 9)]:
    index = a6 + offset - 0x63fc00
    assert int.from_bytes(stack[index:index + 2], 'big') == value, 'final local'
for offset, expected in [(-0x36, b"DHRYSTONE PROGRAM, 1'ST STRING\0"),
                         (-0x56, b"DHRYSTONE PROGRAM, 2'ND STRING\0")]:
    index = a6 + offset - 0x63fc00
    assert stack[index:index + len(expected)] == expected, 'local string'
assert capture('dhry_code.hex', 0x10fe - 0xbca) == ram[0x600bca:0x6010fe], 'code changed'
print(json.dumps({'status': 'PASS', 'iterations': 50000,
                  'checks': ['all captured globals/arrays', 'records and guards',
                             'final registers/locals/strings', 'unchanged code'],
                  'scope': 'Original loop fixture end state; not Mac timer or hardware validation'}))
