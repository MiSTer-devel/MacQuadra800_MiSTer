#!/usr/bin/env python3
"""Run unchanged Quadra ROM extended-add bytes in a small CPU fixture.

Synthetic exact operands exercise the SANE wrapper observed during Whetstone.
This is not the complete Whetstone workload or a MiSTer score prediction.
The existing CPU bench uses the 16-bit adapter, not the platform SDRAM path.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from resolve_sane_rom import ROM_SHA

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--prepare-only', action='store_true', help='write fixture and identity without compiling or running')
    p.add_argument('--stack', type=lambda x: int(x, 0), default=0xe000)
    p.add_argument('--mmu', choices=('off', '4k', '8k'), default='off')
    p.add_argument('--core', type=Path)
    p.add_argument('--fpu', type=Path)
    p.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
    a = p.parse_args()
    rom = a.rom.read_bytes()
    if hashlib.sha256(rom).hexdigest() != ROM_SHA:
        p.error('unexpected ROM identity')
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    kernel = rom[0xeaa4c:0xeaa92]
    assert len(kernel) == 70 and kernel[-4:] == bytes.fromhex('4e740008')
    (out/'add.bin').write_bytes(kernel)
    # All instructions in this wrapper use registers, stack-relative data or
    # immediate constants. No PC-relative/absolute code reference is relocated.
    asm = ''' org 0
 dc.l $e000,start
 rept 254
 dc.l fail
 endr
 org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
 move.l #$12345678,a6
 move.l #$13579bdf,a0
 move.w #99,d7
 move.w #1,($f108).l
again:
 pea ($2002).l
 pea ($2022).l
 jsr ($1000).l
 dbra d7,again
 move.w #2,($f108).l
 cmpa.l #$e000,sp
 bne fail
 cmpa.l #$12345678,a6
 bne fail
 cmpa.l #$13579bdf,a0
 bne fail
 cmp.w #$4005,($2022).l
 bne fail
 cmp.l #$cc000000,($2024).l
 bne fail
 tst.l ($2028).l
 bne fail
 cmp.w #$3fff,($2002).l
 bne fail
 cmp.l #$80000000,($2004).l
 bne fail
 tst.l ($2008).l
 bne fail
 cmp.w #$a55a,($2000).l
 bne fail
 cmp.w #$5aa5,($200c).l
 bne fail
 cmp.w #$a55a,($2020).l
 bne fail
 cmp.w #$5aa5,($202c).l
 bne fail
 move.w #$600d,($f102).l
 stop #$2700
fail:
 move.w #$bad0,($f102).l
 stop #$2700
 org $1000
 incbin "add.bin"
 org $2000
 dc.w $a55a,$3fff
 dc.l $80000000,0
 dc.w $5aa5
 org $2020
 dc.w $a55a,$4000
 dc.l $80000000,0
 dc.w $5aa5
'''
    if not 0xc000 <= a.stack < 0xf000 or a.stack & 1:
        p.error('stack must be word-aligned in C000..EFFF')
    asm = asm.replace('$e000', f'${a.stack:x}')
    if a.mmu != 'off':
        if not a.prepare_only:
            p.error('--mmu requires --prepare-only; page tables are supplied by the 32-bit bench')
        setup = ' move.l #$4000,d0\n movec d0,urp\n movec d0,srp\n move.l #$' + ('8000' if a.mmu == '4k' else 'c000') + ',d0\n movec d0,tc\n'
        asm = asm.replace(' move.l #$12345678,a6', setup + ' move.l #$12345678,a6')
    (out/'program.s').write_text(asm)

    def run(cmd, log):
        with (out/log).open('w') as f:
            proc = subprocess.run(list(map(str, cmd)), cwd=out, stdout=f, stderr=subprocess.STDOUT)
        content = (out/log).read_text()
        if proc.returncode:
            raise RuntimeError(content[-4000:])
        return content

    run([a.vasm, '-Fbin', '-m68040', '-no-opt', '-o', 'program.bin', 'program.s'], 'assemble.log')
    program = (out/'program.bin').read_bytes()
    assert program[0x1000:0x1046] == kernel
    run(['python3', ROOT/'rtl/ap68040/tb/bin2hex.py', 'program.bin', 'program.hex'], 'hex.log')
    rtl = ROOT/'rtl/ap68040/rtl'
    units = ['ap040_tg68k_compat', 'ap040_core', 'ap040_bus16_adapter',
             'ap040_bus_timeout', 'ap040_regfile', 'ap040_alu', 'ap040_muldiv',
             'ap040_mmu', 'ap040_cache', 'ap040_fpu', 'ap040_walker_cdc', 'primitives/dpram']
    sources = [ROOT/'rtl/ap68040/tb/tb_ap040_program.v']
    for unit in units:
        override = a.core if unit == 'ap040_core' else a.fpu if unit == 'ap040_fpu' else None
        sources.append(override.resolve() if override else rtl/(unit+'.v'))
    identity = {'scope': __doc__, 'rom_sha256': ROM_SHA,
                'rom_range': '408eaa4c..408eaa92 exclusive',
                'kernel_sha256': hashlib.sha256(kernel).hexdigest(),
                'program_sha256': hashlib.sha256(program).hexdigest(),
                'sources': {str(s): hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
                'oracle': '100 exact additions of 1 to 2 produce extended 102 = 4005:cc000000:00000000; source/guards/stack/A0/A6 unchanged',
                'pipeline': False, 'mmu': a.mmu, 'stack': hex(a.stack)}
    (out/'identity.json').write_text(json.dumps(identity, indent=2)+'\n')
    if a.prepare_only:
        return
    run(['iverilog', '-g2012', '-I', rtl, '-s', 'tb_ap040_program', '-o', 'bench.vvp', *sources], 'compile.log')
    result = run(['vvp', 'bench.vvp', '+prog=program.hex', '+prof', '+memlat'], 'run.log')
    if 'ALL TESTS PASSED' not in result:
        raise RuntimeError(result[-4000:])
    # Negative control: replace only FADD.X with FSUB.X in the fixture.
    # The independent 102 oracle must reject this otherwise executable code.
    poisoned = bytearray(program)
    arithmetic = 0x1000 + (0xeaa7a - 0xeaa4c)
    assert poisoned[arithmetic:arithmetic+4] == bytes.fromhex('f2174822')
    poisoned[arithmetic+3] = 0x28
    (out/'negative.bin').write_bytes(poisoned)
    run(['python3', ROOT/'rtl/ap68040/tb/bin2hex.py', 'negative.bin', 'negative.hex'], 'negative_hex.log')
    negative = run(['vvp', 'bench.vvp', '+prog=negative.hex', '+phase=0'], 'negative.log')
    if 'TEST FAILED' not in negative or 'ALL TESTS PASSED' in negative:
        raise RuntimeError('subtraction negative control did not fail as required: ' + negative[-2000:])
    print('PASS: subtraction negative control rejected')
    print('\n'.join(line for line in result.splitlines() if 'STAMP' in line or 'passed' in line or 'ALL TESTS' in line))


if __name__ == '__main__':
    main()
