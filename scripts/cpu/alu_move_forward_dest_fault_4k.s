 org 0
 dc.l $7000,start,handler
 rept 253
 dc.l fail
 endr
 org $400
start:
 move.w #$2700,sr
 moveq #0,d0
 movec d0,cacr
 move.l #$4203,($4000).l
 move.l #$4403,($4200).l
 move.l #$3,($4400).l
 move.l #$1003,($4404).l
 move.l #$0,($4408).l
 move.l #$3003,($440c).l
 move.l #$4003,($4410).l
 move.l #$5003,($4414).l
 move.l #$6003,($4418).l
 move.l #$7003,($441c).l
 move.l #$8003,($4420).l
 move.l #$9003,($4424).l
 move.l #$a003,($4428).l
 move.l #$b003,($442c).l
 move.l #$c003,($4430).l
 move.l #$d003,($4434).l
 move.l #$e003,($4438).l
 move.l #$f003,($443c).l
 move.l #$4000,d0
 movec d0,urp
 movec d0,srp
 move.l #$8000,d0
 movec d0,tc
 move.l #$80008000,d6
 movec d6,cacr
 move.l #$255aa55a,($c000).l
 move.l #$11223344,($d000).l
 movea.l #$d000,a1
 moveq #7,d7
loop:
 movea.l #$bffc,a0
 tst.w d7
 bne.s ready
 movea.l #$2000,a1
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
 cmp.l #$2000,20(sp)
 bne fail
 move.w #4,($f100).l
 move.w 6(sp),d0
 and.w #$f000,d0
 cmp.w #$7000,d0
 bne fail
 move.w #5,($f100).l
 cmpa.l #$c000,a0
 bne fail
 move.w #6,($f100).l
 cmpa.l #$2000,a1
 bne fail
 move.w #7,($f100).l
 cmp.l #$255aa55a,($c000).l
 bne fail
 move.w #8,($f100).l
 cmp.l #$255aa55a,($d000).l
 bne fail
 move.w #$600d,($f102).l
 stop #$2700
fail:
 move.w #$bad0,($f102).l
 stop #$2700
