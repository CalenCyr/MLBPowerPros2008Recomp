// SPDX-License-Identifier: GPL-3.0-or-later
// Memoized dispatch for DolRecomp LLVM-backend headers, whose dolrecomp_find_original is a
// linear chain over thousands of regions. Include after the generated header, with
// LOOKUP_BASE and LOOKUP_SLOTS (instruction slots) defined. Same results and same order of
// checks as the generated dolrecomp_call; addresses outside the window keep the generated
// lookup. ponytail: one fixed window per translation unit, a sorted region table if more
// layouts ever need it.
#include <stdint.h>

#define LOOKUP_NONE ((DolRecompFunction)(uintptr_t)1)
static DolRecompFunction s_lookup[LOOKUP_SLOTS];

static DolRecompFunction find_original(u32 address) {
    const u32 offset = address - LOOKUP_BASE;
    if ((offset & 3u) || offset >= ((u32)LOOKUP_SLOTS << 2))
        return dolrecomp_find_original(address);
    DolRecompFunction fn = s_lookup[offset >> 2];
    if (!fn) {
        fn = dolrecomp_find_original(address);
        s_lookup[offset >> 2] = fn ? fn : LOOKUP_NONE;
        return fn;
    }
    return fn == LOOKUP_NONE ? NULL : fn;
}

static int call_original(CPUState* ctx, u32 address) {
    DolRecompFunction fn = find_original(address);
    if (!fn) return 0;
    ctx->pc = address;
    fn(ctx);
    return 1;
}

// Without DOLRECOMP_ENABLE_REPLACEMENTS the generated dolrecomp_dispatch_replacement returns 0.
#ifdef DOLRECOMP_ENABLE_REPLACEMENTS
#define LOOKUP_REPLACEMENT(ctx, address) dolrecomp_dispatch_replacement(ctx, address)
#else
#define LOOKUP_REPLACEMENT(ctx, address) 0
#endif

static int fast_call(CPUState* ctx, u32 address) {
    u32 alias;
    ctx->pc = address;
    if (LOOKUP_REPLACEMENT(ctx, address)) return 1;
    if (ctx->host_call && ppc_host_call(ctx, address)) return 1;
    if (call_original(ctx, address)) return 1;
    if (dolrecomp_physical_pc_alias(ctx, address, &alias)) {
        ctx->pc = alias;
        if (LOOKUP_REPLACEMENT(ctx, alias)) return 1;
        if (ctx->host_call && ppc_host_call(ctx, alias)) return 1;
        if (call_original(ctx, alias)) return 1;
    }
    return 0;
}
