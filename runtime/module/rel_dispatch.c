// SPDX-License-Identifier: GPL-3.0-or-later
// Separate header scope: both generated headers define the same local helpers.
#include "runtime_rel.h"
#include <stdio.h>
#include <stdlib.h>
int powerpros_rel_dispatch(CPUState* ctx, u32 address) {
    static unsigned trace_samples;
    const int executed = dolrecomp_call(ctx, address);
    if (executed && trace_samples < 8) {
        const char* path = getenv("STATICRECOMP_REL_TRACE_FILE");
        if (path && *path) {
            FILE* trace = fopen(path,"a");
            if (trace) {
                fprintf(trace,"%08X,%08X,%u\n",address,ctx->pc,ctx->exception);
                fclose(trace);
            }
        }
        ++trace_samples;
    }
    return executed;
}
