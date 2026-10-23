#!/usr/bin/env python3
"""Check the microcode branch restriction used by experiment24.
Usage: python3 check_fp_branch_kinds.py /path/to/ap68040_faster
Importing the generator builds its tables without rewriting generated RTL.
"""
import importlib.util
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "tools"))
spec = importlib.util.spec_from_file_location("cpu66_ucode", root / "tools/ucode.py")
ucode = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ucode)
fp = []
dynamic = []
for name, words in ucode.ROUTINES.items():
    for index, word in enumerate(words):
        fields = word.f
        if fields["op"] == "FPU":
            assert fields["br"] in (None, "COND"), (name, index, fields)
            fp.append(fields["br"])
        if fields["op"] == "EOP":
            assert fields["br"] is None, (name, index, fields)
            dynamic.append((name, index))
useq = (root / "rtl/ap68040_useq.sv").read_text()
assignments = re.findall(r"nu\.br\s*=\s*([^;]+);", useq)
assert assignments == ["uw.br"], assignments
print(f"PASS: {len(fp)} explicit FPU uops: {fp.count(None)} NONE, "
      f"{fp.count('COND')} COND; {len(dynamic)} dynamic EOP uops all NONE; "
      "sequencer copies uw.br unchanged")
