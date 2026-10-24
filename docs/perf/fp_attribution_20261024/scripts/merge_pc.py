#!/usr/bin/env python3
"""fp_attribution 2026-10-24: side-by-side per-address costs of the two cores
on the same binary, from the JSON files fpattr.py writes (its 'top' lists).

usage: merge_pc.py new.json old.json [--lo 0xADDR --hi 0xADDR] [--top N]
With --lo/--hi, every address in the range that either core's top list holds
is printed in address order (an annotated hot loop); otherwise the top N
addresses by the two cores' summed cycles.
"""
import argparse, json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('new'); ap.add_argument('old')
    ap.add_argument('--lo', type=lambda x: int(x, 0)); ap.add_argument('--hi', type=lambda x: int(x, 0))
    ap.add_argument('--top', type=int, default=25)
    a = ap.parse_args()
    n = json.load(open(a.new)); o = json.load(open(a.old))
    rows = {}
    for src, j in (('new', n), ('old', o)):
        for t in j.get('all', j['top']):
            pc = int(t['pc'], 16)
            r = rows.setdefault(pc, {'text': t['text'], 'class': t['class']})
            r[src] = (t['count'], t['cycles'])
    if a.lo is not None:
        sel = sorted(pc for pc in rows if a.lo <= pc <= a.hi)
    else:
        sel = sorted(rows, key=lambda pc: -(rows[pc].get('new', (0, 0))[1] + rows[pc].get('old', (0, 0))[1]))[:a.top]
    print('%-8s %-7s %-34s %9s | %10s %7s | %10s %7s | %6s' % ('pc', 'class', 'instruction', 'count/it', 'dual cyc', 'clk/ins', 'ship cyc', 'clk/ins', 'ratio'))
    for pc in sel:
        r = rows[pc]
        nc, ncy = r.get('new', (0, 0)); oc, ocy = r.get('old', (0, 0))
        cnt = nc or oc
        print('%08x %-7s %-34s %9.0f | %10.0f %7.2f | %10.0f %7.2f | %6s' % (
            pc, r['class'], r['text'], cnt, ncy, ncy / nc if nc else 0, ocy, ocy / oc if oc else 0,
            '%.2f' % (ncy / ocy) if ocy and nc and oc else '-'))


if __name__ == '__main__':
    main()
