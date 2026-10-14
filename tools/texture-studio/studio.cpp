// SPDX-License-Identifier: GPL-3.0-or-later
// Power Pros Wii 2008 Texture Studio.
#include "gx.h"
#include "names.h"
#include "pack.h"
#include "projectbin.h"

#include <SDL3/SDL.h>

#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <set>

namespace tstudio { int RunSelftest(); }

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--selftest") == 0) return tstudio::RunSelftest();
    // Developer checks against local game data (nothing of it is stored).
    if (argc == 3 && std::strcmp(argv[1], "--list-pack") == 0) {
        std::ifstream f(argv[2], std::ios::binary);
        const std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), {});
        for (const auto& t : tstudio::FindTextures(d))
            std::printf("%#x %u %u %u %#x %016llx\n", t.offset, t.width, t.height, t.format, t.paletteEntries ? t.paletteData : 0,
                        static_cast<unsigned long long>(tstudio::TextureHash(
                            std::span<const uint8_t>(d.data() + t.data, d.size() - t.data), t.width, t.height, t.format)));
        return 0;
    }
    if (argc == 3 && std::strcmp(argv[1], "--list-entries") == 0) {
        std::string error;
        const auto index = tstudio::ReadProjectIndex(argv[2], &error);
        if (!index) { std::fprintf(stderr, "%s\n", error.c_str()); return 1; }
        for (const auto& e : *index) std::printf("%llu %u %s\n", static_cast<unsigned long long>(e.offset), e.size, e.name.c_str());
        return 0;
    }
    if (argc == 4 && std::strcmp(argv[1], "--check-dumps") == 0) {  // names computed here vs the game's dumps
        std::string error;
        const auto index = tstudio::ReadProjectIndex(argv[2], &error);
        if (!index) { std::fprintf(stderr, "%s\n", error.c_str()); return 1; }
        std::set<std::string> mine, texKeys;
        auto texKey = [](const std::string& n) { return n.substr(0, n.find('_', n.find('_', 5) + 1)); };
        for (const auto& e : *index) {
            if (!e.name.ends_with(".pack")) continue;
            const auto d = tstudio::ReadEntry(argv[2], e);
            for (const auto& t : tstudio::FindTextures(d)) {
                const std::span<const uint8_t> px(d.data() + t.data, d.size() - t.data);
                tstudio::ParsedName n{t.width, t.height, t.format, tstudio::TextureHash(px, t.width, t.height, t.format)};
                if (tstudio::IsPaletted(t.format)) {
                    n.hasPalette = true;
                    std::optional<uint64_t> ph;
                    if (t.paletteEntries)
                        ph = tstudio::PaletteHash(px, t.width, t.height, t.format,
                                                  std::span<const uint8_t>(d.data() + t.paletteData, 2u * t.paletteEntries));
                    if (ph) n.paletteHash = *ph; else n.paletteWildcard = true;
                }
                mine.insert(tstudio::ReplacementName(n));
                texKeys.insert(texKey(tstudio::ReplacementName(n)));
            }
        }
        int total = 0, exact = 0, texture = 0;
        for (const auto& f : std::filesystem::directory_iterator(argv[3])) {
            const std::string stem = tstudio::Utf8(f.path().stem());
            if (!tstudio::ParseName(stem)) continue;
            ++total;
            exact += mine.count(stem) ? 1 : 0;
            texture += texKeys.count(texKey(stem)) ? 1 : 0;
        }
        std::printf("entries %zu, distinct names %zu\n", index->size(), mine.size());
        std::printf("dumps %d, same texture %d, same full name %d\n", total, texture, exact);
        return 0;
    }
    return 0;
}
