 org 0
 dc.l $7000,start,fail
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
 move.l #$2003,($4408).l
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
 move.l #$12345678,($1ffe).l
 move.w #$beef,($1ffc).l
 move.w #$a55a,($2002).l
 move.l #$deadbeef,($cffc).l
 move.l #$beefcafe,($d004).l
 movea.l #$d000,a1
 moveq #7,d7
loop:
 movea.l #$1ffa,a0
 move.w #$2710,sr
 nop
 nop
 nop
 nop
 addq.w #6,a0
 subq.w #2,a0
 move.l (a0),(a1)
 move.w sr,d1
 cmp.l #$12345678,($d000).l
 bne fail
 cmpa.l #$1ffe,a0
 bne fail
 cmpa.l #$d000,a1
 bne fail
 and.w #$1f,d1
 cmp.w #$10,d1
 bne fail
 cmp.l #$12345678,($1ffe).l
 bne fail
 cmp.w #$beef,($1ffc).l
 bne fail
 cmp.w #$a55a,($2002).l
 bne fail
 cmp.l #$deadbeef,($cffc).l
 bne fail
 cmp.l #$beefcafe,($d004).l
 bne fail
 dbra d7,loop
 move.w #$600d,($f102).l
 stop #$2700
fail:
 move.w #$bad0,($f102).l
 stop #$2700
