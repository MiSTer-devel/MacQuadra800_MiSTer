#!/usr/bin/env python3
"""Run one explicit CPU assembly fixture and reject silent simulator failures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
for name in ('asm', 'core', 'cache', 'pipeline', 'out'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--monitor', action='append', default=[], metavar='FILE:TOP')
p.add_argument('--expect', action='append', default=[], help='required literal in simulation output')
p.add_argument('--plusarg', action='append', default=[], help='simulator argument without leading +')
p.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
a = p.parse_args()
out = a.out.resolve()
if out.exists():
    p.error('output directory already exists; choose a fresh directory')
rtl = ROOT / 'rtl/ap68040/rtl'
units = ('ap040_tg68k_compat', 'ap040_bus16_adapter', 'ap040_bus_timeout',
         'ap040_regfile', 'ap040_alu', 'ap040_muldiv', 'ap040_mmu',
         'ap040_fpu', 'ap040_walker_cdc', 'primitives/dpram')
sources = [ROOT / 'rtl/ap68040/tb/tb_ap040_program.v', a.core.resolve(),
           a.cache.resolve(), a.pipeline.resolve(), *[rtl / (u + '.v') for u in units]]
tops = ['-s', 'tb_ap040_program']
for spec in a.monitor:
    file, top = spec.rsplit(':', 1)
    sources.append(Path(file).resolve())
    tops += ['-s', top]
asm = a.asm.resolve()
for file in [asm, *sources]:
    if not file.is_file():
        p.error(f'missing input: {file}')
flags = ['-DAP040_EXPERIMENTAL_' + x for x in
         ('XSTORE', 'LEA', 'PIPELINE', 'PIPELINE_LOADS', 'PIPELINE_STORES', 'PIPELINE_PEA', 'PIPELINE_P6')]
flags += ['-DAP040_PIPELINE_COMPARE', '-DAP040_PIPELINE_MEMORY_ENTRY', '-DAP040_PIPELINE_EARLY_DRAIN']
out.mkdir(parents=True)
def hashes():
    return {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in [asm, *sources]}
identity = {'sources': hashes(), 'flags': flags, 'commands': []}
def run(cmd, log):
    cmd = list(map(str, cmd))
    identity['commands'].append(cmd)
    (out / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    with (out / log).open('w') as f:
        result = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    text = (out / log).read_text()
    if result.returncode:
        raise RuntimeError(f'{log}: exit {result.returncode}\n{text[-2000:]}')
    return text
run([a.vasm, '-Fbin', '-m68040', '-no-opt', '-o', out / 'test.bin', asm], 'assemble.log')
run(['python3', ROOT / 'rtl/ap68040/tb/bin2hex.py', out / 'test.bin', out / 'test.hex'], 'hex.log')
run(['iverilog', '-g2012', '-I', rtl, *tops, *flags, '-o', out / 'test.vvp', *sources], 'compile.log')
log = run(['vvp', out / 'test.vvp', '+prog=' + str(out / 'test.hex'),
           *['+' + x for x in a.plusarg]], 'run.log')
if 'ALL TESTS PASSED' not in log or any(x in log for x in ('FAIL', 'FATAL', 'ERROR')):
    raise RuntimeError('simulator did not pass cleanly; inspect ' + str(out / 'run.log'))
for expected in a.expect:
    if expected not in log:
        raise RuntimeError('missing required evidence: ' + expected)
if hashes() != identity['sources']:
    raise RuntimeError('input sources changed during the run')
(out / 'PASS.txt').write_text('ALL TESTS PASSED; expected evidence found; input hashes unchanged.\n')
print(out / 'PASS.txt')
