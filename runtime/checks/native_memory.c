/* Executes the game's translated memory routines without an interpreter.
 * This is a CPU verification harness, not a game runtime or launcher. */
#ifndef DOLRECOMP_CPU_HEADER
#define DOLRECOMP_CPU_HEADER "cpu/cpu.h"
#endif
#include DOLRECOMP_CPU_HEADER
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void func_80004000(CPUState* cpu);

enum { TEST_RAM_BYTES = 8192, STACK_OFFSET = 0x20000 };
static const u32 RAM_BASE = 0x80000000u;
static const u32 DATA_OFFSET = 0x10000u;
static const u32 RETURN_SENTINEL = 0xDEADC0DCu;
static unsigned fallback_count;
/* Guest cycles charged by native code across all cases; lets two module builds of
   the same routines be compared for cycle accounting. */
static unsigned long long charged_cycles;

static void reject_fallback(CPUState* cpu, u32 raw, u32 address) {
    ++fallback_count;
    fprintf(stderr, "Unexpected instruction fallback %08X at %08X\n", raw, address);
    cpu->exception = 1;
}

static int invoke(CPUState* cpu, u32 entry, u32 arg3, u32 arg4, u32 size) {
    const u32 saved31 = 0x12345678u;
    const u32 stack = RAM_BASE + STACK_OFFSET;
    memset(cpu->gpr, 0, sizeof(cpu->gpr));
    cpu->gpr[1] = stack;
    cpu->gpr[3] = arg3;
    cpu->gpr[4] = arg4;
    cpu->gpr[5] = size;
    cpu->gpr[31] = saved31;
    cpu->pc = entry;
    cpu->lr = RETURN_SENTINEL;
    cpu->ctr = cpu->cr = cpu->xer = cpu->exception = 0;
    /* The SDK memcpy uses floating-point loads/stores on aligned blocks. */
    cpu->msr = 0x00002000u;
    cpu->instruction_fallback = reject_fallback;
    fallback_count = 0;
    unsigned batches = 0;
    while (cpu->pc != RETURN_SENTINEL && !cpu->exception && batches++ < 4096) {
        cpu->downcount = 1000000;
        func_80004000(cpu);
        charged_cycles += (unsigned long long)(1000000 - cpu->downcount);
    }
    if (cpu->pc != RETURN_SENTINEL || cpu->exception || fallback_count ||
        cpu->gpr[3] != arg3 || cpu->gpr[1] != stack || cpu->gpr[31] != saved31) {
        fprintf(stderr, "Routine failed entry=%08X size=%u pc=%08X exception=%u batches=%u\n",
                entry, size, cpu->pc, cpu->exception, batches);
        return 0;
    }
    return 1;
}

static void seed(u8* expected, u8* actual) {
    for (unsigned i = 0; i < TEST_RAM_BYTES; ++i)
        expected[i] = (u8)((i * 73u + (i >> 3) * 19u) & 255u);
    memcpy(actual, expected, TEST_RAM_BYTES);
}

static int compare_ram(const u8* actual, const u8* expected, u32 entry,
                       unsigned destination, unsigned source, unsigned size) {
    if (!memcmp(actual, expected, TEST_RAM_BYTES)) return 1;
    fprintf(stderr, "Memory mismatch entry=%08X dst=%u src_or_fill=%u size=%u\n",
            entry, destination, source, size);
    unsigned shown = 0;
    for (unsigned i = 0; i < TEST_RAM_BYTES && shown < 12; ++i) {
        if (actual[i] != expected[i]) {
            fprintf(stderr, "  offset=%u expected=%02X actual=%02X\n", i, expected[i], actual[i]);
            ++shown;
        }
    }
    return 0;
}

static int read_reference(FILE* reference, u8* expected, u32 entry,
                          unsigned destination, unsigned source, unsigned size) {
    unsigned char meta[16];
    u32 fields[4];
    if (fread(meta, 1, sizeof(meta), reference) != sizeof(meta)) return 0;
    for (unsigned i = 0; i < 4; ++i)
        fields[i] = (u32)meta[i * 4] | ((u32)meta[i * 4 + 1] << 8) |
                    ((u32)meta[i * 4 + 2] << 16) | ((u32)meta[i * 4 + 3] << 24);
    if (fields[0] != entry || fields[1] != destination || fields[2] != source || fields[3] != size) {
        fprintf(stderr, "Reference case ordering mismatch.\n");
        return 0;
    }
    return fread(expected, 1, TEST_RAM_BYTES, reference) == TEST_RAM_BYTES;
}

int main(int argc, char** argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: powerpros_native_checks memory-reference.bin\n");
        return 1;
    }
    FILE* reference = fopen(argv[1], "rb");
    unsigned char header[76];
    if (!reference || fread(header, 1, sizeof(header), reference) != sizeof(header) ||
        memcmp(header, "PPPMREF1", 8) || memcmp(header + 8, DOL_SOURCE_SHA256, 64) ||
        header[72] != 0x30 || header[73] != 0x09 || header[74] || header[75]) {
        fprintf(stderr, "Missing or incompatible PPC reference fixture.\n");
        if (reference) fclose(reference);
        return 1;
    }
    CPUState* cpu = (CPUState*)calloc(1, sizeof(*cpu));
    u8 expected[TEST_RAM_BYTES];
    const unsigned sizes[] = {0, 1, 2, 3, 4, 7, 8, 15, 16, 20, 21, 31, 32, 33, 63, 64, 65, 255, 256, 257, 1024};
    const unsigned fills[] = {0, 1, 0x7F, 0x80, 0xFF, 0x1234};
    unsigned checks = 0;
    if (!cpu || !cpu_init(cpu)) {
        free(cpu);
        fclose(reference);
        return 1;
    }
    u8* actual = cpu->ram + DATA_OFFSET;
    for (unsigned alignment = 0; alignment < 8; ++alignment) {
        for (unsigned n = 0; n < sizeof(sizes) / sizeof(sizes[0]); ++n) {
            for (unsigned v = 0; v < sizeof(fills) / sizeof(fills[0]); ++v) {
                seed(expected, actual);
                unsigned offset = 64 + alignment;
                if (!read_reference(reference, expected, 0x800065BCu, offset, fills[v], sizes[n])) goto failed;
                if (!invoke(cpu, 0x800065BCu, RAM_BASE + DATA_OFFSET + offset, fills[v], sizes[n]) ||
                    !compare_ram(actual, expected, 0x800065BCu, offset, fills[v], sizes[n])) goto failed;
                ++checks;
            }
        }
    }
    for (unsigned destination_alignment = 0; destination_alignment < 8; ++destination_alignment) {
        for (unsigned source_alignment = 0; source_alignment < 8; ++source_alignment) {
            for (unsigned n = 0; n < sizeof(sizes) / sizeof(sizes[0]); ++n) {
                unsigned destination = 64 + destination_alignment;
                unsigned source = 2048 + source_alignment;
                seed(expected, actual);
                if (!read_reference(reference, expected, 0x8000626Cu, destination, source, sizes[n])) goto failed;
                if (!invoke(cpu, 0x8000626Cu, RAM_BASE + DATA_OFFSET + destination,
                            RAM_BASE + DATA_OFFSET + source, sizes[n]) ||
                    !compare_ram(actual, expected, 0x8000626Cu, destination, source, sizes[n])) goto failed;
                ++checks;
            }
        }
    }
    if (checks != 2352 || fgetc(reference) != EOF) goto failed;
    printf("PASS: %u native memset/memcpy cases match original PPC; no instruction fallback; charged_cycles=%llu.\n",
           checks, charged_cycles);
    cpu_free(cpu);
    free(cpu);
    fclose(reference);
    return 0;
failed:
    fprintf(stderr, "FAIL after %u successful cases.\n", checks);
    cpu_free(cpu);
    free(cpu);
    fclose(reference);
    return 1;
}
