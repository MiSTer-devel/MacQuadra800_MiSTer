#!/usr/bin/env python3
"""Compare unchanged kernel fixtures on the Mac CPU and an isolated upstream CPU.

The RAM response contract is identical, but the Mac includes its cache/MMU/store
buffer and upstream does not. Results describe these paths, not isolated IPC or
Speedometer scores. An upstream reset ISP poke is explicit in the testbench.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
NAMES = ('queens', 'bubble', 'permute', 'towers')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--upstream', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    for name in NAMES:
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--verilator', default='/home/alans/verilator5/bin/verilator')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--latencies', default='0,3,8')
    ap.add_argument('--variants', default='upstream,current')
    ap.add_argument('--kernels', default=','.join(NAMES))
    args = ap.parse_args()
    if not set(args.variants.split(',')) <= {'upstream', 'current'}:
        ap.error('--variants must contain upstream and/or current')
    if not set(args.kernels.split(',')) <= set(NAMES):
        ap.error('--kernels contains an unknown name')
    if any(int(x) < 0 for x in args.latencies.split(',')):
        ap.error('latencies must be nonnegative')
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    rtl = ROOT / 'rtl/ap68040/rtl'
    pipe = args.upstream.resolve() / 'rtl/ap040_pipe'
    tb = ROOT / 'verilator/tb_cpu_upstream_compare.sv'
    fixtures = [getattr(args, name).resolve() for name in NAMES]
    flags = ['-DAP040_EXPERIMENTAL_' + x for x in
             ('XSTORE', 'LEA', 'PIPELINE', 'PIPELINE_LOADS', 'PIPELINE_STORES', 'PIPELINE_PEA', 'PIPELINE_P6')]
    flags += ['-DAP040_PIPELINE_' + x for x in ('MEMORY_ENTRY', 'COMPARE', 'EARLY_DRAIN')]
    units = ('ap040_core', 'ap040_bus_timeout', 'ap040_regfile', 'ap040_alu',
             'ap040_muldiv', 'ap040_mmu', 'ap040_cache', 'ap040_fpu', 'primitives/dpram')
    sources = {
        'current': [tb, ROOT/'rtl/wombat_cpu.sv', ROOT/'rtl/wombat_store_buffer.sv',
                    *[rtl/(u+'.v') for u in units], ROOT/'rtl/ap68040/experimental/ap040_pipeline_integer.sv'],
        'upstream': [tb, *[pipe/(u+'.v') for u in (
            'ap040_pipe_sys', 'ap040_pipe_cpu', 'ap040_pipe_membus', 'ap040_inst_fetch',
            'ap040_decode', 'ap040_ea_calc', 'ap040_ea_fetch', 'ap040_execute',
            'ap040_writeback', 'ap040_pipe_alu', 'ap040_pipe_regfile')]]}
    rows = []
    for variant in args.variants.split(','):
        d = out / variant; d.mkdir(exist_ok=True)
        src = sources[variant]
        opts = flags if variant == 'current' else ['-DUPSTREAM_PIPE']
        headers = list((rtl if variant == 'current' else pipe).glob('*.svh'))
        identity = {'headers': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in headers},
                    'sources': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in src},
                    'fixtures': {name: {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                                 for name, p in zip(NAMES, fixtures)}, 'defines': opts,
                    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
        (d/'identity.json').write_text(json.dumps(identity, indent=2)+'\n')
        with (d/'compile.log').open('w') as log:
            subprocess.run([args.verilator, '--binary', '--timing', '-Wno-fatal', '-Wno-BLKLOOPINIT',
                                '-j', str(args.jobs), '--top-module', 'tb_cpu_upstream_compare',
                                '--Mdir', str(d/'obj'), '-I'+str(rtl if variant == 'current' else pipe),
                                *opts, *map(str, src)], stdout=log, stderr=subprocess.STDOUT, check=True)
        for index, (name, program) in enumerate(zip(NAMES, fixtures)):
            if name not in args.kernels.split(','):
                continue
            for latency in map(int, args.latencies.split(',')):
                path = d / f'{name}-latency{latency}.log'
                with path.open('w') as log:
                    try:
                        rc = subprocess.run([str(d/'obj/Vtb_cpu_upstream_compare'), '+prog='+str(program),
                                             '+kernel='+str(index), '+latency='+str(latency)],
                                            stdout=log, stderr=subprocess.STDOUT, timeout=180).returncode
                    except subprocess.TimeoutExpired:
                        rc = 'timeout'
                text = path.read_text()
                match = re.search(r'BENCH PASS kernel=\d+ cycles=(\d+) latency=\d+ fetches=(\d+) reads=(\d+) writes=(\d+)', text)
                row = dict(variant=variant, kernel=name, latency=latency, returncode=rc,
                           passed=rc == 0 and bool(match), log=str(path))
                if row['passed']:
                    row.update(zip(('cycles','fetches','reads','writes'), map(int, match.groups())))
                else:
                    row['failure'] = '\n'.join(text.splitlines()[-6:])
                rows.append(row)
                (out/'results.json').write_text(json.dumps(rows, indent=2)+'\n')
                print(json.dumps(row), flush=True)
    # Failed kernels are recorded, never assigned a speedup.
    print(f'{sum(r["passed"] for r in rows)}/{len(rows)} benchmark runs passed', flush=True)


if __name__ == '__main__':
    main()
