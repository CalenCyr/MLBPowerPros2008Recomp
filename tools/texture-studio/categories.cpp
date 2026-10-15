// SPDX-License-Identifier: GPL-3.0-or-later
#include "categories.h"

#include "lang.h"

#include <cctype>
#include <cstdlib>
#include <map>

namespace tstudio {
namespace {
// MLB teams of 2008 by the codes the packs use (stadium packs use "oka" and "st").
const std::map<std::string, std::string>& Teams() {
    static const std::map<std::string, std::string> teams{
        {"ARI", "Diamondbacks"}, {"ATL", "Braves"}, {"BAL", "Orioles"}, {"BOS", "Red Sox"}, {"CHC", "Cubs"},
        {"CIN", "Reds"}, {"CLE", "Indians"}, {"COL", "Rockies"}, {"CWS", "White Sox"}, {"DET", "Tigers"},
        {"FLA", "Marlins"}, {"HOU", "Astros"}, {"KC", "Royals"}, {"LAA", "Angels"}, {"LAD", "Dodgers"},
        {"MIL", "Brewers"}, {"MIN", "Twins"}, {"NYM", "Mets"}, {"NYY", "Yankees"}, {"OAK", "Athletics"},
        {"PHI", "Phillies"}, {"PIT", "Pirates"}, {"SD", "Padres"}, {"SEA", "Mariners"}, {"SF", "Giants"},
        {"STL", "Cardinals"}, {"TB", "Rays"}, {"TEX", "Rangers"}, {"TOR", "Blue Jays"}, {"WSH", "Nationals"}};
    return teams;
}

std::string Team(std::string code) {
    for (char& c : code) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    if (code == "OKA") code = "OAK";
    if (code == "ST") code = "STL";
    const auto it = Teams().find(code);
    return it == Teams().end() ? code : it->second + " (" + code + ")";
}

bool Starts(std::string_view s, std::string_view p) { return s.substr(0, p.size()) == p; }
} // namespace

const std::vector<std::string>& GroupOrder() {
    static const std::vector<std::string> order{"Menús", "Estadios", "Uniformes", "Cartas de jugador", "Logos",
                                                "Nombres de equipo", "Caras", "MLB Life", "Temporada", "Success",
                                                "Modelos", "Otros", "Solo vistas en juego"};
    return order;
}

Category Categorize(std::string_view packName) {
    const std::string stem(packName.substr(0, packName.rfind('.')));
    if (Starts(stem, "stadium_")) {
        std::string rest = stem.substr(8);
        if (rest.size() > 3 && rest.ends_with("tbl")) rest.resize(rest.size() - 3);
        if (Starts(rest, "sky_")) return {"Estadios", "Cielos"};
        if (Starts(rest, "org")) return {"Estadios", "Original " + std::to_string(std::atoi(rest.c_str() + 3))};
        if (Starts(rest, "bullpen")) return {"Estadios", "Bullpen"};
        static const std::map<std::string, std::string> special{
            {"common", "Común"}, {"season", "Temporada"}, {"hanabi", "Fuegos artificiales"}, {"debug", "Depuración"},
            {"ml01", "MLB Life"}};
        if (const auto it = special.find(rest); it != special.end()) return {"Estadios", it->second};
        return {"Estadios", Team(rest)};
    }
    if (Starts(stem, "PWM_mdl_uniform_")) {  // PWM_mdl_uniform_MLB_CHC_00 / PWM_mdl_uniform_AAA_ARI_AAA_01
        const std::string rest = stem.substr(16);
        const size_t a = rest.find('_'), b = rest.find('_', a + 1);
        const std::string league = rest.substr(0, a), code = rest.substr(a + 1, b - a - 1);
        return {"Uniformes", Team(code) + (league == "MLB" ? "" : " " + league)};
    }
    if (Starts(stem, "env_player_card_")) {  // env_player_card_03NYY_YANKEES
        const std::string rest = stem.substr(16);
        size_t i = 0;
        while (i < rest.size() && std::isdigit(static_cast<unsigned char>(rest[i]))) ++i;
        return {"Cartas de jugador", Team(rest.substr(i, rest.find('_', i) - i))};
    }
    if (Starts(stem, "env_playercard_")) return {"Cartas de jugador", "Datos"};
    for (const char* logo : {"env_teamlogo", "env_team_logo", "team_logo", "env_arrange_logo", "env_scs_teamlogo", "env_mii_teamlogo"})
        if (Starts(stem, logo)) return {"Logos", Starts(stem, "env_") ? stem.substr(4) : stem};
    if (Starts(stem, "env_teamname") || Starts(stem, "env_mii_teamname")) return {"Nombres de equipo", stem.substr(4)};
    if (Starts(stem, "mylife_")) return {"MLB Life", stem.substr(7)};
    if (Starts(stem, "season_")) return {"Temporada", stem.substr(7)};
    if (Starts(stem, "Scs")) return {"Success", stem};
    if (Starts(stem, "PWM_mdl_face")) return {"Caras", stem.substr(8)};
    if (Starts(stem, "PWM_")) return {"Modelos", stem.substr(4)};
    if (Starts(stem, "env_")) {
        static const std::map<std::string, std::string> menus{
            {"mainmenu", "Menú principal"}, {"title_logo", "Título"}, {"common", "Común"}, {"credit", "Créditos"},
            {"vs", "Enfrentamiento"}, {"stadium_menu", "Selección de estadio"}};
        const std::string rest = stem.substr(4);
        if (const auto it = menus.find(rest); it != menus.end()) return {"Menús", it->second};
        return {"Menús", rest};
    }
    return {"Otros", stem};
}

const char* GroupLabelEn(std::string_view group) {
    static const std::map<std::string_view, const char*> labels{
        {"Todo", "All"}, {"Menús", "Menus"}, {"Estadios", "Stadiums"}, {"Uniformes", "Uniforms"},
        {"Cartas de jugador", "Player cards"}, {"Logos", "Logos"}, {"Nombres de equipo", "Team names"}, {"Caras", "Faces"},
        {"MLB Life", "MLB Life"}, {"Temporada", "Season"}, {"Success", "Success"}, {"Modelos", "Models"}, {"Otros", "Other"},
        {"Solo vistas en juego", "Seen in game only"}};
    const auto it = labels.find(group);
    return it == labels.end() ? nullptr : it->second;
}

std::string GroupLabel(const std::string& group) {
    const char* en = GroupLabelEn(group);
    return en ? Tr(group.c_str(), en) : group;
}

std::string SubgroupLabel(const std::string& subgroup) {
    if (power_pros_ui::g_lang != power_pros_ui::Lang::En) return subgroup;
    // The Spanish subgroups Categorize and Catalog::AddCapture make; everything else is a name already.
    static const std::map<std::string_view, const char*> labels{
        {"Cielos", "Skies"}, {"Común", "Common"}, {"Temporada", "Season"}, {"Fuegos artificiales", "Fireworks"},
        {"Depuración", "Debug"}, {"Datos", "Data"}, {"Menú principal", "Main menu"}, {"Título", "Title"},
        {"Créditos", "Credits"}, {"Enfrentamiento", "Matchup"}, {"Selección de estadio", "Stadium select"}};
    if (const auto it = labels.find(subgroup); it != labels.end()) return it->second;
    if (Starts(subgroup, "Sesión ")) return "Session " + subgroup.substr(std::string_view("Sesión ").size());
    return subgroup;
}

} // namespace tstudio
