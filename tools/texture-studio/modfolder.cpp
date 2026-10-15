// SPDX-License-Identifier: GPL-3.0-or-later
#include "modfolder.h"

#include "lang.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <fstream>
#include <iterator>

namespace tstudio {
namespace {
std::string Trim(std::string_view s) {
    const size_t a = s.find_first_not_of(" \t"), b = s.find_last_not_of(" \t");
    return a == std::string_view::npos ? std::string() : std::string(s.substr(a, b - a + 1));
}
// Folder-safe version of a category name.
std::string Safe(std::string_view s) {
    std::string out;
    for (char c : s)
        out += std::string_view("<>:\"/\\|?*").find(c) == std::string_view::npos && static_cast<unsigned char>(c) >= 32 ? c : '_';
    return out.empty() ? "_" : out;
}
uint32_t Crc32(const std::string& data) {
    static const auto table = [] {
        std::array<uint32_t, 256> t{};
        for (uint32_t i = 0; i < 256; ++i) {
            uint32_t c = i;
            for (int k = 0; k < 8; ++k) c = c & 1 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            t[i] = c;
        }
        return t;
    }();
    uint32_t c = 0xFFFFFFFFu;
    for (unsigned char b : data) c = table[(c ^ b) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFFu;
}
bool IsReplacement(const std::filesystem::path& p) {
    std::string ext = Utf8(p.extension());
    for (char& c : ext) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return (ext == ".png" || ext == ".dds") && Utf8(p.filename()).rfind("tex1_", 0) == 0;
}
std::string Generic(const std::filesystem::path& p) {
    const auto s = p.generic_u8string();
    return {s.begin(), s.end()};
}
} // namespace

std::optional<std::string> ValidModName(std::string_view raw, std::string* error) {
    const std::string name = Trim(raw);
    auto fail = [&](const char* why) -> std::optional<std::string> {
        if (error) *error = why;
        return std::nullopt;
    };
    if (name.empty()) return fail(Tr("Escribe un nombre para el mod.", "Type a name for the mod."));
    if (name.size() > 60) return fail(Tr("El nombre es demasiado largo (máximo 60 caracteres).", "The name is too long (60 characters at most)."));
    for (char c : name)
        if (static_cast<unsigned char>(c) < 32 || std::string_view("<>:\"/\\|?*").find(c) != std::string_view::npos)
            return fail(Tr("El nombre no puede llevar < > : \" / \\ | ? *", "The name can't contain < > : \" / \\ | ? *"));
    if (name.back() == '.') return fail(Tr("El nombre no puede terminar en punto.", "The name can't end with a period."));
    std::string upper = Trim(name.substr(0, name.find('.')));
    for (char& c : upper) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    const bool numbered = upper.size() == 4 && (upper.starts_with("COM") || upper.starts_with("LPT")) && upper[3] >= '1' && upper[3] <= '9';
    if (upper == "CON" || upper == "PRN" || upper == "AUX" || upper == "NUL" || numbered)
        return fail(Tr("Windows no permite ese nombre de carpeta.", "Windows doesn't allow that folder name."));
    return name;
}

std::vector<ModInfo> ListMods(const std::filesystem::path& modsDir, const std::vector<std::string>& enabled) {
    std::vector<ModInfo> out;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(modsDir, ec)) {
        if (!e.is_directory(ec)) continue;
        const std::string id = Utf8(e.path().filename());
        out.push_back({id, e.path(), std::find(enabled.begin(), enabled.end(), id) != enabled.end()});
    }
    std::sort(out.begin(), out.end(), [](const ModInfo& a, const ModInfo& b) { return a.id < b.id; });
    return out;
}

bool CreateMod(const std::filesystem::path& modsDir, const std::string& rawName, std::string* error) {
    const auto name = ValidModName(rawName, error);
    if (!name) return false;
    const auto root = modsDir / PathFromUtf8(*name);
    std::error_code ec;
    if (std::filesystem::exists(root, ec)) {
        if (error) *error = Tr("Ya existe un mod con ese nombre.", "A mod with that name already exists.");
        return false;
    }
    std::filesystem::create_directories(root / "textures", ec);
    std::ofstream toml(root / "mod.toml", std::ios::binary);
    std::string escaped;
    for (char c : *name) {
        if (c == '"' || c == '\\') escaped += '\\';
        escaped += c;
    }
    toml << "name = \"" << escaped << "\"\r\nversion = \"1\"\r\n"
         << "description = \"Texturas creadas con Power Pros Wii 2008 Texture Studio.\"\r\n";
    if (ec || !toml) {
        if (error) *error = Tr("No se puede crear la carpeta del mod (¿permisos?).", "Can't create the mod folder (permissions?).");
        return false;
    }
    return true;
}

std::filesystem::path CategoryPath(const CatalogTexture& t) { return PathFromUtf8(Safe(t.group)) / PathFromUtf8(Safe(t.subgroup)); }

std::filesystem::path ReplacementPath(const std::filesystem::path& modRoot, const CatalogTexture& t, std::string_view name) {
    return modRoot / "textures" / CategoryPath(t) / PathFromUtf8(std::string(name) + ".png");
}

std::unordered_map<std::string, std::filesystem::path> FindReplacements(const std::filesystem::path& modRoot) {
    std::unordered_map<std::string, std::filesystem::path> out;
    std::error_code ec;
    for (std::filesystem::recursive_directory_iterator it(modRoot / "textures", ec), end; !ec && it != end; it.increment(ec))
        if (it->is_regular_file(ec) && IsReplacement(it->path())) out.emplace(Utf8(it->path().stem()), it->path());
    return out;
}

bool WriteZip(const std::filesystem::path& modRoot, const std::filesystem::path& zip, std::string* error) {
    std::vector<std::pair<std::string, std::filesystem::path>> files;  // name in the zip -> file
    const std::string top = Utf8(modRoot.filename());
    std::error_code ec;
    if (std::filesystem::exists(modRoot / "mod.toml", ec)) files.emplace_back(top + "/mod.toml", modRoot / "mod.toml");
    for (std::filesystem::recursive_directory_iterator it(modRoot / "textures", ec), end; !ec && it != end; it.increment(ec))
        if (it->is_regular_file(ec) && IsReplacement(it->path()))
            files.emplace_back(top + "/" + Generic(it->path().lexically_relative(modRoot)), it->path());
    std::ofstream out(zip, std::ios::binary | std::ios::trunc);
    auto u16 = [](std::string& s, uint16_t v) { s += static_cast<char>(v & 0xFF); s += static_cast<char>(v >> 8); };
    auto u32 = [&](std::string& s, uint32_t v) { u16(s, v & 0xFFFF); u16(s, static_cast<uint16_t>(v >> 16)); };
    std::string central;
    uint64_t offset = 0;
    for (const auto& [name, path] : files) {
        std::ifstream in(path, std::ios::binary);
        const std::string data((std::istreambuf_iterator<char>(in)), {});
        if (offset + data.size() > 0xFFFFFFF0ull) {
            if (error) *error = Tr("El mod pasa de 4 GB: no cabe en un .zip simple.", "The mod is over 4 GB: it doesn't fit in a simple .zip.");
            return false;
        }
        const uint32_t crc = Crc32(data);
        const auto size = static_cast<uint32_t>(data.size());
        std::string local("PK\x03\x04", 4);
        u16(local, 20); u16(local, 0x0800); u16(local, 0); u16(local, 0); u16(local, 0x21);  // UTF-8 names, stored
        u32(local, crc); u32(local, size); u32(local, size);
        u16(local, static_cast<uint16_t>(name.size())); u16(local, 0);
        out << local << name << data;
        std::string c("PK\x01\x02", 4);
        u16(c, 20); u16(c, 20); u16(c, 0x0800); u16(c, 0); u16(c, 0); u16(c, 0x21);
        u32(c, crc); u32(c, size); u32(c, size);
        u16(c, static_cast<uint16_t>(name.size())); u16(c, 0); u16(c, 0); u16(c, 0); u16(c, 0); u32(c, 0);
        u32(c, static_cast<uint32_t>(offset));
        central += c + name;
        offset += local.size() + name.size() + data.size();
    }
    std::string end("PK\x05\x06", 4);
    u16(end, 0); u16(end, 0);
    u16(end, static_cast<uint16_t>(files.size())); u16(end, static_cast<uint16_t>(files.size()));
    u32(end, static_cast<uint32_t>(central.size())); u32(end, static_cast<uint32_t>(offset)); u16(end, 0);
    out << central << end;
    if (!out) {
        if (error) *error = Tr("No se puede escribir el .zip.", "Can't write the .zip.");
        return false;
    }
    return true;
}

} // namespace tstudio
