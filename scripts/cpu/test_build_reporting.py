from pathlib import Path
import os, shutil, subprocess, tempfile
source = Path(__file__).resolve().parents[1] / 'build_only.sh'
with tempfile.TemporaryDirectory(prefix='quadra-build-status-') as tmp:
    root = Path(tmp)
    for directory in ['scripts', 'bin', 'output_files']:
        (root / directory).mkdir()
    shutil.copyfile(source, root/'scripts/build_only.sh')
    (root/'MacQuadra800.qsf').write_text('')
    (root/'scripts/local.env').write_text(f"QUARTUS_BIN='{root}/bin'\n")
    mock = root/'bin/quartus_sh'
    mock.write_text('''#!/usr/bin/env python3
import os
from pathlib import Path
p=Path('output_files')
if os.environ['CASE'] != 'stale':
    (p/'MacQuadra800.map.summary').write_text('Status : Successful\\n')
    (p/'MacQuadra800.fit.summary').write_text('Status : Successful\\n')
    (p/'MacQuadra800.rbf').write_bytes(b'new')
    if os.environ['CASE'] != 'no_timing':
        (p/'MacQuadra800.sta.summary').write_text('Slack : '+('-0.123' if os.environ['CASE']=='negative' else '0.123')+'\\n')
raise SystemExit(int(os.environ.get('FLOW_RC','0')))
''')
    mock.chmod(0o755)
    cases = [('stale','1',False), ('stale','0',False), ('no_timing','0',False), ('negative','0',False), ('positive','0',True)]
    for case,rc,ok in cases:
        for suffix in ['map.summary','fit.summary','sta.summary','rbf']:
            p=root/'output_files'/('MacQuadra800.'+suffix)
            p.write_text('Slack : -9.999\nStatus : Successful\n')
            os.utime(p,(1,1))
        result=subprocess.run(['bash','scripts/build_only.sh','--no-wait'],cwd=root,env={**os.environ,'CASE':case,'FLOW_RC':rc},text=True,capture_output=True)
        assert (result.returncode==0)==ok, result.stdout+result.stderr
        assert '-9.999' not in result.stdout, result.stdout
        if case=='stale':
            assert 'NO FRESH ARTIFACT' in result.stdout, result.stdout
            assert 'Timing (STA)           not generated for this run' in result.stdout, result.stdout
        if case=='no_timing':
            assert 'no fresh, parseable timing result' in result.stdout, result.stdout
        print(f'PASS case={case} flow_rc={rc} script_rc={result.returncode}')
