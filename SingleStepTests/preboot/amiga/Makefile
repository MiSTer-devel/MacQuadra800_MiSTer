# Amiga 68040 test floppies — payload builds (wombat33 port of the
# MacIIvi 68030 original; see README.md / DEBUGGING.md).
# Shares the bench mains, recovery.s, display_1bpp.c and jsonl_writer.c
# with the Mac supervisor_bench; only the platform layer here is
# Amiga-specific. Targets a 68040 Amiga (A4000/040 class, FS-UAE, or a
# Minimig-style 040 core); the gate refuses anything else.

# The Amiga bitplane is 1 bpp with a fixed 80-byte stride — force that
# before common.mk (whose default is the Quadra's 8 bpp DAFB variant).
VIDEO_VARIANT := mdc824

include ../common/make/common.mk

BUILD := build
SB    := ../supervisor_bench
COMMON_RUNTIME := $(COMMON)/runtime
COMMON_DISPLAY := $(COMMON)/display

# External framebuffer + trackdisk writer + the Amiga-side cache idiom
# (raw CPUSHA — no _HwPriv here; see amiga_gate.c).
ACFLAGS := $(CFLAGS) -DDISPLAY_FB_EXTERN -DJW_BACKEND_EXTERN -DAMIGA_BENCH
PAYLOAD_AMIGA_LD := payload_amiga.ld

PAYLOADS := $(BUILD)/payload_cpu_amiga.bin \
            $(BUILD)/payload_fpu_amiga.bin \
            $(BUILD)/payload_saverestore_amiga.bin \
            $(BUILD)/payload_integration_amiga.bin \
            $(BUILD)/payload_mmu_amiga.bin \
            $(BUILD)/payload_mmu_full_amiga.bin

all: payloads
payloads: $(BUILD)/bootblock.bin $(PAYLOADS)
.PHONY: all payloads clean

$(BUILD):
	mkdir -p $@

# ---------- bootblock (flat 1024 bytes; checksum patched later) ------
$(BUILD)/bootblock.o: bootblock.s | $(BUILD)
	$(AS) $(ASFLAGS) -o $@ $<
$(BUILD)/bootblock.elf: $(BUILD)/bootblock.o
	$(LD) $(LDFLAGS) -Ttext=0 -o $@ $<
$(BUILD)/bootblock.bin: $(BUILD)/bootblock.elf
	$(OBJCOPY) -O binary $< $@

# ---------- platform objects -----------------------------------------
$(BUILD)/payload_entry_amiga.o: payload_entry_amiga.s | $(BUILD)
	$(AS) $(ASFLAGS) -o $@ $<
$(BUILD)/jsonl_trackdisk.o: jsonl_trackdisk.c | $(BUILD)
	$(CC) $(ACFLAGS) -c -o $@ $<
$(BUILD)/eject_amiga.o: eject_amiga.c | $(BUILD)
	$(CC) $(ACFLAGS) -c -o $@ $<
# Gate flavors: cpu disks need a 68040; fpu-bearing disks add the FPU
# check (68LC040 refused); mmu disks add the MOVEC TC probe (EC040 refused).
$(BUILD)/amiga_gate.o: amiga_gate.c | $(BUILD)
	$(CC) $(ACFLAGS) -c -o $@ $<
$(BUILD)/amiga_gate_fpu.o: amiga_gate.c | $(BUILD)
	$(CC) $(ACFLAGS) -DGATE_NEED_FPU -c -o $@ $<
$(BUILD)/amiga_gate_mmu.o: amiga_gate.c | $(BUILD)
	$(CC) $(ACFLAGS) -DGATE_NEED_MMU -c -o $@ $<

# ---------- shared objects, Amiga-flavored ---------------------------
$(BUILD)/jsonl_writer.o: $(COMMON_RUNTIME)/jsonl_writer.c | $(BUILD)
	$(CC) $(ACFLAGS) -c -o $@ $<
$(BUILD)/jsonl_writer_48k.o: $(COMMON_RUNTIME)/jsonl_writer.c | $(BUILD)
	$(CC) $(ACFLAGS) -DJW_BATCH_BYTES=49152 -c -o $@ $<
$(BUILD)/freestanding.o: $(COMMON_RUNTIME)/freestanding.c | $(BUILD)
	$(CC) $(ACFLAGS) -c -o $@ $<
$(BUILD)/font_ascii.o: $(COMMON_DISPLAY)/display_1bpp.c | $(BUILD)
	$(CC) $(ACFLAGS) -c -o $@ $<
$(BUILD)/recovery.o: $(COMMON_RUNTIME)/recovery.s | $(BUILD)
	$(AS) $(ASFLAGS) --defsym NO_SCRNBASE_DOT=1 -o $@ $<
$(BUILD)/recovery_mmu.o: $(COMMON_RUNTIME)/recovery.s | $(BUILD)
	$(AS) $(ASFLAGS) --defsym NO_SCRNBASE_DOT=1 --defsym MMU_RECOVERY=1 -o $@ $<
$(BUILD)/bench_main.o: $(SB)/bench_main.c ../../gen/cpu_tests.h | $(BUILD)
	$(CC) $(ACFLAGS) -I$(SB) -c -o $@ $<
$(BUILD)/fpu_bench_main.o: $(SB)/fpu_bench_main.c ../../gen/fpu_tests.h | $(BUILD)
	$(CC) $(ACFLAGS) -I$(SB) -c -o $@ $<
$(BUILD)/cpu_fpu_bench_main.o: $(SB)/cpu_fpu_bench_main.c ../../macos_bench/cpu_fpu_tests.h | $(BUILD)
	$(CC) $(ACFLAGS) -I$(SB) -c -o $@ $<
$(BUILD)/cpu_fpu_save_restore_bench_main.o: $(SB)/cpu_fpu_bench_main.c ../../macos_bench/save_restore_tests.h | $(BUILD)
	$(CC) $(ACFLAGS) -I$(SB) -DCPU_FPU_CORPUS_HEADER='"../../macos_bench/save_restore_tests.h"' -c -o $@ $<
$(BUILD)/mmu_bench_main.o: $(SB)/mmu_bench_main.c ../../gen/mmu_tests.h | $(BUILD)
	$(CC) $(ACFLAGS) -I$(SB) -c -o $@ $<
# Full MMU: 48K single-flush batch; the harness identity window follows
# the Amiga load base (payload at $80000, not the Mac's $40000).
$(BUILD)/mmu_bench_main_full.o: $(SB)/mmu_bench_main.c ../../gen/mmu_tests.h | $(BUILD)
	$(CC) $(ACFLAGS) -I$(SB) -DMMU_FULL -DJW_BATCH_BYTES=49152 \
	    -DMMU_PAYLOAD_WINDOW_BASE=0x80000U -c -o $@ $<

# ---------- payloads --------------------------------------------------
# No fline_shim here: it forwards through the Mac ROM's low-mem table
# and every bench references it weak (bench mains skip it when absent).
AMIGA_BASE_OBJS := $(BUILD)/payload_entry_amiga.o \
                   $(BUILD)/jsonl_trackdisk.o \
                   $(BUILD)/eject_amiga.o \
                   $(BUILD)/freestanding.o \
                   $(BUILD)/font_ascii.o

$(BUILD)/payload_cpu_amiga.elf: $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate.o $(BUILD)/jsonl_writer.o $(BUILD)/bench_main.o $(BUILD)/recovery.o $(PAYLOAD_AMIGA_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_AMIGA_LD) -o $@ $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate.o $(BUILD)/jsonl_writer.o $(BUILD)/bench_main.o $(BUILD)/recovery.o
$(BUILD)/payload_fpu_amiga.elf: $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_fpu.o $(BUILD)/jsonl_writer.o $(BUILD)/fpu_bench_main.o $(BUILD)/recovery.o $(PAYLOAD_AMIGA_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_AMIGA_LD) -o $@ $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_fpu.o $(BUILD)/jsonl_writer.o $(BUILD)/fpu_bench_main.o $(BUILD)/recovery.o
$(BUILD)/payload_saverestore_amiga.elf: $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_fpu.o $(BUILD)/jsonl_writer.o $(BUILD)/cpu_fpu_save_restore_bench_main.o $(BUILD)/recovery.o $(PAYLOAD_AMIGA_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_AMIGA_LD) -o $@ $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_fpu.o $(BUILD)/jsonl_writer.o $(BUILD)/cpu_fpu_save_restore_bench_main.o $(BUILD)/recovery.o
$(BUILD)/payload_integration_amiga.elf: $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_fpu.o $(BUILD)/jsonl_writer.o $(BUILD)/cpu_fpu_bench_main.o $(BUILD)/recovery.o $(PAYLOAD_AMIGA_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_AMIGA_LD) -o $@ $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_fpu.o $(BUILD)/jsonl_writer.o $(BUILD)/cpu_fpu_bench_main.o $(BUILD)/recovery.o
$(BUILD)/payload_mmu_amiga.elf: $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_mmu.o $(BUILD)/jsonl_writer.o $(BUILD)/mmu_bench_main.o $(BUILD)/recovery_mmu.o $(PAYLOAD_AMIGA_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_AMIGA_LD) -o $@ $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_mmu.o $(BUILD)/jsonl_writer.o $(BUILD)/mmu_bench_main.o $(BUILD)/recovery_mmu.o
$(BUILD)/payload_mmu_full_amiga.elf: $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_mmu.o $(BUILD)/jsonl_writer_48k.o $(BUILD)/mmu_bench_main_full.o $(BUILD)/recovery_mmu.o $(PAYLOAD_AMIGA_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_AMIGA_LD) -o $@ $(AMIGA_BASE_OBJS) $(BUILD)/amiga_gate_mmu.o $(BUILD)/jsonl_writer_48k.o $(BUILD)/mmu_bench_main_full.o $(BUILD)/recovery_mmu.o

$(BUILD)/payload%.bin: $(BUILD)/payload%.elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD)
