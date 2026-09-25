; Four resident data translations must survive alternation, then all flush.
 org 0
 dc.l $3400,start
 rept 254
 dc.l failed
 endr
 org $400
start:
 move.w #$2700,sr
 lea ($4400).l,a0
 moveq #0,d0
 moveq #63,d1
 tables:
 move.l d0,d2
 lsl.l #8,d2
 lsl.l #4,d2
 addq.l #3,d2
 move.l d2,(a0)+
 addq.l #1,d0
 dbra d1,tables
 move.l #$4203,($4000).l
 move.l #$4403,($4200).l
 move.l #$11111111,($8100).l
 move.l #$22222222,($9100).l
 move.l #$33333333,($a100).l
 move.l #$44444444,($b100).l
 move.l #$55555555,($c100).l
 move.l #$66666666,($d100).l
 move.l #$77777777,($e100).l
 move.l #$88888888,($7100).l
 move.l #$4000,d0
 movec d0,urp
 movec d0,srp
 move.l #$8000,d0
 movec d0,tc
 pflusha
 bsr warm
 ; Update descriptors without flushing: ATC must still preserve old mappings.
 move.l #$c003,($4420).l
 move.l #$d003,($4424).l
 move.l #$e003,($4428).l
 move.l #$7003,($442c).l
 bsr warm
 pflusha
 cmpi.l #$55555555,($8100).l
 bne failed
 cmpi.l #$66666666,($9100).l
 bne failed
 cmpi.l #$77777777,($a100).l
 bne failed
 cmpi.l #$88888888,($b100).l
 bne failed
 moveq #0,d0
 movec d0,tc
 cmpi.l #$11111111,($8100).l
 bne failed
 cmpi.l #$22222222,($9100).l
 bne failed
 cmpi.l #$33333333,($a100).l
 bne failed
 cmpi.l #$44444444,($b100).l
 bne failed
 move.w #$600d,($f102).l
 stop #$2700
warm:
 moveq #3,d7
again:
 cmpi.l #$11111111,($8100).l
 bne failed
 cmpi.l #$22222222,($9100).l
 bne failed
 cmpi.l #$33333333,($a100).l
 bne failed
 cmpi.l #$44444444,($b100).l
 bne failed
 dbra d7,again
 rts
failed:
 move.w #$bad0,($f102).l
 stop #$2700
