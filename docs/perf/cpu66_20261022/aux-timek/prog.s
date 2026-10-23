 org 0
 dc.l $10000
 dc.l start
 rept 254
 dc.l unexp
 endr
 org $400
start:
 move.w #$2700,sr
 move.l #$50f00000,($1d4).l
 move.l #$50f00000,($1d8).l
 move.l #$7000,($2ae).l
 move.l #$80008000,d0
 movec d0,cacr
 jsr $55ce4
 moveq #0,d0
 move.w ($d00).l,d0
 move.l d0,($50000004).l
 move.w ($d02).l,d0
 move.l d0,($50000008).l
 move.l #$a5a5a5a5,($50000000).l
 bra.s *
unexp:
 move.l #$bad,($50000000).l
 bra.s *
 org $55ce4
 incbin "SetUpTimeK.bin"
