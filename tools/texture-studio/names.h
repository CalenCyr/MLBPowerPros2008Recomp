// SPDX-License-Identifier: GPL-3.0-or-later
// Dolphin-style replacement names, hashed like aurora's texture_replacement.cpp: XXH64 (seed 0) of the
// base level's padded bytes, and of the palette range between the smallest and largest index used.
#pragma once
#include "core.h"
#include <optional>

namespace tstudio {
uint64_t TextureHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt);
std::optional<uint64_t> PaletteHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt,
                                    std::span<const uint8_t> paletteBE);
struct ParsedName {
    uint32_t width = 0, height = 0, format = 0;
    uint64_t textureHash = 0;
    bool hasPalette = false, paletteWildcard = false;
    uint64_t paletteHash = 0;
};
std::string ReplacementName(const ParsedName& n);              // "tex1_..." without extension
std::optional<ParsedName> ParseName(std::string_view stem);    // nullopt unless a tex1_ name
} // namespace tstudio
