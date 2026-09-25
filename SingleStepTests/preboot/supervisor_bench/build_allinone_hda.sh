#!/bin/bash
# build_allinone_hda.sh -- one SCSI-bootable .hda that chains EVERY suite:
#   cpu -> fpu -> saverestore -> mmu_full -> integration (last: both
#   emulators die in its corpus tail, so it must not block the chain).
# Each payload's DONE point jumps to a stub at $7C000 that _Reads the
# next payload over $40000 (the boot block's own load step, repeated).
# All suites append into ONE 1 MB /Results.jsonl at fixed per-suite
# regions; g_results_max_bytes is sized per region so an overrun cannot
# cross into the next suite's region.
#
# Inputs:
#   $1 -- template .hda (defaults to ~/testdisk.hda; APM + Apple_HFS @1)
#   $2 -- output .hda   (defaults to /tmp/allinone.hda)
# Flavor: pass EXTRA_ASFLAGS="--defsym BOOT_SET_DTT0=1" in the env for
# the emulator build; the script forwards it to make so the finding-23
# footgun (make re-run without the flag) cannot bite here.
set -euo pipefail

RB="${RB:-$HOME/repos/rusty-backup/target/release/rb-cli}"
TEMPLATE="${1:-$HOME/testdisk.hda}"
OUT="${2:-/tmp/allinone.hda}"
BUILD=build
BOOT="$BUILD/boot_stub_patch.bin"
RESULTS_SIZE=1048576
IMG="${OUT}@1"

# Suite order is load-bearing: emulators validate suites 1-4 fully and
# suite 5 only to ~row 972 (test-blockers finding 23).
SUITES=(cpu fpu saverestore mmu_full integration)
PAYLOADS=("$BUILD/payload_cpu_scsi.bin"
          "$BUILD/payload_fpu_scsi.bin"
          "$BUILD/payload_cpu_fpu_save_restore_scsi.bin"
          "$BUILD/payload_mmu_full_scsi.bin"
          "$BUILD/payload_cpu_fpu_scsi.bin")
FILES=(/Payload /Payload2 /Payload3 /Payload4 /Payload5)
# Region sizes: measured single-suite outputs + headroom (cpu 205K,
# fpu 136K, sr 1K, mmu-full 25K, integration 157K). max_bytes = region
# minus one writer batch (16K; mmu-full batches 48K), because the last
# flush writes a whole zero-padded batch.
REGION_SIZES=(262144 180224 32768 98304 262144)
BATCH_SIZES=(16384 16384 16384 49152 16384)

[[ -x "$RB" ]]       || { echo "rb-cli not found at $RB"; exit 1; }
[[ -f "$TEMPLATE" ]] || { echo "missing template $TEMPLATE"; exit 1; }
command -v jq >/dev/null || { echo "jq required"; exit 1; }

make cpu fpu cpu_fpu_save_restore mmu_full cpu_fpu EXTRA_ASFLAGS="${EXTRA_ASFLAGS:-}"
[[ -f "$BOOT" ]] || { echo "missing $BOOT"; exit 1; }
for p in "${PAYLOADS[@]}"; do [[ -f "$p" ]] || { echo "missing $p"; exit 1; }; done
for p in "${PAYLOADS[@]}"; do
    sz=$(stat -c%s "$p")
    # Read extent must stay below the $7C000 chain stub (payload_entry_cpu.s).
    (( sz <= 245760 )) || { echo "$p is $sz bytes, past the 0x3C000 chain limit"; exit 1; }
done

cp -f "$TEMPLATE" "$OUT"

"$RB" put --boot "$BOOT" --quiet "$IMG" >/dev/null

ABS=(); REL=(); SIZES=()
for i in "${!PAYLOADS[@]}"; do
    j=$("$RB" put --print-offset --quiet "$IMG" "${PAYLOADS[$i]}" "${FILES[$i]}")
    ABS+=($(jq -r '.result.offset' <<<"$j"))
    REL+=($(jq -r '.result.offset - .result.partition_offset' <<<"$j"))
    SIZES+=($(stat -c%s "${PAYLOADS[$i]}"))
done

"$RB" put --zero "$RESULTS_SIZE" --dst /Results.jsonl --quiet "$IMG" >/dev/null
RJ=$("$RB" locate --quiet "$IMG" /Results.jsonl)
RES_ABS=$(jq -r '.result.offset' <<<"$RJ")
RES_REL=$(jq -r '.result.offset - .result.partition_offset' <<<"$RJ")

"$RB" fsck --quiet "$IMG" >/dev/null

python3 - "$OUT" "$RES_ABS" "$RES_REL" "$RESULTS_SIZE" \
    "${SUITES[*]}" "${ABS[*]}" "${REL[*]}" "${SIZES[*]}" \
    "${REGION_SIZES[*]}" "${BATCH_SIZES[*]}" <<'PY'
import json, struct, sys

image = sys.argv[1]
res_abs, res_rel, res_size = (int(x) for x in sys.argv[2:5])
suites   = sys.argv[5].split()
abs_off  = [int(x) for x in sys.argv[6].split()]
rel_off  = [int(x) for x in sys.argv[7].split()]
sizes    = [int(x) for x in sys.argv[8].split()]
regions  = [int(x) for x in sys.argv[9].split()]
batches  = [int(x) for x in sys.argv[10].split()]
n = len(suites)
assert sum(regions) <= res_size, "regions overflow /Results.jsonl"

with open(image, "r+b") as f:
    data = f.read()

    def patch(pos, *longs):
        f.seek(pos)
        for v in longs: f.write(struct.pack(">I", v))

    def find_in(marker, lo, hi):
        p = data.find(marker, lo, hi)
        if p < 0: sys.exit(f"{marker} not found in [{lo:#x},{hi:#x})")
        if data.find(marker, p + 1, hi) >= 0:
            sys.exit(f"{marker} ambiguous in [{lo:#x},{hi:#x})")
        return p

    # Boot stub: PAYLDOFF -> payload #1; PAYLCKSZ covers payload #1's
    # HFS region only (the C row is stable because payloads are never
    # rewritten; /Results.jsonl is outside the window).
    p = data.find(b"PAYLDOFF")
    if p < 0: sys.exit("PAYLDOFF marker not found in boot stub")
    patch(p + 8, rel_off[0])
    ck_len = min(rel_off[1] - rel_off[0], 0x40000) & ~3
    if not (sizes[0] <= ck_len <= sizes[0] + 0x10000):
        sys.exit(f"suspicious checksum window {ck_len:#x} vs payload {sizes[0]:#x}")
    c = data.find(b"PAYLCKSZ")
    if c < 0: sys.exit("PAYLCKSZ marker not found in boot stub")
    patch(c + 8, ck_len)

    region_start = 0
    manifest = {"results_rel_offset": res_rel, "results_abs_offset": res_abs,
                "results_size": res_size, "suites": []}
    for i in range(n):
        lo, hi = abs_off[i], abs_off[i] + sizes[i]
        r = find_in(b"RJSNLTAG", lo, hi)
        patch(r + 8, res_rel + region_start, regions[i] - batches[i])
        nx = find_in(b"NEXTPAYL", lo, hi)
        if i + 1 < n:
            nlen = (sizes[i + 1] + 511) & ~511
            patch(nx + 8, rel_off[i + 1], nlen)
        else:
            patch(nx + 8, 0, 0)
        manifest["suites"].append({
            "suite": suites[i], "file_rel_offset": rel_off[i],
            "payload_bytes": sizes[i],
            "region_offset": region_start, "region_size": regions[i],
            "max_bytes": regions[i] - batches[i]})
        region_start += regions[i]

    # Host-side expected value for the boot block's C row (rotating sum).
    # Re-read AFTER patching: the RJSNLTAG/NEXTPAYL longs live inside
    # the window, so the pre-patch buffer would give the wrong sum.
    f.flush()
    f.seek(abs_off[0])
    s = 0
    for (v,) in struct.iter_unpack(">I", f.read(ck_len)):
        s = (s + v) & 0xFFFFFFFF
        s = ((s << 1) | (s >> 31)) & 0xFFFFFFFF
    manifest["expected_C"] = f"{s:08X}"

with open(image + ".manifest.json", "w") as m:
    json.dump(manifest, m, indent=2)
    m.write("\n")

print(f"payload chain: " + " -> ".join(
    f"{suites[i]}@0x{rel_off[i]:X}({sizes[i]}B)" for i in range(n)))
print(f"results: @ partition byte 0x{res_rel:X}, {res_size} bytes, regions " +
      " ".join(f"{suites[i]}+0x{manifest['suites'][i]['region_offset']:X}" for i in range(n)))
print(f"cksum window 0x{ck_len:X}, expected C = {manifest['expected_C']}")
print(f"manifest: {image}.manifest.json")
PY

echo ""
echo "wrote $OUT ($(stat -c%s "$OUT") bytes)"
