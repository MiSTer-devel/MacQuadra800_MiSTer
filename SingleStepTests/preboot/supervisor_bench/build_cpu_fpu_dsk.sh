#!/bin/bash
# build_cpu_fpu_dsk.sh -- assemble a 1.44MB HFS floppy that boots the
# CPU+FPU integration bench (macos_bench/cpu_fpu_tests.h).
#
# Patches two markers:
#   PAYLDOFF (boot stub) -> /Payload partition-relative byte offset
#   RJSNLTAG (payload)   -> /Results.jsonl partition-relative byte offset
set -euo pipefail

RB="${RB:-$HOME/repos/rusty-backup/target/release/rb-cli}"
OUT="${1:-/tmp/cpufpubench.dsk}"
BUILD=build
BOOT="$BUILD/boot_stub_patch.bin"
PAYLOAD="$BUILD/payload_cpu_fpu_scsi.bin"
RESULTS_SIZE=409600          # must be >= g_results_max_bytes in variant_cpu_scsi.s
IMG="$OUT"

[[ -x "$RB" ]] || { echo "rb-cli not found at $RB"; exit 1; }
command -v jq >/dev/null || { echo "jq required"; exit 1; }

make cpu_fpu
[[ -f "$BOOT" ]]    || { echo "missing $BOOT"; exit 1; }
[[ -f "$PAYLOAD" ]] || { echo "missing $PAYLOAD"; exit 1; }

rm -f "$OUT"
"$RB" new floppy --quiet hfs --size 1440K --name CPUFPUBench "$OUT" >/dev/null

put_get_off() {
    local host="$1" dst="$2" dec
    dec=$("$RB" put --print-offset --quiet "$IMG" "$host" "$dst" |
          jq -r '.result.offset - .result.partition_offset')
    printf '%x' "$dec"
}

"$RB" put --boot "$BOOT" --quiet "$IMG" >/dev/null
PAYLOAD_OFF=$(put_get_off "$PAYLOAD" /Payload)

"$RB" put --zero "$RESULTS_SIZE" --dst /Results.jsonl --quiet "$IMG" >/dev/null
RESULTS_OFF=$(
    "$RB" locate --quiet "$IMG" /Results.jsonl |
    jq -r '.result.offset - .result.partition_offset' |
    xargs printf '%x'
)

"$RB" fsck --quiet "$IMG" >/dev/null

python3 - "$OUT" "0x${PAYLOAD_OFF}" "0x${RESULTS_OFF}" <<'PY'
import struct, sys
image, payload_off, results_off = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0)
with open(image, "r+b") as f:
    data = f.read()
    p = data.find(b"PAYLDOFF")
    if p < 0: sys.exit("PAYLDOFF marker not found in boot stub")
    f.seek(p + 8); f.write(struct.pack(">I", payload_off))
    r = data.find(b"RJSNLTAG")
    if r < 0: sys.exit("RJSNLTAG marker not found in payload")
    f.seek(r + 8); f.write(struct.pack(">I", results_off))
    # PAYLCKSZ: how many bytes of the loaded image the boot block
    # checksums and shows on screen. Exactly the region HFS gave
    # /Payload, so the value never covers /Results.jsonl (which the
    # bench rewrites) and stays stable across runs.
    c = data.find(b"PAYLCKSZ")
    if c < 0: sys.exit("PAYLCKSZ marker not found in boot stub")
    ck_len = min(results_off - payload_off, 0x40000) & ~3
    if ck_len <= 0: sys.exit(f"bad checksum window {ck_len}")
    f.seek(c + 8); f.write(struct.pack(">I", ck_len))
print(f"patched: payload@0x{payload_off:X}, results@0x{results_off:X}, cksum window 0x{ck_len:X}")
PY

echo ""
echo "boot stub:  $BOOT ($(stat -c%s "$BOOT") bytes)"
echo "payload:    $PAYLOAD ($(stat -c%s "$PAYLOAD") bytes) @ byte 0x${PAYLOAD_OFF}"
echo "results:    @ byte 0x${RESULTS_OFF} ($RESULTS_SIZE bytes pre-allocated)"
echo ""
echo "wrote $OUT ($(stat -c%s "$OUT") bytes)"
