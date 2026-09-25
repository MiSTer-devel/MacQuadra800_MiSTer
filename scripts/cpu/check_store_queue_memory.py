#!/usr/bin/env python3
"""Check a candidate queue against the registered-first-miss SDRAM path."""
import argparse
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--candidate', type=pathlib.Path, required=True)
p.add_argument('--out', type=pathlib.Path, required=True)
p.add_argument('--verilator', default='/home/alans/verilator5/bin/verilator')
a = p.parse_args()
for label, source in [('baseline', root/'rtl/wombat_store_buffer.sv'),
                      ('candidate', a.candidate.resolve())]:
    for posted in (0, 1):
        out = a.out.resolve()/f'{label}_posted{posted}'
        out.mkdir(parents=True, exist_ok=True)
        cmd = [a.verilator, '--binary', '--timing', '-j', '4', '-Wno-fatal',
               '-Wno-WIDTH', '-Wno-UNSIGNED', '-Wno-CMPCONST', '-Wno-DECLFILENAME',
               '+define+SIMULATION=1', '--top-module', 'tb_memory_path',
               f'-GPOSTED={posted}', '-GFAST_BYPASS=1', '-GDIRECT_FIRST_MISS=1',
               '-GREGISTERED_FIRST_MISS=1', '-GADAPTER_LINE_HIT=1',
               '-GDIRECT_MEM_ACK=0', '-GREGISTERED_LINE_HIT=1',
               '--Mdir', str(out/'obj'), '-o', 'run_memory',
               str(root/'scripts/cpu/tb_store_queue_memory.sv'), str(source),
               *[str(root/f) for f in ('verilator/tb_sdram.sv',
                 'rtl/wombat_bus32.sv', 'rtl/sdram_beat32.sv', 'rtl/sdram.sv',
                 'verilator/altddio_out_stub.v')]]
        with (out/'compile.log').open('w') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
        with (out/'run.log').open('w') as log:
            subprocess.run([str(out/'obj/run_memory')], stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        text = (out/'run.log').read_text()
        assert 'tb_memory_path: OK' in text, text
        print(f'{label} posted={posted}: PASS (data and SDRAM protocol)', flush=True)
