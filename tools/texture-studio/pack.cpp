// SPDX-License-Identifier: GPL-3.0-or-later
// Port of tools/packwii.py find_textures (kept in step with it).
#include "pack.h"

#include "gx.h"

#include <cstring>
#include <optional>
#include <unordered_map>

namespace tstudio {
namespace {
std::optional<uint32_t> Pointer(std::span<const uint8_t> d, size_t o) {
    if (o + 4 > d.size()) return std::nullopt;
    const uint32_t p = Be32(d, o);
    if ((p >> 30) != 1) return std::nullopt;
    return p & 0x3FFFFFFF;
}
bool Pow2Size(uint32_t v) { return v >= 4 && v <= 1024 && (v & (v - 1)) == 0; }
struct Palette { uint16_t entries; uint32_t data; };
} // namespace

std::vector<PackTexture> FindTextures(std::span<const uint8_t> d) {
    std::vector<PackTexture> out;
    if (d.size() < 0x30 || std::memcmp(d.data(), "PACKWII ", 8) != 0) return out;
    std::unordered_map<uint32_t, Palette> pals;  // palette header offset -> palette
    for (size_t o = 0x20; o + 12 <= d.size(); o += 4) {
        const uint16_t w = Be16(d, o), h = Be16(d, o + 2);
        const auto p = Pointer(d, o + 8);
        if (!p || *p >= d.size()) continue;
        const uint8_t kind = d[o + 4];
        if (h == 0 && kind == 0x81 && (w == 16 || w == 256) && *p + 2ull * w <= d.size()) {
            pals[static_cast<uint32_t>(o)] = {w, *p};
            continue;
        }
        if (!Pow2Size(w) || !Pow2Size(h)) continue;
        uint32_t fmt;
        bool model;
        if ((kind == 0x80 || kind == 0x81 || kind == 0x82 || kind == 0x84) && d[o + 5] == 0) {
            fmt = kind == 0x80 ? 6 : kind == 0x81 ? 5 : kind == 0x82 ? 9 : 8;
            model = true;
        } else if (kind == 0 && IsKnownFormat(Be32(d, o + 4))) {
            fmt = Be32(d, o + 4);
            model = false;
        } else {
            continue;
        }
        if (*p + static_cast<uint64_t>(TextureBytes(w, h, fmt)) > d.size()) continue;
        PackTexture t{static_cast<uint32_t>(o), w, h, fmt, *p, model};
        if (!model && o + 0x30 <= d.size()) {
            const uint16_t n = Be16(d, o + 0x24);
            const auto pp = Pointer(d, o + 0x2C);
            if ((n == 16 || n == 256) && pp && *pp + 2ull * n <= d.size()) {
                t.paletteEntries = n;
                t.paletteData = *pp;
            }
        }
        out.push_back(t);
    }
    std::unordered_map<uint32_t, size_t> byOffset;
    for (size_t i = 0; i < out.size(); ++i) byOffset[out[i].offset] = i;
    auto needsPalette = [](const PackTexture& t) { return (t.format == 8 || t.format == 9) && t.paletteEntries == 0; };
    // Texture sets: {u32 n, -> n texture headers, u32 m, -> m palettes}; one palette for all or one each.
    for (size_t o = 0x20; o + 16 <= d.size(); o += 4) {
        const uint32_t c1 = Be32(d, o), c2 = Be32(d, o + 8);
        if (c1 == 0 || c1 >= 4096 || c2 == 0 || c2 >= 4096) continue;
        const auto l1 = Pointer(d, o + 4), l2 = Pointer(d, o + 12);
        if (!l1 || !l2 || *l1 + 4ull * c1 > d.size() || *l2 + 4ull * c2 > d.size()) continue;
        bool ok = true;
        for (uint32_t i = 0; ok && i < c1; ++i) { const auto x = Pointer(d, *l1 + 4 * i); ok = x && byOffset.count(*x); }
        for (uint32_t i = 0; ok && i < c2; ++i) { const auto x = Pointer(d, *l2 + 4 * i); ok = x && pals.count(*x); }
        if (!ok) continue;
        for (uint32_t i = 0; i < c1; ++i) {
            PackTexture& t = out[byOffset[*Pointer(d, *l1 + 4 * i)]];
            if (!needsPalette(t)) continue;
            const Palette& pal = pals[*Pointer(d, *l2 + 4 * (c2 == c1 ? i : 0))];
            t.paletteEntries = pal.entries;
            t.paletteData = pal.data;
        }
    }
    // By position: a model's palette header follows it (+0x24); otherwise the palette colours follow
    // the pixels (verified against the runtime's dumps). The header just before is the previous texture's.
    std::unordered_map<uint32_t, Palette> byData;
    for (const auto& [_, pal] : pals) byData.emplace(pal.data, pal);
    for (PackTexture& t : out) {
        if (!needsPalette(t)) continue;
        const uint16_t want = t.format == 8 ? 16 : 256;
        const uint32_t end = t.data + TextureBytes(t.width, t.height, t.format);
        const Palette* found = nullptr;
        if (auto it = pals.find(t.offset + 0x24); t.model && it != pals.end()) found = &it->second;
        else if (auto jt = byData.find(end); jt != byData.end() && jt->second.entries == want) found = &jt->second;
        if (!found) continue;
        t.paletteEntries = found->entries;
        t.paletteData = found->data;
        t.paletteByPosition = true;
    }
    return out;
}

} // namespace tstudio
