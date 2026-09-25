 org 0
 dc.l $7000,start,fail
 rept 253
 dc.l fail
 endr
 org $400
start:
 move.w #$2700,sr
 fmove.l #99,fp0
 movea.l #$3000,a0
 fmovem.x fp0,(a0)
 cmp.l #$40050000,($3000).l
 bne fail
 cmp.l #$c6000000,($3004).l
 bne fail
 cmp.l #$00000000,($3008).l
 bne fail
 cmp.l #$00000000,($2ffc).l
 bne fail
 cmp.l #$00000000,($300c).l
 bne fail
 cmpa.l #$3000,a0
 bne fail
 move.w #$600d,($f102).l
 stop #$2700
fail:
 move.w #$bad0,($f102).l
 stop #$2700
