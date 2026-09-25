#!/usr/bin/env python3
"""Run the original Speedometer integer Matrix routine in the shared CPU/RAM harness."""
import runpy
import sys
from pathlib import Path
sys.argv[1:1] = ['--kernel', 'matrix']
runpy.run_path(str(Path(__file__).with_name('profile_quick.py')), run_name='__main__')
