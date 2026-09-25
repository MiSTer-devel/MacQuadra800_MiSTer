#!/usr/bin/env python3
"""Check precise bus faults during FPU extended operand and FMOVEM stores.

Uses the existing CPU bench: F140 bus fault, or an invalid MMU page at 2000.
This is a fault-ordering gate, not a platform memory-performance benchmark.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

_p = Path(__file__).resolve(); R = _p.parents[2] if (_p.parents[2]/'rtl').exists() else _p.parents[3]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--core', type=Path, required=True)
p.add_argument('--cache', type=Path, required=True)
p.add_argument('--pipeline-module', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--mmu', choices=('off','4k','8k'), default='off')
a = p.parse_args(); d = a.out.resolve(); d.mkdir(parents=True, exist_ok=True)
rtl = R/'rtl/ap68040/rtl'
units = ['ap040_tg68k_compat', 'ap040_bus16_adapter', 'ap040_bus_timeout',
         'ap040_regfile', 'ap040_alu', 'ap040_muldiv', 'ap040_mmu',
         'ap040_cache', 'ap040_fpu', 'ap040_walker_cdc', 'primitives/dpram']
sources = [R/'rtl/ap68040/tb/tb_ap040_program.v', a.core.resolve(),
           a.pipeline_module.resolve(),
           *(rtl/(u+'.v') for u in units if u != 'ap040_cache'), a.cache.resolve()]
flags = ['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE','LEA','PIPELINE','PIPELINE_LOADS','PIPELINE_STORES','PIPELINE_PEA','PIPELINE_P6')]
flags += ['-DAP040_PIPELINE_COMPARE','-DAP040_PIPELINE_MEMORY_ENTRY','-DAP040_PIPELINE_EARLY_DRAIN']
(d/'identity.json').write_text(json.dumps({'scope': __doc__, 'flags': flags, 'mmu': a.mmu,
    'sources': {str(x): hashlib.sha256(x.read_bytes()).hexdigest() for x in sources}}, indent=2)+'\n')

def run(cmd, log):
    with (d/log).open('w') as f:
        proc = subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT)
    content = (d/log).read_text()
    if proc.returncode: raise RuntimeError(content[-3000:])
    return content

run(['iverilog','-g2012','-I',rtl,'-s','tb_ap040_program',*flags,'-o',d/'bench.vvp',*sources], 'compile.log')
for mode in ('postinc', 'predec', 'movem'):
    for word in range(3):
        fault_address = 0xf140 if a.mmu == 'off' else 0x2000
        base = fault_address-4*word
        initial = base+12 if mode=='predec' else base
        op = 'fmove.x fp0,(a0)+' if mode=='postinc' else ('fmove.x fp0,-(a0)' if mode=='predec' else 'fmovem.x fp0,(a0)')
        name = f'{mode}_word{word}'
        prefix_checks = ''
        if word >= 1:
            prefix_checks += f' cmp.l #$40050000,(${base:x}).l\n bne fail\n'
        if word >= 2:
            prefix_checks += f' cmp.l #$c6000000,(${base+4:x}).l\n bne fail\n'
        asm = f''' org 0
 dc.l $7000,start,handler
 rept 253
 dc.l fail
 endr
 org $400
start:
 move.w #$2700,sr
 moveq #0,d0
 movec d0,cacr
 fmove.l #99,fp0
 movea.l #${initial:x},a0
 moveq #$55,d2
faulting:
 {op}
 moveq #7,d2
 bra fail
handler:
 cmp.w #$2700,(sp)
 bne fail
 cmp.l #faulting,2(sp)
 bne fail
 cmp.l #${fault_address:x},20(sp)
 bne fail
 cmpa.l #${initial:x},a0
 bne fail
 cmp.l #$55,d2
 bne fail
 move.w 6(sp),d0
 and.w #$f000,d0
 cmp.w #$7000,d0
 bne fail
 fmove.l fp0,d1
 cmp.l #99,d1
 bne fail
{prefix_checks} move.w #$600d,($f102).l
 stop #$2700
fail:
 move.w #$bad0,($f102).l
 stop #$2700
'''
        if a.mmu != 'off':
            shift = 12 if a.mmu == '4k' else 13
            setup = ' move.l #$4203,($4000).l\n move.l #$4403,($4200).l\n'
            for page in range(65536 >> shift):
                desc = 0 if page == (0x2000 >> shift) else (page << shift) | 3
                setup += f' move.l #${desc:x},(${0x4400+4*page:x}).l\n'
            setup += ' move.l #$4000,d0\n movec d0,urp\n movec d0,srp\n'
            setup += ' move.l #$'+('8000' if shift == 12 else 'c000')+',d0\n movec d0,tc\n'
            asm = asm.replace(' fmove.l #99,fp0', setup+' fmove.l #99,fp0')
            # Prove translation remains enabled in the exception handler.
            asm = asm.replace('handler:\n', 'handler:\n movec tc,d0\n btst #15,d0\n beq fail\n')
        for expected in ('cmp.l #$40050000', 'cmp.l #$c6000000')[:word]:
            assert 0 < asm.index(expected) < asm.index('move.w #$600d')
        (d/(name+'.s')).write_text(asm)
        run(['/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot','-Fbin','-m68040','-no-opt','-o',d/(name+'.bin'),d/(name+'.s')],name+'_asm.log')
        run(['python3',R/'rtl/ap68040/tb/bin2hex.py',d/(name+'.bin'),d/(name+'.hex')],name+'_hex.log')
        result = run(['vvp',d/'bench.vvp','+prog='+str(d/(name+'.hex'))],name+'.log')
        if 'ALL TESTS PASSED' not in result or 'FAIL' in result or 'FATAL' in result: raise RuntimeError(name+': '+result[-3000:])
        print(name, 'PASS (all bus phases)', flush=True)
