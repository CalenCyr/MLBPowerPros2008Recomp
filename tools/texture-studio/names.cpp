// SPDX-License-Identifier: GPL-3.0-or-later
#include "names.h"

#include "gx.h"

#define XXH_INLINE_ALL
#include <xxhash.h>

#include <algorithm>
#include <charconv>
#include <cstdio>

namespace tstudio {

uint64_t TextureHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt) {
    const size_t n = std::min<size_t>(TextureBytes(w, h, fmt), px.size());
    return XXH64(px.data(), n, 0);
}

std::optional<uint64_t> PaletteHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt,
                                    std::span<const uint8_t> paletteBE) {
    const size_t n = TextureBytes(w, h, fmt);
    if (n == 0 || px.size() < n || !IsPaletted(fmt)) return std::nullopt;
    uint32_t lo = UINT32_MAX, hi = 0;
    auto see = [&](uint32_t v) { lo = std::min(lo, v); hi = std::max(hi, v); };
    if (fmt == 8) for (size_t i = 0; i < n; ++i) { see(px[i] & 15); see(px[i] >> 4); }
    else if (fmt == 9) for (size_t i = 0; i < n; ++i) see(px[i]);
    else for (size_t i = 0; i + 2 <= n; i += 2) see((px[i] << 8 | px[i + 1]) & 0x3FFF);
    const size_t off = 2ull * lo, size = 2ull * (hi + 1 - lo);
    if (off + size > paletteBE.size()) return std::nullopt;
    return XXH64(paletteBE.data() + off, size, 0);
}

std::string ReplacementName(const ParsedName& n) {
    char buf[96];
    if (!n.hasPalette)
        std::snprintf(buf, sizeof buf, "tex1_%ux%u_%016llx_%u", n.width, n.height,
                      static_cast<unsigned long long>(n.textureHash), n.format);
    else if (n.paletteWildcard)
        std::snprintf(buf, sizeof buf, "tex1_%ux%u_%016llx_$_%u", n.width, n.height,
                      static_cast<unsigned long long>(n.textureHash), n.format);
    else
        std::snprintf(buf, sizeof buf, "tex1_%ux%u_%016llx_%016llx_%u", n.width, n.height,
                      static_cast<unsigned long long>(n.textureHash), static_cast<unsigned long long>(n.paletteHash), n.format);
    return buf;
}

std::optional<ParsedName> ParseName(std::string_view stem) {
    std::vector<std::string_view> parts;
    for (size_t start = 0;;) {
        const size_t us = stem.find('_', start);
        parts.push_back(stem.substr(start, us == std::string_view::npos ? std::string_view::npos : us - start));
        if (us == std::string_view::npos) break;
        start = us + 1;
    }
    if ((parts.size() != 4 && parts.size() != 5) || parts[0] != "tex1") return std::nullopt;
    auto number = [](std::string_view s, int base, uint64_t& out) {
        return !s.empty() && std::from_chars(s.data(), s.data() + s.size(), out, base).ptr == s.data() + s.size();
    };
    ParsedName n;
    const size_t x = parts[1].find('x');
    uint64_t w, h, tex, fmt;
    if (x == std::string_view::npos || !number(parts[1].substr(0, x), 10, w) || !number(parts[1].substr(x + 1), 10, h) ||
        !number(parts[2], 16, tex) || !number(parts.back(), 10, fmt))
        return std::nullopt;
    n.width = static_cast<uint32_t>(w);
    n.height = static_cast<uint32_t>(h);
    n.textureHash = tex;
    n.format = static_cast<uint32_t>(fmt);
    if (parts.size() == 5) {
        n.hasPalette = true;
        if (parts[3] == "$") n.paletteWildcard = true;
        else if (!number(parts[3], 16, n.paletteHash)) return std::nullopt;
    }
    return n;
}

} // namespace tstudio
