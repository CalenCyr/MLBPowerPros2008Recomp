// SPDX-License-Identifier: GPL-3.0-or-later
// Types and byte helpers shared by the Texture Studio core (no UI, no game data).
#pragma once
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace tstudio {

struct Image {
    uint32_t width = 0, height = 0;
    std::vector<uint8_t> rgba;  // width * height * 4, rows top to bottom
    bool Empty() const { return rgba.empty(); }
};

inline uint16_t Be16(std::span<const uint8_t> d, size_t o) {
    return o + 2 <= d.size() ? static_cast<uint16_t>(d[o] << 8 | d[o + 1]) : 0;
}
inline uint32_t Be32(std::span<const uint8_t> d, size_t o) {
    return o + 4 <= d.size() ? static_cast<uint32_t>(d[o]) << 24 | d[o + 1] << 16 | d[o + 2] << 8 | d[o + 3] : 0;
}
inline std::string Utf8(const std::filesystem::path& p) {
    const auto s = p.u8string();
    return {s.begin(), s.end()};
}
inline std::filesystem::path PathFromUtf8(std::string_view s) {
    return std::filesystem::path(std::u8string(s.begin(), s.end()));
}

} // namespace tstudio
