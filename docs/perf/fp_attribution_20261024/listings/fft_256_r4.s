	idnt	"c/fft.c"
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	section	"CODE",code
	cnop	0,4
l5
	fmovem.x	l12,-(a7)
	movem.l	l11,-(a7)
	fmove.d	(4+l13,a7),fp1
	fbge	l9
	fneg.x	fp1,fp0
	bra	l10
l9
	fmove.x	fp1,fp0
l10
l11	reg
l12	freg
l13	equ	0
	rts
; stacksize=0
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l14
	fmovem.x	l23,-(a7)
	movem.l	l22,-(a7)
	fmove.d	(4+l24,a7),fp2
	fcmp.d	#$3ff921fb54442d18,fp2
	fble	l18
	fneg.x	fp2
	fadd.d	#$400921fb54442d18,fp2
	bra	l21
l18
	fcmp.d	#$bff921fb54442d18,fp2
	fbge	l21
	fneg.x	fp2
	fadd.d	#$c00921fb54442d18,fp2
l21
	fmove.x	fp2,fp1
	fmul.x	fp2,fp1
	fmove.d	#$bc62f49b46814157,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3ce952c77030ad4a,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bd6ae7f3e733b81f,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3de6124613a86d09,fp0
	fmul.x	fp1,fp0
	fadd.d	#$be5ae64567f544e4,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3ec71de3a556c734,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bf2a01a01a01a01a,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3f81111111111111,fp0
	fmul.x	fp1,fp0
	fadd.d	#$bfc5555555555555,fp0
	fmul.x	fp1,fp0
	fadd.d	#$3ff0000000000000,fp0
	fmul.x	fp2,fp0
l22	reg
l23	freg	fp2
	fmovem.x	(a7)+,l23
l24	equ	12
	rts
; stacksize=12
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l25
	sub.w	#64,a7
	fmovem.x	l86,-(a7)
	movem.l	l85,-(a7)
	moveq	#0,d3
	moveq	#0,d2
l75
	cmp.l	d2,d3
	ble	l33
	move.w	d2,d0
	lsl.w	#3,d0
	lea	l1,a0
	add.w	d0,a0
	move.l	(4,a0),(4+l87,a7)
	move.l	(a0),(0+l87,a7)
	lea	l2,a2
	add.w	d0,a2
	move.l	(4,a2),(12+l87,a7)
	move.l	(a2),(8+l87,a7)
	move.w	d3,d0
	lsl.w	#3,d0
	lea	l1,a1
	add.w	d0,a1
	move.l	(4,a1),(4,a0)
	move.l	(a1),(a0)
	lea	l2,a0
	add.w	d0,a0
	move.l	(4,a0),(4,a2)
	move.l	(a0),(a2)
	move.l	(4+l87,a7),(4,a1)
	move.l	(0+l87,a7),(a1)
	move.l	(12+l87,a7),(4,a0)
	move.l	(8+l87,a7),(a0)
l33
	move.l	#128,d0
	cmp.l	#128,d3
	blt	l81
l76
	sub.l	d0,d3
	asr.l	#1,d0
	ble	l81
	cmp.l	d3,d0
	ble	l76
l81
	add.l	d0,d3
	addq.l	#1,d2
	cmp.l	#255,d2
	blt	l75
	moveq	#1,d4
	fmove.l	(68+l87,a7),fp2
l77
	move.l	d4,d3
	lsl.l	#1,d3
	fmove.l	d4,fp0
	fmove.x	fp0,fp1
	fmove.d	#$400921fb54442d18,fp0
	fdiv.x	fp1,fp0
	fmul.x	fp2,fp0
	fmove.d	fp0,(0+l87,a7)
	fmove.d	#$3fe0000000000000,fp0
	fmul.d	(0+l87,a7),fp0
	fmove.d	fp0,(8+l87,a7)
	move.l	(12+l87,a7),-(a7)
	move.l	(12+l87,a7),-(a7)
	jsr	l14
	fmove.d	fp0,(24+l87,a7)
	fmove.d	(24+l87,a7),fp0
	fmul.d	#$c000000000000000,fp0
	fmove.d	fp0,(16+l87,a7)
	fmove.d	(16+l87,a7),fp0
	fmul.d	(24+l87,a7),fp0
	fmove.d	fp0,(32+l87,a7)
	move.l	(12+l87,a7),-(a7)
	move.l	(12+l87,a7),-(a7)
	jsr	l14
	fmove.d	fp0,(48+l87,a7)
	move.l	#$3ff00000,(56+l87,a7)
	move.l	#$00000000,(60+l87,a7)
	move.l	#$00000000,(64+l87,a7)
	move.l	#$00000000,(68+l87,a7)
	moveq	#0,d1
	add.w	#16,a7
	tst.l	d4
	ble	l83
	move.l	d4,d5
l78
	move.l	d1,d2
	cmp.l	#256,d1
	bge	l84
	move.l	d5,d6
l79
	move.w	d6,d0
	lsl.w	#3,d0
	lea	l1,a0
	add.w	d0,a0
	fmove.d	(a0),fp0
	fmul.d	(40+l87,a7),fp0
	fmove.d	fp0,(16+l87,a7)
	lea	l2,a2
	add.w	d0,a2
	fmove.d	(a2),fp0
	fmul.d	(48+l87,a7),fp0
	fmove.d	fp0,(56+l87,a7)
	fmove.d	(16+l87,a7),fp0
	fsub.d	(56+l87,a7),fp0
	fmove.d	fp0,(0+l87,a7)
	fmove.d	(a2),fp0
	fmul.d	(40+l87,a7),fp0
	fmove.d	fp0,(56+l87,a7)
	fmove.d	(a0),fp0
	fmul.d	(48+l87,a7),fp0
	fmove.d	fp0,(16+l87,a7)
	fmove.d	(16+l87,a7),fp0
	fadd.d	(56+l87,a7),fp0
	fmove.d	fp0,(8+l87,a7)
	move.w	d2,d0
	lsl.w	#3,d0
	lea	l1,a1
	add.w	d0,a1
	fmove.d	(a1),fp0
	fsub.d	(0+l87,a7),fp0
	fmove.d	fp0,(a0)
	lea	l2,a0
	add.w	d0,a0
	fmove.d	(a0),fp0
	fsub.d	(8+l87,a7),fp0
	fmove.d	fp0,(a2)
	fmove.d	(a1),fp0
	fadd.d	(0+l87,a7),fp0
	fmove.d	fp0,(a1)
	fmove.d	(a0),fp0
	fadd.d	(8+l87,a7),fp0
	fmove.d	fp0,(a0)
	add.l	d3,d2
	add.l	d3,d6
	cmp.l	#256,d2
	blt	l79
l84
	move.l	(44+l87,a7),(20+l87,a7)
	move.l	(40+l87,a7),(16+l87,a7)
	fmove.d	(24+l87,a7),fp0
	fmul.d	(16+l87,a7),fp0
	fmove.d	fp0,(0+l87,a7)
	fmove.d	(48+l87,a7),fp0
	fmul.d	(32+l87,a7),fp0
	fmove.d	fp0,(8+l87,a7)
	fmove.d	(0+l87,a7),fp0
	fsub.d	(8+l87,a7),fp0
	fmove.d	fp0,(8+l87,a7)
	fmove.d	(40+l87,a7),fp0
	fadd.d	(8+l87,a7),fp0
	fmove.d	fp0,(40+l87,a7)
	fmove.d	(48+l87,a7),fp0
	fmul.d	(24+l87,a7),fp0
	fmove.d	fp0,(8+l87,a7)
	fmove.d	(32+l87,a7),fp0
	fmul.d	(16+l87,a7),fp0
	fmove.d	fp0,(0+l87,a7)
	fmove.d	(0+l87,a7),fp0
	fadd.d	(8+l87,a7),fp0
	fmove.d	fp0,(0+l87,a7)
	fmove.d	(48+l87,a7),fp0
	fadd.d	(0+l87,a7),fp0
	fmove.d	fp0,(48+l87,a7)
	addq.l	#1,d1
	addq.l	#1,d5
	cmp.l	d1,d4
	bgt	l78
l83
	move.l	d3,d4
	cmp.l	#256,d3
	blt	l77
l85	reg	a2/d2/d3/d4/d5/d6
	movem.l	(a7)+,a2/d2/d3/d4/d5/d6
l86	freg	fp2
	fmovem.x	(a7)+,l86
l87	equ	36
	add.w	#64,a7
	rts
; stacksize=132
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	public	_main
	cnop	0,4
_main
	subq.w	#8,a7
	fmovem.x	l145,-(a7)
	movem.l	l144,-(a7)
	move.l	#12345,d3
	moveq	#0,d2
l136
	move.l	#1103515245,d0
	mulu.l	d3,d0
	move.l	#12345,d3
	add.l	d0,d3
	move.l	d3,d0
	lsr.l	#8,d0
	and.l	#65535,d0
	fmove.l	d0,fp0
	fdiv.d	#$40e0000000000000,fp0
	fsub.d	#$3ff0000000000000,fp0
	move.w	d2,d0
	lsl.w	#3,d0
	lea	l3,a1
	add.w	d0,a1
	fmove.d	fp0,(a1)
	move.l	#1103515245,d1
	mulu.l	d3,d1
	move.l	#12345,d3
	add.l	d1,d3
	move.l	d3,d1
	lsr.l	#8,d1
	and.l	#65535,d1
	fmove.l	d1,fp0
	fdiv.d	#$40e0000000000000,fp0
	fsub.d	#$3ff0000000000000,fp0
	lea	l4,a0
	add.w	d0,a0
	fmove.d	fp0,(a0)
	lea	l1,a2
	move.l	(4,a1),(4,a2,d0.w)
	move.l	(a1),(0,a2,d0.w)
	lea	l2,a1
	move.l	(4,a0),(4,a1,d0.w)
	move.l	(a0),(0,a1,d0.w)
	addq.l	#1,d2
	cmp.l	#256,d2
	blt	l136
	jsr	_stamp
	fmove.d	#$3f70000000000000,fp3
	moveq	#0,d5
l137
	move.l	#1,-(a7)
	jsr	l25
	move.l	#-1,-(a7)
	jsr	l25
	moveq	#0,d1
	addq.w	#8,a7
l138
	move.w	d1,d0
	lsl.w	#3,d0
	lea	l1,a0
	add.w	d0,a0
	fmove.d	(a0),fp0
	fmul.x	fp3,fp0
	fmove.d	fp0,(a0)
	lea	l2,a0
	add.w	d0,a0
	fmove.d	(a0),fp0
	fmul.x	fp3,fp0
	fmove.d	fp0,(a0)
	addq.l	#1,d1
	cmp.l	#256,d1
	blt	l138
	addq.l	#1,d5
	cmp.l	#4,d5
	blt	l137
	jsr	_stamp
	fmove.d	#$0000000000000000,fp2
	moveq	#0,d2
l139
	move.w	d2,d0
	move.w	d0,d3
	lsl.w	#3,d3
	lea	l1,a3
	add.w	d3,a3
	lea	l3,a5
	add.w	d3,a5
	fmove.d	(a3),fp0
	fsub.d	(a5),fp0
	fmove.d	fp0,(0+l146,a7)
	move.l	(4+l146,a7),-(a7)
	move.l	(4+l146,a7),-(a7)
	jsr	l5
	addq.w	#8,a7
	fcmp.x	fp0,fp2
	fbge	l107
	fmove.d	(a3),fp0
	fsub.d	(a5),fp0
	fmove.d	fp0,(0+l146,a7)
	move.l	(4+l146,a7),-(a7)
	move.l	(4+l146,a7),-(a7)
	jsr	l5
	fmove.x	fp0,fp2
	addq.w	#8,a7
l107
	lea	l2,a2
	add.w	d3,a2
	lea	l4,a4
	add.w	d3,a4
	fmove.d	(a2),fp0
	fsub.d	(a4),fp0
	fmove.d	fp0,(0+l146,a7)
	move.l	(4+l146,a7),-(a7)
	move.l	(4+l146,a7),-(a7)
	jsr	l5
	addq.w	#8,a7
	fcmp.x	fp0,fp2
	fbge	l109
	fmove.d	(a2),fp0
	fsub.d	(a4),fp0
	fmove.d	fp0,(0+l146,a7)
	move.l	(4+l146,a7),-(a7)
	move.l	(4+l146,a7),-(a7)
	jsr	l5
	fmove.x	fp0,fp2
	addq.w	#8,a7
l109
	addq.l	#1,d2
	cmp.l	#256,d2
	blt	l139
	fcmp.d	#$3e112e0be826d696,fp2
	fble	l111
	moveq	#1,d0
	bra	l88
l111
	moveq	#0,d0
l88
l144	reg	a2/a3/a4/a5/d2/d3/d4/d5
	movem.l	(a7)+,a2/a3/a4/a5/d2/d3/d4/d5
l145	freg	fp2/fp3
	fmovem.x	(a7)+,l145
l146	equ	56
	addq.w	#8,a7
	rts
	public	_stamp
	section	"BSS",bss
	cnop	0,4
l1
	ds.b	2048
	cnop	0,4
l2
	ds.b	2048
	cnop	0,4
l3
	ds.b	2048
	cnop	0,4
l4
	ds.b	2048
