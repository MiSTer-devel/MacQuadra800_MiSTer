#!/usr/bin/env python3
"""Exact ROM SANE add fixture through wombat_cpu, cache and ordered write queue.

Controlled 32-bit RAM latency, no platform SDRAM or retained-line shortcut.
Optional real MMU supports 4K/8K identity or remapped operand pages. Synthetic exact operands, not the full Whetstone workload.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('rom', type=Path)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--core', type=Path)
p.add_argument('--fpu', type=Path)
p.add_argument('--mmu', choices=('off', '4k', '8k'), default='off')
p.add_argument('--stack', type=lambda x: int(x, 0), default=0xe000)
p.add_argument('--require-fpu-crossing', action='store_true')
p.add_argument('--remap', action='store_true')
p.add_argument('--latencies', nargs='+', type=int, default=[0, 3, 8])
a = p.parse_args()
if any(x < 0 for x in a.latencies):
    p.error('latencies must be nonnegative')
if a.remap and a.mmu == 'off':
    p.error('--remap requires --mmu')
d = a.out.resolve(); d.mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, str(ROOT/'scripts/cpu/profile_sane_add.py'), str(a.rom.resolve()), '--out', str(d), '--prepare-only', '--mmu', a.mmu, '--stack', hex(a.stack)], check=True)
rtl = ROOT/'rtl/ap68040/rtl'
units = ['ap040_core', 'ap040_bus_timeout', 'ap040_regfile', 'ap040_alu',
         'ap040_muldiv', 'ap040_mmu', 'ap040_cache', 'ap040_fpu', 'primitives/dpram']
sources = [ROOT/'scripts/cpu/tb_cpu_sane.sv', ROOT/'rtl/wombat_cpu.sv',
           ROOT/'rtl/wombat_store_buffer.sv', ROOT/'rtl/ap68040/experimental/ap040_pipeline_integer.sv']
for unit in units:
    override = a.core if unit == 'ap040_core' else a.fpu if unit == 'ap040_fpu' else None
    sources.append(override.resolve() if override else rtl/(unit+'.v'))
flags = ['-DAP040_EXPERIMENTAL_'+x for x in ('XSTORE', 'LEA', 'PIPELINE', 'PIPELINE_LOADS', 'PIPELINE_STORES', 'PIPELINE_PEA', 'PIPELINE_P6')]
flags += ['-DAP040_PIPELINE_MEMORY_ENTRY', '-DAP040_PIPELINE_COMPARE', '-DAP040_PIPELINE_EARLY_DRAIN']
identity = json.loads((d/'identity.json').read_text())
identity.update(scope=__doc__, pipeline=True, mmu=a.mmu, remap=a.remap, require_fpu_crossing=a.require_fpu_crossing, flags=flags,
                sources={str(s): hashlib.sha256(s.read_bytes()).hexdigest() for s in sources}, latencies=a.latencies)
(d/'identity.json').write_text(json.dumps(identity, indent=2)+'\n')

def run(cmd, log, expect_failure=False):
    with (d/log).open('w') as f:
        proc = subprocess.run(list(map(str, cmd)), cwd=d, stdout=f, stderr=subprocess.STDOUT)
    content = (d/log).read_text()
    if (proc.returncode != 0) != expect_failure:
        raise RuntimeError(content[-4000:])
    return content

run(['/home/alans/verilator5/bin/verilator', '--binary', '--timing', '-Wno-fatal', '-Wno-BLKLOOPINIT', '-j', '4', '--top-module', 'tb_cpu_sane', '--Mdir', d/'obj', '-I'+str(rtl), *flags, *sources], 'compile32.log')
runtime = [f'+mmu={0 if a.mmu == "off" else 12 if a.mmu == "4k" else 13}', f'+remap={int(a.remap)}', f'+require_cross={int(a.require_fpu_crossing)}']
for latency in a.latencies:
    result = run([d/'obj/Vtb_cpu_sane', '+prog='+str(d/'program.hex'), f'+latency={latency}', *runtime], f'run32_latency{latency}.log')
    assert 'SANE_ADD PASS' in result
    if a.mmu != 'off': assert 'MMU PASS' in result
    print('\n'.join(x for x in result.splitlines() if x.startswith(('SANE_', 'LATENCY', 'MMU', 'FPU_CROSS'))), flush=True)
# Independent guest oracle and host memory oracle must reject wrong arithmetic.
poisoned = bytearray((d/'program.bin').read_bytes())
assert poisoned[0x102e:0x1032] == bytes.fromhex('f2174822')
poisoned[0x1031] = 0x28
(d/'negative.bin').write_bytes(poisoned)
run([sys.executable, ROOT/'rtl/ap68040/tb/bin2hex.py', 'negative.bin', 'negative.hex'], 'negative_hex.log')
negative = run([d/'obj/Vtb_cpu_sane', '+prog='+str(d/'negative.hex'), '+latency=3', *runtime], 'negative32.log', expect_failure=True)
assert 'guest failed' in negative and 'SANE_ADD PASS' not in negative
print('PASS: subtraction negative control rejected', flush=True)
