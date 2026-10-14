// SPDX-License-Identifier: GPL-3.0-or-later
#include "transfer.h"

#include "images.h"
#include "modfolder.h"

#include <cctype>
#include <map>
#include <set>

namespace tstudio {
namespace {
using Found = std::unordered_map<std::string, std::filesystem::path>;

std::string Lower(std::string s) {
    for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}

// Every name a replacement of this texture can have: its own, the any-palette "$" one, and the
// palette variants seen in captures.
std::vector<std::string> ReplacementNames(const CatalogTexture& t) {
    std::vector<std::string> names{t.name};
    if (t.key.hasPalette && !t.key.paletteWildcard) {
        ParsedName any = t.key;
        any.paletteWildcard = true;
        names.push_back(ReplacementName(any));
    }
    names.insert(names.end(), t.paletteVariants.begin(), t.paletteVariants.end());
    return names;
}

// Writes `img` under each of `names` (PNG, through a temporary file so a failed save never loses the
// previous replacement), then removes any other file of the `replaces` names still in the mod.
bool WriteNames(const Image& img, const std::filesystem::path& modRoot, const CatalogTexture& t,
                const std::vector<std::string>& names, const std::vector<std::string>& replaces, Found& found, std::string* error) {
    std::set<std::filesystem::path> written;
    for (const auto& name : names) {
        const auto target = ReplacementPath(modRoot, t, name);
        auto temp = target;
        temp += ".tmp";
        std::error_code ec;
        if (!SavePng(temp, img, error)) {
            std::filesystem::remove(temp, ec);
            return false;
        }
        std::filesystem::rename(temp, target, ec);
        if (ec) {  // some filesystems refuse to rename over an existing file
            ec.clear();
            std::filesystem::remove(target, ec);
            std::filesystem::rename(temp, target, ec);
        }
        if (ec) {
            std::filesystem::remove(temp, ec);
            if (error) *error = "No se puede escribir " + Utf8(target.filename()) + ".";
            return false;
        }
        written.insert(target);
    }
    for (const auto& name : replaces) {
        const auto it = found.find(name);
        if (it != found.end() && !written.count(it->second)) {
            std::error_code ec;
            std::filesystem::remove(it->second, ec);
            found.erase(it);
        }
    }
    for (const auto& name : names) found[name] = ReplacementPath(modRoot, t, name);
    return true;
}

ImportResult ImportNames(Catalog& c, int index, const std::filesystem::path& file, const std::filesystem::path& modRoot,
                         const std::vector<std::string>& names, const std::vector<std::string>& replaces, Found& found) {
    const CatalogTexture& t = c.Textures()[index];
    ImportResult r{Utf8(file.filename()), t.name};
    std::string error;
    const auto img = LoadImage(file, &error);
    if (!img) {
        r.message = error;
        return r;
    }
    const SizeCheck size = CheckReplacementSize(t.key.width, t.key.height, img->width, img->height);
    if (size == SizeCheck::WrongAspect || size == SizeCheck::TooLarge) {
        r.message = SizeCheckMessage(size);
        return r;
    }
    if (!WriteNames(*img, modRoot, t, names, replaces, found, &error)) {
        r.message = error;
        return r;
    }
    r.ok = true;
    r.message = size == SizeCheck::Ok ? "Importada." : SizeCheckMessage(size);
    return r;
}

// What an import onto texture t writes: the "$" name alone, or its own name plus the captured variants.
std::vector<std::string> NamesToWrite(const CatalogTexture& t, bool allPalettes) {
    if (allPalettes && t.key.hasPalette) {
        ParsedName any = t.key;
        any.paletteWildcard = true;
        return {ReplacementName(any)};
    }
    std::vector<std::string> names{t.name};
    names.insert(names.end(), t.paletteVariants.begin(), t.paletteVariants.end());
    return names;
}
} // namespace

std::vector<std::filesystem::path> ReplacementsOf(const CatalogTexture& t, const Found& found) {
    std::vector<std::filesystem::path> out;
    for (const auto& name : ReplacementNames(t))
        if (const auto it = found.find(name); it != found.end()) out.push_back(it->second);
    return out;
}

size_t RemoveReplacements(const CatalogTexture& t, const Found& found) {
    size_t n = 0;
    for (const auto& f : ReplacementsOf(t, found)) {
        std::error_code ec;
        n += std::filesystem::remove(f, ec) ? 1 : 0;
    }
    return n;
}

ImportResult ImportOne(Catalog& c, int index, const std::filesystem::path& file, const std::filesystem::path& modRoot,
                       bool allPalettes) {
    Found found = FindReplacements(modRoot);
    const CatalogTexture& t = c.Textures()[index];
    return ImportNames(c, index, file, modRoot, NamesToWrite(t, allPalettes), ReplacementNames(t), found);
}

std::vector<ImportResult> ImportFolder(Catalog& c, const std::filesystem::path& folder, const std::filesystem::path& modRoot,
                                       Progress* progress) {
    std::vector<ImportResult> out;
    std::map<std::string, std::filesystem::path> byName;  // stem -> chosen file (.png wins)
    std::error_code ec;
    for (std::filesystem::recursive_directory_iterator it(folder, ec), end; !ec && it != end; it.increment(ec)) {
        if (!it->is_regular_file(ec)) continue;
        const std::string ext = Lower(Utf8(it->path().extension()));
        if (ext != ".png" && ext != ".dds") continue;
        const std::string stem = Utf8(it->path().stem());
        if (!ParseName(stem)) {
            out.push_back({Utf8(it->path().filename()), "", false, "Nombre no reconocido (debe empezar por tex1_)."});
            continue;
        }
        auto [pos, inserted] = byName.emplace(stem, it->path());
        if (inserted) continue;
        const bool newIsPng = ext == ".png";
        const auto loser = newIsPng ? pos->second : it->path();
        if (newIsPng) pos->second = it->path();
        out.push_back({Utf8(loser.filename()), stem, false, "Repetido: se usó el .png."});
    }
    if (progress) progress->total = byName.size();
    Found found = FindReplacements(modRoot);  // scanned once for the whole folder
    for (const auto& [stem, file] : byName) {
        const ParsedName name = *ParseName(stem);
        if (const int i = c.Find(stem); i >= 0) {
            const CatalogTexture& t = c.Textures()[i];
            out.push_back(ImportNames(c, i, file, modRoot, NamesToWrite(t, false), ReplacementNames(t), found));
        } else if (const int j = name.hasPalette ? c.FindTexture(name) : -1; j >= 0) {
            // "$" (every palette) or a palette variant the game showed: keep the name it was given.
            const auto replaces = name.paletteWildcard ? ReplacementNames(c.Textures()[j]) : std::vector<std::string>{stem};
            out.push_back(ImportNames(c, j, file, modRoot, {stem}, replaces, found));
        } else {
            out.push_back({Utf8(file.filename()), stem, false, "No corresponde a ninguna textura del juego."});
        }
        if (progress) ++progress->done;
    }
    return out;
}

size_t Export(Catalog& c, const std::vector<int>& textures, const std::filesystem::path& out, std::vector<std::string>* problems,
              Progress* progress) {
    if (progress) progress->total = textures.size();
    size_t written = 0;
    for (int i : textures) {
        const CatalogTexture& t = c.Textures()[i];
        const Image img = c.Original(t);
        std::string error;
        if (img.Empty()) {
            if (problems) problems->push_back(t.name + ": formato no soportado para exportar");
        } else {
            const auto file = out / PathFromUtf8(t.group) / PathFromUtf8(t.subgroup) / PathFromUtf8(t.name + ".png");
            if (SavePng(file, img, &error)) ++written;
            else if (problems) problems->push_back(t.name + ": " + error);
        }
        if (progress) ++progress->done;
    }
    return written;
}

} // namespace tstudio
