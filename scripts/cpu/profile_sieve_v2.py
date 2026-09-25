#!/usr/bin/env python3
"""Speedometer 4.02 Sieve, one full inner pass, on the current CPU RTL (v2).

Same extracted bytes, scope, oracle and guards as profile_sieve.py
(profile_quick.py --kernel sieve, 2026-09-20); the runner is
speedometer_fixture_v2.py (--rtl-root snapshot, production macros, latencies
0 and 3, required negative control, --profile).  Not a hardware score.
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from speedometer_fixture_v2 import main


def build(d, kbin):
    # Every flag denotes the odd integer 2*i+3.  Trial division is independent
    # of the guest's sieve algorithm and checks all output bytes, not just count.
    def prime(n):
        return n >= 2 and all(n % k for k in range(2, math.isqrt(n) + 1))
    expected = [int(prime(2 * i + 3)) for i in range(8191)]
    (d / 'expected.hex').write_text(''.join(f'{v:02x}\n' for v in expected))
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
 lea ($9000).l,a2
 jsr ($0b6a).l
 move.w d7,($f100).l
 move.w #$600d,($f102).l
 stop #$2700
unexpected:
 move.w #$bad0,($f102).l
 stop #$2700
 org $0b6a
 incbin "{kbin}"
 rts
 org $8ffe
 dc.w $a55a
 org $afff
 dc.b $5a,$a5
'''
    SPEC['count'] = sum(expected)
    SPEC['tb_init'] = f'$readmemh("{d / "expected.hex"}",expected);'
    SPEC['tb_oracle'] = '''     if(readbyte('h8ffe)!==8'ha5 || readbyte('h8fff)!==8'h5a || readbyte('hafff)!==8'h5a || readbyte('hb000)!==8'ha5) $fatal(1,"sieve guards changed");
     if(mem['hf100>>1]!==16'd''' + str(sum(expected)) + ''') $fatal(1,"sieve count mismatch %0d",mem['hf100>>1]);
     for(i=0;i<8191;i=i+1) if(readbyte('h9000+i)!==expected[i]) $fatal(1,"sieve flag mismatch index=%0d",i);
     $display("SIEVE8191 PASS cycles=%0d latency=%0d prime_flags=PASS guards=PASS",cycles,latency);'''
    return asm, [d / 'expected.hex'], {'odd_first': 3, 'odd_last': 16383, 'count': sum(expected), 'flags': 8191}


SPEC = {
    'name': 'sieve',
    'description': __doc__,
    'range': (0x0b6a, 0x0bae),
    'build': build,
    'tb_decls': 'reg [7:0] expected[0:8190];',
    'pass_tag': 'SIEVE8191',
    # clr.b (a2,d4.w) -> two NOPs: composites are never cleared.
    'control': (0x0b94, bytes.fromhex('42324000'), bytes.fromhex('4e714e71')),
    'control_why': 'CLR.B (A2,D4.W) at 0xb94 replaced by two NOPs; composites stay set, count becomes 8191',
    'control_expect': r'sieve (count|flag) mismatch',
    'scope': 'unchanged CODE3 0xb6a..0xbad Sieve inner pass including initialization of all 8191 flags; '
             'original addresses; harness supplies A2=0x9000 and an RTS after the range; excludes allocation, '
             'disposal, outer 100-pass repetition and timing/UI',
}

if __name__ == '__main__':
    main(SPEC)
