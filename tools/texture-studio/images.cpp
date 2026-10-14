// SPDX-License-Identifier: GPL-3.0-or-later
#include "images.h"

#include <SDL3/SDL.h>

#include <cctype>
#include <cstring>
#include <fstream>
#include <iterator>

namespace tstudio {
namespace {
uint32_t Le32(const std::vector<uint8_t>& d, size_t o) {
    return o + 4 <= d.size() ? d[o] | d[o + 1] << 8 | d[o + 2] << 16 | static_cast<uint32_t>(d[o + 3]) << 24 : 0;
}

std::optional<Image> LoadDds(const std::filesystem::path& file, std::string* error) {
    std::ifstream f(file, std::ios::binary);
    const std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), {});
    const uint32_t h = Le32(d, 12), w = Le32(d, 16);
    const bool rgba8 = d.size() >= 128 && std::memcmp(d.data(), "DDS ", 4) == 0 && Le32(d, 84) == 0 && Le32(d, 88) == 32 &&
                       Le32(d, 92) == 0xFF && Le32(d, 104) == 0xFF000000u;
    if (!rgba8 || w == 0 || h == 0 || w > 16384 || h > 16384 || d.size() < 128 + 4ull * w * h) {
        if (error) *error = "Solo se admiten DDS RGBA8 sin comprimir (los que vuelca el juego).";
        return std::nullopt;
    }
    return Image{w, h, std::vector<uint8_t>(d.begin() + 128, d.begin() + 128 + 4ull * w * h)};
}
} // namespace

std::optional<Image> LoadImage(const std::filesystem::path& file, std::string* error) {
    std::string ext = Utf8(file.extension());
    for (char& c : ext) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    if (ext == ".dds") return LoadDds(file, error);
    SDL_Surface* loaded = SDL_LoadPNG(Utf8(file).c_str());
    if (!loaded) {
        if (error) *error = std::string("No se puede leer el PNG: ") + SDL_GetError();
        return std::nullopt;
    }
    SDL_Surface* rgba = SDL_ConvertSurface(loaded, SDL_PIXELFORMAT_RGBA32);
    SDL_DestroySurface(loaded);
    if (!rgba) {
        if (error) *error = std::string("No se puede convertir el PNG: ") + SDL_GetError();
        return std::nullopt;
    }
    Image img{static_cast<uint32_t>(rgba->w), static_cast<uint32_t>(rgba->h), {}};
    img.rgba.resize(static_cast<size_t>(img.width) * img.height * 4);
    for (uint32_t y = 0; y < img.height; ++y)
        std::memcpy(&img.rgba[static_cast<size_t>(y) * img.width * 4],
                    static_cast<const uint8_t*>(rgba->pixels) + static_cast<size_t>(y) * rgba->pitch, img.width * 4);
    SDL_DestroySurface(rgba);
    return img;
}

bool SavePng(const std::filesystem::path& file, const Image& image, std::string* error) {
    std::error_code ec;
    std::filesystem::create_directories(file.parent_path(), ec);
    SDL_Surface* s = SDL_CreateSurfaceFrom(static_cast<int>(image.width), static_cast<int>(image.height), SDL_PIXELFORMAT_RGBA32,
                                           const_cast<uint8_t*>(image.rgba.data()), static_cast<int>(image.width * 4));
    const bool ok = s && SDL_SavePNG(s, Utf8(file).c_str());
    if (!ok && error) *error = std::string("No se puede guardar el PNG: ") + SDL_GetError();
    if (s) SDL_DestroySurface(s);
    return ok;
}

SizeCheck CheckReplacementSize(uint32_t ow, uint32_t oh, uint32_t w, uint32_t h) {
    if (w > 4096 || h > 4096) return SizeCheck::TooLarge;
    if (static_cast<uint64_t>(w) * oh != static_cast<uint64_t>(h) * ow) return SizeCheck::WrongAspect;
    return w % ow == 0 && h % oh == 0 ? SizeCheck::Ok : SizeCheck::NotMultiple;
}

const char* SizeCheckMessage(SizeCheck check) {
    switch (check) {
    case SizeCheck::Ok: return "Tamaño correcto.";
    case SizeCheck::NotMultiple: return "Aviso: no es un múltiplo exacto (×2, ×4, ×8); el juego lo escalará.";
    case SizeCheck::WrongAspect: return "La imagen no tiene la misma proporción que la textura original.";
    case SizeCheck::TooLarge: return "La imagen supera 4096 píxeles de lado.";
    }
    return "";
}

} // namespace tstudio
