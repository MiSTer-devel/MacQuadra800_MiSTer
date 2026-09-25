 org 0
 dc.l $7000,start
 rept 24
 dc.l fail
 endr
 dc.l handler
 rept 229
 dc.l fail
 endr
 org $400
start:
 move.w #$2710,sr
 move.l #$80008000,d6
 movec d6,cacr
 move.l #$12345678,($c000).l
 movea.l #$d000,a1
 moveq #7,d7
loop:
 movea.l #$bffc,a0
 nop
 nop
producer:
 addq.w #4,a0
following:
 move.l (a0),(a1)
 dbra d7,loop
 move.l #$deadbeef,($d000).l
 movea.l #$bffc,a0
 clr.w -(sp)
 pea producer
 move.w #$2010,-(sp)
 rte
 bra fail
handler:
 cmp.w #$2010,(sp)
 bne fail
 cmp.l #following,2(sp)
 bne fail
 move.w 6(sp),d0
 and.w #$f000,d0
 cmp.w #$0000,d0
 bne fail
 cmpa.l #$c000,a0
 bne fail
 cmpa.l #$d000,a1
 bne fail
 cmp.l #$deadbeef,($d000).l
 bne fail
 cmp.l #$12345678,($c000).l
 bne fail
 move.w #$600d,($f102).l
 stop #$2700
fail:
 move.w #$bad0,($f102).l
 stop #$2700
