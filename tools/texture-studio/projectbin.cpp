// SPDX-License-Identifier: GPL-3.0-or-later
#include "projectbin.h"

#include <fstream>

namespace tstudio {

std::optional<std::vector<ProjectEntry>> ReadProjectIndex(const std::filesystem::path& file, std::string* error) {
    auto fail = [&](const char* why) -> std::optional<std::vector<ProjectEntry>> {
        if (error) *error = why;
        return std::nullopt;
    };
    std::ifstream f(file, std::ios::binary);
    if (!f) return fail("No se puede abrir project.bin.");
    std::vector<uint8_t> head(0x40);
    if (!f.read(reinterpret_cast<char*>(head.data()), head.size())) return fail("project.bin está incompleto.");
    const uint32_t records = Be32(head, 0x14), order = Be32(head, 0x28), names = Be32(head, 0x2C), data = Be32(head, 0x34);
    if (!(0x40 <= records && records < order && order < names && names < data && data <= 0x1000000))
        return fail("project.bin no tiene el formato esperado.");
    std::vector<uint8_t> h(data);
    f.seekg(0);
    if (!f.read(reinterpret_cast<char*>(h.data()), h.size())) return fail("project.bin está incompleto.");
    const uint32_t count = (order - records) / 0x1C;
    std::vector<ProjectEntry> out;
    for (uint32_t i = 1; order + 8ull * (i + 1) <= names; ++i) {
        const uint32_t index = Be32(h, order + 8 * i), sector = Be32(h, order + 8 * i + 4);
        if (index == 0 && sector == 0) break;
        if (index >= count) return fail("project.bin no tiene el formato esperado.");
        const size_t rec = records + static_cast<size_t>(index) * 0x1C;
        const size_t nameStart = static_cast<size_t>(names) + Be32(h, rec + 4);
        size_t nameEnd = nameStart;
        while (nameEnd < h.size() && h[nameEnd] != 0) ++nameEnd;
        if (nameEnd >= h.size()) return fail("project.bin no tiene el formato esperado.");
        std::string name(h.begin() + nameStart, h.begin() + nameEnd);
        if (!name.empty() && name.front() == '/') name.erase(0, 1);
        out.push_back({std::move(name), data + static_cast<uint64_t>(sector) * 0x800, Be32(h, rec + 24)});
    }
    return out;
}

std::vector<uint8_t> ReadEntry(const std::filesystem::path& file, const ProjectEntry& entry) {
    // Sizes come from the file itself: never allocate past its end (a corrupt record would ask for 4 GB).
    std::error_code ec;
    const uint64_t fileSize = std::filesystem::file_size(file, ec);
    if (ec || entry.offset > fileSize || entry.size > fileSize - entry.offset) return {};
    std::ifstream f(file, std::ios::binary);
    std::vector<uint8_t> out(entry.size);
    f.seekg(static_cast<std::streamoff>(entry.offset));
    if (!f || !f.read(reinterpret_cast<char*>(out.data()), out.size())) return {};
    return out;
}

} // namespace tstudio
