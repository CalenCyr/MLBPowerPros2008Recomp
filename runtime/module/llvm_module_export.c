// SPDX-License-Identifier: GPL-3.0-or-later
// LLVM-DOL variant of module_export.c: identical descriptor and REL guard, with a
// memoized address lookup in front of the generated linear region chain.
#include "main.h"
// 2 MiB window covers the DOL text.
#define LOOKUP_BASE 0x80000000u
#define LOOKUP_SLOTS (0x00200000u >> 2)
#include "llvm_lookup.h"
#define dolrecomp_call fast_call
#include "module_export.c"
