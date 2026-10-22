; AP68040: the DBcc period floor (the dbcc_floor input, bench register $F10C)
; assembled with vasmm68k_mot -Fbin -m68040
;
; A host whose firmware times a bare "dbf d0,*" loop against a real 68040's
; 4 clocks per taken DBcc (the NeXT ROM's delay()) sets dbcc_floor so that
; a DBcc following a taken DBcc leaves EX no earlier than that many clocks
; after it.  The program times its loops with the bench's clock count
; ($F2EC, a noncachable read) and checks:
;   1    floor 0: 999 taken dbf cost well under 9 clocks each (the loop's
;        natural rate, 2-3 clocks)
;   2    floor 9: at least 9 clocks per taken dbf, and not more than the
;        floor plus the bracketing overhead
;   3    floor 4: the same at 4
;   4    a subq/bne loop runs the same with floor 9 as with floor 0: the
;        floor slows only DBcc
;   5    a never-taken dbf (counter 0) in a bne loop runs the same with
;        floor 9 as with floor 0: only a TAKEN DBcc arms the floor
;   6    floor 9 then floor 0 again: the floor releases (nothing sticks)

FAILREG	equ	$F100
DONEREG	equ	$F102
FLOOR	equ	$F10C		; bench: the core's dbcc_floor input (word)
CYCLES	equ	$F2EC		; bench: the clock count (long, read)

ITER	equ	1000		; dbf executions per timed loop (999 taken)
SLACK	equ	256		; bracketing overhead allowed (two bus reads, the
				; exit mispredict, wait states and BCLK/2)

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
	move.l	#$0000A040,d0		; DTT1: supervisor data noncachable
	movec	d0,dtt1			; (the bench registers)
	move.l	#$80008000,d0		; both caches on
	movec	d0,cacr
	move.w	#$2700,sr

; warm the instruction cache and the branch predictors on every timed loop
	move.w	#0,(FLOOR).l
	bsr	meas_dbf
	bsr	meas_bne
	bsr	meas_ntk

;------------------------------------------------- 1 floor 0: the natural rate
	move.w	#0,(FLOOR).l
	bsr	meas_dbf
	move.l	d2,d3			; d3 = cycles at floor 0
	cmp.l	#(ITER-1)*6,d2		; well under 9 a pass (2-3 natural)
	bhs	fail1

;------------------------------------------------- 2 floor 9
	move.w	#9,(FLOOR).l
	bsr	meas_dbf
	cmp.l	#(ITER-1)*9,d2
	blo	fail2
	cmp.l	#(ITER-1)*9+SLACK,d2
	bhi	fail3

;------------------------------------------------- 3 floor 4
	move.w	#4,(FLOOR).l
	bsr	meas_dbf
	cmp.l	#(ITER-1)*4,d2
	blo	fail4
	cmp.l	#(ITER-1)*4+SLACK,d2
	bhi	fail5

;------------------------------------------------- 4 subq/bne: not a DBcc
	move.w	#0,(FLOOR).l
	bsr	meas_bne
	move.l	d2,d4
	move.w	#9,(FLOOR).l
	bsr	meas_bne
	sub.l	d4,d2			; floor 9 minus floor 0
	bpl.s	.p4
	neg.l	d2
.p4:	cmp.l	#SLACK,d2
	bhi	fail6

;------------------------------------------------- 5 a never-taken dbf
	move.w	#0,(FLOOR).l
	bsr	meas_ntk
	move.l	d2,d4
	move.w	#9,(FLOOR).l
	bsr	meas_ntk
	sub.l	d4,d2
	bpl.s	.p5
	neg.l	d2
.p5:	cmp.l	#SLACK,d2
	bhi	fail7

;------------------------------------------------- 6 the floor releases
	move.w	#0,(FLOOR).l
	bsr	meas_dbf
	sub.l	d3,d2			; against test 1's count
	bpl.s	.p6
	neg.l	d2
.p6:	cmp.l	#SLACK,d2
	bhi	fail8

	move.w	#$600D,(DONEREG).l
	bra.s	*

; d2 = clocks around ITER executions of an aligned "dbf d0,*"
meas_dbf:
	move.w	#ITER-1,d0
	move.l	(CYCLES).l,d1
	cnop	0,4
.a:	dbf	d0,.a
	move.l	(CYCLES).l,d2
	sub.l	d1,d2
	rts

; d2 = clocks around ITER passes of a subq/bne loop
meas_bne:
	move.l	#ITER,d0
	move.l	(CYCLES).l,d1
	cnop	0,4
.b:	subq.l	#1,d0
	bne.s	.b
	move.l	(CYCLES).l,d2
	sub.l	d1,d2
	rts

; d2 = clocks around ITER passes of a bne loop holding a dbf that is never
; taken (its counter is 0 on every pass)
meas_ntk:
	move.l	#ITER,d0
	move.l	(CYCLES).l,d5
	cnop	0,4
.c:	moveq	#0,d1
	dbf	d1,.c			; d1 = 0 -> -1: falls through every time
	subq.l	#1,d0
	bne.s	.c
	move.l	(CYCLES).l,d2
	sub.l	d5,d2
	rts

fail1:	failt	1
fail2:	failt	2
fail3:	failt	3
fail4:	failt	4
fail5:	failt	5
fail6:	failt	6
fail7:	failt	7
fail8:	failt	8

fail_all:
	move.w	d7,(FAILREG).l
	move.w	#$BAD,(DONEREG).l
	bra.s	*

unexp:
	failt	99
