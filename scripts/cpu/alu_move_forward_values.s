 org 0
 dc.l $7000,start,fail
 rept 253
 dc.l fail
 endr
 org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d6
 movec d6,cacr
 move.l #$81234567,($3000).l
 move.l #$bad0bad0,($2ff8).l
 move.l #$bad1bad1,($3008).l
 move.l #$a55aa55a,($5ffc).l
 move.l #$beefcafe,($6004).l
 moveq #7,d7
loop:
 movea.l #$2ff8,a0
 movea.l #$6004,a7
 move.w #$2710,sr
 nop
 nop
 addq.w #8,a0
 move.l (a0),-(a7)
 move.w sr,d1
 cmp.l #$81234567,($6000).l
 bne fail
 cmpa.l #$3000,a0
 bne fail
 cmpa.l #$6000,a7
 bne fail
 and.w #$1f,d1
 cmp.w #$18,d1
 bne fail
 cmp.l #$a55aa55a,($5ffc).l
 bne fail
 cmp.l #$beefcafe,($6004).l
 bne fail
 movea.l #$3008,a0
 movea.l #$6004,a7
 move.w #$2710,sr
 nop
 nop
 subq.w #8,a0
 move.l (a0),-(a7)
 move.w sr,d1
 cmp.l #$81234567,($6000).l
 bne fail
 cmpa.l #$3000,a0
 bne fail
 cmpa.l #$6000,a7
 bne fail
 and.w #$1f,d1
 cmp.w #$18,d1
 bne fail
 cmp.l #$a55aa55a,($5ffc).l
 bne fail
 cmp.l #$beefcafe,($6004).l
 bne fail
 movea.l #$2ff8,a0
 movea.l #$6004,a7
 moveq #8,d0
 move.w #$2710,sr
 nop
 nop
 adda.w d0,a0
 move.l (a0),-(a7)
 move.w sr,d1
 cmp.l #$81234567,($6000).l
 bne fail
 cmpa.l #$3000,a0
 bne fail
 cmpa.l #$6000,a7
 bne fail
 and.w #$1f,d1
 cmp.w #$18,d1
 bne fail
 cmp.l #$a55aa55a,($5ffc).l
 bne fail
 cmp.l #$beefcafe,($6004).l
 bne fail
 movea.l #$0,a0
 movea.l #$6004,a7
 move.l #$3000,d0
 move.w #$2710,sr
 nop
 nop
 movea.l d0,a0
 move.l (a0),-(a7)
 move.w sr,d1
 cmp.l #$81234567,($6000).l
 bne fail
 cmpa.l #$3000,a0
 bne fail
 cmpa.l #$6000,a7
 bne fail
 and.w #$1f,d1
 cmp.w #$18,d1
 bne fail
 cmp.l #$a55aa55a,($5ffc).l
 bne fail
 cmp.l #$beefcafe,($6004).l
 bne fail
 dbra d7,loop
 move.w #$600d,($f102).l
 stop #$2700
fail:
 move.w #$bad0,($f102).l
 stop #$2700
