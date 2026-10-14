// SPDX-License-Identifier: GPL-3.0-or-later
// TextureStudio.exe --selftest: synthetic data only (no game content). Prints the first failures.
#include "core.h"
#include "gx.h"
#include "pack.h"

#include <cstdio>
#include <cstring>

namespace tstudio {
namespace {
int g_checks = 0, g_failures = 0;
#define CHECK(cond)                                                                       \
    do {                                                                                  \
        ++g_checks;                                                                       \
        if (!(cond)) {                                                                    \
            ++g_failures;                                                                 \
            std::fprintf(stderr, "selftest: %s:%d: %s\n", __FILE__, __LINE__, #cond);     \
        }                                                                                 \
    } while (0)

uint32_t Pixel(const Image& img, uint32_t x, uint32_t y) {  // 0xRRGGBBAA
    const uint8_t* p = &img.rgba[(static_cast<size_t>(y) * img.width + x) * 4];
    return static_cast<uint32_t>(p[0]) << 24 | p[1] << 16 | p[2] << 8 | p[3];
}

void TestGx() {
    CHECK(TextureBytes(8, 4, 1) == 32);       // I8: one 8x4 block
    CHECK(TextureBytes(4, 4, 9) == 32);       // C8 4x4 pads to one 8x4 block
    CHECK(TextureBytes(8, 8, 8) == 32);       // C4: one 8x8 block
    CHECK(TextureBytes(4, 4, 6) == 64);       // RGBA8: one 4x4 block, two 32-byte halves
    CHECK(TextureBytes(512, 512, 9) == 512 * 512);
    CHECK(TextureBytes(16, 16, 7) == 0);      // unknown format

    // I8 16x4 = two blocks side by side: block 0 holds x 0..7, block 1 holds x 8..15.
    std::vector<uint8_t> i8(64);
    for (size_t i = 0; i < i8.size(); ++i) i8[i] = static_cast<uint8_t>(i);
    const auto v = Values(i8, 16, 4, 1);
    CHECK(v.size() == 64);
    CHECK(v[0] == 0 && v[7] == 7 && v[8] == 32 && v[16] == 8);  // (8,0) starts block 1; (0,1) = 8
    const Image grey = Decode(i8, 16, 4, 1, {});
    CHECK(grey.width == 16 && grey.height == 4 && Pixel(grey, 8, 0) == 0x202020FFu);

    // C4 8x8: high nibble first.
    std::vector<uint8_t> c4(32, 0x12);
    const auto n = Values(c4, 8, 8, 8);
    CHECK(n[0] == 1 && n[1] == 2);
    const uint8_t pal[] = {0x80, 0x00, 0xFC, 0x00, 0x83, 0xE0};  // black, red, green (RGB5A3 opaque)
    const Image c4img = Decode(c4, 8, 8, 8, pal);
    CHECK(Pixel(c4img, 0, 0) == 0xFF0000FFu && Pixel(c4img, 1, 0) == 0x00FF00FFu);

    // RGB5A3: opaque white, and translucent 0x7F00 (a=7 -> 255, r=15 -> 255).
    const uint8_t rgb5a3[32] = {0xFF, 0xFF, 0x7F, 0x00};
    const Image c = Decode(rgb5a3, 4, 4, 5, {});
    CHECK(Pixel(c, 0, 0) == 0xFFFFFFFFu && Pixel(c, 1, 0) == 0xFF0000FFu);

    // RGBA8 4x4: AR pairs in the first 32 bytes, GB pairs in the next 32.
    std::vector<uint8_t> rgba8(64);
    rgba8[0] = 0x80; rgba8[1] = 0x11; rgba8[32] = 0x22; rgba8[33] = 0x33;
    CHECK(Pixel(Decode(rgba8, 4, 4, 6, {}), 0, 0) == 0x11223380u);

    CHECK(Decode(std::span<const uint8_t>(i8.data(), 10), 16, 4, 1, {}).Empty());  // short data
    CHECK(Decode(i8, 16, 4, 3, {}).Empty());                                        // IA8: not decodable
}
// A synthetic PACKWII: header, one layout C8 texture with its palette pointer, one model C4 texture
// whose palette follows it (+0x24), and one texture whose pixels run past the end (ignored).
std::vector<uint8_t> SyntheticPack() {
    std::vector<uint8_t> d(0x400, 0);
    std::memcpy(d.data(), "PACKWII ", 8);
    d[0x17] = 0x20;
    auto put16 = [&](size_t o, uint16_t v) { d[o] = v >> 8; d[o + 1] = v & 0xFF; };
    auto put32 = [&](size_t o, uint32_t v) { for (int i = 0; i < 4; ++i) d[o + i] = (v >> (24 - 8 * i)) & 0xFF; };
    // layout texture at 0x40: 8x4 C8, pixels at 0x100, palette (256 entries) at 0x200 via +0x2C
    put16(0x40, 8); put16(0x42, 4); put32(0x44, 9); put32(0x48, 0x40000100);
    put32(0x54, 1); put32(0x58, 1); put16(0x64, 256); put32(0x68, 2); put32(0x6C, 0x40000200);
    // model texture at 0x80: 8x8 C4 (type 0x84), pixels at 0x140, palette header at 0xA4 -> data 0x160
    put16(0x80, 8); put16(0x82, 8); d[0x84] = 0x84; put32(0x88, 0x40000140);
    put16(0xA4, 16); d[0xA8] = 0x81; put32(0xAC, 0x40000160);
    // broken texture at 0xC0: 1024x1024 RGBA8 whose pixels would end past the file
    put16(0xC0, 1024); put16(0xC2, 1024); put32(0xC4, 6); put32(0xC8, 0x40000180);
    return d;
}

void TestPack() {
    const auto d = SyntheticPack();
    const auto t = FindTextures(d);
    CHECK(t.size() == 2);
    if (t.size() != 2) return;
    CHECK(t[0].offset == 0x40 && t[0].format == 9 && t[0].data == 0x100 && !t[0].model);
    CHECK(t[0].paletteEntries == 256 && t[0].paletteData == 0x200 && !t[0].paletteByPosition);
    CHECK(t[1].offset == 0x80 && t[1].format == 8 && t[1].model);
    CHECK(t[1].paletteEntries == 16 && t[1].paletteData == 0x160 && t[1].paletteByPosition);
    CHECK(FindTextures(std::span<const uint8_t>(d.data(), 0x30)).empty());   // truncated
    std::vector<uint8_t> other(d);
    other[0] = 'X';
    CHECK(FindTextures(other).empty());                                       // not PACKWII
}
} // namespace

int RunSelftest() {
    TestGx();
    TestPack();
    std::printf("selftest %s (%d checks)\n", g_failures ? "FAILED" : "ok", g_checks);
    return g_failures ? 1 : 0;
}

} // namespace tstudio
