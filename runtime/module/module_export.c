// SPDX-License-Identifier: GPL-3.0-or-later
// Diagnostic module. Optional REL support requires the verified fixed layout.
#include "main.h"
#include "StaticRecompABI.h"
#include "module_tables.inc"
#ifdef POWERPROS_ENABLE_REL
int powerpros_rel_dispatch(CPUState* ctx, u32 address);
static u32 rel_be32(const u8* bytes) {
    return ((u32)bytes[0]<<24)|((u32)bytes[1]<<16)|((u32)bytes[2]<<8)|bytes[3];
}
static int rel_layout_matches(const CPUState* ctx) {
    const u32 offset = MODULE_REL_HEADER - 0x80000000u;
    const StaticRecompRelModule* module = &s_rel_modules[0];
    if (!ctx->ram || (u64)offset + module->section_info_offset + (u64)module->section_count*8 > ctx->ram_size) return 0;
    const u8* header = ctx->ram + offset;
    if (rel_be32(header)!=module->module_id || rel_be32(header+0x0C)!=module->section_count ||
        rel_be32(header+0x1C)!=module->version ||
        rel_be32(header+0x10)!=MODULE_REL_HEADER+module->section_info_offset) return 0;
    for (unsigned i=0;i<module->num_sections;++i) {
        const u8* entry = header + module->section_info_offset + s_rel_sections[i].section_index*8;
        const u32 start = rel_be32(entry) & ~1u;
        const u32 size = rel_be32(entry+4);
        if (start != s_rel_sections[i].linked_start || size != s_rel_sections[i].size) return 0;
    }
    return 1;
}
#endif
static int dispatch(CPUState* ctx, u32 address);

void dolrecomp_indirect_dispatch(CPUState* ctx, u32 address) {
    (void)dispatch(ctx, address);
}
static int dispatch(CPUState* ctx, u32 address) {
#ifdef POWERPROS_ENABLE_REL
    if (address >= MODULE_REL_CODE_START && address < MODULE_REL_CODE_END)
        return rel_layout_matches(ctx) ? powerpros_rel_dispatch(ctx,address) : 0;
#endif
    return dolrecomp_call(ctx, address);
}
static void on_state_loaded(CPUState* ctx) {
    ppc_fpscr_updated(ctx);
}
static const StaticRecompModuleDesc descriptor = {
    STATICRECOMP_ABI_VERSION, GXRUNTIME_CPU_ABI_VERSION, sizeof(CPUState),
    "RL8E54", 0x8000403Cu, dispatch, on_state_loaded,
    s_code_ranges, MODULE_CODE_RANGE_COUNT,
    s_smc_ranges, MODULE_SMC_RANGE_COUNT,
    s_chunk_ranges, MODULE_CHUNK_RANGE_COUNT, s_chunk_hashes,
#ifdef POWERPROS_ENABLE_REL
    s_rel_modules, MODULE_REL_MODULE_COUNT
#else
    NULL, 0
#endif
};
#if defined(_WIN32)
__declspec(dllexport)
#else
__attribute__((visibility("default")))
#endif
const StaticRecompModuleDesc* staticrecomp_get_module(void) {
    return &descriptor;
}
