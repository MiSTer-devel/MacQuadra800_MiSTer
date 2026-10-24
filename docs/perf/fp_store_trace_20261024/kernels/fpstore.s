; fp_store_trace 2026-10-24: back-to-back FP store kernels for the dual
; core's standalone bench (rtl/ap68040_faster/tb/tb_ap68040.sv) and the
; shipping core's scratch bench (tb_wombat_prog).  As the attribution's C
; images: user mode, copyback data (DTT0), both caches on; the bench
; registers through DTT1 (supervisor, noncachable), so a stamp is a TRAP #0
; with the tag in d0.  Each kernel runs twice: the first pass warms the
; caches (I-cache, and the buffer's lines allocated dirty), the second is
; the one to read.  Stamp tags: kernel << 4 | pass, pass 1 first (odd
; tags), then pass 0 (even tags); the closing stamp of a kernel is its
; opening tag + 8, and the cycles printed with it are the kernel's.
;
;   $1x  empty (the stamp overhead)
;   $2x  100 x fmove.d fp0,(a0)+          FPU_K_OUT8 with the (An)+ update
;   $3x  100 x fmove.d fp0,(a0)           the same address every time
;   $4x  100 x fmove.d fp0,(a0)+ ; addq.l #1,d1
;   $5x  100 x fmove.d fp0,(a0)  ; addq.l #1,d1
;   $6x  100 x fmove.s fp0,(a0)+          FPU_K_OUT4: no GET, one store
;   $7x  100 x fmove.x fp0,(a0)+          FPU_K_OUT12: two GETs, three stores
;   $8x   50 x fmove.x fp0,-(a7)
;   $9x   50 x fmovem.x fp0-fp1,-(a7)
;   $Ax   50 x fmovem.x (a7)+,fp0-fp1
;   $Bx  100 x fmove.l fp0,(a0)+          integer store: F_SHR / F_PACKI
;   $Cx  100 x move.l d1,(a0)+            an integer store, for reference
;   $Dx  100 x fmove.d (a0)+,fp0          an FP load, for reference (the
;                                         buffer refilled with doubles first)
;   $Ex  100 x fadd.x fp1,fp0 ; fmove.d fp0,(a0)+   the matmul shape
;   $Fx  100 x fmove.d fp0,(a0)+ ; fmove.d (a1)+,fp2   store then unrelated load

STAMP	equ	$F108
DONEREG	equ	$F102
BUF	equ	$20000
BUF2	equ	$24000

STMP	macro
	move.w	#\1,d0
	add.w	d5,d0
	trap	#0
	endm

	org	0
	dc.l	$7F000		; SSP
	dc.l	start
	rept	254
	dc.l	unexp
	endr

start:
	move.l	#$80008000,d0	; both caches on
	movec	d0,cacr
	move.l	#$00008020,d0	; DTT0: user data, copyback
	movec	d0,dtt0
	move.l	#$0000A040,d0	; DTT1: supervisor data, noncachable serialized
	movec	d0,dtt1
	move.l	#tstamp,($80).w	; TRAP #0: stamp, tag in d0
	move.l	#tdone,($84).w	; TRAP #1: done, d0 = 0 passes
	lea	($7E000).l,a0
	move.l	a0,usp
	andi.w	#$DFFF,sr	; user mode
	fmove.l	#3,fp0		; 3.0: an ordinary normalized value
	fmove.l	#5,fp1
	fmove.l	#7,fp2
	moveq	#0,d1

; $1x: the stamp overhead
	moveq	#1,d5
k0:	STMP	$10
	STMP	$18
	dbra	d5,k0

; $2x: fmove.d fp0,(a0)+
	moveq	#1,d5
k1:	lea	(BUF).l,a0
	STMP	$20
	rept	100
	fmove.d	fp0,(a0)+
	endr
	STMP	$28
	dbra	d5,k1

; $3x: fmove.d fp0,(a0)
	moveq	#1,d5
k2:	lea	(BUF).l,a0
	STMP	$30
	rept	100
	fmove.d	fp0,(a0)
	endr
	STMP	$38
	dbra	d5,k2

; $4x: fmove.d fp0,(a0)+ ; addq.l #1,d1
	moveq	#1,d5
k3:	lea	(BUF).l,a0
	STMP	$40
	rept	100
	fmove.d	fp0,(a0)+
	addq.l	#1,d1
	endr
	STMP	$48
	dbra	d5,k3

; $5x: fmove.d fp0,(a0) ; addq.l #1,d1
	moveq	#1,d5
k4:	lea	(BUF).l,a0
	STMP	$50
	rept	100
	fmove.d	fp0,(a0)
	addq.l	#1,d1
	endr
	STMP	$58
	dbra	d5,k4

; $6x: fmove.s fp0,(a0)+
	moveq	#1,d5
k5:	lea	(BUF).l,a0
	STMP	$60
	rept	100
	fmove.s	fp0,(a0)+
	endr
	STMP	$68
	dbra	d5,k5

; $7x: fmove.x fp0,(a0)+
	moveq	#1,d5
k6:	lea	(BUF).l,a0
	STMP	$70
	rept	100
	fmove.x	fp0,(a0)+
	endr
	STMP	$78
	dbra	d5,k6

; $8x: fmove.x fp0,-(a7)
	moveq	#1,d5
k7:	STMP	$80
	rept	50
	fmove.x	fp0,-(a7)
	endr
	STMP	$88
	lea	600(a7),a7
	dbra	d5,k7

; $9x / $Ax: fmovem.x fp0-fp1,-(a7) then fmovem.x (a7)+,fp0-fp1
	moveq	#1,d5
k8:	STMP	$90
	rept	50
	fmovem.x	fp0-fp1,-(a7)
	endr
	STMP	$98
	STMP	$A0
	rept	50
	fmovem.x	(a7)+,fp0-fp1
	endr
	STMP	$A8
	dbra	d5,k8

; $Bx: fmove.l fp0,(a0)+
	moveq	#1,d5
k9:	lea	(BUF).l,a0
	STMP	$B0
	rept	100
	fmove.l	fp0,(a0)+
	endr
	STMP	$B8
	dbra	d5,k9

; $Cx: move.l d1,(a0)+
	moveq	#1,d5
k10:	lea	(BUF).l,a0
	STMP	$C0
	rept	100
	move.l	d1,(a0)+
	endr
	STMP	$C8
	dbra	d5,k10

; $Dx: fmove.d (a0)+,fp0  (the buffer holds the doubles $2x wrote: 3.0)
	moveq	#1,d5
k11:	lea	(BUF).l,a0
	rept	100		; the buffer holds 3.0 doubles again (the
	fmove.d	fp0,(a0)+	; integer kernels left denormal bit patterns)
	endr
	lea	(BUF).l,a0
	STMP	$D0
	rept	100
	fmove.d	(a0)+,fp0
	endr
	STMP	$D8
	dbra	d5,k11

; $Ex: fadd.x fp1,fp0 ; fmove.d fp0,(a0)+
	moveq	#1,d5
k12:	lea	(BUF).l,a0
	fmove.l	#3,fp0
	STMP	$E0
	rept	100
	fadd.x	fp1,fp0
	fmove.d	fp0,(a0)+
	endr
	STMP	$E8
	dbra	d5,k12

; $Fx: fmove.d fp0,(a0)+ ; fmove.d (a1)+,fp2
	moveq	#1,d5
k13:	lea	(BUF2).l,a1
	rept	100		; BUF2 = 3.0 doubles for the loads
	fmove.d	fp0,(a1)+
	endr
	lea	(BUF).l,a0
	lea	(BUF2).l,a1
	STMP	$F0
	rept	100
	fmove.d	fp0,(a0)+
	fmove.d	(a1)+,fp2
	endr
	STMP	$F8
	dbra	d5,k13

	moveq	#0,d0
	trap	#1
	bra.s	*

; TRAP #0: the stamp (supervisor: DTT1 puts the write on the bus)
tstamp:
	nop
	move.w	d0,(STAMP).l
	nop
	rte
; TRAP #1: the end, d0 = 0 passes
tdone:
	tst.l	d0
	bne.s	tfail
	move.w	#$600D,(DONEREG).l
	bra.s	*
tfail:
	move.w	d0,($F100).l
	move.w	#$BAD0,(DONEREG).l
	bra.s	*
unexp:
	moveq	#99,d0
	bra.s	tfail
