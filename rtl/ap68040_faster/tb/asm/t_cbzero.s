; AP68040: dirty copyback lines must survive a streaming store miss storm
; assembled with vasmm68k_mot -Fbin -m68040
;
; The NeXT kernel's vm_fault zero-fills a page with bzero (the exact routine
; below, 8 KB of unrolled CLR.L through a supervisor copyback transparent
; translation) while its vm_page structures sit dirty in the data cache.
; Every store of the bzero misses and allocates, so each dirty structure
; line is evicted and pushed.  On hardware (2026-10-19) a vm_page flag
; update was lost around a zero fill.  This checks:
;   1    a 4 KB structure region written (all lines dirty), byte flags
;        changed with ORI.B/ANDI.B/BSET/BCLR, then bzero of 8 KB elsewhere:
;        every structure long reads back as written
;   2    the same, interleaved: bzero 512 bytes, update flags, repeat
;   3    after CPUSHA and the caches off, memory holds the structure
;        region as written and the zeroed page is zero
FAILREG	equ	$F100
DONEREG	equ	$F102
STRUCT	equ	$20000		; 4 KB of "vm_page" data (the cache's size)
ZPAGE	equ	$30000		; the page being zero-filled (8 KB)
ZPAGE2	equ	$34000

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
	moveq	#0,d6			; round

;------------------------------------------------- 1 structure dirty, then bzero 8 KB
round:
	bsr	fill_struct		; d5 = seed for this round
	bsr	flip_flags
	move.l	#ZPAGE,-(sp)
	move.l	#$2000,-(sp)
	bsr	bzero
	addq.l	#8,sp
	bsr	check_struct
	tst.l	d0
	beq.s	.ok1
	failt	1
.ok1:
;------------------------------------------------- 2 interleaved
	moveq	#15,d4
	lea	(ZPAGE2).l,a4
.il:	move.l	a4,-(sp)
	move.l	#$200,-(sp)
	bsr	bzero
	addq.l	#8,sp
	lea	$200(a4),a4
	bsr	flip_flags
	dbf	d4,.il
	bsr	check_struct
	tst.l	d0
	beq.s	.ok2
	failt	2
.ok2:
	addq.l	#1,d6
	cmp.l	#6,d6
	bne	round

;------------------------------------------------- 3 memory after CPUSHA
	cpusha	dc
	moveq	#0,d0
	movec	d0,cacr
	cinva	bc
	bsr	check_struct
	tst.l	d0
	beq.s	.ok3
	failt	3
.ok3:	lea	(ZPAGE).l,a0
	move.w	#$2000/4-1,d1
.z:	tst.l	(a0)+
	beq.s	.zn
	failt	4
.zn:	dbf	d1,.z

	bsr	nocache
	move.w	#$600D,(DONEREG).l
	bra.s	*

; the structure region: long i = (STRUCT + 4i) ^ seed, seed from the round;
; flip_flags then changes byte +2 of every 16-byte line and keeps the
; expected values in step (byte +2 of each line: |= $40, &= $FB, bset 7,
; bclr 0 on alternate rounds)
fill_struct:
	move.l	d6,d5
	mulu.l	#$9E3779B1,d5
	lea	(STRUCT).l,a0
	move.w	#$1000/4-1,d1
.f:	move.l	a0,d0
	eor.l	d5,d0
	move.l	d0,(a0)+
	dbf	d1,.f
	rts

flip_flags:
	lea	(STRUCT+2).l,a0
	move.w	#$1000/16-1,d1
.fl:	ori.b	#$40,(a0)
	andi.b	#$fb,(a0)
	bset	#7,(a0)
	bclr	#0,(a0)
	lea	16(a0),a0
	dbf	d1,.fl
	rts

; d0 = 0 if every long matches: (addr ^ seed) with byte +2 of each line
; carrying the flag changes (ORI $40, ANDI $FB, BSET 7, BCLR 0 are
; idempotent, so any number of flips gives the same byte)
check_struct:
	lea	(STRUCT).l,a0
	move.w	#$1000/4-1,d1
.c:	move.l	a0,d0
	eor.l	d5,d0
	move.l	a0,d2
	and.l	#$C,d2
	bne.s	.cmp
	move.l	d0,d2			; long 0 of the line: byte +2 is the flags byte
	lsr.l	#8,d2
	or.b	#$C0,d2
	and.b	#$FA,d2
	lsl.l	#8,d2
	and.l	#$0000FF00,d2
	and.l	#$FFFF00FF,d0
	or.l	d2,d0
.cmp:	cmp.l	(a0)+,d0
	bne.s	.bad
	dbf	d1,.c
	moveq	#0,d0
	rts
.bad:	moveq	#1,d0
	rts

; the NeXT kernel's bzero (mk-183 at $04092E12), byte for byte
bzero:
	link.w	a6,#0
	movea.l	12(a6),a0
	move.l	8(a6),d0
	ble.s	.bz_end
	move.l	a0,d1
	neg.l	d1
	andi.l	#3,d1
	bra.s	.bz_al
.bz_b:	clr.b	(a0)+
	subq.l	#1,d0
.bz_al:	dbeq	d1,.bz_b
	move.l	d0,d1
	andi.l	#$1C,d1
	lsr.l	#1,d1
	neg.l	d1
	addi.l	#$12,d1
	dc.w	$4EFB,$1800		; jmp (0,pc,d1.l): the kernel's computed jump
.bz_j:	clr.l	(a0)+
	clr.l	(a0)+
	clr.l	(a0)+
	clr.l	(a0)+
	clr.l	(a0)+
	clr.l	(a0)+
	clr.l	(a0)+
	clr.l	(a0)+
	subi.l	#$20,d0
	bge.s	.bz_j
	btst	#1,d0
	beq.s	.bz_w
	clr.w	(a0)+
.bz_w:	btst	#0,d0
	beq.s	.bz_end
	clr.b	(a0)
.bz_end:
	unlk	a6
	rts

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
