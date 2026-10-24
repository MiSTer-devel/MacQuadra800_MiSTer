	idnt	"c/fpmm.c"
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	section	"CODE",code
	cnop	0,4
l4
	fmovem.x	l41,-(a7)
	movem.l	l40,-(a7)
	moveq	#0,d4
l34
	moveq	#0,d3
	move.w	d4,d0
	muls.w	#160,d0
	lea	l3,a4
	add.w	d0,a4
	lea	l1,a3
	add.w	d0,a3
l35
	move.w	d3,d0
	move.w	d0,d5
	lsl.w	#3,d5
	lea	(a4,d5.w),a2
	move.l	#$00000000,(a2)
	move.l	#$00000000,(4,a2)
	moveq	#0,d2
l36
	move.w	d2,d0
	move.w	d0,d1
	lsl.w	#3,d1
	lea	(a3,d1.w),a1
	muls.w	#160,d0
	lea	l2,a0
	add.w	d0,a0
	add.w	d5,a0
	fmove.d	(a0),fp0
	fmul.d	(a1),fp0
	fmove.d	(a2),fp1
	fadd.x	fp0,fp1
	fmove.d	fp1,(a2)
	addq.l	#1,d2
	cmp.l	#20,d2
	blt	l36
	addq.l	#1,d3
	cmp.l	#20,d3
	blt	l35
	addq.l	#1,d4
	cmp.l	#20,d4
	blt	l34
l40	reg	a2/a3/a4/d2/d3/d4/d5
	movem.l	(a7)+,a2/a3/a4/d2/d3/d4/d5
l41	freg
l42	equ	28
	rts
; stacksize=28
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	cnop	0,4
l43
	fmovem.x	l50,-(a7)
	movem.l	l49,-(a7)
	fmove.d	(4+l51,a7),fp1
	fbge	l47
	fneg.x	fp1,fp0
	bra	l48
l47
	fmove.x	fp1,fp0
l48
l49	reg
l50	freg
l51	equ	0
	rts
; stacksize=0
	machine	68040
	fpu	1
	opt o+,ol+,op+,oc+,ot+,oj+,ob+,om+,a-
	public	_main
	cnop	0,4
_main
	sub.w	#16,a7
	fmovem.x	l155,-(a7)
	movem.l	l154,-(a7)
	moveq	#0,d1
l136
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
l137
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
	blt	l137
	move.l	d3,d1
	cmp.l	#20,d3
	blt	l136
	jsr	_stamp
	moveq	#0,d5
l138
	jsr	l4
	addq.l	#1,d5
	cmp.l	#4,d5
	blt	l138
	jsr	_stamp
	fmove.d	#$0000000000000000,fp4
	moveq	#0,d1
l139
	moveq	#0,d2
	move.w	d1,d0
	muls.w	#160,d0
	lea	l3,a1
	add.w	d0,a1
l140
	move.w	d2,d0
	fadd.d	(0,a1,d0.w*8),fp4
	addq.l	#1,d2
	cmp.l	#20,d2
	blt	l140
	addq.l	#1,d1
	cmp.l	#20,d1
	blt	l139
	fmove.d	#$0000000000000000,fp2
	moveq	#0,d3
l141
	fmove.d	#$0000000000000000,fp1
	fmove.d	#$0000000000000000,fp3
	moveq	#0,d1
	move.w	d3,d4
	move.w	d4,d5
	lsl.w	#3,d5
l142
	move.w	d1,d0
	muls.w	#160,d0
	lea	l1,a0
	add.w	d0,a0
	fadd.d	(0,a0,d5.w),fp1
	addq.l	#1,d1
	cmp.l	#20,d1
	blt	l142
	moveq	#0,d2
	move.w	#160,d0
	muls.w	d4,d0
	lea	l2,a1
	add.w	d0,a1
l143
	move.w	d2,d0
	fadd.d	(0,a1,d0.w*8),fp3
	addq.l	#1,d2
	cmp.l	#20,d2
	blt	l143
	fmove.x	fp3,fp0
	fmul.x	fp1,fp0
	fadd.x	fp0,fp2
	addq.l	#1,d3
	cmp.l	#20,d3
	blt	l141
	fmove.x	fp4,fp0
	fsub.x	fp2,fp0
	fmove.d	fp0,-(a7)
	jsr	l43
	fmove.d	fp0,(8+l156,a7)
	fmove.d	fp2,-(a7)
	jsr	l43
	add.w	#16,a7
	fcmp.d	#$3ff0000000000000,fp0
	fble	l89
	fmove.d	fp2,-(a7)
	jsr	l43
	fmove.d	fp0,(16+l156,a7)
	addq.w	#8,a7
	bra	l90
l89
	move.l	#$3ff00000,(8+l156,a7)
	move.l	#$00000000,(12+l156,a7)
l90
	fmove.d	#$3e112e0be826d696,fp0
	fmul.d	(8+l156,a7),fp0
	fcmp.d	(0+l156,a7),fp0
	fbge	l87
	moveq	#1,d0
	bra	l52
l87
	fmove.d	#$0000000000000000,fp2
	moveq	#0,d3
l144
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
	blt	l144
	fmove.d	520+l3,fp0
	fsub.x	fp2,fp0
	fmove.d	fp0,-(a7)
	jsr	l43
	fmove.d	fp0,(8+l156,a7)
	fmove.d	fp2,-(a7)
	jsr	l43
	add.w	#16,a7
	fcmp.d	#$3ff0000000000000,fp0
	fble	l98
	fmove.d	fp2,-(a7)
	jsr	l43
	fmove.d	fp0,(16+l156,a7)
	addq.w	#8,a7
	bra	l99
l98
	fmove.d	#$3ff0000000000000,fp0
	fmove.d	fp0,(8+l156,a7)
l99
	fmove.d	#$3e112e0be826d696,fp0
	fmul.d	(8+l156,a7),fp0
	fcmp.d	(0+l156,a7),fp0
	fbge	l96
	moveq	#2,d0
	bra	l52
l96
	moveq	#0,d0
l52
l154	reg	a2/a3/a4/d2/d3/d4/d5/d6
	movem.l	(a7)+,a2/a3/a4/d2/d3/d4/d5/d6
l155	freg	fp2/fp3/fp4/fp5/fp6
	fmovem.x	(a7)+,l155
l156	equ	92
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
