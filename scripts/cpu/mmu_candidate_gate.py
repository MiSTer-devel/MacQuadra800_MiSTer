#!/usr/bin/env python3
"""Run existing real-core MMU programs against an isolated MMU source."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--mmu-module', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--program', type=Path, help='run only this assembly fixture')
p.add_argument('--monitor', type=Path, help='additional mmu_copy_monitor module')
a = p.parse_args()
out = a.out.resolve()
out.mkdir(parents=True, exist_ok=True)
rtl = root / 'rtl/ap68040/rtl'
tb = root / 'rtl/ap68040/tb'
programs = ('t_mmu', 't_bitfield_mmu', 't_atcprobe', 't_moves_fc', 't_exceptions')
units = ('ap040_tg68k_compat', 'ap040_core', 'ap040_bus16_adapter',
         'ap040_bus_timeout', 'ap040_regfile', 'ap040_alu', 'ap040_muldiv',
         'ap040_cache', 'ap040_fpu', 'ap040_walker_cdc', 'primitives/dpram')
sources = [tb / 'tb_ap040_program.v', a.mmu_module.resolve(),
           root / 'rtl/ap68040/experimental/ap040_pipeline_integer.sv',
           *[rtl / (u + '.v') for u in units]]
if a.monitor:
    sources.append(a.monitor.resolve())
flags = ['-DAP040_EXPERIMENTAL_' + x for x in
         ('XSTORE', 'LEA', 'PIPELINE', 'PIPELINE_LOADS', 'PIPELINE_STORES',
          'PIPELINE_PEA', 'PIPELINE_P6')]
flags += ['-DAP040_PIPELINE_COMPARE', '-DAP040_PIPELINE_MEMORY_ENTRY',
          '-DAP040_PIPELINE_EARLY_DRAIN']
fixtures = [a.program.resolve()] if a.program else [tb / 'asm' / (t + '.s') for t in programs]
(out / 'identity.json').write_text(json.dumps({str(f): hashlib.sha256(f.read_bytes()).hexdigest()
    for f in sources + fixtures}, indent=2))

def run(command, logfile):
    with (out / logfile).open('w') as log:
        subprocess.run(list(map(str, command)), stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=600)

run(['iverilog', '-g2012', '-I', rtl, '-s', 'tb_ap040_program', *flags,
     *( ['-s', 'mmu_copy_monitor'] if a.monitor else []), '-o', out / 'test.vvp', *sources], 'compile.log')
for fixture in fixtures:
    t = fixture.stem
    run(['/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot',
         '-Fbin', '-m68040', '-no-opt', '-o', out / (t + '.bin'),
         fixture], t + '.asm.log')
    run(['python3', tb / 'bin2hex.py', out / (t + '.bin'), out / (t + '.hex')], t + '.hex.log')
    run(['vvp', out / 'test.vvp', '+prog=' + str(out / (t + '.hex'))], t + '.log')
    log = (out / (t + '.log')).read_text()
    assert 'ALL TESTS PASSED' in log and 'FAIL:' not in log and 'TEST FAILED' not in log, log[-3000:]
    print('PASS', t, flush=True)
