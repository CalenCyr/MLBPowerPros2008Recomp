// SPDX-License-Identifier: GPL-3.0-or-later
// TextureStudio.exe --selftest: synthetic data only (no game content). Prints the first failures.
#include "core.h"
#include "gx.h"

#include <cstdio>

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
} // namespace

int RunSelftest() {
    TestGx();
    std::printf("selftest %s (%d checks)\n", g_failures ? "FAILED" : "ok", g_checks);
    return g_failures ? 1 : 0;
}

} // namespace tstudio
