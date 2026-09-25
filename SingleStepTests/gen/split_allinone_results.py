#!/usr/bin/env python3
"""Split an all-in-one bench disk's /Results.jsonl into per-suite files.

Usage:
  split_allinone_results.py <image.hda.manifest.json> <results-or-image> [outdir]

<results-or-image> is either the extracted /Results.jsonl (the hardware
workflow: pull the file off the disk) or the whole .hda (the manifest
carries the absolute offset). Each suite's region is carved out, NULs
stripped, and written to <outdir>/<suite>.jsonl with a line count report.
"""
import json
import os
import sys


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    manifest_path, blob_path = sys.argv[1], sys.argv[2]
    outdir = sys.argv[3] if len(sys.argv) == 4 else "."
    with open(manifest_path) as f:
        m = json.load(f)
    size = os.path.getsize(blob_path)
    base = 0 if size == m["results_size"] else m["results_abs_offset"]
    os.makedirs(outdir, exist_ok=True)
    with open(blob_path, "rb") as f:
        for s in m["suites"]:
            f.seek(base + s["region_offset"])
            raw = f.read(s["region_size"]).replace(b"\x00", b"")
            lines = [ln for ln in raw.split(b"\n") if ln.strip()]
            out = os.path.join(outdir, f"{s['suite']}.jsonl")
            with open(out, "wb") as o:
                o.write(b"\n".join(lines) + (b"\n" if lines else b""))
            bad = sum(1 for ln in lines if not _is_json(ln))
            print(f"{s['suite']:12s} {len(lines):5d} rows, {len(raw):6d} bytes"
                  f"{'' if bad == 0 else f', {bad} UNPARSEABLE'} -> {out}")
    return 0


def _is_json(line: bytes) -> bool:
    try:
        json.loads(line)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    sys.exit(main())
