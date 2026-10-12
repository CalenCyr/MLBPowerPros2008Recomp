// SPDX-License-Identifier: GPL-3.0-or-later
// LLVM-REL variant of rel_dispatch.c with a memoized lookup over the linked REL text.
// POWERPROS_REL_LOOKUP_BASE/_SLOTS come from layout.json (runtime/module/CMakeLists.txt).
// The generated dolrecomp_find_original is a ~185k-line if-chain reached only on a lookup
// cache miss; optimizing it took ~33 min per build. The hot path is in llvm_lookup.h.
#ifdef __clang__
#pragma clang optimize off
#endif
#include "runtime_rel.h"
#ifdef __clang__
#pragma clang optimize on
#endif
#define LOOKUP_BASE POWERPROS_REL_LOOKUP_BASE
#define LOOKUP_SLOTS POWERPROS_REL_LOOKUP_SLOTS
#include "llvm_lookup.h"
#define dolrecomp_call fast_call
#include "rel_dispatch.c"
