#!/usr/bin/env python3
"""Ensure legacy CPU runner checks simulator exit status as well as banners."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'rtl/ap68040/tb/run_tests.sh').read_text()
functions = source[source.index('fail=0\nrun()'):source.index('run reset ')]
mock = '''#!/bin/sh
case "$1" in
 pass) echo 'ALL TESTS PASSED'; exit 0 ;;
 late) echo 'ALL TESTS PASSED'; echo 'FATAL: final assertion'; exit 1 ;;
 failure_zero) echo 'ALL TESTS PASSED'; echo 'TEST FAILED'; exit 0 ;;
 no_banner) exit 0 ;;
 negative) echo 'FATAL: TEST FAILED: poisoned register'; exit 1 ;;
 unrelated) echo 'unrelated simulator failure'; exit 1 ;;
 negative_zero) echo 'TEST FAILED'; exit 0 ;;
esac
exit 99
'''
cases = [('run', 'pass', 0), ('run', 'late', 1),
         ('run', 'failure_zero', 1), ('run', 'no_banner', 1),
         ('negrun', 'negative', 0), ('negrun', 'unrelated', 1),
         ('negrun', 'negative_zero', 1)]
with tempfile.TemporaryDirectory(prefix='quadra-runner-status-') as directory:
    path = Path(directory)
    (path / 'vvp').write_text(mock)
    (path / 'vvp').chmod(0o755)
    env = dict(os.environ, WORK=str(path), PATH=str(path) + os.pathsep + os.environ['PATH'])
    for function, case, expected in cases:
        script = 'set -eu\n' + functions + f'\n{function} {case} {case}\ntest "$fail" -eq {expected}\n'
        result = subprocess.run(['sh', '-c', script], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit(f'runner status regression: {case}\n{result.stdout}')
print(f'LEGACY_RUNNER_STATUS PASS cases={len(cases)}')
