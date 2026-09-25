 org 0
 dc.l $3800,start
 rept 254
 dc.l failed
 endr
 org $400
start:
 move.w #$2700,sr
 move.l #$80008000,d7
 movec d7,cacr
 move.w #1,($f100).l
 moveq #7,d7
 bra.w case1
 cnop 0,64
case1:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c101).l,a0
 move.l #$80,d0
 move.w #$271f,sr
 nop
 nop
 move.b d0,(a0)
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c101,a0
 bne failed
 cmp.l #$aa80ccdd,($c100).l
 bne failed
 cmp.l #$eeff1122,($c104).l
 bne failed
 dbra d7,case1
 move.w #2,($f100).l
 moveq #7,d7
 bra.w case2
 cnop 0,64
case2:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c101).l,a0
 move.l #$80,d0
 move.w #$271f,sr
 nop
 nop
 move.b d0,(a0)+
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c102,a0
 bne failed
 cmp.l #$aa80ccdd,($c100).l
 bne failed
 cmp.l #$eeff1122,($c104).l
 bne failed
 dbra d7,case2
 move.w #3,($f100).l
 moveq #7,d7
 bra.w case3
 cnop 0,64
case3:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c102).l,a0
 move.l #$80,d0
 move.w #$271f,sr
 nop
 nop
 move.b d0,-(a0)
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c101,a0
 bne failed
 cmp.l #$aa80ccdd,($c100).l
 bne failed
 cmp.l #$eeff1122,($c104).l
 bne failed
 dbra d7,case3
 move.w #4,($f100).l
 moveq #7,d7
 bra.w case4
 cnop 0,64
case4:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c0f1).l,a0
 move.l #$80,d0
 move.w #$271f,sr
 nop
 nop
 move.b d0,16(a0)
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c0f1,a0
 bne failed
 cmp.l #$aa80ccdd,($c100).l
 bne failed
 cmp.l #$eeff1122,($c104).l
 bne failed
 dbra d7,case4
 move.w #5,($f100).l
 moveq #7,d7
 bra.w case5
 cnop 0,64
case5:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c101).l,a0
 move.l #$8001,d0
 move.w #$271f,sr
 nop
 nop
 move.w d0,(a0)
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c101,a0
 bne failed
 cmp.l #$aa8001dd,($c100).l
 bne failed
 cmp.l #$eeff1122,($c104).l
 bne failed
 dbra d7,case5
 move.w #6,($f100).l
 moveq #7,d7
 bra.w case6
 cnop 0,64
case6:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c101).l,a0
 move.l #$8001,d0
 move.w #$271f,sr
 nop
 nop
 move.w d0,(a0)+
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c103,a0
 bne failed
 cmp.l #$aa8001dd,($c100).l
 bne failed
 cmp.l #$eeff1122,($c104).l
 bne failed
 dbra d7,case6
 move.w #7,($f100).l
 moveq #7,d7
 bra.w case7
 cnop 0,64
case7:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c103).l,a0
 move.l #$8001,d0
 move.w #$271f,sr
 nop
 nop
 move.w d0,-(a0)
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c101,a0
 bne failed
 cmp.l #$aa8001dd,($c100).l
 bne failed
 cmp.l #$eeff1122,($c104).l
 bne failed
 dbra d7,case7
 move.w #8,($f100).l
 moveq #7,d7
 bra.w case8
 cnop 0,64
case8:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c0f1).l,a0
 move.l #$8001,d0
 move.w #$271f,sr
 nop
 nop
 move.w d0,16(a0)
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c0f1,a0
 bne failed
 cmp.l #$aa8001dd,($c100).l
 bne failed
 cmp.l #$eeff1122,($c104).l
 bne failed
 dbra d7,case8
 move.w #9,($f100).l
 moveq #7,d7
 bra.w case9
 cnop 0,64
case9:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c101).l,a0
 move.l #$80000001,d0
 move.w #$271f,sr
 nop
 nop
 move.l d0,(a0)
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c101,a0
 bne failed
 cmp.l #$aa800000,($c100).l
 bne failed
 cmp.l #$01ff1122,($c104).l
 bne failed
 dbra d7,case9
 move.w #10,($f100).l
 moveq #7,d7
 bra.w case10
 cnop 0,64
case10:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c101).l,a0
 move.l #$80000001,d0
 move.w #$271f,sr
 nop
 nop
 move.l d0,(a0)+
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c105,a0
 bne failed
 cmp.l #$aa800000,($c100).l
 bne failed
 cmp.l #$01ff1122,($c104).l
 bne failed
 dbra d7,case10
 move.w #11,($f100).l
 moveq #7,d7
 bra.w case11
 cnop 0,64
case11:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c105).l,a0
 move.l #$80000001,d0
 move.w #$271f,sr
 nop
 nop
 move.l d0,-(a0)
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c101,a0
 bne failed
 cmp.l #$aa800000,($c100).l
 bne failed
 cmp.l #$01ff1122,($c104).l
 bne failed
 dbra d7,case11
 move.w #12,($f100).l
 moveq #7,d7
 bra.w case12
 cnop 0,64
case12:
 move.l #$aabbccdd,($c100).l
 move.l #$eeff1122,($c104).l
 lea ($c0f1).l,a0
 move.l #$80000001,d0
 move.w #$271f,sr
 nop
 nop
 move.l d0,16(a0)
 move.w sr,d6
 cmp.w #$2718,d6
 bne failed
 cmpa.l #$c0f1,a0
 bne failed
 cmp.l #$aa800000,($c100).l
 bne failed
 cmp.l #$01ff1122,($c104).l
 bne failed
 dbra d7,case12
 move.w #13,($f100).l
 moveq #7,d7
 bra.w case13
 cnop 0,64
case13:
 move.l #$aabbccdd,($c200).l
 movea.l #$c200,sp
 move.l #$80,d0
 move.w #$271f,sr
 nop
 nop
 move.b d0,(sp)+
 move.w sr,d6
 move.l sp,d5
 movea.l #$3800,sp
 cmp.w #$2718,d6
 bne failed
 cmp.l #$c202,d5
 bne failed
 cmp.l #$80bbccdd,($c200).l
 bne failed
 dbra d7,case13
 move.w #14,($f100).l
 moveq #7,d7
 bra.w case14
 cnop 0,64
case14:
 move.l #$aabbccdd,($c200).l
 movea.l #$c202,sp
 move.l #$80,d0
 move.w #$271f,sr
 nop
 nop
 move.b d0,-(sp)
 move.w sr,d6
 move.l sp,d5
 movea.l #$3800,sp
 cmp.w #$2718,d6
 bne failed
 cmp.l #$c200,d5
 bne failed
 cmp.l #$80bbccdd,($c200).l
 bne failed
 dbra d7,case14
 move.w #15,($f100).l
 moveq #7,d7
 bra.w case15
 cnop 0,64
case15:
 lea ($c100).l,a0
 move.w #$271f,sr
 nop
 nop
 move.l a0,(a0)+
 move.w sr,d6
 cmp.w #$2710,d6
 bne failed
 cmpa.l #$c104,a0
 bne failed
 cmp.l #$c100,($c100).l
 bne failed
 dbra d7,case15
 moveq #0,d0
 movec d0,cacr
 lea ($c100).l,a0
 move.l #$12345678,d0
 move.l d0,(a0)
 cmp.l #$12345678,($c100).l
 bne failed
 move.w #$600d,($f102).l
 stop #$2700
failed:
 move.w #$bad0,($f102).l
 stop #$2700
