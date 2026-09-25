 org 0
 dc.l $7000,start,handler
 rept 253
 dc.l fail
 endr
 org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d6
 movec d6,cacr
 move.l #$a55aa55a,($3000).l
 move.l #$11223344,($3100).l
 movea.l #$3100,a1
 moveq #7,d7
loop:
 movea.l #$2ffc,a0
 tst.w d7
 bne.s ready
 movea.l #$f13c,a0
ready:
 move.w #$2710,sr
 nop
 nop
 nop
 nop
 addq.w #6,a0
producer:
 subq.w #2,a0
faulting:
 move.l (a0),(a1)
 dbra d7,loop
 bra fail
handler:
 move.w #1,($f100).l
 cmp.w #$2710,(sp)
 bne fail
 move.w #2,($f100).l
 cmp.l #faulting,2(sp)
 bne fail
 move.w #3,($f100).l
 cmp.l #$f140,20(sp)
 bne fail
 move.w #4,($f100).l
 move.w 6(sp),d0
 and.w #$f000,d0
 cmp.w #$7000,d0
 bne fail
 move.w #5,($f100).l
 cmpa.l #$f140,a0
 bne fail
 move.w #6,($f100).l
 cmpa.l #$3100,a1
 bne fail
 move.w #7,($f100).l
 cmp.l #$a55aa55a,($3000).l
 bne fail
 move.w #8,($f100).l
 cmp.l #$a55aa55a,($3100).l
 bne fail
 move.w #$600d,($f102).l
 stop #$2700
fail:
 move.w #$bad0,($f102).l
 stop #$2700
