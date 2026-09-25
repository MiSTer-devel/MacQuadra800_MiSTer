#!/usr/bin/env python3
"""Replace fixture setup only; preserve all original benchmark and data bytes >= $1000.

Both CPUs must use these same generated fixtures. Host-side oracles replace
wrapper-side checks. No original benchmark instruction is rewritten or skipped.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path

NAMES = ('queens', 'bubble', 'permute', 'towers')
BODIES = (
''' pea ($c0c0).l
 pea ($c080).l
 pea ($c060).l
 pea ($c020).l
 pea ($c000).l
 moveq #1,d0
 move.w d0,-(sp)
 jsr ($91a4).l
''',
''' lea ($c000).l,a2
 move.w #500,d0
 move.w d0,($5fb0).l
 jsr ($9586).l
''',
''' lea ($4000).l,a2
 move.w #$a55a,d0
 move.w d0,(a2)
 move.w #$5aa5,d0
 move.w d0,16(a2)
 moveq #0,d0
 lea -$2058(a5),a0
 move.l d0,(a0)
 pea (a2)
 jsr ($65ba).l
 lea 4(sp),sp
 pea (a2)
 moveq #7,d0
 move.w d0,-(sp)
 jsr ($65ea).l
''',
''' move.w #$a55a,d0
 move.w d0,($5fb4).l
 move.w #$5aa5,d0
 move.w d0,($6010).l
 jsr ($9818).l
''')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    for name in NAMES:
        ap.add_argument('--'+name, type=Path, required=True, help='original program.hex')
    ap.add_argument('--vasm', default='/home/alans/mister/MacQuadra800_fixtures/wombat-vasm/vasmm68k_mot')
    args = ap.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    identities = {}
    for name, body in zip(NAMES, BODIES):
        path = getattr(args, name).resolve()
        original = b''.join(int(w,16).to_bytes(2,'big') for w in path.read_text().split())
        asm = ''' org 0
 dc.l $e000,start
 rept 254
 dc.l unexpected
 endr
 org $400
start:
 move.w #$2700,d0
 move.w d0,sr
 move.l #$80008000,d0
 movec d0,cacr
 lea ($8000).l,a5
'''+body+''' move.w #$600d,d0
 move.w d0,($f102).l
finished:
 bra finished
unexpected:
 moveq #-1,d0
 move.w d0,($f102).l
 bra unexpected
'''
        # Upstream absolute stores currently support longwords only. Use
        # an address register for word stores in setup/completion code.
        asm = re.sub(r'move.w d0,(\(\$[0-9a-f]+\)\.l)', r'lea \1,a0\n move.w d0,(a0)', asm)
        asm = asm.replace('move.w d0,16(a2)', 'lea 16(a2),a0\n move.w d0,(a0)')
        (out/(name+'.s')).write_text(asm)
        with (out/(name+'-asm.log')).open('w') as f:
            subprocess.run([args.vasm,'-Fbin','-m68040','-no-opt','-o',str(out/(name+'-wrapper.bin')),
                            str(out/(name+'.s'))], stdout=f, stderr=subprocess.STDOUT, check=True)
        wrapper = (out/(name+'-wrapper.bin')).read_bytes()
        assert len(wrapper) < 0x1000
        program = wrapper + bytes(0x1000-len(wrapper)) + original[0x1000:]
        assert program[0x1000:] == original[0x1000:]
        (out/(name+'.hex')).write_text(''.join(program[i:i+2].hex()+'\n' for i in range(0,len(program),2)))
        identities[name] = dict(original=str(path), original_sha256=hashlib.sha256(original).hexdigest(),
                                program_sha256=hashlib.sha256(program).hexdigest(),
                                unchanged_from_0x1000_sha256=hashlib.sha256(original[0x1000:]).hexdigest())
    (out/'identity.json').write_text(json.dumps(identities,indent=2)+'\n')


if __name__ == '__main__':
    main()
