// SPDX-License-Identifier: GPL-3.0-or-later
// PROJECT.BIN index (tools/projectbin.py has the layout).
#pragma once
#include "core.h"
#include <optional>

namespace tstudio {
struct ProjectEntry { std::string name; uint64_t offset = 0; uint32_t size = 0; };  // name without the leading '/'
std::optional<std::vector<ProjectEntry>> ReadProjectIndex(const std::filesystem::path& file, std::string* error);
std::vector<uint8_t> ReadEntry(const std::filesystem::path& file, const ProjectEntry& entry);  // empty on error
} // namespace tstudio
