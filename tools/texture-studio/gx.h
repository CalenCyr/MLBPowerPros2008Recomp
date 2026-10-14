// SPDX-License-Identifier: GPL-3.0-or-later
// GameCube/Wii GX texture formats: block sizes and decoders (big-endian, tiled).
#pragma once
#include "core.h"

namespace tstudio {

bool IsKnownFormat(uint32_t fmt);  // I4 I8 IA4 IA8 RGB565 RGB5A3 RGBA8 C4 C8 C14X2 CMPR
bool IsDecodable(uint32_t fmt);    // I4 I8 RGB5A3 RGBA8 C4 C8
bool IsPaletted(uint32_t fmt);     // C4 C8 C14X2
const char* FormatName(uint32_t fmt);
// Bytes of the base level, padded to whole blocks (what the runtime hashes). 0 for unknown formats.
uint32_t TextureBytes(uint32_t w, uint32_t h, uint32_t fmt);
// Untiled texel values (h * w) of a 4-, 8- or 16-bit format; empty if the data is short or RGBA8.
std::vector<uint16_t> Values(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt);
// RGBA image; palette = big-endian RGB5A3 entries (empty: C4/C8 show their indices in grey).
Image Decode(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt, std::span<const uint8_t> paletteBE);

} // namespace tstudio
