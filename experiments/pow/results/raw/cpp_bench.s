	.build_version macos, 27, 0	sdk_version 27, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	__Z12measured_powdd             ; -- Begin function _Z12measured_powdd
	.p2align	2
__Z12measured_powdd:                    ; @_Z12measured_powdd
	.cfi_startproc
; %bb.0:
	b	_pow
	.cfi_endproc
                                        ; -- End function
	.section	__TEXT,__literal16,16byte_literals
	.p2align	4, 0x0                          ; -- Begin function main
lCPI1_0:
	.quad	0x3fe0000000000000              ; double 0.5
	.quad	0xc020000000000000              ; double -8
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_main
	.p2align	2
_main:                                  ; @main
Lfunc_begin0:
	.cfi_startproc
	.cfi_personality 155, ___gxx_personality_v0
	.cfi_lsda 16, Lexception0
; %bb.0:
	sub	sp, sp, #240
	stp	d9, d8, [sp, #128]              ; 16-byte Folded Spill
	stp	x28, x27, [sp, #144]            ; 16-byte Folded Spill
	stp	x26, x25, [sp, #160]            ; 16-byte Folded Spill
	stp	x24, x23, [sp, #176]            ; 16-byte Folded Spill
	stp	x22, x21, [sp, #192]            ; 16-byte Folded Spill
	stp	x20, x19, [sp, #208]            ; 16-byte Folded Spill
	stp	x29, x30, [sp, #224]            ; 16-byte Folded Spill
	add	x29, sp, #224
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	.cfi_offset w21, -40
	.cfi_offset w22, -48
	.cfi_offset w23, -56
	.cfi_offset w24, -64
	.cfi_offset w25, -72
	.cfi_offset w26, -80
	.cfi_offset w27, -88
	.cfi_offset w28, -96
	.cfi_offset b8, -104
	.cfi_offset b9, -112
	mov	x8, #0                          ; =0x0
Lloh0:
	adrp	x9, ___stack_chk_guard@GOTPAGE
Lloh1:
	ldr	x9, [x9, ___stack_chk_guard@GOTPAGEOFF]
Lloh2:
	ldr	x9, [x9]
	stur	x9, [x29, #-104]
	stp	xzr, xzr, [sp, #48]
	str	xzr, [sp, #64]
	mov	w19, #2026                      ; =0x7ea
	mov	w20, #16384                     ; =0x4000
	mov	x21, #32557                     ; =0x7f2d
	movk	x21, #19605, lsl #16
	movk	x21, #62509, lsl #32
	movk	x21, #22609, lsl #48
	mov	x22, #33103                     ; =0x814f
	movk	x22, #63335, lsl #16
	movk	x22, #31614, lsl #32
	movk	x22, #5125, lsl #48
	mov	x9, #4368491638549381120        ; =0x3ca0000000000000
	dup.2d	v0, x9
	str	q0, [sp, #16]                   ; 16-byte Folded Spill
	fmov	d8, #1.50000000
Lloh3:
	adrp	x9, lCPI1_0@PAGE
Lloh4:
	ldr	q0, [x9, lCPI1_0@PAGEOFF]
	str	q0, [sp]                        ; 16-byte Folded Spill
	add	x23, sp, #72
	add	x24, sp, #32
	add	x25, sp, #48
LBB1_1:                                 ; =>This Inner Loop Header: Depth=1
	madd	x19, x19, x21, x22
	ror	x9, x19, #35
	lsr	x10, x19, #11
	ucvtf	d0, x10
	lsr	x9, x9, #7
	and	x9, x9, #0x1fffffffffffff0
	ucvtf	d1, x9
	fmul	d0, d0, d8
	mov.d	v0[1], v1[0]
	ldp	q1, q2, [sp]                    ; 32-byte Folded Reload
	fmul.2d	v0, v0, v2
	fadd.2d	v0, v0, v1
	str	q0, [sp, #32]
	stp	x8, x23, [sp, #72]
	ldr	x9, [sp, #64]
	stp	x24, x25, [sp, #88]
	cmp	x8, x9
	b.hs	LBB1_3
; %bb.2:                                ;   in Loop: Header=BB1_1 Depth=1
	ldr	q0, [sp, #32]
	str	q0, [x8], #16
	str	x8, [sp, #56]
	subs	x20, x20, #1
	b.ne	LBB1_1
	b	LBB1_5
LBB1_3:                                 ;   in Loop: Header=BB1_1 Depth=1
Ltmp0:
	add	x0, sp, #80
	bl	__ZZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE12emplace_backIJS2_EEERS2_DpOT_ENKUlvE0_clEv
Ltmp1:
; %bb.4:                                ;   in Loop: Header=BB1_1 Depth=1
	ldr	x8, [sp, #72]
	str	x8, [sp, #56]
	subs	x20, x20, #1
	b.ne	LBB1_1
LBB1_5:
Ltmp3:
Lloh5:
	adrp	x0, __ZNSt3__14coutE@GOTPAGE
Lloh6:
	ldr	x0, [x0, __ZNSt3__14coutE@GOTPAGEOFF]
Lloh7:
	adrp	x1, l_.str@PAGE
Lloh8:
	add	x1, x1, l_.str@PAGEOFF
	mov	w2, #25                         ; =0x19
	bl	__ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m
Ltmp4:
; %bb.6:
	mov	w22, #0                         ; =0x0
	mov	w23, #44                        ; =0x2c
	mov	w24, #-75                       ; =0xffffffb5
	add	x26, sp, #80
	b	LBB1_8
LBB1_7:                                 ;   in Loop: Header=BB1_8 Depth=1
	add	w22, w22, #1
	cmp	w22, #20
	b.eq	LBB1_22
LBB1_8:                                 ; =>This Loop Header: Depth=1
                                        ;     Child Loop BB1_11 Depth 2
                                        ;       Child Loop BB1_13 Depth 3
	movi.2d	v0, #0000000000000000
	stp	q0, q0, [sp, #80]
	bl	__ZNSt3__16chrono12steady_clock3nowEv
	mov	x20, x0
	mov	w21, #0                         ; =0x0
	ldp	x8, x9, [sp, #48]
	b	LBB1_11
LBB1_9:                                 ;   in Loop: Header=BB1_11 Depth=2
	mov	x9, x8
LBB1_10:                                ;   in Loop: Header=BB1_11 Depth=2
	add	w21, w21, #1
	cmp	w21, #32
	b.eq	LBB1_15
LBB1_11:                                ;   Parent Loop BB1_8 Depth=1
                                        ; =>  This Loop Header: Depth=2
                                        ;       Child Loop BB1_13 Depth 3
	cmp	x9, x8
	b.eq	LBB1_9
; %bb.12:                               ;   in Loop: Header=BB1_11 Depth=2
	mov	x19, #0                         ; =0x0
	mov	x25, #0                         ; =0x0
LBB1_13:                                ;   Parent Loop BB1_8 Depth=1
                                        ;     Parent Loop BB1_11 Depth=2
                                        ; =>    This Inner Loop Header: Depth=3
	add	x8, x8, x19
	ldp	d0, d1, [x8]
	; InlineAsm Start
	; InlineAsm End
Ltmp6:
	bl	__Z12measured_powdd
Ltmp7:
; %bb.14:                               ;   in Loop: Header=BB1_13 Depth=3
	fmov	x8, d0
	and	x9, x25, #0x3
	ldr	x10, [x26, x9, lsl #3]
	add	x8, x10, x8
	str	x8, [x26, x9, lsl #3]
	add	x25, x25, #1
	ldp	x8, x9, [sp, #48]
	sub	x10, x9, x8
	add	x19, x19, #16
	cmp	x25, x10, asr #4
	b.lo	LBB1_13
	b	LBB1_10
LBB1_15:                                ;   in Loop: Header=BB1_8 Depth=1
	bl	__ZNSt3__16chrono12steady_clock3nowEv
	subs	w1, w22, #5
	b.lo	LBB1_7
; %bb.16:                               ;   in Loop: Header=BB1_8 Depth=1
Ltmp9:
	mov	x21, x0
	ldp	x27, x28, [sp, #80]
	ldp	x19, x25, [sp, #96]
Lloh9:
	adrp	x0, __ZNSt3__14coutE@GOTPAGE
Lloh10:
	ldr	x0, [x0, __ZNSt3__14coutE@GOTPAGEOFF]
	bl	__ZNSt3__113basic_ostreamIcNS_11char_traitsIcEEElsEi
Ltmp10:
; %bb.17:                               ;   in Loop: Header=BB1_8 Depth=1
	strb	w23, [sp, #32]
Ltmp11:
	add	x1, sp, #32
	mov	w2, #1                          ; =0x1
	bl	__ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m
Ltmp12:
; %bb.18:                               ;   in Loop: Header=BB1_8 Depth=1
	sub	x8, x21, x20
	scvtf	d0, x8
	ldp	x9, x8, [sp, #48]
	sub	x8, x8, x9
	lsl	x8, x8, #1
	ucvtf	d1, x8
	fdiv	d0, d0, d1
Ltmp13:
	bl	__ZNSt3__113basic_ostreamIcNS_11char_traitsIcEEElsEd
Ltmp14:
; %bb.19:                               ;   in Loop: Header=BB1_8 Depth=1
	strb	w23, [sp, #32]
Ltmp15:
	add	x1, sp, #32
	mov	w2, #1                          ; =0x1
	bl	__ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m
Ltmp16:
; %bb.20:                               ;   in Loop: Header=BB1_8 Depth=1
	add	x8, x28, x27
	add	x9, x19, x25
	ldr	x10, [x0]
	ldur	x10, [x10, #-24]
	add	x10, x0, x10
	ldr	w11, [x10, #8]
	and	w11, w11, w24
	orr	w11, w11, #0x8
	str	w11, [x10, #8]
Ltmp17:
	add	x1, x8, x9
	bl	__ZNSt3__113basic_ostreamIcNS_11char_traitsIcEEElsEy
Ltmp18:
; %bb.21:                               ;   in Loop: Header=BB1_8 Depth=1
	ldr	x8, [x0]
	ldur	x8, [x8, #-24]
	add	x8, x0, x8
	ldr	w9, [x8, #8]
	and	w9, w9, w24
	orr	w9, w9, #0x2
	str	w9, [x8, #8]
	mov	w8, #10                         ; =0xa
	strb	w8, [sp, #32]
Ltmp19:
	add	x1, sp, #32
	mov	w2, #1                          ; =0x1
	bl	__ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m
Ltmp20:
	b	LBB1_7
LBB1_22:
	ldr	x0, [sp, #48]
	cbz	x0, LBB1_24
; %bb.23:
	str	x0, [sp, #56]
	bl	__ZdlPv
LBB1_24:
	ldur	x8, [x29, #-104]
Lloh11:
	adrp	x9, ___stack_chk_guard@GOTPAGE
Lloh12:
	ldr	x9, [x9, ___stack_chk_guard@GOTPAGEOFF]
Lloh13:
	ldr	x9, [x9]
	cmp	x9, x8
	b.ne	LBB1_26
; %bb.25:
	mov	w0, #0                          ; =0x0
	ldp	x29, x30, [sp, #224]            ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #208]            ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #192]            ; 16-byte Folded Reload
	ldp	x24, x23, [sp, #176]            ; 16-byte Folded Reload
	ldp	x26, x25, [sp, #160]            ; 16-byte Folded Reload
	ldp	x28, x27, [sp, #144]            ; 16-byte Folded Reload
	ldp	d9, d8, [sp, #128]              ; 16-byte Folded Reload
	add	sp, sp, #240
	ret
LBB1_26:
	bl	___stack_chk_fail
LBB1_27:
Ltmp2:
	b	LBB1_31
LBB1_28:
Ltmp5:
	b	LBB1_31
LBB1_29:
Ltmp21:
	b	LBB1_31
LBB1_30:
Ltmp8:
LBB1_31:
	ldr	x8, [sp, #48]
	cbz	x8, LBB1_33
; %bb.32:
	str	x8, [sp, #56]
	mov	x19, x0
	mov	x0, x8
	bl	__ZdlPv
	mov	x0, x19
LBB1_33:
	bl	__Unwind_Resume
	.loh AdrpLdr	Lloh3, Lloh4
	.loh AdrpLdrGotLdr	Lloh0, Lloh1, Lloh2
	.loh AdrpAdd	Lloh7, Lloh8
	.loh AdrpLdrGot	Lloh5, Lloh6
	.loh AdrpLdrGot	Lloh9, Lloh10
	.loh AdrpLdrGotLdr	Lloh11, Lloh12, Lloh13
Lfunc_end0:
	.cfi_endproc
	.section	__TEXT,__gcc_except_tab
	.p2align	2, 0x0
GCC_except_table1:
Lexception0:
	.byte	255                             ; @LPStart Encoding = omit
	.byte	255                             ; @TType Encoding = omit
	.byte	1                               ; Call site Encoding = uleb128
	.uleb128 Lcst_end0-Lcst_begin0
Lcst_begin0:
	.uleb128 Ltmp0-Lfunc_begin0             ; >> Call Site 1 <<
	.uleb128 Ltmp1-Ltmp0                    ;   Call between Ltmp0 and Ltmp1
	.uleb128 Ltmp2-Lfunc_begin0             ;     jumps to Ltmp2
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp3-Lfunc_begin0             ; >> Call Site 2 <<
	.uleb128 Ltmp4-Ltmp3                    ;   Call between Ltmp3 and Ltmp4
	.uleb128 Ltmp5-Lfunc_begin0             ;     jumps to Ltmp5
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp6-Lfunc_begin0             ; >> Call Site 3 <<
	.uleb128 Ltmp7-Ltmp6                    ;   Call between Ltmp6 and Ltmp7
	.uleb128 Ltmp8-Lfunc_begin0             ;     jumps to Ltmp8
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp9-Lfunc_begin0             ; >> Call Site 4 <<
	.uleb128 Ltmp20-Ltmp9                   ;   Call between Ltmp9 and Ltmp20
	.uleb128 Ltmp21-Lfunc_begin0            ;     jumps to Ltmp21
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp20-Lfunc_begin0            ; >> Call Site 5 <<
	.uleb128 Lfunc_end0-Ltmp20              ;   Call between Ltmp20 and Lfunc_end0
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
Lcst_end0:
	.p2align	2, 0x0
                                        ; -- End function
	.section	__TEXT,__text,regular,pure_instructions
	.private_extern	___clang_call_terminate ; -- Begin function __clang_call_terminate
	.globl	___clang_call_terminate
	.weak_def_can_be_hidden	___clang_call_terminate
	.p2align	2
___clang_call_terminate:                ; @__clang_call_terminate
	.cfi_startproc
; %bb.0:
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	mov	x29, sp
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	bl	___cxa_begin_catch
	bl	__ZSt9terminatev
	.cfi_endproc
                                        ; -- End function
	.globl	__ZZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE12emplace_backIJS2_EEERS2_DpOT_ENKUlvE0_clEv ; -- Begin function _ZZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE12emplace_backIJS2_EEERS2_DpOT_ENKUlvE0_clEv
	.weak_def_can_be_hidden	__ZZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE12emplace_backIJS2_EEERS2_DpOT_ENKUlvE0_clEv
	.p2align	2
__ZZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE12emplace_backIJS2_EEERS2_DpOT_ENKUlvE0_clEv: ; @_ZZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE12emplace_backIJS2_EEERS2_DpOT_ENKUlvE0_clEv
	.cfi_startproc
; %bb.0:
	stp	x26, x25, [sp, #-80]!           ; 16-byte Folded Spill
	stp	x24, x23, [sp, #16]             ; 16-byte Folded Spill
	stp	x22, x21, [sp, #32]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #48]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #64]             ; 16-byte Folded Spill
	add	x29, sp, #64
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	.cfi_offset w21, -40
	.cfi_offset w22, -48
	.cfi_offset w23, -56
	.cfi_offset w24, -64
	.cfi_offset w25, -72
	.cfi_offset w26, -80
	ldr	x23, [x0, #16]
	ldp	x20, x8, [x23]
	sub	x21, x8, x20
	asr	x24, x21, #4
	add	x8, x24, #1
	lsr	x9, x8, #60
	cbnz	x9, LBB3_5
; %bb.1:
	ldr	x9, [x23, #16]
	mov	x10, #9223372036854775792       ; =0x7ffffffffffffff0
	sub	x9, x9, x20
	asr	x11, x9, #3
	cmp	x11, x8
	csel	x8, x11, x8, hi
	cmp	x9, x10
	mov	x9, #1152921504606846975        ; =0xfffffffffffffff
	csel	x8, x8, x9, lo
	lsr	x9, x8, #60
	cbnz	x9, LBB3_6
; %bb.2:
	mov	x19, x0
	ldr	x25, [x0, #8]
	lsl	x22, x8, #4
	mov	x0, x22
	bl	__Znwm
	add	x8, x0, x21
	add	x26, x0, x22
	ldr	q0, [x25]
	str	q0, [x8]
	add	x25, x8, #16
	sub	x22, x8, x24, lsl #4
	mov	x0, x22
	mov	x1, x20
	mov	x2, x21
	bl	_memcpy
	stp	x22, x25, [x23]
	str	x26, [x23, #16]
	cbz	x20, LBB3_4
; %bb.3:
	mov	x0, x20
	bl	__ZdlPv
LBB3_4:
	ldr	x8, [x19]
	str	x25, [x8]
	ldp	x29, x30, [sp, #64]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #48]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #32]             ; 16-byte Folded Reload
	ldp	x24, x23, [sp, #16]             ; 16-byte Folded Reload
	ldp	x26, x25, [sp], #80             ; 16-byte Folded Reload
	ret
LBB3_5:
	bl	__ZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE20__throw_length_errorB9nqe220106Ev
LBB3_6:
	bl	__ZSt28__throw_bad_array_new_lengthB9nqe220106v
	.cfi_endproc
                                        ; -- End function
	.private_extern	__ZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE20__throw_length_errorB9nqe220106Ev ; -- Begin function _ZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE20__throw_length_errorB9nqe220106Ev
	.globl	__ZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE20__throw_length_errorB9nqe220106Ev
	.weak_def_can_be_hidden	__ZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE20__throw_length_errorB9nqe220106Ev
	.p2align	2
__ZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE20__throw_length_errorB9nqe220106Ev: ; @_ZNSt3__16vectorINS_5arrayIdLm2EEENS_9allocatorIS2_EEE20__throw_length_errorB9nqe220106Ev
	.cfi_startproc
; %bb.0:
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	mov	x29, sp
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
Lloh14:
	adrp	x0, l_.str.1@PAGE
Lloh15:
	add	x0, x0, l_.str.1@PAGEOFF
	bl	__ZNSt3__120__throw_length_errorB9nqe220106EPKc
	.loh AdrpAdd	Lloh14, Lloh15
	.cfi_endproc
                                        ; -- End function
	.private_extern	__ZNSt3__120__throw_length_errorB9nqe220106EPKc ; -- Begin function _ZNSt3__120__throw_length_errorB9nqe220106EPKc
	.globl	__ZNSt3__120__throw_length_errorB9nqe220106EPKc
	.weak_def_can_be_hidden	__ZNSt3__120__throw_length_errorB9nqe220106EPKc
	.p2align	2
__ZNSt3__120__throw_length_errorB9nqe220106EPKc: ; @_ZNSt3__120__throw_length_errorB9nqe220106EPKc
Lfunc_begin1:
	.cfi_startproc
	.cfi_personality 155, ___gxx_personality_v0
	.cfi_lsda 16, Lexception1
; %bb.0:
	stp	x20, x19, [sp, #-32]!           ; 16-byte Folded Spill
	stp	x29, x30, [sp, #16]             ; 16-byte Folded Spill
	add	x29, sp, #16
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	mov	x20, x0
	mov	w0, #16                         ; =0x10
	bl	___cxa_allocate_exception
	mov	x19, x0
Ltmp22:
	mov	x1, x20
	bl	__ZNSt12length_errorC1B9nqe220106EPKc
Ltmp23:
; %bb.1:
Lloh16:
	adrp	x1, __ZTISt12length_error@GOTPAGE
Lloh17:
	ldr	x1, [x1, __ZTISt12length_error@GOTPAGEOFF]
Lloh18:
	adrp	x2, __ZNSt12length_errorD1Ev@GOTPAGE
Lloh19:
	ldr	x2, [x2, __ZNSt12length_errorD1Ev@GOTPAGEOFF]
	mov	x0, x19
	bl	___cxa_throw
LBB5_2:
Ltmp24:
	mov	x20, x0
	mov	x0, x19
	bl	___cxa_free_exception
	mov	x0, x20
	bl	__Unwind_Resume
	.loh AdrpLdrGot	Lloh18, Lloh19
	.loh AdrpLdrGot	Lloh16, Lloh17
Lfunc_end1:
	.cfi_endproc
	.section	__TEXT,__gcc_except_tab
	.p2align	2, 0x0
GCC_except_table5:
Lexception1:
	.byte	255                             ; @LPStart Encoding = omit
	.byte	255                             ; @TType Encoding = omit
	.byte	1                               ; Call site Encoding = uleb128
	.uleb128 Lcst_end1-Lcst_begin1
Lcst_begin1:
	.uleb128 Lfunc_begin1-Lfunc_begin1      ; >> Call Site 1 <<
	.uleb128 Ltmp22-Lfunc_begin1            ;   Call between Lfunc_begin1 and Ltmp22
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp22-Lfunc_begin1            ; >> Call Site 2 <<
	.uleb128 Ltmp23-Ltmp22                  ;   Call between Ltmp22 and Ltmp23
	.uleb128 Ltmp24-Lfunc_begin1            ;     jumps to Ltmp24
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp23-Lfunc_begin1            ; >> Call Site 3 <<
	.uleb128 Lfunc_end1-Ltmp23              ;   Call between Ltmp23 and Lfunc_end1
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
Lcst_end1:
	.p2align	2, 0x0
                                        ; -- End function
	.section	__TEXT,__text,regular,pure_instructions
	.private_extern	__ZNSt12length_errorC1B9nqe220106EPKc ; -- Begin function _ZNSt12length_errorC1B9nqe220106EPKc
	.globl	__ZNSt12length_errorC1B9nqe220106EPKc
	.weak_def_can_be_hidden	__ZNSt12length_errorC1B9nqe220106EPKc
	.p2align	2
__ZNSt12length_errorC1B9nqe220106EPKc:  ; @_ZNSt12length_errorC1B9nqe220106EPKc
	.cfi_startproc
; %bb.0:
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	mov	x29, sp
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	bl	__ZNSt11logic_errorC2EPKc
Lloh20:
	adrp	x8, __ZTVSt12length_error@GOTPAGE
Lloh21:
	ldr	x8, [x8, __ZTVSt12length_error@GOTPAGEOFF]
	add	x8, x8, #16
	str	x8, [x0]
	ldp	x29, x30, [sp], #16             ; 16-byte Folded Reload
	ret
	.loh AdrpLdrGot	Lloh20, Lloh21
	.cfi_endproc
                                        ; -- End function
	.private_extern	__ZSt28__throw_bad_array_new_lengthB9nqe220106v ; -- Begin function _ZSt28__throw_bad_array_new_lengthB9nqe220106v
	.globl	__ZSt28__throw_bad_array_new_lengthB9nqe220106v
	.weak_def_can_be_hidden	__ZSt28__throw_bad_array_new_lengthB9nqe220106v
	.p2align	2
__ZSt28__throw_bad_array_new_lengthB9nqe220106v: ; @_ZSt28__throw_bad_array_new_lengthB9nqe220106v
	.cfi_startproc
; %bb.0:
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	mov	x29, sp
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	mov	w0, #8                          ; =0x8
	bl	___cxa_allocate_exception
	bl	__ZNSt20bad_array_new_lengthC1Ev
Lloh22:
	adrp	x1, __ZTISt20bad_array_new_length@GOTPAGE
Lloh23:
	ldr	x1, [x1, __ZTISt20bad_array_new_length@GOTPAGEOFF]
Lloh24:
	adrp	x2, __ZNSt20bad_array_new_lengthD1Ev@GOTPAGE
Lloh25:
	ldr	x2, [x2, __ZNSt20bad_array_new_lengthD1Ev@GOTPAGEOFF]
	bl	___cxa_throw
	.loh AdrpLdrGot	Lloh24, Lloh25
	.loh AdrpLdrGot	Lloh22, Lloh23
	.cfi_endproc
                                        ; -- End function
	.private_extern	__ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m ; -- Begin function _ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m
	.globl	__ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m
	.weak_def_can_be_hidden	__ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m
	.p2align	2
__ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m: ; @_ZNSt3__124__put_character_sequenceB9nqe220106IcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m
Lfunc_begin2:
	.cfi_startproc
	.cfi_personality 155, ___gxx_personality_v0
	.cfi_lsda 16, Lexception2
; %bb.0:
	sub	sp, sp, #112
	stp	x26, x25, [sp, #32]             ; 16-byte Folded Spill
	stp	x24, x23, [sp, #48]             ; 16-byte Folded Spill
	stp	x22, x21, [sp, #64]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #80]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #96]             ; 16-byte Folded Spill
	add	x29, sp, #96
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	.cfi_offset w21, -40
	.cfi_offset w22, -48
	.cfi_offset w23, -56
	.cfi_offset w24, -64
	.cfi_offset w25, -72
	.cfi_offset w26, -80
	mov	x21, x2
	mov	x20, x1
	mov	x19, x0
Ltmp25:
	add	x0, sp, #8
	mov	x1, x19
	bl	__ZNSt3__113basic_ostreamIcNS_11char_traitsIcEEE6sentryC1ERS3_
Ltmp26:
; %bb.1:
	ldrb	w8, [sp, #8]
	cmp	w8, #1
	b.ne	LBB8_10
; %bb.2:
	ldr	x8, [x19]
	ldur	x8, [x8, #-24]
	add	x4, x19, x8
	ldr	x22, [x4, #40]
	ldr	w24, [x4, #8]
	ldr	w23, [x4, #144]
	cmn	w23, #1
	b.ne	LBB8_7
; %bb.3:
Ltmp28:
	add	x8, sp, #24
	mov	x25, x4
	mov	x0, x4
	bl	__ZNKSt3__18ios_base6getlocEv
Ltmp29:
; %bb.4:
Ltmp30:
Lloh26:
	adrp	x1, __ZNSt3__15ctypeIcE2idE@GOTPAGE
Lloh27:
	ldr	x1, [x1, __ZNSt3__15ctypeIcE2idE@GOTPAGEOFF]
	add	x0, sp, #24
	bl	__ZNKSt3__16locale9use_facetERNS0_2idE
Ltmp31:
; %bb.5:
	ldr	x8, [x0]
	ldr	x8, [x8, #56]
Ltmp32:
	mov	w1, #32                         ; =0x20
	blr	x8
Ltmp33:
; %bb.6:
	mov	x23, x0
	add	x0, sp, #24
	bl	__ZNSt3__16localeD1Ev
	mov	x4, x25
	str	w23, [x25, #144]
LBB8_7:
	mov	w8, #176                        ; =0xb0
	and	w8, w24, w8
	add	x3, x20, x21
	cmp	w8, #32
	csel	x2, x3, x20, eq
Ltmp35:
	sxtb	w5, w23
	mov	x0, x22
	mov	x1, x20
	bl	__ZNSt3__116__pad_and_outputB9nqe220106IcNS_11char_traitsIcEEEENS_19ostreambuf_iteratorIT_T0_EES6_PKS4_S8_S8_RNS_8ios_baseES4_
Ltmp36:
; %bb.8:
	cbnz	x0, LBB8_10
; %bb.9:
	ldr	x8, [x19]
	ldur	x8, [x8, #-24]
	add	x0, x19, x8
	ldr	w8, [x0, #32]
	mov	w9, #5                          ; =0x5
Ltmp38:
	orr	w1, w8, w9
	bl	__ZNSt3__18ios_base5clearEj
Ltmp39:
LBB8_10:
	add	x0, sp, #8
	bl	__ZNSt3__113basic_ostreamIcNS_11char_traitsIcEEE6sentryD1Ev
LBB8_11:
	mov	x0, x19
	ldp	x29, x30, [sp, #96]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #80]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #64]             ; 16-byte Folded Reload
	ldp	x24, x23, [sp, #48]             ; 16-byte Folded Reload
	ldp	x26, x25, [sp, #32]             ; 16-byte Folded Reload
	add	sp, sp, #112
	ret
LBB8_12:
Ltmp40:
	b	LBB8_15
LBB8_13:
Ltmp34:
	mov	x20, x0
	add	x0, sp, #24
	bl	__ZNSt3__16localeD1Ev
	b	LBB8_16
LBB8_14:
Ltmp37:
LBB8_15:
	mov	x20, x0
LBB8_16:
	add	x0, sp, #8
	bl	__ZNSt3__113basic_ostreamIcNS_11char_traitsIcEEE6sentryD1Ev
	b	LBB8_18
LBB8_17:
Ltmp27:
	mov	x20, x0
LBB8_18:
	mov	x0, x20
	bl	___cxa_begin_catch
	ldr	x8, [x19]
	ldur	x8, [x8, #-24]
Ltmp41:
	add	x0, x19, x8
	bl	__ZNSt3__18ios_base33__set_badbit_and_consider_rethrowEv
Ltmp42:
; %bb.19:
	bl	___cxa_end_catch
	b	LBB8_11
LBB8_20:
Ltmp43:
	mov	x19, x0
Ltmp44:
	bl	___cxa_end_catch
Ltmp45:
; %bb.21:
	mov	x0, x19
	bl	__Unwind_Resume
LBB8_22:
Ltmp46:
	bl	___clang_call_terminate
	.loh AdrpLdrGot	Lloh26, Lloh27
Lfunc_end2:
	.cfi_endproc
	.section	__TEXT,__gcc_except_tab
	.p2align	2, 0x0
GCC_except_table8:
Lexception2:
	.byte	255                             ; @LPStart Encoding = omit
	.byte	155                             ; @TType Encoding = indirect pcrel sdata4
	.uleb128 Lttbase0-Lttbaseref0
Lttbaseref0:
	.byte	1                               ; Call site Encoding = uleb128
	.uleb128 Lcst_end2-Lcst_begin2
Lcst_begin2:
	.uleb128 Ltmp25-Lfunc_begin2            ; >> Call Site 1 <<
	.uleb128 Ltmp26-Ltmp25                  ;   Call between Ltmp25 and Ltmp26
	.uleb128 Ltmp27-Lfunc_begin2            ;     jumps to Ltmp27
	.byte	1                               ;   On action: 1
	.uleb128 Ltmp28-Lfunc_begin2            ; >> Call Site 2 <<
	.uleb128 Ltmp29-Ltmp28                  ;   Call between Ltmp28 and Ltmp29
	.uleb128 Ltmp37-Lfunc_begin2            ;     jumps to Ltmp37
	.byte	1                               ;   On action: 1
	.uleb128 Ltmp30-Lfunc_begin2            ; >> Call Site 3 <<
	.uleb128 Ltmp33-Ltmp30                  ;   Call between Ltmp30 and Ltmp33
	.uleb128 Ltmp34-Lfunc_begin2            ;     jumps to Ltmp34
	.byte	1                               ;   On action: 1
	.uleb128 Ltmp35-Lfunc_begin2            ; >> Call Site 4 <<
	.uleb128 Ltmp36-Ltmp35                  ;   Call between Ltmp35 and Ltmp36
	.uleb128 Ltmp37-Lfunc_begin2            ;     jumps to Ltmp37
	.byte	1                               ;   On action: 1
	.uleb128 Ltmp38-Lfunc_begin2            ; >> Call Site 5 <<
	.uleb128 Ltmp39-Ltmp38                  ;   Call between Ltmp38 and Ltmp39
	.uleb128 Ltmp40-Lfunc_begin2            ;     jumps to Ltmp40
	.byte	1                               ;   On action: 1
	.uleb128 Ltmp39-Lfunc_begin2            ; >> Call Site 6 <<
	.uleb128 Ltmp41-Ltmp39                  ;   Call between Ltmp39 and Ltmp41
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp41-Lfunc_begin2            ; >> Call Site 7 <<
	.uleb128 Ltmp42-Ltmp41                  ;   Call between Ltmp41 and Ltmp42
	.uleb128 Ltmp43-Lfunc_begin2            ;     jumps to Ltmp43
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp42-Lfunc_begin2            ; >> Call Site 8 <<
	.uleb128 Ltmp44-Ltmp42                  ;   Call between Ltmp42 and Ltmp44
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp44-Lfunc_begin2            ; >> Call Site 9 <<
	.uleb128 Ltmp45-Ltmp44                  ;   Call between Ltmp44 and Ltmp45
	.uleb128 Ltmp46-Lfunc_begin2            ;     jumps to Ltmp46
	.byte	1                               ;   On action: 1
	.uleb128 Ltmp45-Lfunc_begin2            ; >> Call Site 10 <<
	.uleb128 Lfunc_end2-Ltmp45              ;   Call between Ltmp45 and Lfunc_end2
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
Lcst_end2:
	.byte	1                               ; >> Action Record 1 <<
                                        ;   Catch TypeInfo 1
	.byte	0                               ;   No further actions
	.p2align	2, 0x0
                                        ; >> Catch TypeInfos <<
	.long	0                               ; TypeInfo 1
Lttbase0:
	.p2align	2, 0x0
                                        ; -- End function
	.section	__TEXT,__text,regular,pure_instructions
	.private_extern	__ZNSt3__116__pad_and_outputB9nqe220106IcNS_11char_traitsIcEEEENS_19ostreambuf_iteratorIT_T0_EES6_PKS4_S8_S8_RNS_8ios_baseES4_ ; -- Begin function _ZNSt3__116__pad_and_outputB9nqe220106IcNS_11char_traitsIcEEEENS_19ostreambuf_iteratorIT_T0_EES6_PKS4_S8_S8_RNS_8ios_baseES4_
	.globl	__ZNSt3__116__pad_and_outputB9nqe220106IcNS_11char_traitsIcEEEENS_19ostreambuf_iteratorIT_T0_EES6_PKS4_S8_S8_RNS_8ios_baseES4_
	.weak_def_can_be_hidden	__ZNSt3__116__pad_and_outputB9nqe220106IcNS_11char_traitsIcEEEENS_19ostreambuf_iteratorIT_T0_EES6_PKS4_S8_S8_RNS_8ios_baseES4_
	.p2align	2
__ZNSt3__116__pad_and_outputB9nqe220106IcNS_11char_traitsIcEEEENS_19ostreambuf_iteratorIT_T0_EES6_PKS4_S8_S8_RNS_8ios_baseES4_: ; @_ZNSt3__116__pad_and_outputB9nqe220106IcNS_11char_traitsIcEEEENS_19ostreambuf_iteratorIT_T0_EES6_PKS4_S8_S8_RNS_8ios_baseES4_
Lfunc_begin3:
	.cfi_startproc
	.cfi_personality 155, ___gxx_personality_v0
	.cfi_lsda 16, Lexception3
; %bb.0:
	sub	sp, sp, #112
	stp	x26, x25, [sp, #32]             ; 16-byte Folded Spill
	stp	x24, x23, [sp, #48]             ; 16-byte Folded Spill
	stp	x22, x21, [sp, #64]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #80]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #96]             ; 16-byte Folded Spill
	add	x29, sp, #96
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	.cfi_offset w21, -40
	.cfi_offset w22, -48
	.cfi_offset w23, -56
	.cfi_offset w24, -64
	.cfi_offset w25, -72
	.cfi_offset w26, -80
	mov	x19, x0
	cbz	x0, LBB9_16
; %bb.1:
	mov	x23, x5
	mov	x20, x4
	mov	x22, x3
	mov	x21, x2
	mov	x24, x1
	ldr	x26, [x4, #24]
	sub	x25, x2, x1
	cmp	x25, #1
	b.lt	LBB9_3
; %bb.2:
	ldr	x8, [x19]
	ldr	x8, [x8, #96]
	mov	x0, x19
	mov	x1, x24
	mov	x2, x25
	blr	x8
	cmp	x0, x25
	b.ne	LBB9_15
LBB9_3:
	sub	x8, x22, x24
	cmp	x26, x8
	b.le	LBB9_12
; %bb.4:
	mov	x9, #-9                         ; =0xfffffffffffffff7
	movk	x9, #32767, lsl #48
	sub	x24, x26, x8
	cmp	x24, x9
	b.hs	LBB9_17
; %bb.5:
	cmp	x24, #23
	b.hs	LBB9_7
; %bb.6:
	strb	w24, [sp, #31]
	add	x25, sp, #8
	b	LBB9_8
LBB9_7:
	and	x8, x24, #0x7ffffffffffffff8
	add	x8, x8, #8
	mov	w9, #25                         ; =0x19
	cmp	x8, #24
	csel	x26, x9, x8, eq
	mov	x0, x26
	bl	__Znwm
	mov	x25, x0
	orr	x8, x26, #0x8000000000000000
	stp	x0, x24, [sp, #8]
	str	x8, [sp, #24]
LBB9_8:
	mov	x0, x25
	mov	x1, x23
	mov	x2, x24
	bl	_memset
	strb	wzr, [x25, x24]
	ldrsb	w8, [sp, #31]
	ldr	x9, [sp, #8]
	cmp	w8, #0
	add	x8, sp, #8
	csel	x1, x9, x8, lt
	ldr	x8, [x19]
	ldr	x8, [x8, #96]
Ltmp47:
	mov	x0, x19
	mov	x2, x24
	blr	x8
Ltmp48:
; %bb.9:
	ldrsb	w8, [sp, #31]
	tbnz	w8, #31, LBB9_11
; %bb.10:
	cmp	x0, x24
	b.ne	LBB9_15
	b	LBB9_12
LBB9_11:
	ldr	x8, [sp, #8]
	mov	x23, x0
	mov	x0, x8
	bl	__ZdlPv
	cmp	x23, x24
	b.ne	LBB9_15
LBB9_12:
	sub	x22, x22, x21
	cmp	x22, #1
	b.lt	LBB9_14
; %bb.13:
	ldr	x8, [x19]
	ldr	x8, [x8, #96]
	mov	x0, x19
	mov	x1, x21
	mov	x2, x22
	blr	x8
	cmp	x0, x22
	b.ne	LBB9_15
LBB9_14:
	str	xzr, [x20, #24]
	b	LBB9_16
LBB9_15:
	mov	x19, #0                         ; =0x0
LBB9_16:
	mov	x0, x19
	ldp	x29, x30, [sp, #96]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #80]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #64]             ; 16-byte Folded Reload
	ldp	x24, x23, [sp, #48]             ; 16-byte Folded Reload
	ldp	x26, x25, [sp, #32]             ; 16-byte Folded Reload
	add	sp, sp, #112
	ret
LBB9_17:
	bl	__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE20__throw_length_errorB9nqe220106Ev
LBB9_18:
Ltmp49:
	mov	x19, x0
	ldrsb	w8, [sp, #31]
	tbz	w8, #31, LBB9_20
; %bb.19:
	ldr	x0, [sp, #8]
	bl	__ZdlPv
LBB9_20:
	mov	x0, x19
	bl	__Unwind_Resume
Lfunc_end3:
	.cfi_endproc
	.section	__TEXT,__gcc_except_tab
	.p2align	2, 0x0
GCC_except_table9:
Lexception3:
	.byte	255                             ; @LPStart Encoding = omit
	.byte	255                             ; @TType Encoding = omit
	.byte	1                               ; Call site Encoding = uleb128
	.uleb128 Lcst_end3-Lcst_begin3
Lcst_begin3:
	.uleb128 Lfunc_begin3-Lfunc_begin3      ; >> Call Site 1 <<
	.uleb128 Ltmp47-Lfunc_begin3            ;   Call between Lfunc_begin3 and Ltmp47
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp47-Lfunc_begin3            ; >> Call Site 2 <<
	.uleb128 Ltmp48-Ltmp47                  ;   Call between Ltmp47 and Ltmp48
	.uleb128 Ltmp49-Lfunc_begin3            ;     jumps to Ltmp49
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp48-Lfunc_begin3            ; >> Call Site 3 <<
	.uleb128 Lfunc_end3-Ltmp48              ;   Call between Ltmp48 and Lfunc_end3
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
Lcst_end3:
	.p2align	2, 0x0
                                        ; -- End function
	.section	__TEXT,__text,regular,pure_instructions
	.private_extern	__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE20__throw_length_errorB9nqe220106Ev ; -- Begin function _ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE20__throw_length_errorB9nqe220106Ev
	.globl	__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE20__throw_length_errorB9nqe220106Ev
	.weak_def_can_be_hidden	__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE20__throw_length_errorB9nqe220106Ev
	.p2align	2
__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE20__throw_length_errorB9nqe220106Ev: ; @_ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE20__throw_length_errorB9nqe220106Ev
	.cfi_startproc
; %bb.0:
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	mov	x29, sp
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
Lloh28:
	adrp	x0, l_.str.2@PAGE
Lloh29:
	add	x0, x0, l_.str.2@PAGEOFF
	bl	__ZNSt3__120__throw_length_errorB9nqe220106EPKc
	.loh AdrpAdd	Lloh28, Lloh29
	.cfi_endproc
                                        ; -- End function
	.section	__TEXT,__cstring,cstring_literals
l_.str:                                 ; @.str
	.asciz	"round,ns_per_op,checksum\n"

l_.str.1:                               ; @.str.1
	.asciz	"vector"

l_.str.2:                               ; @.str.2
	.asciz	"basic_string"

.subsections_via_symbols
