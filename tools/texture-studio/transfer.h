// SPDX-License-Identifier: GPL-3.0-or-later
// Export originals as PNG; import edited PNG/DDS files into a mod under their tex1_ names.
#pragma once
#include "catalog.h"

namespace tstudio {
struct ImportResult { std::string file; std::string texture; bool ok = false; std::string message; };
// One image onto one texture (the selected one). allPalettes: write the $ name instead of the exact one.
ImportResult ImportOne(Catalog& c, int texture, const std::filesystem::path& image, const std::filesystem::path& modRoot,
                       bool allPalettes);
// A folder (recursive): files whose name is a known tex1_ name; others reported.
std::vector<ImportResult> ImportFolder(Catalog& c, const std::filesystem::path& folder, const std::filesystem::path& modRoot);
// Original images as PNG under <out>/<group>/<subgroup>/<name>.png. Returns how many were written.
size_t Export(Catalog& c, const std::vector<int>& textures, const std::filesystem::path& out, std::vector<std::string>* problems);
} // namespace tstudio
