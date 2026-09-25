# RTL-simulation payloads: the shared bench mains built for a bare
# 68040 core in a flat-RAM testbench (tb_corpus.v + AP68040 rtl).
# Same platform trio as the Amiga port minus the OS: external
# framebuffer, external (RAM memcpy) writer, raw-CPUSHA cache idiom
# (AMIGA_BENCH really means "bare-metal 040, no Mac ROM").
#
# Narrow the corpus for smoke runs:
#   make payloads CDEFS="-DLAST_TEST_INDEX=9"

VIDEO_VARIANT := mdc824

include ../common/make/common.mk

BUILD := build
SB    := ../supervisor_bench
COMMON_RUNTIME := $(COMMON)/runtime
COMMON_DISPLAY := $(COMMON)/display

SCFLAGS := $(CFLAGS) -DDISPLAY_FB_EXTERN -DJW_BACKEND_EXTERN -DAMIGA_BENCH

PAYLOADS := $(BUILD)/payload_cpu_sim.bin \
            $(BUILD)/payload_fpu_sim.bin \
            $(BUILD)/payload_saverestore_sim.bin \
            $(BUILD)/payload_integration_sim.bin \
            $(BUILD)/payload_mmu_sim.bin

all: payloads
payloads: $(PAYLOADS)
.PHONY: all payloads clean

$(BUILD):
	mkdir -p $@

$(BUILD)/payload_entry_sim.o: payload_entry_sim.s | $(BUILD)
	$(AS) $(ASFLAGS) -o $@ $<
$(BUILD)/payload_entry_sim_mmu.o: payload_entry_sim.s | $(BUILD)
	$(AS) $(ASFLAGS) --defsym SIM_MMU_WORLD=1 -o $@ $<
$(BUILD)/jsonl_sim.o: jsonl_sim.c | $(BUILD)
	$(CC) $(SCFLAGS) -c -o $@ $<
$(BUILD)/eject_stub.o: ../amiga/eject_amiga.c | $(BUILD)
	$(CC) $(SCFLAGS) -c -o $@ $<
$(BUILD)/jsonl_writer.o: $(COMMON_RUNTIME)/jsonl_writer.c | $(BUILD)
	$(CC) $(SCFLAGS) -c -o $@ $<
$(BUILD)/freestanding.o: $(COMMON_RUNTIME)/freestanding.c | $(BUILD)
	$(CC) $(SCFLAGS) -c -o $@ $<
$(BUILD)/font_ascii.o: $(COMMON_DISPLAY)/display_1bpp.c | $(BUILD)
	$(CC) $(SCFLAGS) -c -o $@ $<
$(BUILD)/recovery.o: $(COMMON_RUNTIME)/recovery.s | $(BUILD)
	$(AS) $(ASFLAGS) --defsym NO_SCRNBASE_DOT=1 -o $@ $<
$(BUILD)/recovery_mmu.o: $(COMMON_RUNTIME)/recovery.s | $(BUILD)
	$(AS) $(ASFLAGS) --defsym NO_SCRNBASE_DOT=1 --defsym MMU_RECOVERY=1 -o $@ $<
$(BUILD)/jsonl_writer_48k.o: $(COMMON_RUNTIME)/jsonl_writer.c | $(BUILD)
	$(CC) $(SCFLAGS) -DJW_BATCH_BYTES=49152 -c -o $@ $<
$(BUILD)/jsonl_sim_48k.o: jsonl_sim.c | $(BUILD)
	$(CC) $(SCFLAGS) -DJW_BATCH_BYTES=49152 -c -o $@ $<
$(BUILD)/bench_main.o: $(SB)/bench_main.c ../../gen/cpu_tests.h | $(BUILD)
	$(CC) $(SCFLAGS) -I$(SB) -c -o $@ $<
$(BUILD)/fpu_bench_main.o: $(SB)/fpu_bench_main.c ../../gen/fpu_tests.h | $(BUILD)
	$(CC) $(SCFLAGS) -I$(SB) -c -o $@ $<
$(BUILD)/cpu_fpu_bench_main.o: $(SB)/cpu_fpu_bench_main.c ../../macos_bench/cpu_fpu_tests.h | $(BUILD)
	$(CC) $(SCFLAGS) -I$(SB) -c -o $@ $<
$(BUILD)/cpu_fpu_save_restore_bench_main.o: $(SB)/cpu_fpu_bench_main.c ../../macos_bench/save_restore_tests.h | $(BUILD)
	$(CC) $(SCFLAGS) -I$(SB) -DCPU_FPU_CORPUS_HEADER='"../../macos_bench/save_restore_tests.h"' -c -o $@ $<
# Full MMU corpus (live translation): 48K single-flush batch; the harness
# identity window default ($40000) matches the sim payload base.
$(BUILD)/mmu_bench_main_full.o: $(SB)/mmu_bench_main.c ../../gen/mmu_tests.h | $(BUILD)
	$(CC) $(SCFLAGS) -I$(SB) -DMMU_FULL -DJW_BATCH_BYTES=49152 -c -o $@ $<

SIM_BASE := $(BUILD)/payload_entry_sim.o \
            $(BUILD)/jsonl_sim.o \
            $(BUILD)/eject_stub.o \
            $(BUILD)/jsonl_writer.o \
            $(BUILD)/freestanding.o \
            $(BUILD)/font_ascii.o \
            $(BUILD)/recovery.o

$(BUILD)/payload_cpu_sim.elf: $(SIM_BASE) $(BUILD)/bench_main.o $(PAYLOAD_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_LD) -o $@ $(SIM_BASE) $(BUILD)/bench_main.o
$(BUILD)/payload_fpu_sim.elf: $(SIM_BASE) $(BUILD)/fpu_bench_main.o $(PAYLOAD_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_LD) -o $@ $(SIM_BASE) $(BUILD)/fpu_bench_main.o
$(BUILD)/payload_saverestore_sim.elf: $(SIM_BASE) $(BUILD)/cpu_fpu_save_restore_bench_main.o $(PAYLOAD_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_LD) -o $@ $(SIM_BASE) $(BUILD)/cpu_fpu_save_restore_bench_main.o
$(BUILD)/payload_integration_sim.elf: $(SIM_BASE) $(BUILD)/cpu_fpu_bench_main.o $(PAYLOAD_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_LD) -o $@ $(SIM_BASE) $(BUILD)/cpu_fpu_bench_main.o
SIM_MMU := $(BUILD)/payload_entry_sim_mmu.o $(BUILD)/jsonl_sim_48k.o \
           $(BUILD)/eject_stub.o $(BUILD)/jsonl_writer_48k.o \
           $(BUILD)/freestanding.o $(BUILD)/font_ascii.o $(BUILD)/recovery_mmu.o
$(BUILD)/payload_mmu_sim.elf: $(SIM_MMU) $(BUILD)/mmu_bench_main_full.o $(PAYLOAD_LD)
	$(LD) $(LDFLAGS) -T $(PAYLOAD_LD) -o $@ $(SIM_MMU) $(BUILD)/mmu_bench_main_full.o
$(BUILD)/payload%.bin: $(BUILD)/payload%.elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD)
