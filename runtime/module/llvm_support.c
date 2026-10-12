// SPDX-License-Identifier: GPL-3.0-or-later
// Helper required by DolRecomp LLVM-backend objects and absent from GXRuntime.
// Same semantics as DolRecomp src/cpu/cpu.c (nested commit 71ce7f9): without a
// host_call hook every region is native; with one, the chassis must answer the
// region query, otherwise the region stays on the interpreter (safe, slow).
#include "core/cpu.h"

#define PPC_HOST_CALL_NATIVE_REGION_QUERY 0xFFFFFFFCu
#define PPC_NATIVE_REGION_QUERY_PENDING 0xFEu
#define PPC_NATIVE_REGION_QUERY_HANDLED 0xFFu

bool ppc_native_region_available(CPUState* cpu, u32 start, u32 end) {
    if (!cpu || !cpu->host_call)
        return true;

    u32 saved_addr = cpu->external_addr;
    u32 saved_value = cpu->external_value;
    u8 saved_rid = cpu->external_rid;
    cpu->external_addr = start;
    cpu->external_value = end;
    cpu->external_rid = PPC_NATIVE_REGION_QUERY_PENDING;
    bool blocked = cpu->host_call(cpu, PPC_HOST_CALL_NATIVE_REGION_QUERY);
    bool handled = cpu->external_rid == PPC_NATIVE_REGION_QUERY_HANDLED;
    cpu->external_addr = saved_addr;
    cpu->external_value = saved_value;
    cpu->external_rid = saved_rid;
    return handled && !blocked;
}

// Diagnostic for the LLVM-DOL experiment: abort() at shutdown left no trace.
// Print module+offset frames so the runtime/module maps can resolve them.
#include <windows.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
static void print_abort_stack(int sig) {
    void* frames[48];
    USHORT n = RtlCaptureStackBackTrace(0, 48, frames, NULL);
    fprintf(stderr, "[powerpros-diagnostic] abort signal=%d frames=%u\n", sig, n);
    for (USHORT i = 0; i < n; ++i) {
        HMODULE module = NULL;
        char name[MAX_PATH] = "?";
        if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                               GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                               (LPCSTR)frames[i], &module))
            GetModuleFileNameA(module, name, sizeof(name));
        const char* base = strrchr(name, '\\');
        fprintf(stderr, "[powerpros-diagnostic] frame %u %s+0x%llx\n", i, base ? base + 1 : name,
                (unsigned long long)((char*)frames[i] - (char*)module));
    }
    fflush(stderr);
}
BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved) {
    (void)instance; (void)reserved;
    if (reason == DLL_PROCESS_ATTACH)
        signal(SIGABRT, print_abort_stack);
    return TRUE;
}
