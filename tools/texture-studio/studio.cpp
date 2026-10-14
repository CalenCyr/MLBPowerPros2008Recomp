// SPDX-License-Identifier: GPL-3.0-or-later
// Power Pros Wii 2008 Texture Studio.
#include "pack.h"

#include <SDL3/SDL.h>

#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>

namespace tstudio { int RunSelftest(); }

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--selftest") == 0) return tstudio::RunSelftest();
    // Developer checks against local game data (nothing of it is stored).
    if (argc == 3 && std::strcmp(argv[1], "--list-pack") == 0) {
        std::ifstream f(argv[2], std::ios::binary);
        const std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), {});
        for (const auto& t : tstudio::FindTextures(d))
            std::printf("%#x %u %u %u %#x\n", t.offset, t.width, t.height, t.format, t.paletteEntries ? t.paletteData : 0);
        return 0;
    }
    return 0;
}
