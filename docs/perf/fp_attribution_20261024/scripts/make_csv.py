#!/usr/bin/env python3
"""fp_attribution 2026-10-24: one CSV from the fpattr.py JSON files.

usage: make_csv.py out.csv kernel=core=file.json ...
Columns: kernel, core, class_key, class, cycles_per_iter, pct, instr_per_iter,
clk_per_instr, total_cycles_per_iter, total_instr_per_iter
"""
import csv, json, sys


def main():
    out = sys.argv[1]
    w = csv.writer(open(out, 'w', newline=''))
    w.writerow(['kernel', 'core', 'class_key', 'class', 'cycles_per_iter', 'pct', 'instr_per_iter',
                'clk_per_instr', 'total_cycles_per_iter', 'total_instr_per_iter'])
    for spec in sys.argv[2:]:
        kernel, core, path = spec.split('=', 2)
        j = json.load(open(path))
        for key, c in j['classes'].items():
            if c['count'] == 0 and c['cycles'] == 0:
                continue
            w.writerow([kernel, core, key, c['label'], '%.0f' % c['cycles'], '%.1f' % c['pct'],
                        '%.0f' % c['count'], '%.2f' % c['clk_per_instr'] if c['clk_per_instr'] is not None else '',
                        '%.0f' % j['cycles_per_iter'], '%.0f' % j['instr_per_iter']])
        w.writerow([kernel, core, 'total', 'total', '%.0f' % j['cycles_per_iter'], '100.0',
                    '%.0f' % j['instr_per_iter'], '%.2f' % (j['cycles_per_iter'] / j['instr_per_iter']),
                    '%.0f' % j['cycles_per_iter'], '%.0f' % j['instr_per_iter']])
    print('wrote', out)


if __name__ == '__main__':
    main()
