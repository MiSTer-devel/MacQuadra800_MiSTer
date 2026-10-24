; tb_quadra_cpu040 program: RAM at 0, the bench's result at $50000000 ($A5A5A5A5 = pass, else failing test number)
	org	0
	dc.l	$8000		; SSP
	dc.l	start
	dcb.l	22,fault	; 2..23
	dc.l	fault		; 24 spurious
	dc.l	irq1		; 25 level 1 autovector
	dcb.l	6,fault		; 26..31
	dcb.l	224,fault
start:
	moveq	#1,d7		; test 1: byte/word/long stores and loads, caches off
	lea	$4000,a0
	move.l	#$11223344,(a0)
	move.b	#$AA,1(a0)
	move.w	#$BBCC,2(a0)
	cmp.l	#$11AABBCC,(a0)
	bne	fail
	move.b	(a0),d0
	cmp.b	#$11,d0
	bne	fail
	move.w	2(a0),d0
	cmp.w	#$BBCC,d0
	bne	fail
	moveq	#2,d7		; test 2: misaligned long and word
	move.l	#$CAFEBABE,5(a0)
	move.l	5(a0),d0
	cmp.l	#$CAFEBABE,d0
	bne	fail
	move.b	4(a0),d1	; untouched byte (was 0)
	bne	fail
	move.w	#$1234,9(a0)
	cmp.w	#$1234,9(a0)
	bne	fail
	moveq	#3,d7		; test 3: copyback caches via DTTR0/ITTR0 on RAM
	move.l	#$0000C020,d0	; base 0, mask 0: $00xxxxxx, E, copyback (CM=01)
	movec	d0,dtt0
	movec	d0,itt0
	cinva	bc
	move.l	#$80008000,d0
	movec	d0,cacr
	lea	$5000,a1	; fill 1 KB with i*3, then sum it back
	move.w	#255,d1
	moveq	#0,d2
.f	move.l	d2,(a1)+
	addq.l	#3,d2
	dbf	d1,.f
	lea	$5000,a1
	move.w	#255,d1
	moveq	#0,d3
.s	add.l	(a1)+,d3
	dbf	d1,.s
	cmp.l	#97920,d3	; 3*(255*256/2)
	bne	fail
	moveq	#4,d7		; test 4: the pushed lines reach memory (read them caches off)
	cpusha	bc
	moveq	#0,d0
	movec	d0,cacr
	lea	$5000,a1
	move.w	#255,d1
	moveq	#0,d3
.t	add.l	(a1)+,d3
	dbf	d1,.t
	cmp.l	#97920,d3
	bne	fail
	moveq	#5,d7		; test 5: an autovectored level 1 interrupt
	move.l	#$80008000,d0
	movec	d0,cacr
	moveq	#0,d6
	move.w	#$2000,sr
	move.l	#$100000,d1
.w	tst.l	d6
	bne	.ok
	subq.l	#1,d1
	bne	.w
	bra	fail
.ok	moveq	#7,d7		; test 7: an unrolled copy from a read-to-pop port into copyback
				; RAM under a storm of interrupts (the Mac SCSI driver's 4 x 32 move.l (a1),(a2)+)
	move.l	#1,$50000008	; the bench: interrupt storm on, port counter to 0
	lea	$50000010,a1
	lea	$6000,a2
	moveq	#3,d5
.cp	rept	32
	move.l	(a1),(a2)+
	endr
	dbf	d5,.cp
	move.l	#0,$50000008	; storm off
	lea	$6000,a2
	moveq	#0,d0
	move.w	#127,d1
.ck	cmp.l	(a2)+,d0
	bne	fail
	addq.l	#1,d0
	dbf	d1,.ck
	moveq	#8,d7		; test 8: code written through the copyback D-cache runs after CPUSHA BC
	lea	$6800,a3	; a routine: moveq #1,d0 ; rts
	move.l	#$70014e75,(a3)
	cpusha	bc
	jsr	(a3)		; now in the I-cache
	cmp.l	#1,d0
	bne	fail
	move.l	#$70024e75,(a3)	; rewrite it: moveq #2,d0 ; rts (dirty in the D-cache)
	cpusha	bc
	jsr	(a3)
	cmp.l	#2,d0
	bne	fail
	moveq	#9,d7		; test 9: the same with CPUSHA DC + CINVA IC, and BlockMove-style copy
	lea	src9,a0
	lea	$6900,a1
	moveq	#3,d1
.m9	move.l	(a0)+,(a1)+
	dbf	d1,.m9
	cpusha	dc
	cinva	ic
	jsr	$6900
	cmp.l	#$12345678,d0
	bne	fail
	moveq	#6,d7		; test 6: FPU
	fmove.l	#7,fp0
	fmul.l	#6,fp0
	fmove.l	fp0,d0
	cmp.l	#42,d0
	bne	fail
	moveq	#10,d7		; test 10: a word load into An forwarded to the next instruction
	move.l	#$80008000,d0	; (the HFS node check: suba.l a0,a0 ; movea.w $2a(a4),a0 ; adda.l a1,a0)
	movec	d0,cacr
	lea	$6a00,a4
	move.w	#$200,$2a(a4)
	cpusha	dc		; the word is in memory, not the cache
	cinva	dc
	lea	$7000,a1
	suba.l	a0,a0
	movea.w	$2a(a4),a0	; D-cache miss
	adda.l	a1,a0
	cmpa.l	#$7200,a0
	bne	fail
	moveq	#12,d7		; test 12: no write of a0 just before the load
	nop
	nop
	movea.w	$2a(a4),a0
	adda.l	a1,a0
	cmpa.l	#$7200,a0
	bne	fail
	moveq	#13,d7		; test 13: the long form
	move.l	#$200,$2a(a4)
	suba.l	a0,a0
	movea.l	$2a(a4),a0
	adda.l	a1,a0
	cmpa.l	#$7200,a0
	bne	fail
	moveq	#14,d7		; test 14: word load into Dn, then add
	move.w	#$200,$2a(a4)
	moveq	#0,d0
	move.w	$2a(a4),d0
	add.l	a1,d0
	cmp.l	#$7200,d0
	bne	fail
	moveq	#11,d7		; test 11: the same, D-cache hit
	suba.l	a0,a0
	movea.w	$2a(a4),a0
	adda.l	a1,a0
	cmpa.l	#$7200,a0
	bne	fail
	moveq	#15,d7		; test 15: the same word load used as an index, D-cache hit
	suba.l	a0,a0
	movea.w	$2a(a4),a0
	lea	(a1,a0.l),a0
	cmpa.l	#$7200,a0
	bne	fail
	moveq	#16,d7		; test 16: ... and as a base
	suba.l	a0,a0
	movea.w	$2a(a4),a0
	lea	$10(a0),a0
	cmpa.l	#$210,a0
	bne	fail
	moveq	#17,d7		; uncached VRAM stores, then read-after-write
	lea	$F9009000,a0
	move.w	#31,d1
	move.l	#$10203040,d0
.vfill	move.l	d0,(a0)+
	addq.l	#1,d0
	dbf	d1,.vfill
	lea	$F9009000,a0
	move.w	#31,d1
	move.l	#$10203040,d0
.vcheck	cmp.l	(a0)+,d0
	bne	fail
	addq.l	#1,d0
	dbf	d1,.vcheck
	lea	$F9009100,a0
	move.l	#$11223344,(a0)
	move.b	#$AA,1(a0)
	move.w	#$BBCC,2(a0)
	move.l	#$11AABBCC,$5000000C ; bench checks device did not pass stores
	cmp.l	#$11AABBCC,(a0)
	bne	fail
	moveq	#18,d7		; locked RMW after an ordinary queued VRAM store
	move.l	#$12345678,(a0)
	move.l	#$12345678,d0
	move.l	#$89ABCDEF,d1
	cas.l	d0,d1,(a0)
	bne	fail
	cmp.l	#$89ABCDEF,(a0)
	bne	fail
	moveq	#19,d7		; crossing bus words keeps the precise slow path
	move.l	#$CAFEBABE,9(a0)
	cmp.l	#$CAFEBABE,9(a0)
	bne	fail
	move.w	#$4321,19(a0)
	cmp.w	#$4321,19(a0)
	bne	fail
	moveq	#20,d7		; retirement and device ordering under interrupts
	move.l	#1,$50000008
	lea	$F9009200,a0
	move.w	#31,d1
	move.l	#$50607080,d0
.v_irq	move.l	d0,(a0)+
	addq.l	#1,d0
	dbf	d1,.v_irq
	move.l	#0,$50000008
	lea	$F9009200,a0
	move.w	#31,d1
	move.l	#$50607080,d0
.v_verify cmp.l	(a0)+,d0
	bne	fail
	addq.l	#1,d0
	dbf	d1,.v_verify
	moveq	#21,d7		; maintenance waits for the earlier posted store
	move.l	#$55667788,$F9009100
	cpusha	dc
	move.l	#$55667788,$5000000C
	cpusha	dc
	move.l	#$A5A5A5A5,$50000000
	cpusha	dc
.h	bra	.h
irq1:	addq.l	#1,d6
	move.l	d0,-(a7)	; some RAM work, as the Mac's handlers do
	move.l	$7000,d0
	addq.l	#1,d0
	move.l	d0,$7000
	move.l	(a7)+,d0
	move.l	#1,$50000004	; the bench drops IPL on this write
	rte
fail:	move.l	d7,$50000000
	cpusha	dc
.h2	bra	.h2
src9:	move.l	#$12345678,d0
	rts
	nop
	nop
fault:	move.l	#$EE,d7
	bra	fail
