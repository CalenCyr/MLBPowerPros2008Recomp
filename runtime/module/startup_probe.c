// SPDX-License-Identifier: GPL-3.0-or-later
// Bounded startup diagnostic. It stops at the first missing hardware service;
// it is not a Wii boot environment and does not provide graphics or audio.
#include "StaticRecompABI.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
__declspec(dllimport) const StaticRecompModuleDesc* staticrecomp_get_module(void);
static unsigned missing;
static void missing_instruction(CPUState* cpu, u32 raw, u32 cia) {
    fprintf(stderr, "missing instruction service: pc=%08X instruction=%08X\n", cia, raw);
    ++missing;
    cpu->exception = PPC_EXC_PROGRAM;
}
static u64 missing_read(CPUState* cpu, u32 address, u8 size) {
    fprintf(stderr, "missing hardware read: pc=%08X address=%08X size=%u\n", cpu->pc, address, size);
    ++missing;
    cpu->exception = PPC_EXC_DSI;
    return 0;
}
static void missing_write(CPUState* cpu, u32 address, u64 value, u8 size) {
    fprintf(stderr, "missing hardware write: pc=%08X address=%08X size=%u\n", cpu->pc, address, size);
    ++missing;
    cpu->exception = PPC_EXC_DSI;
}
static u32 be32(const unsigned char* p) {
    return ((u32)p[0] << 24) | ((u32)p[1] << 16) | ((u32)p[2] << 8) | p[3];
}
int main(int argc, char** argv) {
    if (argc != 2) { fprintf(stderr, "usage: powerpros_startup_probe main.dol\n"); return 1; }
    FILE* file = fopen(argv[1], "rb");
    if (!file) return 1;
    if (fseek(file, 0, SEEK_END)) { fclose(file); return 1; }
    long length = ftell(file);
    if (length < 256 || length > 32 * 1024 * 1024) { fclose(file); return 1; }
    rewind(file);
    unsigned char* bytes = malloc((size_t)length);
    if (!bytes || fread(bytes, 1, (size_t)length, file) != (size_t)length) {
        free(bytes); fclose(file); return 1;
    }
    fclose(file);
    CPUState cpu;
    if (!cpu_init(&cpu)) { free(bytes); return 1; }
    for (unsigned i = 0; i < 18; ++i) {
        u32 offset = be32(bytes + 4*i), address = be32(bytes + 0x48 + 4*i);
        u32 size = be32(bytes + 0x90 + 4*i);
        if (!size) continue;
        if (offset > (u32)length || size > (u32)length - offset ||
            address < GC_RAM_BASE || address - GC_RAM_BASE > cpu.ram_size ||
            size > cpu.ram_size - (address - GC_RAM_BASE)) {
            fprintf(stderr, "DOL section outside file or MEM1\n");
            free(bytes); cpu_free(&cpu); return 1;
        }
        memcpy(cpu.ram + address - GC_RAM_BASE, bytes + offset, size);
    }
    cpu.pc = be32(bytes + 0xe0);
    free(bytes);
    const StaticRecompModuleDesc* module = staticrecomp_get_module();
    if (module->abi_version != STATICRECOMP_ABI_VERSION ||
        module->cpu_abi_version != GXRUNTIME_CPU_ABI_VERSION ||
        module->cpu_state_size != sizeof(cpu) || module->entry_point != cpu.pc ||
        strcmp(module->game_id, "RL8E54")) { cpu_free(&cpu); return 1; }
    cpu.instruction_fallback = missing_instruction;
    cpu.external_read = missing_read;
    cpu.external_write = missing_write;
    // Reset registers are deliberately zero: this probe measures only the
    // untranslated service boundary, not successful Wii bootstrap behavior.
    printf("startup probe: module ABI %u, CPU ABI %u, entry=%08X\n",
        module->abi_version, module->cpu_abi_version, cpu.pc);
    unsigned dispatches = 0;
    while (!cpu.exception && !missing && dispatches < 100000) {
        cpu.downcount = 100000;
        cpu.cycle_budget = 256;
        if (!module->dispatch(&cpu, cpu.pc)) {
            fprintf(stderr, "uncovered PC=%08X\n", cpu.pc);
            break;
        }
        ++dispatches;
    }
    printf("stopped: dispatches=%u pc=%08X missing_services=%u exception=%08X\n",
        dispatches, cpu.pc, missing, cpu.exception);
    cpu_free(&cpu);
    // A service boundary is useful diagnostic output, not a successful boot.
    return 2;
}
