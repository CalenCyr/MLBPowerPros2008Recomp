// SPDX-License-Identifier: GPL-3.0-or-later
// Pack name -> readable group and subgroup for the Studio's category tree. Names are only guesses from
// the pack names (no game data); unknown packs fall into "Otros".
#pragma once
#include <string>
#include <string_view>
#include <vector>

namespace tstudio {
struct Category { std::string group, subgroup; };
Category Categorize(std::string_view packName);   // "stadium_nyy.pack" -> {"Estadios", "Yankees (NYY)"}
const std::vector<std::string>& GroupOrder();      // display order of the groups
// The group and subgroup keys above stay Spanish (folders and lookups use them); these are what the UI
// shows in the current language. Unknown keys (pack-derived names, team names) are shown as they are.
const char* GroupLabelEn(std::string_view group);  // group keys and "Todo"; nullptr for anything else
std::string GroupLabel(const std::string& group);
std::string SubgroupLabel(const std::string& subgroup);
} // namespace tstudio
