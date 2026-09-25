#!/usr/bin/env python3
"""Summarize a current simulator --cpu-profile TSV without calling dispatches CPI."""
import argparse
from pathlib import Path
import re

from pipeline_prototype import ROOT, workload, encode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--core", type=Path, default=ROOT / "rtl/ap68040/rtl/ap040_core.v")
    parser.add_argument("--verified-opcode-attribution", action="store_true",
                        help="show opcode coverage only when the producer attributes every dispatch correctly")
    args = parser.parse_args()
    rows = [line.split("\t") for line in args.profile.read_text().splitlines()]
    summaries = [r for r in rows if r[0] == "SUMMARY" and r[1].isdigit()]
    if len(summaries) != 1:
        parser.error("expected one numeric SUMMARY row")
    cycles, dispatches = map(int, summaries[0][1:3])
    states = [(int(r[1]), int(r[2])) for r in rows if r[0] == "STATE" and r[1].isdigit()]
    ops = [(int(r[1], 16), int(r[2])) for r in rows if r[0] == "OPCODE" and r[1] != "opcode"]
    if not cycles or not dispatches:
        parser.error("profile must contain nonzero cycles and dispatches")
    if sum(n for _, n in states) != cycles or sum(n for _, n in ops) != dispatches:
        parser.error("state/opcode totals do not match SUMMARY")
    names = {int(number): name for name, number in re.findall(
        r"localparam\s+(S_\w+)\s*=\s*8'd(\d+)", args.core.read_text())}
    supported = {encode(op) for op in workload()}
    coverage = sum(n for op, n in ops if op in supported)
    print(f"Profile: {args.profile}\n")
    print(f"{cycles:,} clocks; {dispatches:,} observed opcode loads; "
          f"{cycles / dispatches:.3f} clocks/opcode load.")
    print("Opcode loads include faulting instructions and may omit folded branches; this is not retirement CPI.")
    if args.verified_opcode_attribution:
        print(f"P0 supports {coverage:,} observed opcode loads ({100 * coverage / dispatches:.2f}%). "
              "This is instruction coverage, not cycle savings.\n")
    else:
        print("Opcode coverage omitted: the legacy ir histogram can misattribute pipeline dispatches.\n")
    print("| CPU state | Clocks | Share |\n|---|---:|---:|")
    for state, count in sorted(states, key=lambda row: row[1], reverse=True)[:20]:
        print(f"| {names.get(state, str(state))} | {count:,} | {100 * count / cycles:.2f}% |")
    if args.verified_opcode_attribution:
        print("\n| Opcode | Observed loads | P0 supported |\n|---|---:|---|")
        for opcode, count in sorted(ops, key=lambda row: row[1], reverse=True)[:20]:
            print(f"| {opcode:04X} | {count:,} | {'yes' if opcode in supported else 'no'} |")
    memory = [(r[1], r[2]) for r in rows if r[0] == "MEM" and r[1] != "name"]
    if memory:
        print("\nMemory counters can overlap; samples and entries are not cycle percentages.")
        print("\n| Memory counter | Value |\n|---|---:|")
        for name, value in memory:
            print(f"| {name} | {int(value):,} |")


if __name__ == "__main__":
    main()
