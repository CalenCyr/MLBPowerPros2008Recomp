// SPDX-License-Identifier: GPL-3.0-or-later
#include "transfer.h"

#include "images.h"
#include "modfolder.h"

#include <cctype>
#include <map>

namespace tstudio {
namespace {
std::string Lower(std::string s) {
    for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}
bool WriteReplacement(const Image& img, const std::filesystem::path& modRoot, const CatalogTexture& t, const std::string& name,
                      std::string* error) {
    // One file per name inside the mod: drop any earlier copy (other folder, or .dds) first.
    const auto existing = FindReplacements(modRoot);
    if (const auto it = existing.find(name); it != existing.end()) {
        std::error_code ec;
        std::filesystem::remove(it->second, ec);
    }
    return SavePng(ReplacementPath(modRoot, t, name), img, error);
}
} // namespace

ImportResult ImportOne(Catalog& c, int index, const std::filesystem::path& file, const std::filesystem::path& modRoot,
                       bool allPalettes) {
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
    std::vector<std::string> names;
    if (allPalettes && t.key.hasPalette) {
        ParsedName any = t.key;
        any.paletteWildcard = true;
        names.push_back(ReplacementName(any));
    } else {
        names.push_back(t.name);
        names.insert(names.end(), t.paletteVariants.begin(), t.paletteVariants.end());
    }
    for (const auto& name : names) {
        if (!WriteReplacement(*img, modRoot, t, name, &error)) {
            r.message = error;
            return r;
        }
    }
    r.ok = true;
    r.message = size == SizeCheck::Ok ? "Importada." : SizeCheckMessage(size);
    return r;
}

std::vector<ImportResult> ImportFolder(Catalog& c, const std::filesystem::path& folder, const std::filesystem::path& modRoot) {
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
    for (const auto& [stem, file] : byName) {
        const ParsedName name = *ParseName(stem);
        int i = c.Find(stem);
        if (i < 0 && name.paletteWildcard) i = c.FindTexture(name);  // "$": the texture with any palette
        if (i < 0) {
            out.push_back({Utf8(file.filename()), stem, false, "No corresponde a ninguna textura del juego."});
            continue;
        }
        out.push_back(ImportOne(c, i, file, modRoot, name.paletteWildcard));
    }
    return out;
}

size_t Export(Catalog& c, const std::vector<int>& textures, const std::filesystem::path& out, std::vector<std::string>* problems) {
    size_t written = 0;
    for (int i : textures) {
        const CatalogTexture& t = c.Textures()[i];
        const Image img = c.Original(t);
        std::string error;
        if (img.Empty()) {
            if (problems) problems->push_back(t.name + ": formato no soportado para exportar");
            continue;
        }
        const auto file = out / PathFromUtf8(t.group) / PathFromUtf8(t.subgroup) / PathFromUtf8(t.name + ".png");
        if (SavePng(file, img, &error)) ++written;
        else if (problems) problems->push_back(t.name + ": " + error);
    }
    return written;
}

} // namespace tstudio
