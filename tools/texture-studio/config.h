// SPDX-License-Identifier: GPL-3.0-or-later
// Minimal line-based editing of the game's Config.toml (same rules as the runtime's WriteSetting).
#pragma once
#include "core.h"
#include <optional>

namespace tstudio {
std::optional<std::string> ReadSetting(const std::filesystem::path& config, std::string_view section, std::string_view key);  // unquoted
std::vector<std::string> ReadEnabledMods(const std::filesystem::path& config);
bool SetModEnabled(const std::filesystem::path& config, const std::string& id, bool enabled);
} // namespace tstudio
