#!/usr/bin/env python3
"""Speedometer 4.02 integer Matrix fixture, v2: profile_quick_v2.py --kernel matrix.

Same harness, macros, snapshot rule (--rtl-root), negative control and
profile as the Quick Sort v2 runner; see its docstring.
"""
import runpy
import sys
from pathlib import Path
sys.argv[1:1] = ['--kernel', 'matrix']
runpy.run_path(str(Path(__file__).with_name('profile_quick_v2.py')), run_name='__main__')
