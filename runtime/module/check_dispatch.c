// SPDX-License-Identifier: GPL-3.0-or-later
// Run the existing original-PPC fixtures through the DLL's public module ABI.
#include "StaticRecompABI.h"
#include <stdio.h>
#include <stdlib.h>
__declspec(dllimport) const StaticRecompModuleDesc* staticrecomp_get_module(void);
void func_80004000(CPUState* ctx) {
    const StaticRecompModuleDesc* module = staticrecomp_get_module();
    if (module->abi_version != STATICRECOMP_ABI_VERSION ||
        module->cpu_abi_version != GXRUNTIME_CPU_ABI_VERSION ||
        module->cpu_state_size != sizeof(*ctx) ||
        !module->dispatch(ctx, ctx->pc)) {
        fprintf(stderr, "Runtime module ABI or dispatch mismatch\n");
        exit(1);
    }
}
