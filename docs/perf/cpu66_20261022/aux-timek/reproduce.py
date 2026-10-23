#!/usr/bin/env python3
"""Read-only extraction and simulation of A/UX's exact SetUpTimeK routine.
Requires Verilator and vasmm68k_mot. No guest binary is included in the repo.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from aux_coff import Coff
from aux_ufs import UFS, read_partitions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True, help='raw A/UX 3.1 1GB .dsk/.hda, opened read-only')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--vasm', default='vasmm68k_mot')
    parser.add_argument('--rtl-source-root', type=Path, default=ROOT, help='optional isolated older source snapshot')
    args = parser.parse_args()
    design = args.rtl_source_root.resolve()
    dest = args.out.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    with args.image.open('rb') as f:
        parts = read_partitions(f)
    for part in parts:
        if part.type != 'Apple_UNIX_SVR2':
            continue
        try:
            fs = UFS(args.image, part_off=part.start)
        except ValueError:
            continue
        kernel = fs.read(fs.lookup('/unix'))
        break
    else:
        raise ValueError('No valid UFS root slice with /unix')
    (dest / 'unix.bin').write_bytes(kernel)
    c = Coff(dest / 'unix.bin')
    code = c.d[c.off(0x55ce4):c.off(0x55d8c)]
    expected = json.loads((HERE / 'source.json').read_text())
    assert hashlib.sha256(code).hexdigest() == expected['routine_sha256'], 'Different kernel: inspect symbol addresses before using this repro'
    (dest / 'SetUpTimeK.bin').write_bytes(code)
    for name in ['prog.s', 'tb_aux_timek.sv']:
        shutil.copy2(HERE / name, dest / name)
    # Test-only control of the existing CPU input; production port list is unchanged.
    wrapper = (design / 'rtl/quadra_cpu040.sv').read_text()
    wrapper = wrapper.replace('input         clk,', 'input         clk,\n\tinput [3:0] dbcc_floor_test,', 1)
    wrapper, count = re.subn(r'\.dbcc_floor\((?:4\'d0|CPU_DBCC_FLOOR)\)', '.dbcc_floor(dbcc_floor_test)', wrapper)
    assert count == 1
    (dest / 'quadra_cpu040.sv').write_text(wrapper)
    subprocess.run([args.vasm, '-m68040', '-Fbin', '-quiet', '-o', 'prog.bin', 'prog.s'], cwd=dest, check=True)
    data = (dest / 'prog.bin').read_bytes()
    assert len(data) % 4 == 0
    (dest / 'prog.hex').write_text('\n'.join(data[i:i + 4].hex() for i in range(0, len(data), 4)) + '\n')
    rtl = design / 'rtl/ap68040_faster/rtl'
    files = [str(rtl / n) for n in re.findall(r'"([^"\n]*v)"', (rtl / 'ap68040.qip').read_text())]
    common = ['verilator', '--binary', '--timing', '-j', '8', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-I' + str(rtl), '-I' + str(rtl / 'gen'), '-I' + str(rtl / 'fpu'), '--top-module', 'tb_aux_timek']
    for mode in ['2x', '1x']:
        cmd = common + (['+define+CPU_AP68040_2X=1'] if mode == '2x' else [])
        cmd += ['--Mdir', str(dest / ('obj_' + mode)), '-o', 'tb_aux_timek'] + files
        cmd += [str(dest / 'quadra_cpu040.sv'), str(design / 'rtl/via6522.sv'), str(dest / 'tb_aux_timek.sv')]
        with (dest / ('build-' + mode + '.log')).open('w') as out:
            subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT, check=True)
    for mode, floor, stall in [('2x', 0, True), ('2x', 4, False), ('1x', 0, False)]:
        cmd = [str(dest / ('obj_' + mode) / 'tb_aux_timek'), f'+floor={floor}'] + (['+expect_stall'] if stall else [])
        result = subprocess.run(cmd, cwd=dest, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        (dest / f'run-{mode}-floor{floor}.log').write_text(result.stdout)
        assert 'PASS:' in result.stdout
        print(result.stdout.split('PASS:', 1)[1].splitlines()[0].strip())


if __name__ == '__main__':
    main()
