#!/usr/bin/env python3
"""Speedometer 4.02 Bubble Sort loop on the current CPU RTL (v2).

Same extracted bytes, scope, input, oracle and guards as profile_bubble.py
(2026-09-19/20); the runner is speedometer_fixture_v2.py (--rtl-root
snapshot, production macros, latencies 0 and 3, required negative control,
--profile).  Not a hardware score.
"""
import random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from speedometer_fixture_v2 import main


def build(d, kbin):
    values = list(range(-250, 250)); random.Random(20260919).shuffle(values)
    (d / 'input.hex').write_text(''.join(f'{v & 65535:04x}\n' for v in values))
    asm = f''' org 0
 dc.l $e000,start
 rept 254
 dc.l unexpected
 endr
 org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d0
 movec d0,cacr
 lea ($8000).l,a5
 lea ($c000).l,a2
 move.w #500,($5fb0).l
 jsr ($9586).l
 move.w #$600d,($f102).l
 stop #$2700
unexpected:
 move.w #$bad0,($f102).l
 stop #$2700
 org $9586
 incbin "{kbin}"
 rts
 org $c000
 dc.w $a55a
''' + ''.join(' dc.w ' + ','.join('$%04x' % (x & 65535) for x in values[i:i + 20]) + '\n' for i in range(0, 500, 20)) + ' dc.w $5aa5\n'
    # Oracle: the input is a shuffle of -250..249, so the sorted array must be
    # exactly -250..249 in order (a sorted permutation of the input).
    return asm, [d / 'input.hex'], values


SPEC = {
    'name': 'bubble',
    'description': __doc__,
    'range': (0x9586, 0x95d2),
    'build': build,
    'tb_decls': '',
    'tb_init': '',
    'tb_oracle': '''     if(mem['hc000>>1]!==16'ha55a || mem['hc3ea>>1]!==16'h5aa5) $fatal(1,"bubble guards changed");
     for(i=0;i<500;i=i+1) if($signed(mem[('hc002+2*i)>>1]) != i-250) $fatal(1,"bubble result mismatch index=%0d value=%h",i,mem[('hc002+2*i)>>1]);
     $display("BUBBLE500 PASS cycles=%0d latency=%0d sorted_permutation=PASS guards=PASS",cycles,latency);''',
    'pass_tag': 'BUBBLE500',
    # move.w d6,(a3) -> NOP: the swap loses its second half.
    'control': (0x95b6, bytes.fromhex('3686'), bytes.fromhex('4e71')),
    'control_why': 'MOVE.W D6,(A3) at 0x95b6 (second half of the swap) replaced by NOP; the array is no longer a sorted permutation',
    'control_expect': r'bubble result mismatch',
    'scope': 'unchanged CODE3 0x9586..0x95d1 sorting loop only (outer count at -$2050(A5)=0x5fb0 set to 500); '
             'fixed shuffled input -250..249 seed 20260919 at 0xc002; harness adds an RTS after the range; '
             'excludes initializer, allocation and five-iteration wrapper',
}

if __name__ == '__main__':
    main(SPEC)
