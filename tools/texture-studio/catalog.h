// SPDX-License-Identifier: GPL-3.0-or-later
// Every texture of the player's project.bin, grouped by replacement name, decoded on demand, and the
// textures seen in capture sessions.
#pragma once
#include "categories.h"
#include "names.h"
#include "projectbin.h"

#include <atomic>
#include <mutex>
#include <unordered_map>

namespace tstudio {

struct Location { uint32_t entry = 0, data = 0, paletteData = 0; uint16_t paletteEntries = 0; };

struct CatalogTexture {
    std::string name;                          // tex1_... (exact palette, or $ when the palette is unknown)
    ParsedName key;
    std::string group, subgroup;
    std::vector<Location> locations;           // every pack holding these exact bytes
    std::vector<std::string> paletteVariants;  // extra tex1_ names seen in captures (other palettes)
    std::vector<int> seenIn;                   // capture session numbers
    std::filesystem::path captureFile;         // only for textures seen in game but in no pack
};

class Catalog {
public:
    bool Build(const std::filesystem::path& projectBin, std::atomic<float>* progress, std::string* error);
    const std::vector<CatalogTexture>& Textures() const;
    const std::vector<ProjectEntry>& Entries() const;
    int Find(std::string_view name) const;          // -1 if absent
    int FindTexture(const ParsedName& n) const;      // same pixels, any palette; -1 if absent
    Image Original(const CatalogTexture& t);         // decoded original (thread-safe)
    void AddCapture(int session, const std::vector<std::filesystem::path>& files);  // dumps of one session

private:
    std::filesystem::path project_;
    std::vector<ProjectEntry> entries_;
    std::vector<CatalogTexture> textures_;
    std::unordered_map<std::string, int> byName_;
    std::unordered_map<std::string, int> byTexture_;  // name without palette -> first texture with those pixels
    std::mutex packMutex_;
    uint32_t cachedEntry_ = UINT32_MAX;
    std::vector<uint8_t> cachedPack_;
    const std::vector<uint8_t>& Pack(uint32_t entry);
};

bool IsVideoFrame(const ParsedName& n);  // THP frames: I8 512x448 and 256x224

} // namespace tstudio
