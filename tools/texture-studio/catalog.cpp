// SPDX-License-Identifier: GPL-3.0-or-later
#include "catalog.h"

#include "gx.h"
#include "images.h"
#include "pack.h"

#include <algorithm>

namespace tstudio {
namespace {
std::string TextureKey(const ParsedName& n) {
    ParsedName k = n;
    k.hasPalette = false;
    return ReplacementName(k);
}
} // namespace

bool IsVideoFrame(const ParsedName& n) {
    return n.format == 1 && ((n.width == 512 && n.height == 448) || (n.width == 256 && n.height == 224));
}

const std::vector<CatalogTexture>& Catalog::Textures() const { return textures_; }
const std::vector<ProjectEntry>& Catalog::Entries() const { return entries_; }

int Catalog::Find(std::string_view name) const {
    const auto it = byName_.find(std::string(name));
    return it == byName_.end() ? -1 : it->second;
}

int Catalog::FindTexture(const ParsedName& n) const {
    const auto it = byTexture_.find(TextureKey(n));
    return it == byTexture_.end() ? -1 : it->second;
}

bool Catalog::Build(const std::filesystem::path& projectBin, std::atomic<float>* progress, std::string* error) {
    auto index = ReadProjectIndex(projectBin, error);
    if (!index) return false;
    project_ = projectBin;
    entries_ = std::move(*index);
    textures_.clear();
    byName_.clear();
    byTexture_.clear();
    for (uint32_t e = 0; e < entries_.size(); ++e) {
        if (progress) *progress = static_cast<float>(e) / static_cast<float>(entries_.size());
        if (!entries_[e].name.ends_with(".pack")) continue;
        const std::vector<uint8_t> d = ReadEntry(project_, entries_[e]);
        const auto found = FindTextures(d);
        if (found.empty()) continue;
        const Category category = Categorize(entries_[e].name);
        for (const PackTexture& t : found) {
            const std::span<const uint8_t> px(d.data() + t.data, d.size() - t.data);
            ParsedName key{t.width, t.height, t.format, TextureHash(px, t.width, t.height, t.format)};
            if (IsPaletted(t.format)) {
                key.hasPalette = true;
                std::optional<uint64_t> ph;
                if (t.paletteEntries)
                    ph = PaletteHash(px, t.width, t.height, t.format,
                                     std::span<const uint8_t>(d.data() + t.paletteData, 2u * t.paletteEntries));
                if (ph) key.paletteHash = *ph; else key.paletteWildcard = true;
            }
            const std::string name = ReplacementName(key);
            const Location where{e, t.data, t.paletteData, t.paletteEntries};
            if (const auto it = byName_.find(name); it != byName_.end()) {
                textures_[it->second].locations.push_back(where);
                continue;
            }
            byName_[name] = static_cast<int>(textures_.size());
            byTexture_.try_emplace(TextureKey(key), static_cast<int>(textures_.size()));
            textures_.push_back({name, key, category.group, category.subgroup, {where}});
        }
    }
    if (progress) *progress = 1.0f;
    return true;
}

const std::vector<uint8_t>& Catalog::Pack(uint32_t entry) {  // caller holds packMutex_
    if (entry != cachedEntry_) {
        cachedPack_ = ReadEntry(project_, entries_[entry]);
        cachedEntry_ = entry;
    }
    return cachedPack_;
}

Image Catalog::Original(const CatalogTexture& t) {
    if (!t.captureFile.empty()) return LoadImage(t.captureFile, nullptr).value_or(Image{});
    if (t.locations.empty()) return {};
    std::lock_guard lock(packMutex_);
    const Location& l = t.locations.front();
    const std::vector<uint8_t>& d = Pack(l.entry);
    if (l.data >= d.size()) return {};
    const std::span<const uint8_t> palette =
        l.paletteEntries && l.paletteData + 2ull * l.paletteEntries <= d.size()
            ? std::span<const uint8_t>(d.data() + l.paletteData, 2u * l.paletteEntries)
            : std::span<const uint8_t>();
    return Decode(std::span<const uint8_t>(d.data() + l.data, d.size() - l.data), t.key.width, t.key.height, t.key.format, palette);
}

void Catalog::AddCapture(int session, const std::vector<std::filesystem::path>& files) {
    auto seen = [session](CatalogTexture& t) {
        if (t.seenIn.empty() || t.seenIn.back() != session) t.seenIn.push_back(session);
    };
    for (const auto& file : files) {
        const std::string stem = Utf8(file.stem());
        const auto n = ParseName(stem);
        if (!n || IsVideoFrame(*n)) continue;
        if (const int i = Find(stem); i >= 0) {
            seen(textures_[i]);
            continue;
        }
        if (const int i = FindTexture(*n); i >= 0) {
            CatalogTexture& t = textures_[i];
            if (std::find(t.paletteVariants.begin(), t.paletteVariants.end(), stem) == t.paletteVariants.end())
                t.paletteVariants.push_back(stem);
            seen(t);
            continue;
        }
        byName_[stem] = static_cast<int>(textures_.size());
        CatalogTexture t{stem, *n, "Solo vistas en juego", "Sesión " + std::to_string(session), {}};
        t.seenIn.push_back(session);
        t.captureFile = file;
        textures_.push_back(std::move(t));
    }
}

} // namespace tstudio
