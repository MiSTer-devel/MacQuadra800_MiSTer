#!/bin/sh
# make-fastboot-rom.sh IN.rom OUT.rom
#
# Produce the SIM-ONLY "fastboot" Quadra 800 ROM: NOP the RAM-test warm
# gate branch so the ~1.5G-cycle startup RAM pattern test is always
# skipped, then fix the ROM checksum the startup verifies (the 40M-80M
# cycle phase) so the patched image passes it.
#
#   patch: file offset $47344 ($40847344): 66 06 (bne.b +6) -> 4E 71 (nop)
#   checksum: 32-bit sum of big-endian uint16 words over [4, end),
#             stored big-endian at offset 0
#
# Rationale and the full RAM-test reverse engineering:
#   docs/quadra800-ram-test.md
# NEVER flash the output to hardware; acceptance-gate sim runs use the
# pristine ROM.
set -e

IN="$1"; OUT="$2"
[ -n "$IN" ] && [ -n "$OUT" ] || { echo "usage: $0 IN.rom OUT.rom" >&2; exit 2; }

python3 - "$IN" "$OUT" <<'EOF'
import struct, sys

src, dst = sys.argv[1], sys.argv[2]
d = bytearray(open(src, 'rb').read())

def wordsum(b):
    return sum(struct.unpack('>H', b[i:i+2])[0] for i in range(4, len(b), 2)) & 0xFFFFFFFF

stored = struct.unpack('>I', d[0:4])[0]
if wordsum(d) != stored:
    sys.exit(f'{src}: stored checksum {stored:08X} != computed {wordsum(d):08X} — wrong or corrupt ROM')

OFF = 0x47344
if d[OFF:OFF+2] != b'\x66\x06':
    sys.exit(f'{src}: bytes at {OFF:#x} are {d[OFF]:02X}{d[OFF+1]:02X}, expected 6606 — not the expected ROM')

d[OFF:OFF+2] = b'\x4e\x71'
d[0:4] = struct.pack('>I', wordsum(d))
open(dst, 'wb').write(d)
print(f'{dst}: patched {OFF:#x} 6606->4E71, checksum {stored:08X}->{wordsum(d):08X}')
EOF
