#!/usr/bin/env python3
"""Check the 64-byte refill selector against an independent halfword-array oracle."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--core", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
source = args.core.read_text()
start = source.index("\t\tif (brf_seed_req) begin : brf_seed_data")
end = source.index("\n\t\t// Queue bookkeeping", start)
root = Path(__file__).resolve().parents[2]
template = (root / "scripts/fixtures/tb_refill_seed_alignment.sv").read_text()
assert template.count("// CANDIDATE_SEED_BLOCK") == 1
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
tb = out / "tb.sv"
tb.write_text(template.replace("// CANDIDATE_SEED_BLOCK", source[start:end]))
subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", str(out / "test.vvp"), str(tb)], check=True)
subprocess.run(["vvp", str(out / "test.vvp")], check=True)
