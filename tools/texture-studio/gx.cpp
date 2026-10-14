// SPDX-License-Identifier: GPL-3.0-or-later
#include "gx.h"

#include <array>
#include <cstring>
#include <optional>

namespace tstudio {
namespace {
struct Block { uint32_t w, h, bpp; };

std::optional<Block> BlockOf(uint32_t fmt) {
    switch (fmt) {
    case 0: case 8: case 14: return Block{8, 8, 4};
    case 1: case 2: case 9: return Block{8, 4, 8};
    case 3: case 4: case 5: case 10: return Block{4, 4, 16};
    case 6: return Block{4, 4, 32};
    default: return std::nullopt;
    }
}

std::array<uint8_t, 4> FromRgb5a3(uint16_t v) {
    if (v & 0x8000)
        return {static_cast<uint8_t>(((v >> 10) & 31) * 255 / 31), static_cast<uint8_t>(((v >> 5) & 31) * 255 / 31),
                static_cast<uint8_t>((v & 31) * 255 / 31), 255};
    return {static_cast<uint8_t>(((v >> 8) & 15) * 17), static_cast<uint8_t>(((v >> 4) & 15) * 17),
            static_cast<uint8_t>((v & 15) * 17), static_cast<uint8_t>(((v >> 12) & 7) * 255 / 7)};
}
} // namespace

bool IsKnownFormat(uint32_t fmt) { return BlockOf(fmt).has_value(); }
bool IsDecodable(uint32_t fmt) { return fmt == 0 || fmt == 1 || fmt == 5 || fmt == 6 || fmt == 8 || fmt == 9; }
bool IsPaletted(uint32_t fmt) { return fmt == 8 || fmt == 9 || fmt == 10; }

const char* FormatName(uint32_t fmt) {
    switch (fmt) {
    case 0: return "I4"; case 1: return "I8"; case 2: return "IA4"; case 3: return "IA8";
    case 4: return "RGB565"; case 5: return "RGB5A3"; case 6: return "RGBA8"; case 8: return "C4";
    case 9: return "C8"; case 10: return "C14X2"; case 14: return "CMPR"; default: return "?";
    }
}

uint32_t TextureBytes(uint32_t w, uint32_t h, uint32_t fmt) {
    const auto b = BlockOf(fmt);
    if (!b) return 0;
    const uint64_t pw = (w + b->w - 1) / b->w * b->w, ph = (h + b->h - 1) / b->h * b->h;
    return static_cast<uint32_t>(pw * ph * b->bpp / 8);
}

std::vector<uint16_t> Values(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt) {
    const auto b = BlockOf(fmt);
    if (!b || fmt == 6 || px.size() < TextureBytes(w, h, fmt)) return {};
    const uint32_t blocksX = (w + b->w - 1) / b->w;
    std::vector<uint16_t> out(static_cast<size_t>(w) * h);
    for (uint32_t y = 0; y < h; ++y) {
        for (uint32_t x = 0; x < w; ++x) {
            const size_t block = static_cast<size_t>(y / b->h) * blocksX + x / b->w;
            const size_t i = block * b->w * b->h + (y % b->h) * b->w + x % b->w;  // texel in data order
            uint16_t v;
            if (b->bpp == 4) v = (i & 1) ? px[i / 2] & 15 : px[i / 2] >> 4;
            else if (b->bpp == 8) v = px[i];
            else v = static_cast<uint16_t>(px[2 * i] << 8 | px[2 * i + 1]);
            out[static_cast<size_t>(y) * w + x] = v;
        }
    }
    return out;
}

Image Decode(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt, std::span<const uint8_t> paletteBE) {
    Image img;
    if (!IsDecodable(fmt) || w == 0 || h == 0 || px.size() < TextureBytes(w, h, fmt)) return img;
    img.width = w;
    img.height = h;
    img.rgba.resize(static_cast<size_t>(w) * h * 4);
    auto put = [&](size_t i, std::array<uint8_t, 4> c) { std::memcpy(&img.rgba[i * 4], c.data(), 4); };
    if (fmt == 6) {
        const uint32_t blocksX = (w + 3) / 4;
        for (uint32_t y = 0; y < h; ++y) {
            for (uint32_t x = 0; x < w; ++x) {
                const size_t base = (static_cast<size_t>(y / 4) * blocksX + x / 4) * 64;
                const size_t t = (y % 4) * 4 + x % 4;
                put(static_cast<size_t>(y) * w + x, {px[base + 2 * t + 1], px[base + 32 + 2 * t],
                                                     px[base + 33 + 2 * t], px[base + 2 * t]});
            }
        }
        return img;
    }
    const auto v = Values(px, w, h, fmt);
    const size_t entries = paletteBE.size() / 2;
    for (size_t i = 0; i < v.size(); ++i) {
        const uint16_t value = v[i];
        if (fmt == 5) {
            put(i, FromRgb5a3(value));
        } else if (fmt == 0 || fmt == 1) {
            const uint8_t g = static_cast<uint8_t>(fmt == 0 ? value * 17 : value);
            put(i, {g, g, g, 255});
        } else if (entries == 0) {  // C4/C8 without a known palette: indices in grey
            const uint8_t g = static_cast<uint8_t>(fmt == 8 ? value * 17 : value);
            put(i, {g, g, g, 255});
        } else if (value < entries) {
            put(i, FromRgb5a3(static_cast<uint16_t>(paletteBE[2 * value] << 8 | paletteBE[2 * value + 1])));
        } else {
            put(i, {0, 0, 0, 0});
        }
    }
    return img;
}

} // namespace tstudio
