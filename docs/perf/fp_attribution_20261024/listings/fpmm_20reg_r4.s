	idnt	"c/fpmm.c"
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	section	"CODE",code
	cnop	0,4
l4
	fmovem.x	l35,-(a7)
	movem.l	l34,-(a7)
	moveq	#0,d4
l28
	moveq	#0,d2
	move.w	d4,d0
	muls.w	#160,d0
	lea	l1,a2
	add.w	d0,a2
	lea	l3,a3
	add.w	d0,a3
l29
	fmove.d	#$0000000000000000,fp1
	moveq	#0,d3
	move.w	d2,d0
	move.w	d0,d5
	lsl.w	#3,d5
l30
	move.w	d3,d0
	move.w	d0,d1
	lsl.w	#3,d1
	lea	(a2,d1.w),a1
	muls.w	#160,d0
	lea	l2,a0
	add.w	d0,a0
	add.w	d5,a0
	fmove.d	(a0),fp0
	fmul.d	(a1),fp0
	fadd.x	fp0,fp1
	addq.l	#1,d3
	cmp.l	#20,d3
	blt	l30
	fmove.d	fp1,(0,a3,d5.w)
	addq.l	#1,d2
	cmp.l	#20,d2
	blt	l29
	addq.l	#1,d4
	cmp.l	#20,d4
	blt	l28
l34	reg	a2/a3/d2/d3/d4/d5
	movem.l	(a7)+,a2/a3/d2/d3/d4/d5
l35	freg
l36	equ	24
	rts
; stacksize=24
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l37
	fmovem.x	l44,-(a7)
	movem.l	l43,-(a7)
	fmove.d	(4+l45,a7),fp1
	fbge	l41
	fneg.x	fp1,fp0
	bra	l42
l41
	fmove.x	fp1,fp0
l42
l43	reg
l44	freg
l45	equ	0
	rts
; stacksize=0
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	public	_main
	cnop	0,4
_main
	sub.w	#16,a7
	fmovem.x	l149,-(a7)
	movem.l	l148,-(a7)
	moveq	#0,d1
l130
	moveq	#0,d2
	moveq	#1,d3
	add.l	d1,d3
	fmove.l	d3,fp2
	move.w	d1,d0
	muls.w	#160,d0
	lea	l1,a2
	add.w	d0,a2
	fmove.l	d1,fp1
	lea	l2,a1
	add.w	d0,a1
l131
	moveq	#2,d0
	add.l	d2,d0
	fmove.l	d0,fp0
	fmove.x	fp0,fp5
	fmove.x	fp2,fp0
	fdiv.x	fp5,fp0
	move.w	d2,d1
	lsl.w	#3,d1
	fmove.d	fp0,(0,a2,d1.w)
	moveq	#1,d0
	add.l	d2,d0
	fmove.l	d0,fp0
	fmul.d	#$3fd0000000000000,fp0
	fsub.x	fp1,fp0
	fmove.d	fp0,(0,a1,d1.w)
	move.l	d0,d2
	cmp.l	#20,d0
	blt	l131
	move.l	d3,d1
	cmp.l	#20,d3
	blt	l130
	jsr	_stamp
	moveq	#0,d5
l132
	jsr	l4
	addq.l	#1,d5
	cmp.l	#4,d5
	blt	l132
	jsr	_stamp
	fmove.d	#$0000000000000000,fp4
	moveq	#0,d1
l133
	moveq	#0,d2
	move.w	d1,d0
	muls.w	#160,d0
	lea	l3,a1
	add.w	d0,a1
l134
	move.w	d2,d0
	fadd.d	(0,a1,d0.w*8),fp4
	addq.l	#1,d2
	cmp.l	#20,d2
	blt	l134
	addq.l	#1,d1
	cmp.l	#20,d1
	blt	l133
	fmove.d	#$0000000000000000,fp2
	moveq	#0,d3
l135
	fmove.d	#$0000000000000000,fp1
	fmove.d	#$0000000000000000,fp3
	moveq	#0,d1
	move.w	d3,d4
	move.w	d4,d5
	lsl.w	#3,d5
l136
	move.w	d1,d0
	muls.w	#160,d0
	lea	l1,a0
	add.w	d0,a0
	fadd.d	(0,a0,d5.w),fp1
	addq.l	#1,d1
	cmp.l	#20,d1
	blt	l136
	moveq	#0,d2
	move.w	#160,d0
	muls.w	d4,d0
	lea	l2,a1
	add.w	d0,a1
l137
	move.w	d2,d0
	fadd.d	(0,a1,d0.w*8),fp3
	addq.l	#1,d2
	cmp.l	#20,d2
	blt	l137
	fmove.x	fp3,fp0
	fmul.x	fp1,fp0
	fadd.x	fp0,fp2
	addq.l	#1,d3
	cmp.l	#20,d3
	blt	l135
	fmove.x	fp4,fp0
	fsub.x	fp2,fp0
	fmove.d	fp0,-(a7)
	jsr	l37
	fmove.d	fp0,(8+l150,a7)
	fmove.d	fp2,-(a7)
	jsr	l37
	add.w	#16,a7
	fcmp.d	#$3ff0000000000000,fp0
	fble	l83
	fmove.d	fp2,-(a7)
	jsr	l37
	fmove.d	fp0,(16+l150,a7)
	addq.w	#8,a7
	bra	l84
l83
	move.l	#$3ff00000,(8+l150,a7)
	move.l	#$00000000,(12+l150,a7)
l84
	fmove.d	#$3e112e0be826d696,fp0
	fmul.d	(8+l150,a7),fp0
	fcmp.d	(0+l150,a7),fp0
	fbge	l81
	moveq	#1,d0
	bra	l46
l81
	fmove.d	#$0000000000000000,fp2
	moveq	#0,d3
l138
	move.w	d3,d0
	move.w	d0,d1
	lea	480+l1,a1
	muls.w	#160,d0
	lea	40+l2,a0
	fmove.d	(0,a0,d0.w),fp0
	fmul.d	(0,a1,d1.w*8),fp0
	fadd.x	fp0,fp2
	addq.l	#1,d3
	cmp.l	#20,d3
	blt	l138
	fmove.d	520+l3,fp0
	fsub.x	fp2,fp0
	fmove.d	fp0,-(a7)
	jsr	l37
	fmove.d	fp0,(8+l150,a7)
	fmove.d	fp2,-(a7)
	jsr	l37
	add.w	#16,a7
	fcmp.d	#$3ff0000000000000,fp0
	fble	l92
	fmove.d	fp2,-(a7)
	jsr	l37
	fmove.d	fp0,(16+l150,a7)
	addq.w	#8,a7
	bra	l93
l92
	fmove.d	#$3ff0000000000000,fp0
	fmove.d	fp0,(8+l150,a7)
l93
	fmove.d	#$3e112e0be826d696,fp0
	fmul.d	(8+l150,a7),fp0
	fcmp.d	(0+l150,a7),fp0
	fbge	l90
	moveq	#2,d0
	bra	l46
l90
	moveq	#0,d0
l46
l148	reg	a2/a3/a4/d2/d3/d4/d5/d6
	movem.l	(a7)+,a2/a3/a4/d2/d3/d4/d5/d6
l149	freg	fp2/fp3/fp4/fp5/fp6
	fmovem.x	(a7)+,l149
l150	equ	92
	add.w	#16,a7
	rts
	public	_stamp
	section	"BSS",bss
	cnop	0,4
l1
	ds.b	3200
	cnop	0,4
l2
	ds.b	3200
	cnop	0,4
l3
	ds.b	3200
