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
} // namespace tstudio
