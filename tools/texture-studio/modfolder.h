// SPDX-License-Identifier: GPL-3.0-or-later
// Player mods: mods/<name>/mod.toml + textures/<group>/<subgroup>/tex1_....png, and a stored .zip to share them.
#pragma once
#include "catalog.h"

#include <optional>
#include <unordered_map>

namespace tstudio {
struct ModInfo { std::string id; std::filesystem::path root; bool enabled = false; };
std::optional<std::string> ValidModName(std::string_view name, std::string* error);   // trimmed name or error
std::vector<ModInfo> ListMods(const std::filesystem::path& modsDir, const std::vector<std::string>& enabled);
bool CreateMod(const std::filesystem::path& modsDir, const std::string& name, std::string* error);
std::filesystem::path ReplacementPath(const std::filesystem::path& modRoot, const CatalogTexture& t, std::string_view name);
std::unordered_map<std::string, std::filesystem::path> FindReplacements(const std::filesystem::path& modRoot);  // stem -> file
bool WriteZip(const std::filesystem::path& modRoot, const std::filesystem::path& zip, std::string* error);
} // namespace tstudio
