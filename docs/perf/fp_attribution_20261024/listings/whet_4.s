	idnt	"c/whet.c"
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	section	"CODE",code
	cnop	0,4
l1
	fmovem.x	l8,-(a7)
	movem.l	l7,-(a7)
	fmove.d	(4+l9,a7),fp0
	fblt	l5
	fmove.d	#$3fe0000000000000,fp1
	fadd.x	fp0,fp1
	bra	l6
l5
	fmove.x	fp0,fp1
	fsub.d	#$3fe0000000000000,fp1
l6
	fmove.l	fpcr,d1
	moveq	#16,d0
	or.l	d1,d0
	and.w	#-33,d0
	fmove.l	d0,fpcr
	fmove.l	fp1,d0
	fmove.l	d1,fpcr
	fmove.l	d0,fp0
l7	reg
l8	freg
l9	equ	0
	rts
; stacksize=0
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l10
	fmovem.x	l14,-(a7)
	movem.l	l13,-(a7)
	fmove.d	(4+l15,a7),fp3
	fmove.x	fp3,fp2
	fmul.x	fp3,fp2
	fmove.x	fp2,fp1
	fmul.x	fp3,fp1
	fmove.d	#$bd6ae7f3e733b81e,fp0
	fmul.x	fp2,fp0
	fadd.d	#$3de6124613a86d09,fp0
	fmul.x	fp2,fp0
	fadd.d	#$be5ae64567f544e3,fp0
	fmul.x	fp2,fp0
	fadd.d	#$3ec71de3a556c733,fp0
	fmul.x	fp2,fp0
	fadd.d	#$bf2a01a01a01a01a,fp0
	fmul.x	fp2,fp0
	fadd.d	#$3f81111111111112,fp0
	fmul.x	fp2,fp0
	fadd.d	#$bfc5555555555555,fp0
	fmul.x	fp1,fp0
	fadd.x	fp3,fp0
l13	reg
l14	freg	fp2/fp3
	fmovem.x	(a7)+,l14
l15	equ	24
	rts
; stacksize=24
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l16
	fmovem.x	l20,-(a7)
	movem.l	l19,-(a7)
	fmove.d	(4+l21,a7),fp1
	fmul.d	(4+l21,a7),fp1
	fmove.d	#$bda93974a8c07c9e,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3e21eed8eff8d896,fp0
	fmul.x	fp1,fp0
	fadd.d	#$be927e4fb7789f5c,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3efa01a01a01a01b,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bf56c16c16c16c17,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3fa5555555555556,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bfe0000000000000,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3ff0000000000000,fp0
l19	reg
l20	freg
l21	equ	0
	rts
; stacksize=0
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l22
	fmovem.x	l32,-(a7)
	movem.l	l31,-(a7)
	fmove.d	(4+l33,a7),fp0
	fdiv.d	#$3ff921fb54442d18,fp0
	fmove.d	fp0,-(a7)
	jsr	l1
	fmove.x	fp0,fp1
	fmul.d	#$3ff921fb54400000,fp1
	fneg.x	fp1
	fadd.d	(12+l33,a7),fp1
	fmove.d	#$3dd0b4611a626332,fp2
	fmul.x	fp0,fp2
	fmove.x	fp1,fp3
	fsub.x	fp2,fp3
	fmove.l	fpcr,d2
	moveq	#16,d0
	or.l	d2,d0
	and.w	#-33,d0
	fmove.l	d0,fpcr
	fmove.l	fp0,d0
	fmove.l	d2,fpcr
	moveq	#3,d1
	and.l	d0,d1
	addq.w	#8,a7
	bne	l26
	fmove.d	fp3,-(a7)
	jsr	l10
	addq.w	#8,a7
	bra	l23
l26
	cmp.l	#1,d1
	bne	l28
	fmove.d	fp3,-(a7)
	jsr	l16
	addq.w	#8,a7
	bra	l23
l28
	cmp.l	#2,d1
	bne	l30
	fmove.d	fp3,-(a7)
	jsr	l10
	fneg.x	fp0,fp0
	addq.w	#8,a7
	bra	l23
l30
	fmove.d	fp3,-(a7)
	jsr	l16
	fneg.x	fp0,fp0
	addq.w	#8,a7
l23
l31	reg	d2
	movem.l	(a7)+,d2
l32	freg	fp2/fp3
	fmovem.x	(a7)+,l32
l33	equ	28
	rts
; stacksize=64
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l34
	fmovem.x	l44,-(a7)
	movem.l	l43,-(a7)
	fmove.d	(4+l45,a7),fp0
	fdiv.d	#$3ff921fb54442d18,fp0
	fmove.d	fp0,-(a7)
	jsr	l1
	fmove.x	fp0,fp1
	fmul.d	#$3ff921fb54400000,fp1
	fneg.x	fp1
	fadd.d	(12+l45,a7),fp1
	fmove.d	#$3dd0b4611a626332,fp2
	fmul.x	fp0,fp2
	fmove.x	fp1,fp3
	fsub.x	fp2,fp3
	fmove.l	fpcr,d2
	moveq	#16,d0
	or.l	d2,d0
	and.w	#-33,d0
	fmove.l	d0,fpcr
	fmove.l	fp0,d0
	fmove.l	d2,fpcr
	moveq	#3,d1
	and.l	d0,d1
	addq.w	#8,a7
	bne	l38
	fmove.d	fp3,-(a7)
	jsr	l16
	addq.w	#8,a7
	bra	l35
l38
	cmp.l	#1,d1
	bne	l40
	fmove.d	fp3,-(a7)
	jsr	l10
	fneg.x	fp0,fp0
	addq.w	#8,a7
	bra	l35
l40
	cmp.l	#2,d1
	bne	l42
	fmove.d	fp3,-(a7)
	jsr	l16
	fneg.x	fp0,fp0
	addq.w	#8,a7
	bra	l35
l42
	fmove.d	fp3,-(a7)
	jsr	l10
	addq.w	#8,a7
l35
l43	reg	d2
	movem.l	(a7)+,d2
l44	freg	fp2/fp3
	fmovem.x	(a7)+,l44
l45	equ	28
	rts
; stacksize=64
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l46
	fmovem.x	l60,-(a7)
	movem.l	l59,-(a7)
	fmove.d	(4+l61,a7),fp2
	fmove.d	#$3ff0000000000000,fp4
	moveq	#0,d1
	moveq	#0,d0
	ftst.x	fp2
	fbge	l50
	fmove.d	#$bff0000000000000,fp4
	fneg.x	fp2,fp2
l50
	fcmp.d	#$3ff0000000000000,fp2
	fble	l52
	fmove.x	fp2,fp0
	fmove.d	#$3ff0000000000000,fp2
	fdiv.x	fp0,fp2
	moveq	#1,d1
l52
	fcmp.d	#$3fd126145e9ecd56,fp2
	fble	l54
	fmove.x	fp2,fp0
	fmul.d	#$3ffbb67ae8584caa,fp0
	fsub.d	#$3ff0000000000000,fp0
	fmove.d	#$3ffbb67ae8584caa,fp1
	fadd.x	fp2,fp1
	fmove.x	fp0,fp2
	fdiv.x	fp1,fp2
	moveq	#1,d0
l54
	fmove.x	fp2,fp1
	fmul.x	fp2,fp1
	fmove.d	#$3fa47ae147ae147b,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bfa642c8590b2164,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3fa8618618618618,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bfaaf286bca1af28,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3fae1e1e1e1e1e1e,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bfb1111111111111,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3fb3b13b13b13b14,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bfb745d1745d1746,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3fbc71c71c71c71c,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bfc2492492492492,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3fc999999999999a,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bfd5555555555555,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3ff0000000000000,fp0
	fmove.x	fp0,fp3
	fmul.x	fp2,fp3
	tst.l	d0
	beq	l56
	fadd.d	#$3fe0c152382d7366,fp3
l56
	tst.l	d1
	beq	l58
	fneg.x	fp3
	fadd.d	#$3ff921fb54442d18,fp3
l58
	fmove.x	fp3,fp0
	fmul.x	fp4,fp0
l59	reg
l60	freg	fp2/fp3/fp4
	fmovem.x	(a7)+,l60
l61	equ	36
	rts
; stacksize=36
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l62
	subq.w	#8,a7
	fmovem.x	l66,-(a7)
	movem.l	l65,-(a7)
	fmove.d	(12+l67,a7),fp0
	fdiv.d	#$3fe62e42fefa39ef,fp0
	fmove.d	fp0,-(a7)
	jsr	l1
	fmove.d	#$3fe62e42fee00000,fp2
	fmul.x	fp0,fp2
	fneg.x	fp2
	fadd.d	(20+l67,a7),fp2
	fmove.d	#$3dea39ef35793c76,fp1
	fmul.x	fp0,fp1
	fsub.x	fp1,fp2
	fmove.d	#$3e21eed8eff8d898,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3e5ae64567f544e4,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3e927e4fb7789f5c,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3ec71de3a556c734,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3efa01a01a01a01a,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3f2a01a01a01a01a,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3f56c16c16c16c17,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3f81111111111111,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3fa5555555555555,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3fc5555555555555,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3fe0000000000000,fp1
	fmul.x	fp2,fp1
	fadd.d	#$3ff0000000000000,fp1
	fmul.x	fp2,fp1
	fmove.d	#$3ff0000000000000,fp2
	fadd.x	fp1,fp2
	fmove.d	fp2,(8+l67,a7)
	fmove.l	fpcr,d1
	moveq	#16,d0
	or.l	d1,d0
	and.w	#-33,d0
	fmove.l	d0,fpcr
	fmove.l	fp0,d0
	fmove.l	d1,fpcr
	moveq	#20,d1
	lsl.l	d1,d0
	add.l	d0,(8+l67,a7)
	fmove.d	(8+l67,a7),fp0
	addq.w	#8,a7
l65	reg
l66	freg	fp2
	fmovem.x	(a7)+,l66
l67	equ	12
	addq.w	#8,a7
	rts
; stacksize=32
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l68
	subq.w	#8,a7
	fmovem.x	l74,-(a7)
	movem.l	l73,-(a7)
	move.l	(16+l75,a7),(4+l75,a7)
	move.l	(12+l75,a7),(0+l75,a7)
	moveq	#20,d2
	move.l	(0+l75,a7),d0
	lsr.l	d2,d0
	and.l	#2047,d0
	move.l	d0,d1
	sub.l	#1023,d1
	move.l	#1048575,d0
	and.l	(0+l75,a7),d0
	move.l	#1072693248,d2
	or.l	d0,d2
	move.l	d2,(0+l75,a7)
	fmove.d	(0+l75,a7),fp3
	fmove.d	(0+l75,a7),fp0
	fcmp.d	#$3ff6a09e667f3bcd,fp0
	fble	l72
	fmove.d	#$3fe0000000000000,fp3
	fmul.d	(0+l75,a7),fp3
	addq.l	#1,d1
l72
	fmove.x	fp3,fp0
	fsub.d	#$3ff0000000000000,fp0
	fmove.d	#$3ff0000000000000,fp1
	fadd.x	fp3,fp1
	fdiv.x	fp1,fp0
	fmove.x	fp0,fp1
	fmul.x	fp0,fp1
	fmul.d	#$4000000000000000,fp0
	fmove.x	fp1,fp2
	fdiv.d	#$4035000000000000,fp2
	fadd.d	#$3faaf286bca1af28,fp2
	fmul.x	fp1,fp2
	fadd.d	#$3fae1e1e1e1e1e1e,fp2
	fmul.x	fp1,fp2
	fadd.d	#$3fb1111111111111,fp2
	fmul.x	fp1,fp2
	fadd.d	#$3fb3b13b13b13b14,fp2
	fmul.x	fp1,fp2
	fadd.d	#$3fb745d1745d1746,fp2
	fmul.x	fp1,fp2
	fadd.d	#$3fbc71c71c71c71c,fp2
	fmul.x	fp1,fp2
	fadd.d	#$3fc2492492492492,fp2
	fmul.x	fp1,fp2
	fadd.d	#$3fc999999999999a,fp2
	fmul.x	fp1,fp2
	fadd.d	#$3fd5555555555555,fp2
	fmul.x	fp1,fp2
	fadd.d	#$3ff0000000000000,fp2
	fmul.x	fp0,fp2
	fmove.l	d1,fp0
	fmove.d	#$3fe62e42fee00000,fp1
	fmul.x	fp0,fp1
	fmul.d	#$3dea39ef35793c76,fp0
	fadd.x	fp2,fp0
	fadd.x	fp1,fp0
l73	reg	d2
	movem.l	(a7)+,d2
l74	freg	fp2/fp3
	fmovem.x	(a7)+,l74
l75	equ	28
	addq.w	#8,a7
	rts
; stacksize=36
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l83
	fmovem.x	l95,-(a7)
	movem.l	l94,-(a7)
	move.l	(4+l96,a7),a4
	move.l	#0,l80
	lea	(8,a4),a0
	lea	(16,a4),a2
	lea	(24,a4),a3
	lea	(32,a4),a1
l92
	fmove.d	(a2),fp0
	fadd.d	(a0),fp0
	fadd.d	(a3),fp0
	fsub.d	(a1),fp0
	fmul.d	l76,fp0
	fmove.d	fp0,(a0)
	fmove.d	(a2),fp0
	fadd.d	(a0),fp0
	fsub.d	(a3),fp0
	fadd.d	(a1),fp0
	fmul.d	l76,fp0
	fmove.d	fp0,(a2)
	fmove.d	(a0),fp0
	fsub.d	(a2),fp0
	fadd.d	(a3),fp0
	fadd.d	(a1),fp0
	fmul.d	l76,fp0
	fmove.d	fp0,(a3)
	fneg.d	(a0),fp0
	fadd.d	(a2),fp0
	fadd.d	(a3),fp0
	fadd.d	(a1),fp0
	fdiv.d	l78,fp0
	fmove.d	fp0,(a1)
	addq.l	#1,l80
	cmp.l	#6,l80
	blt	l92
l94	reg	a2/a3/a4
	movem.l	(a7)+,a2/a3/a4
l95	freg
l96	equ	12
	rts
; stacksize=12
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l97
	fmovem.x	l101,-(a7)
	movem.l	l100,-(a7)
	move.w	2+l81,d0
	lsl.w	#3,d0
	lea	l79,a2
	add.w	d0,a2
	move.w	2+l80,d0
	lsl.w	#3,d0
	lea	l79,a0
	add.w	d0,a0
	move.l	(4,a2),(4,a0)
	move.l	(a2),(a0)
	move.w	2+l82,d0
	lsl.w	#3,d0
	lea	l79,a1
	add.w	d0,a1
	move.l	(4,a1),(4,a2)
	move.l	(a1),(a2)
	move.l	(4,a0),(4,a1)
	move.l	(a0),(a1)
l100	reg	a2
	movem.l	(a7)+,a2
l101	freg
l102	equ	4
	rts
; stacksize=4
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l103
	fmovem.x	l107,-(a7)
	movem.l	l106,-(a7)
	move.l	(20+l108,a7),a0
	fmove.d	(4+l108,a7),fp1
	fadd.d	(12+l108,a7),fp1
	fmul.d	l76,fp1
	fmove.x	fp1,fp0
	fadd.d	(12+l108,a7),fp0
	fmul.d	l76,fp0
	fadd.x	fp1,fp0
	fdiv.d	l78,fp0
	fmove.d	fp0,(a0)
l106	reg
l107	freg
l108	equ	0
	rts
; stacksize=0
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	public	_main
	cnop	0,4
_main
	subq.w	#8,a7
	fmovem.x	l241,-(a7)
	movem.l	l240,-(a7)
	move.l	#$3fdfff97,l76
	move.l	#$2474538f,4+l76
	move.l	#$3fe0020c,l77
	move.l	#$49ba5e35,4+l77
	move.l	#$40000000,l78
	move.l	#$00000000,4+l78
	jsr	_stamp
	move.l	#$3ff00000,8+l79
	move.l	#$00000000,12+l79
	move.l	#$bff00000,16+l79
	move.l	#$00000000,20+l79
	move.l	#$bff00000,24+l79
	move.l	#$00000000,28+l79
	move.l	#$bff00000,32+l79
	move.l	#$00000000,36+l79
	moveq	#1,d2
l222
	fmove.d	16+l79,fp1
	fadd.d	8+l79,fp1
	fadd.d	24+l79,fp1
	fsub.d	32+l79,fp1
	fmul.d	l76,fp1
	fmove.d	fp1,8+l79
	fmove.d	16+l79,fp1
	fadd.d	8+l79,fp1
	fsub.d	24+l79,fp1
	fadd.d	32+l79,fp1
	fmul.d	l76,fp1
	fmove.d	fp1,16+l79
	fmove.d	8+l79,fp1
	fsub.d	16+l79,fp1
	fadd.d	24+l79,fp1
	fadd.d	32+l79,fp1
	fmul.d	l76,fp1
	fmove.d	fp1,24+l79
	fneg.d	8+l79,fp1
	fadd.d	16+l79,fp1
	fadd.d	24+l79,fp1
	fadd.d	32+l79,fp1
	fmul.d	l76,fp1
	fmove.d	fp1,32+l79
	addq.l	#1,d2
	cmp.l	#48,d2
	ble	l222
	move.l	12+l79,4+l109
	move.l	8+l79,l109
	move.l	36+l79,12+l109
	move.l	32+l79,8+l109
	moveq	#1,d2
l223
	pea	l79
	jsr	l83
	addq.l	#1,d2
	addq.w	#4,a7
	cmp.l	#56,d2
	ble	l223
	move.l	12+l79,20+l109
	move.l	8+l79,16+l109
	move.l	36+l79,28+l109
	move.l	32+l79,24+l109
	move.l	#1,l80
	moveq	#1,d2
l224
	cmp.l	#1,l80
	bne	l125
	move.l	#2,l80
	bra	l126
l125
	move.l	#3,l80
l126
	cmp.l	#2,l80
	ble	l128
	move.l	#0,l80
	bra	l129
l128
	move.l	#1,l80
l129
	tst.l	l80
	bgt	l131
	move.l	#1,l80
	bra	l132
l131
	move.l	#0,l80
l132
	addq.l	#1,d2
	cmp.l	#1380,d2
	ble	l224
	fmove.l	l80,fp6
	fmove.d	fp6,32+l109
	move.l	#1,l80
	move.l	#2,l81
	move.l	#3,l82
	moveq	#1,d2
l225
	move.l	l81,d1
	sub.l	l80,d1
	muls.l	l80,d1
	move.l	l82,d0
	sub.l	l81,d0
	muls.l	d1,d0
	move.l	d0,l80
	move.l	l82,d0
	muls.l	l81,d0
	move.l	l82,d1
	sub.l	l80,d1
	muls.l	l81,d1
	sub.l	d1,d0
	move.l	d0,l81
	move.l	l82,d1
	sub.l	l81,d1
	move.l	l81,d0
	add.l	l80,d0
	move.l	d0,d4
	muls.l	d1,d4
	move.l	d4,l82
	add.l	l82,d0
	move.w	2+l82,d1
	subq.w	#1,d1
	lea	l79,a0
	fmove.l	d0,fp6
	fmove.d	fp6,(0,a0,d1.w*8)
	move.l	l81,d0
	muls.l	l80,d0
	muls.l	l82,d0
	move.w	2+l81,d1
	subq.w	#1,d1
	lea	l79,a0
	fmove.l	d0,fp6
	fmove.d	fp6,(0,a0,d1.w*8)
	addq.l	#1,d2
	cmp.l	#840,d2
	ble	l225
	move.l	12+l79,44+l109
	move.l	8+l79,40+l109
	move.l	20+l79,52+l109
	move.l	16+l79,48+l109
	fmove.d	#$3fe0000000000000,fp5
	fmove.d	#$3fe0000000000000,fp4
	moveq	#1,d2
l226
	fmove.d	fp4,-(a7)
	jsr	l22
	fmove.x	fp0,fp2
	fmul.d	l78,fp2
	fmove.d	fp4,-(a7)
	jsr	l34
	fmul.x	fp0,fp2
	fmove.x	fp5,fp1
	fadd.x	fp4,fp1
	fmove.d	fp1,-(a7)
	jsr	l34
	fmove.x	fp0,fp3
	fmove.x	fp4,fp1
	fsub.x	fp5,fp1
	fmove.d	fp1,-(a7)
	jsr	l34
	fmove.x	fp0,fp1
	fadd.x	fp3,fp1
	fsub.d	#$3ff0000000000000,fp1
	fmove.x	fp1,fp0
	fmove.x	fp2,fp1
	fdiv.x	fp0,fp1
	fmove.d	fp1,-(a7)
	jsr	l46
	fmove.x	fp0,fp4
	fmul.d	l76,fp4
	fmove.d	fp5,-(a7)
	jsr	l22
	fmove.x	fp0,fp2
	fmul.d	l78,fp2
	fmove.d	fp5,-(a7)
	jsr	l34
	fmul.x	fp0,fp2
	fmove.x	fp5,fp1
	fadd.x	fp4,fp1
	fmove.d	fp1,-(a7)
	jsr	l34
	fmove.x	fp0,fp3
	fmove.x	fp4,fp1
	fsub.x	fp5,fp1
	fmove.d	fp1,-(a7)
	jsr	l34
	fmove.x	fp0,fp1
	fadd.x	fp3,fp1
	fsub.d	#$3ff0000000000000,fp1
	fmove.x	fp1,fp0
	fmove.x	fp2,fp1
	fdiv.x	fp0,fp1
	fmove.d	fp1,-(a7)
	jsr	l46
	fmove.x	fp0,fp5
	fmul.d	l76,fp5
	addq.l	#1,d2
	add.w	#80,a7
	cmp.l	#128,d2
	ble	l226
	fmove.d	fp4,56+l109
	fmove.d	fp5,64+l109
	move.l	#$3ff00000,(0+l242,a7)
	move.l	#$00000000,(4+l242,a7)
	moveq	#1,d2
	lea	(0+l242,a7),a2
l227
	move.l	a2,-(a7)
	move.l	#$00000000,-(a7)
	move.l	#$3ff00000,-(a7)
	move.l	#$00000000,-(a7)
	move.l	#$3ff00000,-(a7)
	jsr	l103
	addq.l	#1,d2
	add.w	#20,a7
	cmp.l	#3596,d2
	ble	l227
	move.l	(4+l242,a7),76+l109
	move.l	(0+l242,a7),72+l109
	move.l	#1,l80
	move.l	#2,l81
	move.l	#3,l82
	move.l	#$3ff00000,8+l79
	move.l	#$00000000,12+l79
	move.l	#$40000000,16+l79
	move.l	#$00000000,20+l79
	move.l	#$40080000,24+l79
	move.l	#$00000000,28+l79
	moveq	#1,d2
l228
	jsr	l97
	addq.l	#1,d2
	cmp.l	#2464,d2
	ble	l228
	move.l	12+l79,84+l109
	move.l	8+l79,80+l109
	move.l	28+l79,92+l109
	move.l	24+l79,88+l109
	fmove.d	#$3fe8000000000000,fp4
	moveq	#1,d2
l229
	fmove.d	fp4,-(a7)
	jsr	l68
	fdiv.d	l77,fp0
	fmove.d	fp0,-(a7)
	jsr	l62
	fsqrt.x	fp0,fp0
	fmove.x	fp0,fp4
	addq.l	#1,d2
	add.w	#16,a7
	cmp.l	#372,d2
	ble	l229
	fmove.d	fp4,96+l109
	jsr	_stamp
	moveq	#0,d1
	moveq	#1,d3
l230
	move.w	d1,d0
	lsl.w	#3,d0
	lea	l109,a0
	lea	l153,a1
	add.w	d0,a1
	fmove.d	(0,a0,d0.w),fp1
	fmove.d	(a1),fp2
	fmove.x	fp1,fp0
	fsub.x	fp2,fp0
	ftst.x	fp2
	fbge	l159
	fneg.d	(a1),fp1
	bra	l160
l159
	fmove.x	fp2,fp1
l160
	ftst.x	fp0
	fbge	l162
	fneg.x	fp0,fp0
l162
	fcmp.d	#$3ff0000000000000,fp1
	fble	l166
	fmove.x	fp1,fp3
	bra	l167
l166
	fmove.d	#$3ff0000000000000,fp3
l167
	fmove.d	#$3e112e0be826d696,fp1
	fmul.x	fp3,fp1
	fcmp.x	fp0,fp1
	fbge	l164
	move.l	d3,d0
	bra	l110
l164
	addq.l	#1,d1
	addq.l	#1,d3
	cmp.l	#13,d1
	blt	l230
	moveq	#0,d0
l110
l240	reg	a2/d2/d3/d4
	movem.l	(a7)+,a2/d2/d3/d4
l241	freg	fp2/fp3/fp4/fp5/fp6
	fmovem.x	(a7)+,l241
l242	equ	76
	addq.w	#8,a7
	rts
	cnop	0,4
l153
	dc.l	$bfb13c98,$48afdff4
	dc.l	$bff212c3,$881ee00d
	dc.l	$bfafc53f,$afee2f26
	dc.l	$bff1f02c,$cb804f5e
	dc.l	$3ff00000,$00000000
	dc.l	$40180000,$00000000
	dc.l	$40180000,$00000000
	dc.l	$3fdfc0c1,$c0013562
	dc.l	$3fdfc082,$ab9d830c
	dc.l	$3fefff7c,$ede74eae
	dc.l	$40080000,$00000000
	dc.l	$40080000,$00000000
	dc.l	$3fe9335e,$19d37a94
	public	_stamp
	section	"BSS",bss
	cnop	0,4
l76
	ds.b	8
	cnop	0,4
l77
	ds.b	8
	cnop	0,4
l78
	ds.b	8
	cnop	0,4
l79
	ds.b	40
	cnop	0,4
l80
	ds.b	4
	cnop	0,4
l81
	ds.b	4
	cnop	0,4
l82
	ds.b	4
	cnop	0,4
l109
	ds.b	128
