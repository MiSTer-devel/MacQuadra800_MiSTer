; AP68040: a dirty line evicted and re-read at once
; assembled with vasmm68k_mot -Fbin -m68040
;
; Lines of ONE data cache set (addresses $400 apart: the same set index,
; different tags) are written in turn, each store allocating a line and,
; from the fifth on, evicting a dirty one into the push buffer; each
; evicted line is then read back at once, while its push may still be in
; flight, and must return what was written.  The NeXT kernel on hardware
; (2026-10-19) read zero from kernel globals memory held set (a pv table
; base, a name-cache link) after exactly such a sequence.
;   1   8 lines written $400 apart, each read back right after the write
;       that evicted it (the fifth write and later)
;   2   16 lines, the whole set turned over three times, verified after
;       every write
;   3   the same with a load of the evicted line's SECOND long word
;   4   the same with the data cache's copyback memory under DTT0 and the
;       victim re-written (a store hit after the eviction) then read
FAILREG	equ	$F100
DONEREG	equ	$F102
LINES	equ	$40000		; line k at LINES + k*$400 (set 0, tags apart)

failt	macro
	move.w	#\1,d7
	bra	fail_all
	endm

	org	0
	dc.l	$3400
	dc.l	start
	rept	254
	dc.l	unexp
	endr

	org	$400
start:
	move.w	#$2700,sr
	move.l	#$0000A020,d0		; ITT0/DTT0: 0-16 MB supervisor copyback
	movec	d0,itt0
	movec	d0,dtt0
	move.l	#$80008000,d0
	movec	d0,cacr

;------------------------------------------------- 1 eight lines, read each evicted line at once
	moveq	#0,d6			; test number in d6 for the failure code
	bsr	fill8
	bsr	verify8			; (settled)
;------------------------------------------------- 2 sixteen lines, three turns, verified every write
	moveq	#1,d6
	moveq	#2,d5
.t2:	lea	(LINES).l,a0
	move.l	#$A5A50000,d2
	add.l	d5,d2
	moveq	#15,d1
.w2:	move.l	d2,(a0)			; allocate (evicts the line written 4 stores ago)
	move.l	d2,12(a0)
	; read back the line evicted by THIS store: 4 lines back
	lea	-$1000(a0),a1
	cmpa.l	#LINES,a1
	blo.s	.n2
	move.l	d2,d3
	subq.l	#4,d3			; its value: d2 - 4 (one per line)
	cmp.l	(a1),d3
	bne	fail2
	cmp.l	12(a1),d3
	bne	fail2
.n2:	addq.l	#1,d2
	lea	$400(a0),a0
	dbf	d1,.w2
	dbf	d5,.t2

;------------------------------------------------- 3 the second long word of the evicted line
	moveq	#2,d6
	lea	(LINES).l,a0
	move.l	#$5A5A0000,d2
	moveq	#15,d1
.w3:	move.l	d2,4(a0)
	lea	-$1000(a0),a1
	cmpa.l	#LINES,a1
	blo.s	.n3
	move.l	d2,d3
	subq.l	#4,d3
	cmp.l	4(a1),d3
	bne	fail3
.n3:	addq.l	#1,d2
	lea	$400(a0),a0
	dbf	d1,.w3

;------------------------------------------------- 4 evicted, re-written (store hit on the refilled line), read
	moveq	#3,d6
	lea	(LINES).l,a0
	move.l	#$C3C30000,d2
	moveq	#15,d1
.w4:	move.l	d2,8(a0)
	lea	-$1000(a0),a1
	cmpa.l	#LINES,a1
	blo.s	.n4
	move.l	d2,d3
	subq.l	#4,d3
	move.l	d3,d4
	eori.l	#$FFFF,d4
	move.l	d4,8(a1)		; re-write the just-evicted line (allocates it again)
	cmp.l	8(a1),d4
	bne	fail4
	cmp.l	(a1),d3			; the other long written earlier... (test 2/3 left patterns: skip)
.n4:	addq.l	#1,d2
	lea	$400(a0),a0
	dbf	d1,.w4

	bsr	nocache
	move.w	#$600D,(DONEREG).l
	bra.s	*

fill8:
	lea	(LINES).l,a0
	move.l	#$11110000,d2
	moveq	#7,d1
.f:	move.l	d2,(a0)
	lea	-$1000(a0),a1
	cmpa.l	#LINES,a1
	blo.s	.fn
	move.l	d2,d3
	subq.l	#4,d3
	cmp.l	(a1),d3
	bne	fail1
.fn:	addq.l	#1,d2
	lea	$400(a0),a0
	dbf	d1,.f
	rts
verify8:
	lea	(LINES).l,a0
	move.l	#$11110000,d2
	moveq	#7,d1
.v:	cmp.l	(a0),d2
	bne	fail1
	addq.l	#1,d2
	lea	$400(a0),a0
	dbf	d1,.v
	rts

fail1:	failt	1
fail2:	failt	2
fail3:	failt	3
fail4:	failt	4
nocache:
	move.l	#$0000A040,d0
	movec	d0,dtt0
	cpusha	dc
	rts
unexp:	failt	98
fail_all:
	bsr	nocache
	move.w	d7,(FAILREG).l
	move.w	#$BAD,(DONEREG).l
	bra.s	*
