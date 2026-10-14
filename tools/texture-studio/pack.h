// SPDX-License-Identifier: GPL-3.0-or-later
// Texture and palette headers inside a PACKWII file (docs/ingenieria-inversa.md, section 5).
#pragma once
#include "core.h"

namespace tstudio {

struct PackTexture {
    uint32_t offset = 0, width = 0, height = 0, format = 0, data = 0;  // header and pixel positions in the pack
    bool model = false;
    uint16_t paletteEntries = 0;  // 0: no palette found
    uint32_t paletteData = 0;
    bool paletteByPosition = false;  // paired only by position: keep it fixed
};

std::vector<PackTexture> FindTextures(std::span<const uint8_t> pack);  // empty unless "PACKWII "

} // namespace tstudio
