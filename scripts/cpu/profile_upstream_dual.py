#!/usr/bin/env python3
"""Time upstream's synthetic differential test without changing either CPU.

This compares upstream pipeline versus upstream FSM, NOT our optimized Mac CPU.
Preserves the generated programs and their original final-register checks.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--upstream', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--verilator', default='/home/alans/verilator5/bin/verilator')
    args = ap.parse_args()
    root=args.upstream.resolve(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    pipe=root/'rtl/ap040_pipe'; fsm=root/'rtl/ap040'; tests=root/'tests/ap040'
    original=tests/'pipe/tb_ap040_pipe_dual.v'
    s=original.read_text()
    edits=[('integer cyc;', 'integer cyc; integer pcycles, fcycles;'),
           ('\t\tcyc = 0;', '\t\tcyc = 0; pcycles = 0; fcycles = 0;'),
           ('\t\t\tfdone = rd32f(DONE_ADDR);', '\t\t\tfdone = rd32f(DONE_ADDR);\n\t\t\tif(pdone != 0 && pcycles == 0) pcycles = cyc;\n\t\t\tif(fdone != 0 && fcycles == 0) fcycles = cyc;'),
           ('\t\tif (pdone == 32\'d1 && fdone == 32\'d1) begin', '\t\tif (pdone == 32\'d1 && fdone == 32\'d1) begin\n\t\t\t$display("SPEED round=%0d pipeline=%0d fsm=%0d",round,pcycles,fcycles);')]
    for before,after in edits:
        assert s.count(before)==1, before
        s=s.replace(before,after)
    tb=out/'tb_ap040_pipe_dual.v';tb.write_text(s)
    sources=[tb,*[pipe/(u+'.v') for u in (
        'ap040_pipe_core','ap040_pipe_cpu','ap040_pipe_sys','ap040_pipe_membus',
        'ap040_inst_fetch','ap040_decode','ap040_ea_calc','ap040_ea_fetch',
        'ap040_execute','ap040_writeback','ap040_pipe_alu','ap040_pipe_regfile',
        'ap040_pipe_l1','ap040_pipe_bus16')],*[fsm/(u+'.v') for u in (
        'ap040_tg68k_compat','ap040_core','ap040_bus16_adapter','ap040_regfile',
        'ap040_alu','ap040_muldiv','ap040_mmu','ap040_cache','ap040_fpu')],tests/'sim_dpram.v']
    (out/'identity.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [original,*sources]},indent=2)+'\n')
    with (out/'compile.log').open('w') as log:
        subprocess.run([args.verilator,'--binary','--timing','-Wno-fatal','-j','4',
                        '--top-module','tb_ap040_pipe_dual','--Mdir',str(out/'obj'),
                        '-I'+str(pipe),'-I'+str(fsm),*map(str,sources)],stdout=log,stderr=subprocess.STDOUT,check=True)
    with (out/'run.log').open('w') as log:
        subprocess.run([str(out/'obj/Vtb_ap040_pipe_dual')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    text=(out/'run.log').read_text()
    assert 'ALL TESTS PASSED' in text and 'FAIL' not in text, text[-3000:]
    rows=[dict(round=int(a),pipeline=int(b),fsm=int(c),ratio_fsm_over_pipeline=int(c)/int(b))
          for a,b,c in re.findall(r'SPEED round=(\d+) pipeline=(\d+) fsm=(\d+)',text)]
    assert len(rows)==16
    result=dict(scope='upstream generated register programs; upstream FSM baseline, not Mac',rounds=rows,
                aggregate_ratio=sum(r['fsm'] for r in rows)/sum(r['pipeline'] for r in rows))
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
