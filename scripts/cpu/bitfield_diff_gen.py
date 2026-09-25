# bitfield_diff_gen.py seed n > prog.s : n random BFxxx cases (register and memory forms, immediate and Dn offset/width);
# every result, CCR and the memory window lands in $3000-$3FFF, which tb_ap040_program.v +dump= writes out.
# Differential use: assemble, run on two cores, cmp the dumps (scratch/bfdiff/run.sh, 2026-09-24).
import random,sys
r=random.Random(int(sys.argv[1])); n=int(sys.argv[2])
ops=['bftst','bfextu','bfchg','bfexts','bfclr','bfffo','bfset','bfins']
o=[]; P=o.append
P('    org 0'); P('    dc.l $7000,start'); P('    rept 254'); P('    dc.l failed'); P('    endr'); P('    org $400')
P('start:'); P('    move.l #$80008000,d0'); P('    movec d0,cacr'); P('    lea ($3000).l,a5')
for i in range(n):
    op=r.choice(ops); mem=r.random()<0.5
    # operands
    P(f'    move.l #${r.getrandbits(32):08x},d1')     # destination/data register
    P(f'    move.l #${r.getrandbits(32):08x},d4')     # BFINS source
    for k in range(4): P(f'    move.l #${r.getrandbits(32):08x},(${0x5000+k*4-8:x}).l')  # $1ff8..$2007
    if r.random()<0.5:
        off=f'#{r.randrange(32)}'
    else:
        v=r.randrange(-64,25) if mem else r.getrandbits(32)
        P(f'    move.l #${v & 0xffffffff:08x},d2'); off='d2'
    if r.random()<0.5:
        wid=f'#{r.randrange(1,33)}'
    else:
        P(f'    move.l #${r.getrandbits(32):08x},d3'); wid='d3'
    ea='(a0)' if mem else 'd1'
    if mem:
        P(f'    lea ($5000).l,a0')
        if off=='d2': pass
    tgt='' if op in ('bftst','bfins','bfchg','bfclr','bfset') else ',d5'
    P(f'    move.l #$5a5a5a5a,d5')
    if op=='bfins': P(f'    bfins d4,{ea}{{{off}:{wid}}}')
    else: P(f'    {op} {ea}{{{off}:{wid}}}{tgt}')
    P('    move.w ccr,(a5)+')
    P('    move.l d5,(a5)+')
    P('    move.l d1,(a5)+')
    if mem:
        P('    move.l ($4ff8).l,(a5)+'); P('    move.l ($4ffc).l,(a5)+'); P('    move.l ($5000).l,(a5)+'); P('    move.l ($5004).l,(a5)+')
P('    move.w #$600d,($f102).l'); P('    stop #$2700')
P('failed:'); P('    move.w #$bad0,($f102).l'); P('    stop #$2700')
print('\n'.join(o))
