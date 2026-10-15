// SPDX-License-Identifier: GPL-3.0-or-later
// Replacement images: any PNG through SDL3 (stb_image underneath), the RGBA8 DDS files the runtime dumps,
// and the size rules for a replacement.
#pragma once
#include "core.h"
#include <optional>

namespace tstudio {
std::optional<Image> LoadImage(const std::filesystem::path& file, std::string* error);  // PNG (any kind) or RGBA8 DDS
bool SavePng(const std::filesystem::path& file, const Image& image, std::string* error);
// Box-filtered copy whose longer side is at most maxSide (thumbnails); smaller images are returned as they are.
Image Downscale(const Image& image, uint32_t maxSide);
enum class SizeCheck { Ok, NotMultiple, WrongAspect, TooLarge };
SizeCheck CheckReplacementSize(uint32_t originalW, uint32_t originalH, uint32_t w, uint32_t h);
const char* SizeCheckMessage(SizeCheck check);  // in the current language
} // namespace tstudio
