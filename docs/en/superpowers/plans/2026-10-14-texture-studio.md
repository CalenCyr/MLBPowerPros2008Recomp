# Power Pros Wii 2008 Texture Studio — implementation plan

*Versión en español: [../../../superpowers/plans/2026-10-14-texture-studio.md](../../../superpowers/plans/2026-10-14-texture-studio.md)*

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a desktop app that shows every texture of MLB Power Pros 2008 with its context, exports them to PNG and saves the edited PNGs (also in HD) as a texture mod, without touching the game.

**Architecture:** C++20 with SDL3 + Dear ImGui (SDL renderer), built like the Setup. A core without UI (`gx`, `pack`, `projectbin`, `names`, `images`, `categories`, `catalog`, `config`, `modfolder`, `capture`) with its own selftest, and a UI (`studio.cpp`) on top. Replacements are PNGs named `tex1_…` in `mods/<mod>/textures/`, the Dolphin-style system the runtime already loads.

**Tech Stack:** C++20, llvm-mingw (clang), CMake + Ninja, SDL3 (window, rendering, PNG with `SDL_LoadPNG`/`SDL_SavePNG`, dialogs), Dear ImGui, xxhash (header only), Win32 (processes, `ShellExecuteW`). All already pinned in `local/wiicompiled-mlb/src/Launcher/artifacts/dependencies`.

**Spec:** `docs/superpowers/specs/2026-10-14-texture-studio-design.md`

## Global Constraints

- Nothing from the game in the repository, the package or the app: the app reads the player's `project.bin` at run time. Committed tests use synthetic data.
- The Studio never writes `.pack` or `project.bin`; only PNGs in `mods/<mod>/textures/`, `mod.toml`, the `.zip` the player asks for, the `[mods] enabled` line of `Config.toml` and its cache in `UserData/Cache/texture_studio/`.
- Product name: "Power Pros Wii 2008 Texture Studio"; executable `TextureStudio.exe`.
- UI in Spanish, style B of the mockup, **no red stripe**.
- Maximum replacement size: 4096 px per side; same aspect ratio as the original.
- Hash: XXH64, seed 0. Name: `tex1_<w>x<h>_<hash 16 hex>[_<palette hash 16 hex | $>]_<format>`.
- The runtime change is a reproducible patch in `tools/patches/`, registered in `tools/wiicompiled-translate.ps1` after `'wiicompiled-match-benchmark-gameplay'`.
- Every new reverse-engineering finding goes to `docs/ingenieria-inversa.md` and the PDF is regenerated (`python tools/build_re_pdf.py`).
- Commits end with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`; the `tools/check_no_game_data.py` hook must pass.

**Change from the spec (approved for simplicity):** the index is not saved to disk in the first version. It is built in a thread with a progress bar on opening; if it takes more than 5 s on the test PC, the cache is added as a separate task. The spec is updated in Task 12.

## Review Focus

1. Paths with non-ASCII characters (`C:\Users\José\…`, OneDrive): exporting, importing and creating mods must work. → test in Task 4 (PNG in a folder with `ñ`) and Task 7 (mod with `ñ`).
2. Truncated or corrupt data (cut-off `project.bin`, pack with out-of-range pointers): a clear error or an ignored texture, never a crash. → tests in Tasks 2 and 3.
3. Invalid or duplicate mod names (`a/b`, `CON`, empty, already existing): rejected with a message. → test in Task 7.
4. Import folder with files that do not match, duplicates (`.png` and `.dds` with the same name) or of another size: per-file report, nothing half-done. → test in Task 8.
5. Capture without dumps (the player closes the game right away) or with a non-existent dump folder: empty session, no error. → test in Task 9.

---

## File map

```
tools/texture-studio/
  CMakeLists.txt     ejecutable TextureStudio (estático) con SDL3, ImGui, xxhash
  build.ps1          configura y compila con el llvm-mingw fijado (desarrollo y Make-Payload)
  core.h             tipos compartidos (Image, ParsedName) y utilidades de bytes
  gx.h / gx.cpp      tamaños de bloque, decodificadores GX
  pack.h / pack.cpp  texturas y paletas dentro de un PACKWII
  projectbin.h/.cpp  índice y lectura de entradas de project.bin
  names.h/.cpp       hashes y nombres tex1_…; lectura de nombres
  images.h/.cpp      PNG (SDL), DDS RGBA8 del runtime, reglas de tamaño
  categories.h/.cpp  pack → grupo y subgrupo legibles
  catalog.h/.cpp     catálogo completo, decodificación bajo demanda, capturas
  config.h/.cpp      lectura/escritura mínima de Config.toml
  modfolder.h/.cpp   mods: crear, listar, reemplazos, importar, zip
  capture.h/.cpp     lanzar el juego con volcado y recoger la sesión
  selftest.cpp       autotest (--selftest), datos sintéticos
  studio.cpp         main, interfaz
tools/setup/Make-Payload.ps1      compila el Studio y lo mete en el paquete
tools/setup/LocalBuild.ps1        lo instala junto al juego, acceso directo
tools/patches/wiicompiled-texture-studio.patch   launcher (botón) + volcado por variable de entorno
tools/wiicompiled-translate.ps1   registra el parche
docs/texture-studio.md            manual para jugadores
docs/mods.md, docs/ingenieria-inversa.md         referencias
```

Build and selftest command used in every task (from the repo root, PowerShell):

```powershell
.\tools\texture-studio\build.ps1; if ($?) { & local\build\texture-studio\TextureStudio.exe --selftest; "exit $LASTEXITCODE" }
```

Expected output when everything passes: `selftest ok (N checks)` and `exit 0`.

---

### Task 1: Project, selftest and GX decoders

**Files:**
- Create: `tools/texture-studio/CMakeLists.txt`, `tools/texture-studio/build.ps1`, `tools/texture-studio/core.h`, `tools/texture-studio/gx.h`, `tools/texture-studio/gx.cpp`, `tools/texture-studio/selftest.cpp`, `tools/texture-studio/studio.cpp`

**Interfaces:**
- Produces:
  - `core.h`: `struct Image { uint32_t width = 0, height = 0; std::vector<uint8_t> rgba; bool Empty() const; };` `uint16_t Be16(std::span<const uint8_t>, size_t)`, `uint32_t Be32(std::span<const uint8_t>, size_t)` (0 if out of range), `std::string Utf8(const std::filesystem::path&)`, `std::filesystem::path PathFromUtf8(std::string_view)`.
  - `gx.h`: `bool IsKnownFormat(uint32_t)`, `bool IsDecodable(uint32_t)`, `bool IsPaletted(uint32_t)`, `uint32_t TextureBytes(uint32_t w, uint32_t h, uint32_t fmt)`, `std::vector<uint16_t> Values(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt)`, `Image Decode(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt, std::span<const uint8_t> paletteBE)`, `const char* FormatName(uint32_t)`.
  - `selftest.cpp`: `int RunSelftest();` and the `CHECK(cond)` macro; each task adds a `void Test<Something>()` function and calls it from `RunSelftest`.

- [ ] **Step 1: CMake and build script**

`tools/texture-studio/CMakeLists.txt`:

```cmake
# SPDX-License-Identifier: GPL-3.0-or-later
# Power Pros Wii 2008 Texture Studio. Built by tools/texture-studio/build.ps1 (and Make-Payload) with the
# pinned llvm-mingw, statically against SDL3, Dear ImGui and xxhash from the runtime's dependency sources.
cmake_minimum_required(VERSION 3.24)
project(TextureStudio LANGUAGES C CXX)

set(SDL_SOURCE_DIR "" CACHE PATH "SDL3 source tree")
set(IMGUI_SOURCE_DIR "" CACHE PATH "Dear ImGui source tree")
set(XXHASH_SOURCE_DIR "" CACHE PATH "xxhash source tree")
set(UI_INCLUDE_DIR "" CACHE PATH "Patched Wiicompiled runtime/include (power_pros_ui.h)")

set(SDL_SHARED OFF CACHE BOOL "" FORCE)
set(SDL_STATIC ON CACHE BOOL "" FORCE)
set(SDL_TEST_LIBRARY OFF CACHE BOOL "" FORCE)
foreach(subsystem AUDIO CAMERA HAPTIC SENSOR POWER JOYSTICK)
    set(SDL_${subsystem} OFF CACHE BOOL "" FORCE)
endforeach()
add_subdirectory("${SDL_SOURCE_DIR}" sdl EXCLUDE_FROM_ALL)

add_executable(TextureStudio WIN32
    studio.cpp selftest.cpp gx.cpp
    "${IMGUI_SOURCE_DIR}/imgui.cpp"
    "${IMGUI_SOURCE_DIR}/imgui_draw.cpp"
    "${IMGUI_SOURCE_DIR}/imgui_tables.cpp"
    "${IMGUI_SOURCE_DIR}/imgui_widgets.cpp"
    "${IMGUI_SOURCE_DIR}/backends/imgui_impl_sdl3.cpp"
    "${IMGUI_SOURCE_DIR}/backends/imgui_impl_sdlrenderer3.cpp")
target_include_directories(TextureStudio PRIVATE "${IMGUI_SOURCE_DIR}" "${UI_INCLUDE_DIR}" "${XXHASH_SOURCE_DIR}")
target_compile_features(TextureStudio PRIVATE cxx_std_20)
target_compile_definitions(TextureStudio PRIVATE UNICODE _UNICODE)
target_link_libraries(TextureStudio PRIVATE SDL3::SDL3-static)
target_link_options(TextureStudio PRIVATE -static)
```

(The following tasks add their `.cpp` files to the `add_executable` list.)

`tools/texture-studio/build.ps1`:

```powershell
# SPDX-License-Identifier: GPL-3.0-or-later
# Configures and builds Power Pros Wii 2008 Texture Studio with the pinned llvm-mingw, CMake and Ninja
# from a prepared Wiicompiled tree (tools/wiicompiled-translate.ps1 makes one). Output: <Output>\TextureStudio.exe
param(
    [string]$Source = 'local\wiicompiled-mlb\src',
    [string]$Output = 'local\build\texture-studio'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
function Resolve-Root([string]$path) { if ([IO.Path]::IsPathRooted($path)) { $path } else { [IO.Path]::GetFullPath((Join-Path $root $path)) } }
$Source = Resolve-Root $Source
$Output = Resolve-Root $Output
$tools = Join-Path $Source 'Launcher\artifacts\portable-tools'
$deps = Join-Path $Source 'Launcher\artifacts\dependencies'
$env:PATH = "$tools\llvm-mingw\bin;$tools\CMake\bin;$tools\Ninja;$env:PATH"
$tc = "$tools\llvm-mingw\bin".Replace('\', '/')
function Fwd([string]$p) { $p.Replace('\', '/') }
cmake -S $PSScriptRoot -B $Output -G Ninja -DCMAKE_BUILD_TYPE=Release `
    "-DCMAKE_C_COMPILER=$tc/clang.exe" "-DCMAKE_CXX_COMPILER=$tc/clang++.exe" "-DCMAKE_RC_COMPILER=$tc/llvm-windres.exe" `
    "-DSDL_SOURCE_DIR=$(Fwd "$deps\SDL")" "-DIMGUI_SOURCE_DIR=$(Fwd "$deps\imgui")" `
    "-DXXHASH_SOURCE_DIR=$(Fwd "$deps\xxhash")" "-DUI_INCLUDE_DIR=$(Fwd "$Source\runtime\include")" | Out-Host
if ($LASTEXITCODE -ne 0) { throw "texture studio configure failed ($LASTEXITCODE)" }
cmake --build $Output --parallel | Out-Host
if ($LASTEXITCODE -ne 0) { throw "texture studio build failed ($LASTEXITCODE)" }
```

- [ ] **Step 2: `core.h`**

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Types and byte helpers shared by the Texture Studio core (no UI, no game data).
#pragma once
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace tstudio {

struct Image {
    uint32_t width = 0, height = 0;
    std::vector<uint8_t> rgba;  // width * height * 4, rows top to bottom
    bool Empty() const { return rgba.empty(); }
};

inline uint16_t Be16(std::span<const uint8_t> d, size_t o) {
    return o + 2 <= d.size() ? static_cast<uint16_t>(d[o] << 8 | d[o + 1]) : 0;
}
inline uint32_t Be32(std::span<const uint8_t> d, size_t o) {
    return o + 4 <= d.size() ? static_cast<uint32_t>(d[o]) << 24 | d[o + 1] << 16 | d[o + 2] << 8 | d[o + 3] : 0;
}
inline std::string Utf8(const std::filesystem::path& p) {
    const auto s = p.u8string();
    return {s.begin(), s.end()};
}
inline std::filesystem::path PathFromUtf8(std::string_view s) {
    return std::filesystem::path(std::u8string(s.begin(), s.end()));
}

} // namespace tstudio
```

- [ ] **Step 3: Write the `gx` tests (they fail: `gx.h` does not exist)**

`tools/texture-studio/selftest.cpp`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// TextureStudio.exe --selftest: synthetic data only (no game content). Prints the first failures.
#include "core.h"
#include "gx.h"

#include <cstdio>

namespace tstudio {
namespace {
int g_checks = 0, g_failures = 0;
#define CHECK(cond)                                                                       \
    do {                                                                                  \
        ++g_checks;                                                                       \
        if (!(cond)) {                                                                    \
            ++g_failures;                                                                 \
            std::fprintf(stderr, "selftest: %s:%d: %s\n", __FILE__, __LINE__, #cond);     \
        }                                                                                 \
    } while (0)

uint32_t Pixel(const Image& img, uint32_t x, uint32_t y) {  // 0xRRGGBBAA
    const uint8_t* p = &img.rgba[(static_cast<size_t>(y) * img.width + x) * 4];
    return static_cast<uint32_t>(p[0]) << 24 | p[1] << 16 | p[2] << 8 | p[3];
}

void TestGx() {
    CHECK(TextureBytes(8, 4, 1) == 32);       // I8: one 8x4 block
    CHECK(TextureBytes(4, 4, 9) == 32);       // C8 4x4 pads to one 8x4 block
    CHECK(TextureBytes(8, 8, 8) == 32);       // C4: one 8x8 block
    CHECK(TextureBytes(4, 4, 6) == 64);       // RGBA8: one 4x4 block, two 32-byte halves
    CHECK(TextureBytes(512, 512, 9) == 512 * 512);
    CHECK(TextureBytes(16, 16, 7) == 0);      // unknown format

    // I8 16x4 = two blocks side by side: block 0 holds x 0..7, block 1 holds x 8..15.
    std::vector<uint8_t> i8(64);
    for (size_t i = 0; i < i8.size(); ++i) i8[i] = static_cast<uint8_t>(i);
    const auto v = Values(i8, 16, 4, 1);
    CHECK(v.size() == 64);
    CHECK(v[0] == 0 && v[7] == 7 && v[8] == 32 && v[16] == 8);  // (8,0) starts block 1; (0,1) = 8
    const Image grey = Decode(i8, 16, 4, 1, {});
    CHECK(grey.width == 16 && grey.height == 4 && Pixel(grey, 8, 0) == 0x202020FFu);

    // C4 8x8: high nibble first.
    std::vector<uint8_t> c4(32, 0x12);
    const auto n = Values(c4, 8, 8, 8);
    CHECK(n[0] == 1 && n[1] == 2);
    const uint8_t pal[] = {0x80, 0x00, 0xFC, 0x00, 0x83, 0xE0};  // black, red, green (RGB5A3 opaque)
    const Image c4img = Decode(c4, 8, 8, 8, pal);
    CHECK(Pixel(c4img, 0, 0) == 0xFF0000FFu && Pixel(c4img, 1, 0) == 0x00FF00FFu);

    // RGB5A3: opaque white, and translucent 0x7F00 (a=7 -> 255, r=15 -> 255).
    const uint8_t rgb5a3[32] = {0xFF, 0xFF, 0x7F, 0x00};
    const Image c = Decode(rgb5a3, 4, 4, 5, {});
    CHECK(Pixel(c, 0, 0) == 0xFFFFFFFFu && Pixel(c, 1, 0) == 0xFF0000FFu);

    // RGBA8 4x4: AR pairs in the first 32 bytes, GB pairs in the next 32.
    std::vector<uint8_t> rgba8(64);
    rgba8[0] = 0x80; rgba8[1] = 0x11; rgba8[32] = 0x22; rgba8[33] = 0x33;
    CHECK(Pixel(Decode(rgba8, 4, 4, 6, {}), 0, 0) == 0x11223380u);

    CHECK(Decode(std::span<const uint8_t>(i8.data(), 10), 16, 4, 1, {}).Empty());  // short data
    CHECK(Decode(i8, 16, 4, 3, {}).Empty());                                        // IA8: not decodable
}
} // namespace

int RunSelftest() {
    TestGx();
    std::printf("selftest %s (%d checks)\n", g_failures ? "FAILED" : "ok", g_checks);
    return g_failures ? 1 : 0;
}

} // namespace tstudio
```

`tools/texture-studio/studio.cpp` (provisional, Task 10 replaces it with the UI):

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Power Pros Wii 2008 Texture Studio.
#include <SDL3/SDL_main.h>
#include <cstring>

namespace tstudio { int RunSelftest(); }

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--selftest") == 0) return tstudio::RunSelftest();
    return 0;
}
```

- [ ] **Step 4: Build and see it fail**

Run: the build command above.
Expected: build error `'gx.h' file not found`.

- [ ] **Step 5: Implement `gx.h` and `gx.cpp`**

`gx.h`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// GameCube/Wii GX texture formats: block sizes and decoders (big-endian, tiled).
#pragma once
#include "core.h"

namespace tstudio {

bool IsKnownFormat(uint32_t fmt);  // I4 I8 IA4 IA8 RGB565 RGB5A3 RGBA8 C4 C8 C14X2 CMPR
bool IsDecodable(uint32_t fmt);    // I4 I8 RGB5A3 RGBA8 C4 C8
bool IsPaletted(uint32_t fmt);     // C4 C8 C14X2
const char* FormatName(uint32_t fmt);
// Bytes of the base level, padded to whole blocks (what the runtime hashes). 0 for unknown formats.
uint32_t TextureBytes(uint32_t w, uint32_t h, uint32_t fmt);
// Untiled texel values (h * w) of a 4-, 8- or 16-bit format; empty if the data is short or RGBA8.
std::vector<uint16_t> Values(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt);
// RGBA image; palette = big-endian RGB5A3 entries (empty: C4/C8 show their indices in grey).
Image Decode(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt, std::span<const uint8_t> paletteBE);

} // namespace tstudio
```

`gx.cpp`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
#include "gx.h"

#include <array>
#include <cstring>
#include <optional>

namespace tstudio {
namespace {
struct Block { uint32_t w, h, bpp; };

std::optional<Block> BlockOf(uint32_t fmt) {
    switch (fmt) {
    case 0: case 8: case 14: return Block{8, 8, 4};
    case 1: case 2: case 9: return Block{8, 4, 8};
    case 3: case 4: case 5: case 10: return Block{4, 4, 16};
    case 6: return Block{4, 4, 32};
    default: return std::nullopt;
    }
}

std::array<uint8_t, 4> FromRgb5a3(uint16_t v) {
    if (v & 0x8000)
        return {static_cast<uint8_t>(((v >> 10) & 31) * 255 / 31), static_cast<uint8_t>(((v >> 5) & 31) * 255 / 31),
                static_cast<uint8_t>((v & 31) * 255 / 31), 255};
    return {static_cast<uint8_t>(((v >> 8) & 15) * 17), static_cast<uint8_t>(((v >> 4) & 15) * 17),
            static_cast<uint8_t>((v & 15) * 17), static_cast<uint8_t>(((v >> 12) & 7) * 255 / 7)};
}
} // namespace

bool IsKnownFormat(uint32_t fmt) { return BlockOf(fmt).has_value(); }
bool IsDecodable(uint32_t fmt) { return fmt == 0 || fmt == 1 || fmt == 5 || fmt == 6 || fmt == 8 || fmt == 9; }
bool IsPaletted(uint32_t fmt) { return fmt == 8 || fmt == 9 || fmt == 10; }

const char* FormatName(uint32_t fmt) {
    switch (fmt) {
    case 0: return "I4"; case 1: return "I8"; case 2: return "IA4"; case 3: return "IA8";
    case 4: return "RGB565"; case 5: return "RGB5A3"; case 6: return "RGBA8"; case 8: return "C4";
    case 9: return "C8"; case 10: return "C14X2"; case 14: return "CMPR"; default: return "?";
    }
}

uint32_t TextureBytes(uint32_t w, uint32_t h, uint32_t fmt) {
    const auto b = BlockOf(fmt);
    if (!b) return 0;
    const uint64_t pw = (w + b->w - 1) / b->w * b->w, ph = (h + b->h - 1) / b->h * b->h;
    return static_cast<uint32_t>(pw * ph * b->bpp / 8);
}

std::vector<uint16_t> Values(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt) {
    const auto b = BlockOf(fmt);
    if (!b || fmt == 6 || px.size() < TextureBytes(w, h, fmt)) return {};
    const uint32_t blocksX = (w + b->w - 1) / b->w;
    std::vector<uint16_t> out(static_cast<size_t>(w) * h);
    for (uint32_t y = 0; y < h; ++y) {
        for (uint32_t x = 0; x < w; ++x) {
            const size_t block = static_cast<size_t>(y / b->h) * blocksX + x / b->w;
            const size_t i = block * b->w * b->h + (y % b->h) * b->w + x % b->w;  // texel in data order
            uint16_t v;
            if (b->bpp == 4) v = (i & 1) ? px[i / 2] & 15 : px[i / 2] >> 4;
            else if (b->bpp == 8) v = px[i];
            else v = static_cast<uint16_t>(px[2 * i] << 8 | px[2 * i + 1]);
            out[static_cast<size_t>(y) * w + x] = v;
        }
    }
    return out;
}

Image Decode(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt, std::span<const uint8_t> paletteBE) {
    Image img;
    if (!IsDecodable(fmt) || w == 0 || h == 0 || px.size() < TextureBytes(w, h, fmt)) return img;
    img.width = w;
    img.height = h;
    img.rgba.resize(static_cast<size_t>(w) * h * 4);
    auto put = [&](size_t i, std::array<uint8_t, 4> c) { std::memcpy(&img.rgba[i * 4], c.data(), 4); };
    if (fmt == 6) {
        const uint32_t blocksX = (w + 3) / 4;
        for (uint32_t y = 0; y < h; ++y) {
            for (uint32_t x = 0; x < w; ++x) {
                const size_t base = (static_cast<size_t>(y / 4) * blocksX + x / 4) * 64;
                const size_t t = (y % 4) * 4 + x % 4;
                put(static_cast<size_t>(y) * w + x, {px[base + 2 * t + 1], px[base + 32 + 2 * t],
                                                     px[base + 33 + 2 * t], px[base + 2 * t]});
            }
        }
        return img;
    }
    const auto v = Values(px, w, h, fmt);
    const size_t entries = paletteBE.size() / 2;
    for (size_t i = 0; i < v.size(); ++i) {
        const uint16_t value = v[i];
        if (fmt == 5) {
            put(i, FromRgb5a3(value));
        } else if (fmt == 0 || fmt == 1) {
            const uint8_t g = static_cast<uint8_t>(fmt == 0 ? value * 17 : value);
            put(i, {g, g, g, 255});
        } else if (entries == 0) {  // C4/C8 without a known palette: indices in grey
            const uint8_t g = static_cast<uint8_t>(fmt == 8 ? value * 17 : value);
            put(i, {g, g, g, 255});
        } else if (value < entries) {
            put(i, FromRgb5a3(static_cast<uint16_t>(paletteBE[2 * value] << 8 | paletteBE[2 * value + 1])));
        } else {
            put(i, {0, 0, 0, 0});
        }
    }
    return img;
}

} // namespace tstudio
```

Adding `gx.cpp` is already in the CMake list of Step 1.

- [ ] **Step 6: Build and pass the selftest**

Run: the build command.
Expected: `selftest ok (15 checks)`, `exit 0`.

- [ ] **Step 7: Commit**

```bash
git add tools/texture-studio
git commit -m "Texture Studio: project, selftest and GX decoders

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Textures inside a PACKWII

**Files:**
- Create: `tools/texture-studio/pack.h`, `tools/texture-studio/pack.cpp`
- Modify: `tools/texture-studio/CMakeLists.txt` (add `pack.cpp`), `tools/texture-studio/selftest.cpp`

**Interfaces:**
- Consumes: `Be16`, `Be32`, `IsKnownFormat`, `TextureBytes` (Task 1).
- Produces:

```cpp
struct PackTexture {
    uint32_t offset = 0, width = 0, height = 0, format = 0, data = 0;  // header and pixel positions in the pack
    bool model = false;
    uint16_t paletteEntries = 0;  // 0: no palette found
    uint32_t paletteData = 0;
    bool paletteByPosition = false;  // paired only by position: keep it fixed
};
std::vector<PackTexture> FindTextures(std::span<const uint8_t> pack);  // empty unless "PACKWII "
```

Rules (those of `tools/packwii.py`, verified against the game): see the docstring of `packwii.py` and `docs/ingenieria-inversa.md` section 5.

- [ ] **Step 1: Tests (they fail)**

Add to `selftest.cpp` (include `"pack.h"`):

```cpp
// A synthetic PACKWII: header, one layout C8 texture with its palette pointer, one model C4 texture
// whose palette follows the pixels, and one texture whose pixels run past the end (ignored).
std::vector<uint8_t> SyntheticPack() {
    std::vector<uint8_t> d(0x400, 0);
    std::memcpy(d.data(), "PACKWII ", 8);
    d[0x17] = 0x20;
    auto put16 = [&](size_t o, uint16_t v) { d[o] = v >> 8; d[o + 1] = v & 0xFF; };
    auto put32 = [&](size_t o, uint32_t v) { for (int i = 0; i < 4; ++i) d[o + i] = (v >> (24 - 8 * i)) & 0xFF; };
    // layout texture at 0x40: 8x4 C8, pixels at 0x100, palette (256 entries) at 0x200 via +0x2C
    put16(0x40, 8); put16(0x42, 4); put32(0x44, 9); put32(0x48, 0x40000100);
    put32(0x54, 1); put32(0x58, 1); put16(0x64, 256); put32(0x68, 2); put32(0x6C, 0x40000200);
    // model texture at 0x80: 8x8 C4 (type 0x84), pixels at 0x140, palette header at 0xA4 -> data 0x160
    put16(0x80, 8); put16(0x82, 8); d[0x84] = 0x84; put32(0x88, 0x40000140);
    put16(0xA4, 16); d[0xA8] = 0x81; put32(0xAC, 0x40000160);
    // broken texture at 0xC0: 1024x1024 RGBA8 whose pixels would end past the file
    put16(0xC0, 1024); put16(0xC2, 1024); put32(0xC4, 6); put32(0xC8, 0x40000180);
    return d;
}

void TestPack() {
    const auto d = SyntheticPack();
    const auto t = FindTextures(d);
    CHECK(t.size() == 2);
    CHECK(t[0].offset == 0x40 && t[0].format == 9 && t[0].data == 0x100 && !t[0].model);
    CHECK(t[0].paletteEntries == 256 && t[0].paletteData == 0x200 && !t[0].paletteByPosition);
    CHECK(t[1].offset == 0x80 && t[1].format == 8 && t[1].model);
    CHECK(t[1].paletteEntries == 16 && t[1].paletteData == 0x160 && t[1].paletteByPosition);
    CHECK(FindTextures(std::span<const uint8_t>(d.data(), 0x30)).empty());   // truncated
    std::vector<uint8_t> other(d);
    other[0] = 'X';
    CHECK(FindTextures(other).empty());                                       // not PACKWII
}
```

And in `RunSelftest()`: `TestPack();` after `TestGx();`. Add `#include <cstring>` at the top.

- [ ] **Step 2: Build → fails** (`'pack.h' file not found`).

- [ ] **Step 3: Implement**

`pack.h`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Texture and palette headers inside a PACKWII file (docs/ingenieria-inversa.md, section 5).
#pragma once
#include "core.h"

namespace tstudio {

struct PackTexture {
    uint32_t offset = 0, width = 0, height = 0, format = 0, data = 0;
    bool model = false;
    uint16_t paletteEntries = 0;
    uint32_t paletteData = 0;
    bool paletteByPosition = false;
};

std::vector<PackTexture> FindTextures(std::span<const uint8_t> pack);

} // namespace tstudio
```

`pack.cpp`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Port of tools/packwii.py find_textures (kept in step with it).
#include "pack.h"

#include "gx.h"

#include <cstring>
#include <optional>
#include <unordered_map>

namespace tstudio {
namespace {
std::optional<uint32_t> Pointer(std::span<const uint8_t> d, size_t o) {
    if (o + 4 > d.size()) return std::nullopt;
    const uint32_t p = Be32(d, o);
    if ((p >> 30) != 1) return std::nullopt;
    return p & 0x3FFFFFFF;
}
bool Pow2Size(uint32_t v) { return v >= 4 && v <= 1024 && (v & (v - 1)) == 0; }
struct Palette { uint16_t entries; uint32_t data; };
} // namespace

std::vector<PackTexture> FindTextures(std::span<const uint8_t> d) {
    std::vector<PackTexture> out;
    if (d.size() < 0x30 || std::memcmp(d.data(), "PACKWII ", 8) != 0) return out;
    std::unordered_map<uint32_t, Palette> pals;  // palette header offset -> palette
    for (size_t o = 0x20; o + 12 <= d.size(); o += 4) {
        const uint16_t w = Be16(d, o), h = Be16(d, o + 2);
        const auto p = Pointer(d, o + 8);
        if (!p || *p >= d.size()) continue;
        const uint8_t kind = d[o + 4];
        if (h == 0 && kind == 0x81 && (w == 16 || w == 256) && *p + 2ull * w <= d.size()) {
            pals[static_cast<uint32_t>(o)] = {w, *p};
            continue;
        }
        if (!Pow2Size(w) || !Pow2Size(h)) continue;
        uint32_t fmt;
        bool model;
        if ((kind == 0x80 || kind == 0x81 || kind == 0x82 || kind == 0x84) && d[o + 5] == 0) {
            fmt = kind == 0x80 ? 6 : kind == 0x81 ? 5 : kind == 0x82 ? 9 : 8;
            model = true;
        } else if (kind == 0 && IsKnownFormat(Be32(d, o + 4))) {
            fmt = Be32(d, o + 4);
            model = false;
        } else {
            continue;
        }
        if (*p + static_cast<uint64_t>(TextureBytes(w, h, fmt)) > d.size()) continue;
        PackTexture t{static_cast<uint32_t>(o), w, h, fmt, *p, model};
        if (!model && o + 0x30 <= d.size()) {
            const uint16_t n = Be16(d, o + 0x24);
            const auto pp = Pointer(d, o + 0x2C);
            if ((n == 16 || n == 256) && pp && *pp + 2ull * n <= d.size()) {
                t.paletteEntries = n;
                t.paletteData = *pp;
            }
        }
        out.push_back(t);
    }
    std::unordered_map<uint32_t, size_t> byOffset;
    for (size_t i = 0; i < out.size(); ++i) byOffset[out[i].offset] = i;
    auto needsPalette = [](const PackTexture& t) { return (t.format == 8 || t.format == 9) && t.paletteEntries == 0; };
    // Texture sets: {u32 n, -> n texture headers, u32 m, -> m palettes}; one palette for all or one each.
    for (size_t o = 0x20; o + 16 <= d.size(); o += 4) {
        const uint32_t c1 = Be32(d, o), c2 = Be32(d, o + 8);
        if (c1 == 0 || c1 >= 4096 || c2 == 0 || c2 >= 4096) continue;
        const auto l1 = Pointer(d, o + 4), l2 = Pointer(d, o + 12);
        if (!l1 || !l2 || *l1 + 4ull * c1 > d.size() || *l2 + 4ull * c2 > d.size()) continue;
        bool ok = true;
        for (uint32_t i = 0; ok && i < c1; ++i) { const auto x = Pointer(d, *l1 + 4 * i); ok = x && byOffset.count(*x); }
        for (uint32_t i = 0; ok && i < c2; ++i) { const auto x = Pointer(d, *l2 + 4 * i); ok = x && pals.count(*x); }
        if (!ok) continue;
        for (uint32_t i = 0; i < c1; ++i) {
            PackTexture& t = out[byOffset[*Pointer(d, *l1 + 4 * i)]];
            if (!needsPalette(t)) continue;
            const Palette& pal = pals[*Pointer(d, *l2 + 4 * (c2 == c1 ? i : 0))];
            t.paletteEntries = pal.entries;
            t.paletteData = pal.data;
        }
    }
    // By position: a model's palette header follows it (+0x24); otherwise the palette colours follow
    // the pixels (verified against the runtime's dumps). The header just before is the previous texture's.
    std::unordered_map<uint32_t, Palette> byData;
    for (const auto& [_, pal] : pals) byData.emplace(pal.data, pal);
    for (PackTexture& t : out) {
        if (!needsPalette(t)) continue;
        const uint16_t want = t.format == 8 ? 16 : 256;
        const uint32_t end = t.data + TextureBytes(t.width, t.height, t.format);
        const Palette* found = nullptr;
        if (auto it = pals.find(t.offset + 0x24); t.model && it != pals.end()) found = &it->second;
        else if (auto jt = byData.find(end); jt != byData.end() && jt->second.entries == want) found = &jt->second;
        if (!found) continue;
        t.paletteEntries = found->entries;
        t.paletteData = found->data;
        t.paletteByPosition = true;
    }
    return out;
}

} // namespace tstudio
```

- [ ] **Step 4: Build → `selftest ok`.**

- [ ] **Step 5: Local check against `packwii.py` (not committed)**

Add to `studio.cpp` a development mode `--list-pack <file.pack>` that prints `offset w h fmt paletteData` per texture:

```cpp
#include "pack.h"
#include <cstdio>
#include <fstream>
#include <iterator>
// in main, before return 0:
    if (argc == 3 && std::strcmp(argv[1], "--list-pack") == 0) {
        std::ifstream f(argv[2], std::ios::binary);
        const std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), {});
        for (const auto& t : tstudio::FindTextures(d))
            std::printf("%#x %u %u %u %#x\n", t.offset, t.width, t.height, t.format, t.paletteEntries ? t.paletteData : 0);
        return 0;
    }
```

Run (Git Bash):

```bash
PY=/c/Users/david/.pyenv/pyenv-win/versions/3.12.0/python.exe
P=local/analysis/pack/files/env_mainmenu.pack
local/build/texture-studio/TextureStudio.exe --list-pack $P > /tmp/ts.txt
PYTHONPATH=<scratchpad>/pylib $PY -c "
import sys; sys.path.insert(0,'tools'); import packwii
d=open('$P','rb').read()
for t in packwii.find_textures(d): print('%#x %d %d %d %#x'%(t['off'],t['w'],t['h'],t['fmt'],t['pal'][1] if t['pal'] else 0))" > /tmp/py.txt
diff /tmp/ts.txt /tmp/py.txt && echo IGUAL
```

Expected: `IGUAL`. Repeat with `stadium_nyy.pack` and `PWM_mdl_uniform_MLB_CHC_00.pack`. (Python prints `0x0` instead of `0`: normalise with `sed 's/0x0$/0/'` if needed.)

- [ ] **Step 6: Commit** — `Texture Studio: find textures and palettes in PACKWII files`.

---

### Task 3: `project.bin` and `tex1_…` names

**Files:**
- Create: `tools/texture-studio/projectbin.h`, `projectbin.cpp`, `names.h`, `names.cpp`
- Modify: `CMakeLists.txt` (add both `.cpp` files), `selftest.cpp`

**Interfaces:**
- Produces:

```cpp
// projectbin.h
struct ProjectEntry { std::string name; uint64_t offset = 0; uint32_t size = 0; };  // name without the leading '/'
std::optional<std::vector<ProjectEntry>> ReadProjectIndex(const std::filesystem::path& file, std::string* error);
std::vector<uint8_t> ReadEntry(const std::filesystem::path& file, const ProjectEntry& entry);  // empty on error

// names.h
uint64_t TextureHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt);
std::optional<uint64_t> PaletteHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt,
                                    std::span<const uint8_t> paletteBE);
struct ParsedName {
    uint32_t width = 0, height = 0, format = 0;
    uint64_t textureHash = 0;
    bool hasPalette = false, paletteWildcard = false;
    uint64_t paletteHash = 0;
};
std::string ReplacementName(const ParsedName& n);              // "tex1_..." without extension
std::optional<ParsedName> ParseName(std::string_view stem);    // accepts .png/.dds stems; rejects others
```

- [ ] **Step 1: Tests (they fail)**

```cpp
// A synthetic project.bin with two entries, laid out like the real one (tools/projectbin.py).
std::vector<uint8_t> SyntheticProject() {
    std::vector<uint8_t> d(0x3000, 0);
    auto put32 = [&](size_t o, uint32_t v) { for (int i = 0; i < 4; ++i) d[o + i] = (v >> (24 - 8 * i)) & 0xFF; };
    put32(0x00, 2); put32(0x04, 0x800);
    put32(0x14, 0x100);   // records
    put32(0x28, 0x200);   // order
    put32(0x2C, 0x300);   // names
    put32(0x34, 0x800);   // data
    const char names[] = "\0/a.pack\0/b.dat\0";
    std::memcpy(&d[0x300], names, sizeof(names));
    // record 1: name 1, 1 sector, size 5; record 2: name 9, 1 sector, size 3
    put32(0x100 + 0x1C + 4, 1); put32(0x100 + 0x1C + 8, 1); put32(0x100 + 0x1C + 24, 5);
    put32(0x100 + 0x38 + 4, 9); put32(0x100 + 0x38 + 8, 1); put32(0x100 + 0x38 + 24, 3);
    // order: pair 0 unused, (1, sector 0), (2, sector 1), (0, 0)
    put32(0x208, 1); put32(0x20C, 0); put32(0x210, 2); put32(0x214, 1);
    std::memcpy(&d[0x800], "HELLO", 5);
    std::memcpy(&d[0x1000], "abc", 3);
    return d;
}

void TestProjectAndNames(const std::filesystem::path& temp) {
    const auto bytes = SyntheticProject();
    const auto file = temp / "project.bin";
    std::ofstream(file, std::ios::binary).write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    std::string error;
    const auto index = ReadProjectIndex(file, &error);
    CHECK(index && index->size() == 2);
    CHECK(index && (*index)[0].name == "a.pack" && (*index)[0].offset == 0x800 && (*index)[0].size == 5);
    CHECK(index && (*index)[1].name == "b.dat" && (*index)[1].offset == 0x1000);
    CHECK(index && std::string(reinterpret_cast<const char*>(ReadEntry(file, (*index)[0]).data()), 5) == "HELLO");
    const auto cut = temp / "cut.bin";
    std::ofstream(cut, std::ios::binary).write(reinterpret_cast<const char*>(bytes.data()), 0x20);
    CHECK(!ReadProjectIndex(cut, &error) && !error.empty());

    // Hashes (reference values from Python's xxhash, seed 0).
    std::vector<uint8_t> i8(32);
    for (size_t i = 0; i < i8.size(); ++i) i8[i] = static_cast<uint8_t>(i);
    CHECK(TextureHash(i8, 8, 4, 1) == 0xcbf59c5116ff32b4ull);
    const std::vector<uint8_t> c4(32, 0x12);
    CHECK(TextureHash(c4, 8, 8, 8) == 0xc2e5e11911ded5deull);
    const uint8_t pal[] = {0x80, 0x00, 0x81, 0x11, 0x82, 0x22, 0x83, 0x33};
    CHECK(PaletteHash(c4, 8, 8, 8, pal) == 0x9ceb41977776c426ull);              // indices 1..2 only
    CHECK(!PaletteHash(c4, 8, 8, 8, std::span<const uint8_t>(pal, 4)));          // palette too short

    ParsedName n{256, 128, 9, 0x0123456789abcdefull, true, false, 0xfedcba9876543210ull};
    CHECK(ReplacementName(n) == "tex1_256x128_0123456789abcdef_fedcba9876543210_9");
    n.paletteWildcard = true;
    CHECK(ReplacementName(n) == "tex1_256x128_0123456789abcdef_$_9");
    n.hasPalette = false;
    CHECK(ReplacementName(n) == "tex1_256x128_0123456789abcdef_9");
    const auto p = ParseName("tex1_64x32_00000000000000aa_0000000000000bbb_8");
    CHECK(p && p->width == 64 && p->height == 32 && p->textureHash == 0xaa && p->hasPalette && p->paletteHash == 0xbbb && p->format == 8);
    const auto q = ParseName("tex1_64x32_00000000000000aa_$_9");
    CHECK(q && q->paletteWildcard);
    CHECK(!ParseName("hola_64x32_aa_9") && !ParseName("tex1_64x32_zz_9") && !ParseName("tex1_64_aa_9"));
}
```

In `RunSelftest()`: create a temporary folder **with `ñ` in its name** (Review Focus 1) and pass it:

```cpp
    const auto temp = std::filesystem::temp_directory_path() / PathFromUtf8("texture-studio-selftest-ñ");
    std::filesystem::remove_all(temp);
    std::filesystem::create_directories(temp);
    TestProjectAndNames(temp);
```

(Include `<fstream>`, `"projectbin.h"`, `"names.h"`.)

- [ ] **Step 2: Build → fails.**

- [ ] **Step 3: Implement**

`projectbin.h`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// PROJECT.BIN index (tools/projectbin.py has the layout).
#pragma once
#include "core.h"
#include <optional>

namespace tstudio {
struct ProjectEntry { std::string name; uint64_t offset = 0; uint32_t size = 0; };
std::optional<std::vector<ProjectEntry>> ReadProjectIndex(const std::filesystem::path& file, std::string* error);
std::vector<uint8_t> ReadEntry(const std::filesystem::path& file, const ProjectEntry& entry);
} // namespace tstudio
```

`projectbin.cpp`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
#include "projectbin.h"

#include <fstream>

namespace tstudio {

std::optional<std::vector<ProjectEntry>> ReadProjectIndex(const std::filesystem::path& file, std::string* error) {
    auto fail = [&](const char* why) -> std::optional<std::vector<ProjectEntry>> {
        if (error) *error = why;
        return std::nullopt;
    };
    std::ifstream f(file, std::ios::binary);
    if (!f) return fail("No se puede abrir project.bin.");
    std::vector<uint8_t> head(0x40);
    if (!f.read(reinterpret_cast<char*>(head.data()), head.size())) return fail("project.bin está incompleto.");
    const uint32_t records = Be32(head, 0x14), order = Be32(head, 0x28), names = Be32(head, 0x2C), data = Be32(head, 0x34);
    if (!(0x40 <= records && records < order && order < names && names < data && data <= 0x1000000))
        return fail("project.bin no tiene el formato esperado.");
    std::vector<uint8_t> h(data);
    f.seekg(0);
    if (!f.read(reinterpret_cast<char*>(h.data()), h.size())) return fail("project.bin está incompleto.");
    const uint32_t count = (order - records) / 0x1C;
    std::vector<ProjectEntry> out;
    for (uint32_t i = 1; order + 8ull * (i + 1) <= names; ++i) {
        const uint32_t index = Be32(h, order + 8 * i), sector = Be32(h, order + 8 * i + 4);
        if (index == 0 && sector == 0) break;
        if (index >= count) return fail("project.bin no tiene el formato esperado.");
        const size_t rec = records + static_cast<size_t>(index) * 0x1C;
        const size_t nameStart = static_cast<size_t>(names) + Be32(h, rec + 4);
        size_t nameEnd = nameStart;
        while (nameEnd < h.size() && h[nameEnd] != 0) ++nameEnd;
        if (nameEnd >= h.size()) return fail("project.bin no tiene el formato esperado.");
        std::string name(h.begin() + nameStart, h.begin() + nameEnd);
        if (!name.empty() && name.front() == '/') name.erase(0, 1);
        out.push_back({std::move(name), data + static_cast<uint64_t>(sector) * 0x800, Be32(h, rec + 24)});
    }
    return out;
}

std::vector<uint8_t> ReadEntry(const std::filesystem::path& file, const ProjectEntry& entry) {
    std::ifstream f(file, std::ios::binary);
    std::vector<uint8_t> out(entry.size);
    f.seekg(static_cast<std::streamoff>(entry.offset));
    if (!f || !f.read(reinterpret_cast<char*>(out.data()), out.size())) return {};
    return out;
}

} // namespace tstudio
```

`names.h`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Dolphin-style replacement names, hashed like aurora's texture_replacement.cpp: XXH64 (seed 0) of the
// base level's padded bytes, and of the palette range between the smallest and largest index used.
#pragma once
#include "core.h"
#include <optional>

namespace tstudio {
uint64_t TextureHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt);
std::optional<uint64_t> PaletteHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt,
                                    std::span<const uint8_t> paletteBE);
struct ParsedName {
    uint32_t width = 0, height = 0, format = 0;
    uint64_t textureHash = 0;
    bool hasPalette = false, paletteWildcard = false;
    uint64_t paletteHash = 0;
};
std::string ReplacementName(const ParsedName& n);
std::optional<ParsedName> ParseName(std::string_view stem);
} // namespace tstudio
```

`names.cpp`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
#include "names.h"

#include "gx.h"

#define XXH_INLINE_ALL
#include <xxhash.h>

#include <algorithm>
#include <charconv>
#include <cstdio>

namespace tstudio {

uint64_t TextureHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt) {
    const size_t n = std::min<size_t>(TextureBytes(w, h, fmt), px.size());
    return XXH64(px.data(), n, 0);
}

std::optional<uint64_t> PaletteHash(std::span<const uint8_t> px, uint32_t w, uint32_t h, uint32_t fmt,
                                    std::span<const uint8_t> paletteBE) {
    const size_t n = TextureBytes(w, h, fmt);
    if (n == 0 || px.size() < n || !IsPaletted(fmt)) return std::nullopt;
    uint32_t lo = UINT32_MAX, hi = 0;
    auto see = [&](uint32_t v) { lo = std::min(lo, v); hi = std::max(hi, v); };
    if (fmt == 8) for (size_t i = 0; i < n; ++i) { see(px[i] & 15); see(px[i] >> 4); }
    else if (fmt == 9) for (size_t i = 0; i < n; ++i) see(px[i]);
    else for (size_t i = 0; i + 2 <= n; i += 2) see((px[i] << 8 | px[i + 1]) & 0x3FFF);
    const size_t off = 2ull * lo, size = 2ull * (hi + 1 - lo);
    if (off + size > paletteBE.size()) return std::nullopt;
    return XXH64(paletteBE.data() + off, size, 0);
}

std::string ReplacementName(const ParsedName& n) {
    char buf[96];
    if (!n.hasPalette)
        std::snprintf(buf, sizeof buf, "tex1_%ux%u_%016llx_%u", n.width, n.height,
                      static_cast<unsigned long long>(n.textureHash), n.format);
    else if (n.paletteWildcard)
        std::snprintf(buf, sizeof buf, "tex1_%ux%u_%016llx_$_%u", n.width, n.height,
                      static_cast<unsigned long long>(n.textureHash), n.format);
    else
        std::snprintf(buf, sizeof buf, "tex1_%ux%u_%016llx_%016llx_%u", n.width, n.height,
                      static_cast<unsigned long long>(n.textureHash), static_cast<unsigned long long>(n.paletteHash), n.format);
    return buf;
}

std::optional<ParsedName> ParseName(std::string_view stem) {
    std::vector<std::string_view> parts;
    for (size_t start = 0;;) {
        const size_t us = stem.find('_', start);
        parts.push_back(stem.substr(start, us == std::string_view::npos ? std::string_view::npos : us - start));
        if (us == std::string_view::npos) break;
        start = us + 1;
    }
    if ((parts.size() != 4 && parts.size() != 5) || parts[0] != "tex1") return std::nullopt;
    auto number = [](std::string_view s, int base, uint64_t& out) {
        return !s.empty() && std::from_chars(s.data(), s.data() + s.size(), out, base).ptr == s.data() + s.size();
    };
    ParsedName n;
    const size_t x = parts[1].find('x');
    uint64_t w, h, tex, fmt;
    if (x == std::string_view::npos || !number(parts[1].substr(0, x), 10, w) || !number(parts[1].substr(x + 1), 10, h) ||
        !number(parts[2], 16, tex) || !number(parts.back(), 10, fmt))
        return std::nullopt;
    n.width = static_cast<uint32_t>(w);
    n.height = static_cast<uint32_t>(h);
    n.textureHash = tex;
    n.format = static_cast<uint32_t>(fmt);
    if (parts.size() == 5) {
        n.hasPalette = true;
        if (parts[3] == "$") n.paletteWildcard = true;
        else if (!number(parts[3], 16, n.paletteHash)) return std::nullopt;
    }
    return n;
}

} // namespace tstudio
```

- [ ] **Step 4: Build → `selftest ok`.**

- [ ] **Step 5: Local check against the game's dumps (not committed)**

Add the mode `--check-dumps <project.bin> <dump folder>` in `studio.cpp`: it reads the index, walks every `.pack`, computes the name of each texture (as Task 5 will do in the catalog) and counts how many names in the folder match:

```cpp
#include "names.h"
#include "projectbin.h"
#include "gx.h"
#include <set>
// in main:
    if (argc == 4 && std::strcmp(argv[1], "--check-dumps") == 0) {
        std::string error;
        const auto index = tstudio::ReadProjectIndex(argv[2], &error);
        if (!index) { std::fprintf(stderr, "%s\n", error.c_str()); return 1; }
        std::set<std::string> mine;
        for (const auto& e : *index) {
            if (!e.name.ends_with(".pack")) continue;
            const auto d = tstudio::ReadEntry(argv[2], e);
            for (const auto& t : tstudio::FindTextures(d)) {
                const std::span<const uint8_t> px(d.data() + t.data, d.size() - t.data);
                tstudio::ParsedName n{t.width, t.height, t.format, tstudio::TextureHash(px, t.width, t.height, t.format)};
                if (tstudio::IsPaletted(t.format)) {
                    n.hasPalette = true;
                    std::optional<uint64_t> ph;
                    if (t.paletteEntries)
                        ph = tstudio::PaletteHash(px, t.width, t.height, t.format,
                                                  std::span<const uint8_t>(d.data() + t.paletteData, 2u * t.paletteEntries));
                    if (ph) n.paletteHash = *ph; else n.paletteWildcard = true;
                }
                mine.insert(tstudio::ReplacementName(n));
            }
        }
        int total = 0, exact = 0, texture = 0;
        std::set<std::string> texKeys;
        for (const auto& m : mine) texKeys.insert(m.substr(0, m.find('_', m.find('_', 5) + 1)));
        for (const auto& f : std::filesystem::directory_iterator(argv[3])) {
            const std::string stem = tstudio::Utf8(f.path().stem());
            if (!tstudio::ParseName(stem)) continue;
            ++total;
            exact += mine.count(stem) ? 1 : 0;
            texture += texKeys.count(stem.substr(0, stem.find('_', stem.find('_', 5) + 1))) ? 1 : 0;
        }
        std::printf("dumps %d, same texture %d, same full name %d\n", total, texture, exact);
        return 0;
    }
```

Run:

```bash
local/build/texture-studio/TextureStudio.exe --check-dumps local/disc/DATA/files/project.bin local/analysis/game-probe/UserData/Cache/texture_dumps
```

Expected (October 14 dump up to the main menu, 187 files): `same texture 39`, `same full name 36` or more. If it gives less, compare with `scratchpad/hashspike2.py` before continuing.

- [ ] **Step 6: Commit** — `Texture Studio: project.bin index and tex1 names`.

---

### Task 4: Images (PNG, runtime DDS) and size rules

**Files:**
- Create: `tools/texture-studio/images.h`, `images.cpp`
- Modify: `CMakeLists.txt`, `selftest.cpp`

**Interfaces:**
- Produces:

```cpp
std::optional<Image> LoadImage(const std::filesystem::path& file, std::string* error);  // PNG (any kind) or RGBA8 DDS
bool SavePng(const std::filesystem::path& file, const Image& image, std::string* error);
enum class SizeCheck { Ok, NotMultiple, WrongAspect, TooLarge };
SizeCheck CheckReplacementSize(uint32_t originalW, uint32_t originalH, uint32_t w, uint32_t h);
const char* SizeCheckMessage(SizeCheck);  // Spanish
```

- [ ] **Step 1: Tests (they fail)**

```cpp
void TestImages(const std::filesystem::path& temp) {
    Image img{3, 2, {}};
    for (int i = 0; i < 6; ++i) { img.rgba.insert(img.rgba.end(), {uint8_t(i * 40), 7, 200, uint8_t(255 - i)}); }
    const auto png = temp / PathFromUtf8("año.png");   // non-ASCII file name (Review Focus 1)
    std::string error;
    CHECK(SavePng(png, img, &error));
    const auto back = LoadImage(png, &error);
    CHECK(back && back->width == 3 && back->height == 2 && back->rgba == img.rgba);

    // RGBA8 DDS exactly as aurora's encode_rgba8_dds writes it.
    std::vector<uint8_t> dds(128 + 4 * 2 * 1, 0);
    std::memcpy(dds.data(), "DDS ", 4);
    auto le = [&](size_t o, uint32_t v) { for (int i = 0; i < 4; ++i) dds[o + i] = (v >> (8 * i)) & 0xFF; };
    le(4, 124); le(12, 1); le(16, 2); le(76, 32); le(80, 0x41); le(88, 32);
    le(92, 0xFF); le(96, 0xFF00); le(100, 0xFF0000); le(104, 0xFF000000u);
    const uint8_t px[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    std::memcpy(dds.data() + 128, px, 8);
    const auto ddsFile = temp / "t.dds";
    std::ofstream(ddsFile, std::ios::binary).write(reinterpret_cast<const char*>(dds.data()), dds.size());
    const auto d = LoadImage(ddsFile, &error);
    CHECK(d && d->width == 2 && d->height == 1 && d->rgba == std::vector<uint8_t>(px, px + 8));

    std::ofstream(temp / "roto.png", std::ios::binary) << "not a png";
    CHECK(!LoadImage(temp / "roto.png", &error) && !error.empty());

    CHECK(CheckReplacementSize(256, 128, 1024, 512) == SizeCheck::Ok);
    CHECK(CheckReplacementSize(256, 128, 256, 128) == SizeCheck::Ok);
    CHECK(CheckReplacementSize(256, 128, 600, 300) == SizeCheck::NotMultiple);
    CHECK(CheckReplacementSize(256, 128, 1024, 1024) == SizeCheck::WrongAspect);
    CHECK(CheckReplacementSize(1024, 1024, 8192, 8192) == SizeCheck::TooLarge);
}
```

`RunSelftest()`: `TestImages(temp);`. Since `SavePng`/`LoadImage` use SDL, `RunSelftest` does not need `SDL_Init` (only surfaces and IO).

- [ ] **Step 2: Build → fails.**

- [ ] **Step 3: Implement**

`images.h`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Replacement images: any PNG through SDL3 (stb_image underneath), the RGBA8 DDS files the runtime dumps,
// and the size rules for a replacement.
#pragma once
#include "core.h"
#include <optional>

namespace tstudio {
std::optional<Image> LoadImage(const std::filesystem::path& file, std::string* error);
bool SavePng(const std::filesystem::path& file, const Image& image, std::string* error);
enum class SizeCheck { Ok, NotMultiple, WrongAspect, TooLarge };
SizeCheck CheckReplacementSize(uint32_t originalW, uint32_t originalH, uint32_t w, uint32_t h);
const char* SizeCheckMessage(SizeCheck check);
} // namespace tstudio
```

`images.cpp`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
#include "images.h"

#include <SDL3/SDL.h>

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
        std::memcpy(&img.rgba[static_cast<size_t>(y) * img.width * 4], static_cast<const uint8_t*>(rgba->pixels) + y * rgba->pitch,
                    img.width * 4);
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
```

- [ ] **Step 4: Build → `selftest ok`.** If `SDL_LoadPNG` does not read the saved 3×2 image, check that the pinned SDL's `SDL_SavePNG` writes RGBA (if it writes RGB without alpha, the test detects it: fix by saving with explicit alpha).

- [ ] **Step 5: Commit** — `Texture Studio: PNG/DDS images and replacement size rules`.

---

### Task 5: Categories

**Files:**
- Create: `tools/texture-studio/categories.h`, `categories.cpp`
- Modify: `CMakeLists.txt`, `selftest.cpp`

**Interfaces:**
- Produces:

```cpp
struct Category { std::string group, subgroup; };
Category Categorize(std::string_view packName);           // "stadium_nyy.pack" -> {"Estadios", "Yankees (NYY)"}
const std::vector<std::string>& GroupOrder();              // display order of the groups
```

- [ ] **Step 1: Tests (they fail)**

```cpp
void TestCategories() {
    auto is = [](std::string_view pack, const char* g, const char* s) {
        const Category c = Categorize(pack);
        return c.group == g && c.subgroup == s;
    };
    CHECK(is("stadium_nyy.pack", "Estadios", "Yankees (NYY)"));
    CHECK(is("stadium_nyytbl.pack", "Estadios", "Yankees (NYY)"));
    CHECK(is("stadium_oka.pack", "Estadios", "Athletics (OAK)"));
    CHECK(is("stadium_sky_rainy.pack", "Estadios", "Cielos"));
    CHECK(is("stadium_org03.pack", "Estadios", "Original 3"));
    CHECK(is("PWM_mdl_uniform_MLB_CHC_00.pack", "Uniformes", "Cubs (CHC)"));
    CHECK(is("PWM_mdl_uniform_AAA_ARI_AAA_01.pack", "Uniformes", "Diamondbacks (ARI) AAA"));
    CHECK(is("env_player_card_03NYY_YANKEES.pack", "Cartas de jugador", "Yankees (NYY)"));
    CHECK(is("env_mainmenu.pack", "Menús", "Menú principal"));
    CHECK(is("env_shop.pack", "Menús", "shop"));
    CHECK(is("env_teamlogo_aaa01.pack", "Logos", "teamlogo_aaa01"));
    CHECK(is("mylife_bg_house01.pack", "MLB Life", "bg_house01"));
    CHECK(is("season_main_bg.pack", "Temporada", "main_bg"));
    CHECK(is("ScsBG__01.pack", "Success", "ScsBG__01"));
    CHECK(is("PWM_mdl_face_001.pack", "Caras", "face_001"));
    CHECK(is("raro.pack", "Otros", "raro"));
    CHECK(GroupOrder().front() == "Menús");
}
```

- [ ] **Step 2: Build → fails.**

- [ ] **Step 3: Implement**

`categories.h`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Pack name -> readable group and subgroup for the Studio's category tree. Names are only guesses from
// the pack names (no game data); unknown packs fall into "Otros".
#pragma once
#include <string>
#include <string_view>
#include <vector>

namespace tstudio {
struct Category { std::string group, subgroup; };
Category Categorize(std::string_view packName);
const std::vector<std::string>& GroupOrder();
} // namespace tstudio
```

`categories.cpp`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
#include "categories.h"

#include <algorithm>
#include <cctype>
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

std::string Upper(std::string_view s) {
    std::string out(s);
    for (char& c : out) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    return out;
}

std::string Team(std::string code) {
    code = Upper(code);
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
    std::string stem(packName.substr(0, packName.rfind('.')));
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
        std::string rest = stem.substr(16);
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

} // namespace tstudio
```

- [ ] **Step 4: Build → `selftest ok`.**

- [ ] **Step 5: Commit** — `Texture Studio: readable categories from pack names`.

---

### Task 6: Catalog

**Files:**
- Create: `tools/texture-studio/catalog.h`, `catalog.cpp`
- Modify: `CMakeLists.txt`, `selftest.cpp`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces:

```cpp
struct Location { uint32_t entry = 0, data = 0, paletteData = 0; uint16_t paletteEntries = 0; };
struct CatalogTexture {
    std::string name;                     // tex1_... (exact palette, or $ when the palette is unknown)
    ParsedName key;
    std::string group, subgroup;
    std::vector<Location> locations;      // every pack holding these exact bytes
    std::vector<std::string> paletteVariants;  // extra tex1_ names seen in captures (other palettes)
    std::vector<int> seenIn;              // capture session numbers
    std::filesystem::path captureFile;    // only for textures seen in game but in no pack
};
class Catalog {
public:
    bool Build(const std::filesystem::path& projectBin, std::atomic<float>* progress, std::string* error);
    const std::vector<CatalogTexture>& Textures() const;
    const std::vector<ProjectEntry>& Entries() const;
    int Find(std::string_view name) const;                       // -1 if absent
    int FindTexture(const ParsedName& n) const;                   // same pixels, any palette; -1 if absent
    Image Original(const CatalogTexture& t);                      // decoded original (thread-safe)
    void AddCapture(int session, const std::vector<std::filesystem::path>& files);  // dumps of one session
};
bool IsVideoFrame(const ParsedName& n);  // THP frames: I8 512x448 and 256x224
```

- [ ] **Step 1: Tests (they fail)**

Build a synthetic `project.bin` with two identical packs (the same texture in both) and a different one, and check grouping, categories, decoding and captures:

```cpp
// Fills `c` from a synthetic project.bin (Catalog holds a mutex: not movable, so filled in place).
void SyntheticCatalog(const std::filesystem::path& temp, Catalog& c) {
    // project.bin with stadium_nyy.pack and stadium_season.pack (same synthetic pack) and env_mainmenu.pack.
    const auto pack = SyntheticPack();
    std::vector<uint8_t> d(0x800, 0);
    auto put32 = [&](size_t o, uint32_t v) { for (int i = 0; i < 4; ++i) d[o + i] = (v >> (24 - 8 * i)) & 0xFF; };
    put32(0x14, 0x100); put32(0x28, 0x200); put32(0x2C, 0x300); put32(0x34, 0x800);
    const char names[] = "\0/stadium_nyy.pack\0/stadium_season.pack\0/env_mainmenu.pack\0";
    std::memcpy(&d[0x300], names, sizeof(names));
    const uint32_t nameOff[] = {1, 19, 40};
    for (uint32_t i = 0; i < 3; ++i) {
        const size_t rec = 0x100 + 0x1C * (i + 1);
        put32(rec + 4, nameOff[i]); put32(rec + 8, 1); put32(rec + 24, static_cast<uint32_t>(pack.size()));
        put32(0x208 + 8 * i, i + 1); put32(0x20C + 8 * i, i);
    }
    for (int i = 0; i < 3; ++i) d.insert(d.end(), pack.begin(), pack.end()), d.resize(0x800 + 0x800 * (i + 1), 0);
    d[0x800 + 2 * 0x800 + 0x100] = 0x55;  // env_mainmenu: different pixels for the C8 texture
    const auto file = temp / "catalog.bin";
    std::ofstream(file, std::ios::binary).write(reinterpret_cast<const char*>(d.data()), d.size());
    std::string error;
    std::atomic<float> progress{0};
    CHECK(c.Build(file, &progress, &error));
    CHECK(progress == 1.0f);
}

void TestCatalog(const std::filesystem::path& temp) {
    Catalog c;
    SyntheticCatalog(temp, c);
    CHECK(c.Textures().size() == 3);   // C8 (nyy+season), C4 (all three), C8 (mainmenu)
    const int shared = c.Find(c.Textures()[0].name);
    CHECK(shared == 0 && c.Textures()[0].locations.size() == 2 && c.Textures()[0].group == "Estadios");
    const auto& c4 = c.Textures()[1];
    CHECK(c4.key.format == 8 && c4.locations.size() == 3 && c4.key.hasPalette && !c4.key.paletteWildcard);
    const Image img = c.Original(c4);
    CHECK(img.width == 8 && img.height == 8);

    // A capture: one exact match, one palette variant of the C4 texture, one game-only texture, one video frame.
    const auto session = temp / "captures" / "1";
    std::filesystem::create_directories(session);
    ParsedName variant = c4.key;
    variant.paletteHash ^= 1;
    ParsedName only{16, 16, 5, 0x1234};
    ParsedName video{512, 448, 1, 0x99};
    const std::vector<std::filesystem::path> files{session / (c4.name + ".dds"), session / (ReplacementName(variant) + ".dds"),
                                                   session / (ReplacementName(only) + ".dds"), session / (ReplacementName(video) + ".dds")};
    c.AddCapture(1, files);
    CHECK(c.Textures()[1].seenIn == std::vector<int>{1});
    CHECK(c.Textures()[1].paletteVariants.size() == 1);
    const int game = c.Find(ReplacementName(only));
    CHECK(game >= 0 && c.Textures()[game].group == "Solo vistas en juego" && !c.Textures()[game].captureFile.empty());
    CHECK(c.Find(ReplacementName(video)) == -1);
    ParsedName any = c4.key;
    any.paletteWildcard = true;
    CHECK(c.FindTexture(any) == 1);
    CHECK(IsVideoFrame(video) && !IsVideoFrame(only));
}
```

- [ ] **Step 2: Build → fails.**

- [ ] **Step 3: Implement**

`catalog.h` with the declarations above plus:

```cpp
#pragma once
#include "categories.h"
#include "names.h"
#include "projectbin.h"
#include <atomic>
#include <mutex>
#include <unordered_map>
// ... structs and class as in Interfaces, private members:
private:
    std::filesystem::path project_;
    std::vector<ProjectEntry> entries_;
    std::vector<CatalogTexture> textures_;
    std::unordered_map<std::string, int> byName_;
    std::unordered_map<std::string, int> byTexture_;  // "WxH_hash_fmt" -> first texture with those pixels
    std::mutex packMutex_;
    uint32_t cachedEntry_ = UINT32_MAX;
    std::vector<uint8_t> cachedPack_;
    std::vector<uint8_t> Pack(uint32_t entry);
```

`catalog.cpp`:

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
#include "catalog.h"

#include "gx.h"
#include "images.h"
#include "pack.h"

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

std::vector<uint8_t> Catalog::Pack(uint32_t entry) {  // caller holds packMutex_
    if (entry != cachedEntry_) {
        cachedPack_ = ReadEntry(project_, entries_[entry]);
        cachedEntry_ = entry;
    }
    return cachedPack_;
}

Image Catalog::Original(const CatalogTexture& t) {
    if (!t.captureFile.empty()) return LoadImage(t.captureFile, nullptr).value_or(Image{});
    std::lock_guard lock(packMutex_);
    const Location& l = t.locations.front();
    const std::vector<uint8_t> d = Pack(l.entry);
    if (l.data >= d.size()) return {};
    const std::span<const uint8_t> palette =
        l.paletteEntries && l.paletteData + 2ull * l.paletteEntries <= d.size()
            ? std::span<const uint8_t>(d.data() + l.paletteData, 2u * l.paletteEntries)
            : std::span<const uint8_t>();
    return Decode(std::span<const uint8_t>(d.data() + l.data, d.size() - l.data), t.key.width, t.key.height, t.key.format, palette);
}

void Catalog::AddCapture(int session, const std::vector<std::filesystem::path>& files) {
    for (const auto& file : files) {
        const std::string stem = Utf8(file.stem());
        const auto n = ParseName(stem);
        if (!n || IsVideoFrame(*n)) continue;
        if (const int i = Find(stem); i >= 0) {
            if (textures_[i].seenIn.empty() || textures_[i].seenIn.back() != session) textures_[i].seenIn.push_back(session);
            continue;
        }
        if (const auto it = byTexture_.find(TextureKey(*n)); it != byTexture_.end()) {
            CatalogTexture& t = textures_[it->second];
            if (std::find(t.paletteVariants.begin(), t.paletteVariants.end(), stem) == t.paletteVariants.end())
                t.paletteVariants.push_back(stem);
            if (t.seenIn.empty() || t.seenIn.back() != session) t.seenIn.push_back(session);
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
```

(Include `<algorithm>` in `catalog.cpp`; `<cctype>` in `images.cpp`, `modfolder.cpp` and `transfer.cpp`.)

- [ ] **Step 4: Build → `selftest ok`.**

- [ ] **Step 5: Measure with the real game (not committed)**

Add `--catalog <project.bin>` to `studio.cpp`: it builds the catalog and prints the number of textures, the time and how many have `paletteWildcard`:

```cpp
#include "catalog.h"
#include <chrono>
// in main:
    if (argc == 3 && std::strcmp(argv[1], "--catalog") == 0) {
        tstudio::Catalog c;
        std::string error;
        const auto start = std::chrono::steady_clock::now();
        if (!c.Build(argv[2], nullptr, &error)) { std::fprintf(stderr, "%s\n", error.c_str()); return 1; }
        size_t wildcard = 0;
        for (const auto& t : c.Textures()) wildcard += t.key.paletteWildcard;
        std::printf("%zu textures, %zu with unknown palette, %.1f s\n", c.Textures().size(), wildcard,
                    std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count());
        return 0;
    }
```

Run: `local/build/texture-studio/TextureStudio.exe --catalog local/disc/DATA/files/project.bin`
Expected: about 11,000 distinct textures (fewer than 11,292, because repeated ones are grouped), about 430 with an unknown palette. Note the time. If it exceeds 5 s, open an extra disk-cache task before Task 10 (format: version, size and date of `project.bin`, and the serialised list).

- [ ] **Step 6: Commit** — `Texture Studio: catalog with grouping, decoding and captures`.

---

### Task 7: Configuration and mods

**Files:**
- Create: `tools/texture-studio/config.h`, `config.cpp`, `modfolder.h`, `modfolder.cpp`
- Modify: `CMakeLists.txt`, `selftest.cpp`

**Interfaces:**
- Produces:

```cpp
// config.h — minimal line-based editing of the game's Config.toml (same rules as the runtime's WriteSetting)
std::optional<std::string> ReadSetting(const std::filesystem::path& config, std::string_view section, std::string_view key);  // unquoted
std::vector<std::string> ReadEnabledMods(const std::filesystem::path& config);
bool SetModEnabled(const std::filesystem::path& config, const std::string& id, bool enabled);

// modfolder.h
struct ModInfo { std::string id; std::filesystem::path root; bool enabled = false; };
std::optional<std::string> ValidModName(std::string_view name, std::string* error);   // trimmed name or error
std::vector<ModInfo> ListMods(const std::filesystem::path& modsDir, const std::vector<std::string>& enabled);
bool CreateMod(const std::filesystem::path& modsDir, const std::string& name, std::string* error);
std::filesystem::path ReplacementPath(const std::filesystem::path& modRoot, const CatalogTexture& t, std::string_view name);
std::unordered_map<std::string, std::filesystem::path> FindReplacements(const std::filesystem::path& modRoot);  // stem -> file
bool WriteZip(const std::filesystem::path& modRoot, const std::filesystem::path& zip, std::string* error);
```

- [ ] **Step 1: Tests (they fail)**

```cpp
void TestConfigAndMods(const std::filesystem::path& temp) {
    const auto config = temp / "Config.toml";
    std::ofstream(config) << "[paths]\ndvd_root = 'D:\\Juegos\\MLB\\Data'\n\n[video]\nshow_fps = true\n";
    CHECK(ReadSetting(config, "paths", "dvd_root") == std::optional<std::string>("D:\\Juegos\\MLB\\Data"));
    CHECK(ReadEnabledMods(config).empty());
    CHECK(SetModEnabled(config, "HD Menús", true));
    CHECK(SetModEnabled(config, "Otro", true));
    CHECK((ReadEnabledMods(config) == std::vector<std::string>{"HD Menús", "Otro"}));
    CHECK(SetModEnabled(config, "Otro", false));
    CHECK((ReadEnabledMods(config) == std::vector<std::string>{"HD Menús"}));
    CHECK(ReadSetting(config, "video", "show_fps") == std::optional<std::string>("true"));  // untouched

    std::string error;
    CHECK(ValidModName("  HD Menús ñ  ", &error) == std::optional<std::string>("HD Menús ñ"));
    for (const char* bad : {"", "   ", "a/b", "a\\b", "CON", "x:y", "nombre.", "..", "a*b"})
        CHECK(!ValidModName(bad, &error));
    const auto mods = temp / "mods";
    CHECK(CreateMod(mods, "HD Menús ñ", &error));
    CHECK(!CreateMod(mods, "HD Menús ñ", &error) && error.find("existe") != std::string::npos);
    CHECK(std::filesystem::exists(mods / PathFromUtf8("HD Menús ñ") / "mod.toml"));
    const auto list = ListMods(mods, {"HD Menús ñ"});
    CHECK(list.size() == 1 && list[0].enabled);

    CatalogTexture t{"tex1_8x8_00000000000000aa_9", {}, "Estadios", "Yankees (NYY)"};
    const auto root = mods / PathFromUtf8("HD Menús ñ");
    const auto path = ReplacementPath(root, t, t.name);
    const auto rel = path.lexically_relative(root).generic_u8string();
    CHECK(std::string(rel.begin(), rel.end()) == "textures/Estadios/Yankees (NYY)/tex1_8x8_00000000000000aa_9.png");
    std::filesystem::create_directories(path.parent_path());
    std::ofstream(path, std::ios::binary) << "png";
    std::ofstream(root / "textures" / "nota.txt") << "x";
    const auto found = FindReplacements(root);
    CHECK(found.size() == 1 && found.count(t.name));

    const auto zip = temp / "mod.zip";
    CHECK(WriteZip(root, zip, &error));
    std::ifstream z(zip, std::ios::binary);
    const std::string bytes((std::istreambuf_iterator<char>(z)), {});
    CHECK(bytes.substr(0, 4) == std::string("PK\x03\x04", 4));
    CHECK(bytes.find("HD Menús ñ/mod.toml") != std::string::npos);
    CHECK(bytes.find("tex1_8x8_00000000000000aa_9.png") != std::string::npos);
    CHECK(bytes.find("nota.txt") == std::string::npos);    // only mod.toml and replacement images
    CHECK(bytes.find(std::string("PK\x05\x06", 4)) != std::string::npos);
}
```

- [ ] **Step 2: Build → fails.**

- [ ] **Step 3: Implement `config.cpp`**

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Reads and writes single keys of Config.toml line by line, like the runtime's WriteSetting: comments
// and every other line stay as they are.
#include "config.h"

#include <fstream>

namespace tstudio {
namespace {
std::string Trim(std::string_view s) {
    const size_t a = s.find_first_not_of(" \t\r\n"), b = s.find_last_not_of(" \t\r\n");
    return a == std::string_view::npos ? std::string() : std::string(s.substr(a, b - a + 1));
}
std::vector<std::string> Lines(const std::filesystem::path& file) {
    std::ifstream in(file);
    std::vector<std::string> lines;
    for (std::string line; std::getline(in, line);) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        lines.push_back(line);
    }
    return lines;
}
// [first, end) of the section's lines (after its header); first == end == lines.size() if absent.
std::pair<size_t, size_t> Section(const std::vector<std::string>& lines, std::string_view section) {
    size_t start = lines.size();
    for (size_t i = 0; i < lines.size(); ++i) {
        const std::string t = Trim(lines[i]);
        if (t.size() < 2 || t.front() != '[' || t.back() != ']') continue;
        if (start != lines.size()) return {start, i};
        if (Trim(std::string_view(t).substr(1, t.size() - 2)) == section) start = i + 1;
    }
    return {start, lines.size()};
}
size_t KeyLine(const std::vector<std::string>& lines, std::pair<size_t, size_t> range, std::string_view key) {
    for (size_t i = range.first; i < range.second; ++i) {
        const size_t eq = lines[i].find('=');
        if (eq != std::string::npos && Trim(std::string_view(lines[i]).substr(0, eq)) == key) return i;
    }
    return lines.size();
}
std::string Unquote(std::string v) {
    if (v.size() >= 2 && (v.front() == '"' || v.front() == '\'') && v.back() == v.front()) return v.substr(1, v.size() - 2);
    return v;
}
} // namespace

std::optional<std::string> ReadSetting(const std::filesystem::path& config, std::string_view section, std::string_view key) {
    const auto lines = Lines(config);
    const size_t i = KeyLine(lines, Section(lines, section), key);
    if (i == lines.size()) return std::nullopt;
    std::string value = Trim(std::string_view(lines[i]).substr(lines[i].find('=') + 1));
    if (const size_t hash = value.find(" #"); hash != std::string::npos) value = Trim(value.substr(0, hash));
    return Unquote(value);
}

std::vector<std::string> ReadEnabledMods(const std::filesystem::path& config) {
    std::vector<std::string> out;
    const auto value = ReadSetting(config, "mods", "enabled");
    if (!value) return out;
    for (size_t i = 0; i < value->size(); ++i) {
        const char q = (*value)[i];
        if (q != '"' && q != '\'') continue;
        std::string item;
        for (++i; i < value->size() && (*value)[i] != q; ++i) {
            if (q == '"' && (*value)[i] == '\\' && i + 1 < value->size()) ++i;
            item += (*value)[i];
        }
        out.push_back(item);
    }
    return out;
}

bool SetModEnabled(const std::filesystem::path& config, const std::string& id, bool enabled) {
    auto list = ReadEnabledMods(config);
    std::erase(list, id);
    if (enabled) list.push_back(id);
    std::string value = "[";
    for (size_t i = 0; i < list.size(); ++i) {
        value += i ? ", \"" : "\"";
        for (char c : list[i]) { if (c == '"' || c == '\\') value += '\\'; value += c; }
        value += '"';
    }
    value += "]";
    auto lines = Lines(config);
    auto range = Section(lines, "mods");
    if (range.first == lines.size()) {
        if (!lines.empty() && !lines.back().empty()) lines.emplace_back();
        lines.emplace_back("[mods]");
        range = {lines.size(), lines.size()};
    }
    const size_t i = KeyLine(lines, range, "enabled");
    if (i == lines.size()) lines.insert(lines.begin() + range.second, "enabled = " + value);
    else lines[i] = "enabled = " + value;
    std::ofstream out(config, std::ios::binary | std::ios::trunc);
    for (const auto& line : lines) out << line << "\r\n";
    return static_cast<bool>(out);
}

} // namespace tstudio
```

`config.h` declares the three functions (with `#include "core.h"` and `<optional>`).

- [ ] **Step 4: Implement `modfolder.cpp`**

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Player mods: mods/<name>/mod.toml + textures/<group>/<subgroup>/tex1_....png, and a stored .zip to share them.
#include "modfolder.h"

#include <array>
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
    for (char c : s) out += std::string_view("<>:\"/\\|?*").find(c) == std::string_view::npos && static_cast<unsigned char>(c) >= 32 ? c : '_';
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
} // namespace

std::optional<std::string> ValidModName(std::string_view raw, std::string* error) {
    const std::string name = Trim(raw);
    auto fail = [&](const char* why) -> std::optional<std::string> { if (error) *error = why; return std::nullopt; };
    if (name.empty()) return fail("Escribe un nombre para el mod.");
    if (name.size() > 60) return fail("El nombre es demasiado largo (máximo 60 caracteres).");
    for (char c : name)
        if (static_cast<unsigned char>(c) < 32 || std::string_view("<>:\"/\\|?*").find(c) != std::string_view::npos)
            return fail("El nombre no puede llevar < > : \" / \\ | ? *");
    if (name.back() == '.' || name == "." || name == "..") return fail("El nombre no puede terminar en punto.");
    std::string upper = name;
    for (char& c : upper) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    for (const char* reserved : {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "LPT1", "LPT2", "LPT3"})
        if (upper == reserved) return fail("Windows no permite ese nombre de carpeta.");
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
    if (std::filesystem::exists(root, ec)) { if (error) *error = "Ya existe un mod con ese nombre."; return false; }
    std::filesystem::create_directories(root / "textures", ec);
    std::ofstream toml(root / "mod.toml", std::ios::binary);
    std::string escaped;
    for (char c : *name) { if (c == '"' || c == '\\') escaped += '\\'; escaped += c; }
    toml << "name = \"" << escaped << "\"\r\nversion = \"1\"\r\n"
         << "description = \"Texturas creadas con Power Pros Wii 2008 Texture Studio.\"\r\n";
    if (ec || !toml) { if (error) *error = "No se puede crear la carpeta del mod (¿permisos?)."; return false; }
    return true;
}

std::filesystem::path ReplacementPath(const std::filesystem::path& modRoot, const CatalogTexture& t, std::string_view name) {
    return modRoot / "textures" / PathFromUtf8(Safe(t.group)) / PathFromUtf8(Safe(t.subgroup)) / PathFromUtf8(std::string(name) + ".png");
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
            if (const auto rel = it->path().lexically_relative(modRoot).generic_u8string(); true)
                files.emplace_back(top + "/" + std::string(rel.begin(), rel.end()), it->path());
    std::ofstream out(zip, std::ios::binary | std::ios::trunc);
    auto u16 = [&](std::string& s, uint16_t v) { s += static_cast<char>(v & 0xFF); s += static_cast<char>(v >> 8); };
    auto u32 = [&](std::string& s, uint32_t v) { u16(s, v & 0xFFFF); u16(s, v >> 16); };
    std::string central;
    uint64_t offset = 0;
    for (const auto& [name, path] : files) {
        std::ifstream in(path, std::ios::binary);
        const std::string data((std::istreambuf_iterator<char>(in)), {});
        if (offset + data.size() > 0xFFFFFFF0ull) { if (error) *error = "El mod pasa de 4 GB: no cabe en un .zip simple."; return false; }
        const uint32_t crc = Crc32(data);
        std::string local = std::string("PK\x03\x04", 4);
        u16(local, 20); u16(local, 0x0800); u16(local, 0); u16(local, 0); u16(local, 0x21);  // UTF-8 names, stored
        u32(local, crc); u32(local, static_cast<uint32_t>(data.size())); u32(local, static_cast<uint32_t>(data.size()));
        u16(local, static_cast<uint16_t>(name.size())); u16(local, 0);
        out << local << name << data;
        std::string c = std::string("PK\x01\x02", 4);
        u16(c, 20); u16(c, 20); u16(c, 0x0800); u16(c, 0); u16(c, 0); u16(c, 0x21);
        u32(c, crc); u32(c, static_cast<uint32_t>(data.size())); u32(c, static_cast<uint32_t>(data.size()));
        u16(c, static_cast<uint16_t>(name.size())); u16(c, 0); u16(c, 0); u16(c, 0); u16(c, 0); u32(c, 0);
        u32(c, static_cast<uint32_t>(offset));
        central += c + name;
        offset += local.size() + name.size() + data.size();
    }
    std::string end = std::string("PK\x05\x06", 4);
    u16(end, 0); u16(end, 0); u16(end, static_cast<uint16_t>(files.size())); u16(end, static_cast<uint16_t>(files.size()));
    u32(end, static_cast<uint32_t>(central.size())); u32(end, static_cast<uint32_t>(offset)); u16(end, 0);
    out << central << end;
    if (!out) { if (error) *error = "No se puede escribir el .zip."; return false; }
    return true;
}

} // namespace tstudio
```

`modfolder.h` declares what is listed in Interfaces and includes `"catalog.h"`, `<algorithm>`, `<optional>`, `<unordered_map>`.

- [ ] **Step 5: Build → `selftest ok`.** Open the `mod.zip` in the temporary folder with Windows Explorer and check that it shows `HD Menús ñ\mod.toml` and the texture path with the `ñ` written correctly.

- [ ] **Step 6: Commit** — `Texture Studio: Config.toml mods list, mod folders and zip`.

---

### Task 8: Import and export (core)

**Files:**
- Create: `tools/texture-studio/transfer.h`, `transfer.cpp`
- Modify: `CMakeLists.txt`, `selftest.cpp`

**Interfaces:**
- Consumes: `Catalog`, `LoadImage`, `SavePng`, `CheckReplacementSize`, `ReplacementPath`, `ParseName`.
- Produces:

```cpp
struct ImportResult { std::string file; std::string texture; bool ok = false; std::string message; };
// One image onto one texture (the selected one). allPalettes: write the $ name instead of the exact one.
ImportResult ImportOne(Catalog& c, int texture, const std::filesystem::path& image, const std::filesystem::path& modRoot, bool allPalettes);
// A folder (recursive): files whose name is a known tex1_ name; others reported.
std::vector<ImportResult> ImportFolder(Catalog& c, const std::filesystem::path& folder, const std::filesystem::path& modRoot);
// Original images as PNG under <out>/<group>/<subgroup>/<name>.png. Returns how many were written.
size_t Export(Catalog& c, const std::vector<int>& textures, const std::filesystem::path& out, std::vector<std::string>* problems);
```

Behaviour:
- `ImportOne` validates the size (`WrongAspect`/`TooLarge` → `ok=false`, `NotMultiple` → `ok=true` with the warning in `message`), writes an RGBA PNG (even if the input is DDS or another PNG) to `ReplacementPath(modRoot, t, name)`, and also one copy for each of the texture's `paletteVariants` (the same file with its name) except with `allPalettes`. If a replacement with the same name existed in another subfolder of the mod (or as `.dds`), it deletes it first so as not to leave duplicates.
- `ImportFolder` walks the folder; for each `.png`/`.dds` with a valid `ParseName` it looks up the texture (`Find`); if it does not exist → `ok=false`, "No corresponde a ninguna textura del juego" ("Does not match any game texture"); if two files give the same name (`.png` and `.dds`) the `.png` wins and the other is reported as "Repetido: se usó el .png" ("Duplicate: the .png was used"). Files without a `tex1_` name → "Nombre no reconocido" ("Name not recognised").

- [ ] **Step 1: Tests (they fail)** — on the synthetic catalog of Task 6 (move its construction into a function `Catalog SyntheticCatalog(const std::filesystem::path& temp)` in `selftest.cpp` and reuse it):

```cpp
void TestTransfer(const std::filesystem::path& temp) {
    Catalog c;
    SyntheticCatalog(temp, c);
    const auto modRoot = temp / "mods" / "Prueba";
    std::filesystem::create_directories(modRoot / "textures");
    const CatalogTexture& t = c.Textures()[1];                     // 8x8 C4
    const auto exportDir = temp / PathFromUtf8("exportación");
    std::vector<std::string> problems;
    CHECK(Export(c, {0, 1, 2}, exportDir, &problems) == 3 && problems.empty());
    const auto exported = exportDir / PathFromUtf8(t.group) / PathFromUtf8(t.subgroup) / PathFromUtf8(t.name + ".png");
    CHECK(std::filesystem::exists(exported));

    // x4 upscale of the exported image: accepted and written under the mod.
    Image big{32, 32, std::vector<uint8_t>(32 * 32 * 4, 200)};
    const auto bigFile = temp / "big.png";
    CHECK(SavePng(bigFile, big, nullptr));
    const auto r = ImportOne(c, 1, bigFile, modRoot, false);
    CHECK(r.ok && std::filesystem::exists(ReplacementPath(modRoot, t, t.name)));
    // Wrong aspect (32x16 onto the 8x8 texture): rejected.
    Image wide{32, 16, std::vector<uint8_t>(32 * 16 * 4, 1)};
    CHECK(SavePng(temp / "wide.png", wide, nullptr));
    const auto bad = ImportOne(c, 1, temp / "wide.png", modRoot, false);
    CHECK(!bad.ok && bad.message.find("proporción") != std::string::npos);

    // Folder import: one good file, one unknown tex1 name, one random file, a .png/.dds pair.
    const auto in = temp / "chainner";
    std::filesystem::create_directories(in / "sub");
    const ParsedName& k2 = c.Textures()[2].key;
    Image ok2{k2.width * 2, k2.height * 2, std::vector<uint8_t>(k2.width * k2.height * 16, 9)};
    CHECK(SavePng(in / "sub" / PathFromUtf8(c.Textures()[2].name + ".png"), ok2, nullptr));
    std::ofstream(in / PathFromUtf8(c.Textures()[2].name + ".dds"), std::ios::binary) << "dup";
    CHECK(SavePng(in / "tex1_8x8_0000000000000001_5.png", Image{8, 8, std::vector<uint8_t>(256, 1)}, nullptr));
    std::ofstream(in / "foto.png", std::ios::binary) << "x";
    ParsedName any = t.key;                                         // "$" name: every palette of texture 1
    any.paletteWildcard = true;
    CHECK(SavePng(in / PathFromUtf8(ReplacementName(any) + ".png"), Image{16, 16, std::vector<uint8_t>(16 * 16 * 4, 3)}, nullptr));
    const auto report = ImportFolder(c, in, modRoot);
    int good = 0, unknown = 0, unnamed = 0, duplicate = 0;
    for (const auto& x : report) {
        good += x.ok;
        unknown += x.message.find("ninguna textura") != std::string::npos;
        unnamed += x.message.find("no reconocido") != std::string::npos;
        duplicate += x.message.find("Repetido") != std::string::npos;
    }
    CHECK(good == 2 && unknown == 1 && unnamed == 1 && duplicate == 1);
}
```

- [ ] **Step 2: Build → fails.**

- [ ] **Step 3: Implement `transfer.cpp`**

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
#include "transfer.h"

#include "images.h"
#include "modfolder.h"

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

ImportResult ImportOne(Catalog& c, int index, const std::filesystem::path& file, const std::filesystem::path& modRoot, bool allPalettes) {
    const CatalogTexture& t = c.Textures()[index];
    ImportResult r{Utf8(file.filename()), t.name};
    std::string error;
    const auto img = LoadImage(file, &error);
    if (!img) { r.message = error; return r; }
    const SizeCheck size = CheckReplacementSize(t.key.width, t.key.height, img->width, img->height);
    if (size == SizeCheck::WrongAspect || size == SizeCheck::TooLarge) { r.message = SizeCheckMessage(size); return r; }
    std::vector<std::string> names;
    if (allPalettes && t.key.hasPalette) {
        ParsedName any = t.key;
        any.paletteWildcard = true;
        names.push_back(ReplacementName(any));
    } else {
        names.push_back(t.name);
        names.insert(names.end(), t.paletteVariants.begin(), t.paletteVariants.end());
    }
    for (const auto& name : names)
        if (!WriteReplacement(*img, modRoot, t, name, &error)) { r.message = error; return r; }
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
        if (!ParseName(stem)) { out.push_back({Utf8(it->path().filename()), "", false, "Nombre no reconocido (debe empezar por tex1_)."}); continue; }
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
        if (i < 0) { out.push_back({Utf8(file.filename()), stem, false, "No corresponde a ninguna textura del juego."}); continue; }
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
        if (img.Empty()) { if (problems) problems->push_back(t.name + ": formato no soportado para exportar"); continue; }
        const auto file = out / PathFromUtf8(t.group) / PathFromUtf8(t.subgroup) / PathFromUtf8(t.name + ".png");
        if (SavePng(file, img, &error)) ++written;
        else if (problems) problems->push_back(t.name + ": " + error);
    }
    return written;
}

} // namespace tstudio
```

A `…_$_<fmt>.png` file applies to every palette of that texture: it is looked up with `Catalog::FindTexture` (Task 6).

- [ ] **Step 4: Build → `selftest ok`.**

- [ ] **Step 5: Commit** — `Texture Studio: import (single, folder) and export`.

---

### Task 9: In-game capture

**Files:**
- Create: `tools/texture-studio/capture.h`, `capture.cpp`
- Modify: `CMakeLists.txt`, `selftest.cpp`

**Interfaces:**
- Produces:

```cpp
class Capture {
public:
    bool Start(const std::filesystem::path& gameExe, const std::filesystem::path& dumpsDir, std::string* error);
    bool Running() const;
    // Moves the dumps that appeared since Start into <capturesDir>/<n>/; returns n and the files (n = 0 if none).
    std::pair<int, std::vector<std::filesystem::path>> Collect(const std::filesystem::path& capturesDir);
private:
    void* process_ = nullptr;  // HANDLE
    std::filesystem::path dumps_;
    std::set<std::string> before_;
};
std::vector<std::pair<int, std::vector<std::filesystem::path>>> LoadSessions(const std::filesystem::path& capturesDir);
```

- [ ] **Step 1: Tests (they fail)** — without launching the game: simulate with the dump folder.

```cpp
void TestCapture(const std::filesystem::path& temp) {
    const auto dumps = temp / "texture_dumps";
    const auto captures = temp / "captures";
    std::filesystem::create_directories(dumps);
    std::ofstream(dumps / "tex1_8x8_0000000000000001_5.dds") << "old";   // existed before the capture
    Capture cap;
    cap.SeedForTest(dumps);                                                // records "before" without a process
    std::ofstream(dumps / "tex1_8x8_0000000000000002_5.dds") << "new";
    auto [n, files] = cap.Collect(captures);
    CHECK(n == 1 && files.size() == 1 && files[0].filename() == "tex1_8x8_0000000000000002_5.dds");
    CHECK(std::filesystem::exists(dumps / "tex1_8x8_0000000000000001_5.dds"));
    Capture empty;
    empty.SeedForTest(temp / "no-existe");                                 // Review Focus 5
    CHECK(empty.Collect(captures).first == 0);
    const auto sessions = LoadSessions(captures);
    CHECK(sessions.size() == 1 && sessions[0].first == 1 && sessions[0].second.size() == 1);
}
```

Add to the class the public method `void SeedForTest(const std::filesystem::path& dumpsDir);` (stores `dumps_` and `before_` like `Start`, without a process).

- [ ] **Step 2: Build → fails.**

- [ ] **Step 3: Implement `capture.cpp`**

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Runs the game with WIICOMPILED_TEXTURE_DUMPS=1 (patch wiicompiled-texture-studio) and the launcher
// skipped, then keeps the textures it dumped as a numbered capture session.
#include "capture.h"

#include "core.h"

#include <windows.h>

#include <algorithm>

namespace tstudio {
namespace {
std::set<std::string> Names(const std::filesystem::path& dir) {
    std::set<std::string> out;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(dir, ec)) out.insert(Utf8(e.path().filename()));
    return out;
}
} // namespace

void Capture::SeedForTest(const std::filesystem::path& dumpsDir) {
    dumps_ = dumpsDir;
    before_ = Names(dumpsDir);
}

bool Capture::Start(const std::filesystem::path& gameExe, const std::filesystem::path& dumpsDir, std::string* error) {
    SeedForTest(dumpsDir);
    std::wstring command = L"\"" + gameExe.wstring() + L"\"";
    SetEnvironmentVariableW(L"WIICOMPILED_TEXTURE_DUMPS", L"1");
    SetEnvironmentVariableW(L"WIICOMPILED_SKIP_LAUNCHER", L"1");
    STARTUPINFOW si{sizeof si};
    PROCESS_INFORMATION pi{};
    const BOOL ok = CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, 0, nullptr,
                                   gameExe.parent_path().c_str(), &si, &pi);
    SetEnvironmentVariableW(L"WIICOMPILED_TEXTURE_DUMPS", nullptr);
    SetEnvironmentVariableW(L"WIICOMPILED_SKIP_LAUNCHER", nullptr);
    if (!ok) {
        if (error) *error = "No se pudo abrir el juego para capturar (" + std::to_string(GetLastError()) + ").";
        return false;
    }
    CloseHandle(pi.hThread);
    process_ = pi.hProcess;
    return true;
}

bool Capture::Running() const {
    return process_ != nullptr && WaitForSingleObject(static_cast<HANDLE>(process_), 0) == WAIT_TIMEOUT;
}

std::pair<int, std::vector<std::filesystem::path>> Capture::Collect(const std::filesystem::path& capturesDir) {
    if (process_) { CloseHandle(static_cast<HANDLE>(process_)); process_ = nullptr; }
    std::vector<std::filesystem::path> fresh;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(dumps_, ec))
        if (e.is_regular_file(ec) && !before_.count(Utf8(e.path().filename()))) fresh.push_back(e.path());
    if (fresh.empty()) return {0, {}};
    int n = 1;
    for (const auto& [session, _] : LoadSessions(capturesDir)) n = std::max(n, session + 1);
    const auto dir = capturesDir / std::to_string(n);
    std::filesystem::create_directories(dir, ec);
    std::vector<std::filesystem::path> moved;
    for (const auto& f : fresh) {
        const auto target = dir / f.filename();
        std::filesystem::rename(f, target, ec);
        if (ec) { ec.clear(); std::filesystem::copy_file(f, target, ec); std::filesystem::remove(f, ec); }
        moved.push_back(target);
    }
    return {n, moved};
}

std::vector<std::pair<int, std::vector<std::filesystem::path>>> LoadSessions(const std::filesystem::path& capturesDir) {
    std::vector<std::pair<int, std::vector<std::filesystem::path>>> out;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(capturesDir, ec)) {
        const int n = std::atoi(Utf8(e.path().filename()).c_str());
        if (!e.is_directory(ec) || n <= 0) continue;
        std::vector<std::filesystem::path> files;
        for (const auto& f : std::filesystem::directory_iterator(e.path(), ec)) files.push_back(f.path());
        out.emplace_back(n, std::move(files));
    }
    std::sort(out.begin(), out.end());
    return out;
}

} // namespace tstudio
```

- [ ] **Step 4: Build → `selftest ok`.**

- [ ] **Step 5: Commit** — `Texture Studio: in-game capture sessions`.

---

### Task 10: User interface (style B)

**Files:**
- Modify: `tools/texture-studio/studio.cpp` (replace the provisional `main`; the `--selftest`, `--list-pack`, `--check-dumps`, `--catalog` modes are kept in front)
- Create: `tools/texture-studio/ui.h` (style B colours and widgets)

**Interfaces:**
- Consumes: the whole core.
- Command line (used by the launcher, Task 11): `--config <Config.toml> --userdata <UserData> --mods <mods folder> --game <game exe>`. Without arguments: everything relative to the Studio's folder (`UserData/Config.toml`, `UserData`, `mods`, `MLBPowerPros2008.exe`), which is the Setup installation (portable).

- [ ] **Step 1: `ui.h` — colours and widgets**

```cpp
// SPDX-License-Identifier: GPL-3.0-or-later
// Style B of the approved mockup: calm dark panels, blue title band (no red line), Power Pros pills.
#pragma once
#include "power_pros_ui.h"

namespace tstudio::ui {
using power_pros_ui::Rgba;
inline const ImU32 kWindow = Rgba(16, 24, 38), kPanel = Rgba(23, 34, 56), kPanelBorder = Rgba(47, 70, 112),
                   kPanelHeader = Rgba(29, 43, 71), kHeaderText = Rgba(127, 182, 255), kMuted = Rgba(169, 196, 255),
                   kBandTop = Rgba(11, 58, 158), kBandBottom = Rgba(8, 48, 127), kYellow = Rgba(255, 210, 63),
                   kBlueTop = Rgba(54, 163, 255), kBlueBottom = Rgba(11, 95, 208), kGreenTop = Rgba(90, 214, 90),
                   kGreenBottom = Rgba(24, 138, 42), kOrangeTop = Rgba(255, 178, 58), kOrangeBottom = Rgba(224, 106, 0),
                   kRedTop = Rgba(255, 106, 106), kRedBottom = Rgba(200, 30, 42), kGreyTop = Rgba(138, 160, 200),
                   kGreyBottom = Rgba(74, 95, 138);

// Glossy pill button sized to its label. Returns true when clicked.
inline bool Pill(const char* label, ImU32 top, ImU32 bottom, float u, bool small = false, bool enabled = true) {
    using namespace power_pros_ui;
    const float fs = (small ? 15.0f : 18.0f) * u;
    const ImVec2 ts = TextSize(g_bold, fs, label);
    const ImVec2 size(ts.x + 30 * u, fs + 14 * u);
    const ImVec2 p = ImGui::GetCursorScreenPos();
    ImGui::PushID(label);
    const bool clicked = ImGui::InvisibleButton("##pill", ImVec2(size.x + 8 * u, size.y + 10 * u)) && enabled;
    ImGui::PopID();
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const ImVec2 a(p.x + 4 * u, p.y + 4 * u), b(a.x + size.x, a.y + size.y);
    const bool hot = enabled && ImGui::IsItemHovered();
    power_pros_ui::Pill(dl, a, b, enabled ? (hot ? IM_COL32_WHITE : top) : kGreyTop, enabled ? bottom : kGreyBottom, u * 0.6f);
    ShadowedText(dl, g_bold, fs, ImVec2(a.x + (size.x - ts.x) * 0.5f, a.y + (size.y - fs) * 0.5f), IM_COL32_WHITE, label);
    return clicked;
}

// Panel = child window with the calm colours and a header strip.
inline bool BeginPanel(const char* id, const char* header, ImVec2 size) {
    ImGui::PushStyleColor(ImGuiCol_ChildBg, ImGui::ColorConvertU32ToFloat4(kPanel));
    ImGui::PushStyleColor(ImGuiCol_Border, ImGui::ColorConvertU32ToFloat4(kPanelBorder));
    ImGui::PushStyleVar(ImGuiStyleVar_ChildRounding, 12.0f);
    const bool open = ImGui::BeginChild(id, size, ImGuiChildFlags_Borders);
    if (header) {
        ImDrawList* dl = ImGui::GetWindowDrawList();
        const ImVec2 p = ImGui::GetWindowPos();
        const float h = ImGui::GetFontSize() + 12;
        dl->AddRectFilled(p, ImVec2(p.x + ImGui::GetWindowWidth(), p.y + h), kPanelHeader, 12.0f, ImDrawFlags_RoundCornersTop);
        dl->AddText(ImVec2(p.x + 12, p.y + 6), kHeaderText, header);
        ImGui::SetCursorPosY(h + 6);
    }
    return open;
}
inline void EndPanel() {
    ImGui::EndChild();
    ImGui::PopStyleVar();
    ImGui::PopStyleColor(2);
}
} // namespace tstudio::ui
```

- [ ] **Step 2: State and startup**

In `studio.cpp`, the `App` structure:

```cpp
struct Paths { std::filesystem::path config, userData, mods, game; };
struct App {
    Paths paths;
    tstudio::Catalog catalog;
    std::thread builder;
    std::atomic<float> progress{0};
    std::atomic<bool> built{false};
    std::string buildError;
    std::vector<tstudio::ModInfo> mods;
    int activeMod = -1;
    std::unordered_map<std::string, std::filesystem::path> replacements;  // of the active mod
    std::string group = "Menús", subgroup;   // selected category ("" = whole group); group "Todo" = all
    std::string search;
    bool onlyReplaced = false, onlySeen = false;
    std::vector<int> visible;                // filtered texture indices
    int selected = -1;
    bool allPalettes = false;
    std::string toast;                       // last message, shown in the bottom bar
    std::vector<tstudio::ImportResult> report; bool showReport = false;
    tstudio::Capture capture; bool capturing = false;
    std::vector<std::pair<int, std::vector<std::filesystem::path>>> sessions;
    char newModName[64] = "";
    bool showNewMod = false;
};
```

Startup in `main` (after the development modes):

1. `SetProcessDPIAware()`, `SDL_Init(SDL_INIT_VIDEO)`, resizable 1400×860 window `"Power Pros Wii 2008 Texture Studio"`, renderer with vsync, ImGui with `IniFilename = nullptr`, `LoadFonts()` (like `tools/setup/setup.cpp:229-241`).
2. Paths: read the `--config/--userdata/--mods/--game` arguments; by default relative to `SDL_GetBasePath()`.
3. `dvd_root` = `ReadSetting(config, "paths", "dvd_root")`; if it is relative, relative to the game folder. `project.bin` = `<dvd_root>/files/project.bin`. If anything is missing: error screen with "Game not found. Install it with the MLB Power Pros 2008 Setup and open the Studio from the launcher (HERRAMIENTAS → EDITOR DE TEXTURAS)." and an "Exit" button.
4. `builder` thread → `catalog.Build(projectBin, &progress, &buildError)`; when it finishes, `built = true`. Meanwhile, the band and a centred progress bar "Reading the game's textures… N %" are drawn.
5. When finished: `sessions = LoadSessions(userData / "Cache/texture_studio/captures")` and `catalog.AddCapture(n, files)` per session; `mods = ListMods(paths.mods, ReadEnabledMods(paths.config))`; active mod = the first enabled one, or the first one; `replacements = FindReplacements(...)`; `Refilter()`.

- [ ] **Step 3: Filtering**

```cpp
void Refilter(App& a) {
    a.visible.clear();
    std::string needle = a.search;
    for (char& ch : needle) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    const auto& textures = a.catalog.Textures();
    for (int i = 0; i < static_cast<int>(textures.size()); ++i) {
        const auto& t = textures[i];
        if (a.group != "Todo" && t.group != a.group) continue;
        if (!a.subgroup.empty() && t.subgroup != a.subgroup) continue;
        if (a.onlyReplaced && !a.replacements.count(t.name)) continue;
        if (a.onlySeen && t.seenIn.empty()) continue;
        if (!needle.empty()) {
            std::string hay = t.name + " " + t.group + " " + t.subgroup;
            for (const auto& l : t.locations) hay += " " + a.catalog.Entries()[l.entry].name;
            for (char& ch : hay) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
            if (hay.find(needle) == std::string::npos) continue;
        }
        a.visible.push_back(i);
    }
    if (std::find(a.visible.begin(), a.visible.end(), a.selected) == a.visible.end()) a.selected = a.visible.empty() ? -1 : a.visible[0];
}
```

- [ ] **Step 4: Thumbnails**

Cache of `SDL_Texture*` per index with a limit of 600 entries (simple LRU with `std::list` + `unordered_map`), created from `catalog.Original(t)` or from the replacement file (`LoadImage`) when the replacement view is requested. At most 24 are created per frame so as not to block scrolling; the rest show the checkerboard background until the next frame. Scale mode `SDL_SCALEMODE_NEAREST` for the zoomed ones and `LINEAR` for the thumbnails.

```cpp
struct Thumbs {
    struct Entry { SDL_Texture* tex; int w, h; std::list<std::string>::iterator lru; };
    std::unordered_map<std::string, Entry> map;
    std::list<std::string> order;
    int budget = 24;  // creations left this frame
    SDL_Texture* Get(SDL_Renderer* r, const std::string& key, const std::function<tstudio::Image()>& load, int* w, int* h) {
        if (auto it = map.find(key); it != map.end()) {
            order.splice(order.begin(), order, it->second.lru);
            *w = it->second.w; *h = it->second.h;
            return it->second.tex;
        }
        if (budget <= 0) return nullptr;
        --budget;
        const tstudio::Image img = load();
        if (img.Empty()) return nullptr;
        SDL_Texture* tex = SDL_CreateTexture(r, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_STATIC, img.width, img.height);
        SDL_UpdateTexture(tex, nullptr, img.rgba.data(), static_cast<int>(img.width * 4));
        SDL_SetTextureBlendMode(tex, SDL_BLENDMODE_BLEND);
        order.push_front(key);
        map[key] = {tex, static_cast<int>(img.width), static_cast<int>(img.height), order.begin()};
        while (map.size() > 600) { SDL_DestroyTexture(map[order.back()].tex); map.erase(order.back()); order.pop_back(); }
        *w = static_cast<int>(img.width); *h = static_cast<int>(img.height);
        return tex;
    }
    void Forget(const std::string& key) {
        if (auto it = map.find(key); it != map.end()) { SDL_DestroyTexture(it->second.tex); order.erase(it->second.lru); map.erase(it); }
    }
};
```

Key: `"o:" + name` for the original, `"r:" + name` for the replacement (it is `Forget`-ed on import or removal).

Checkerboard background (transparency) drawn with `AddRectFilled` in 8 px squares of `Rgba(90,106,138)`/`Rgba(128,144,176)`.

- [ ] **Step 5: Drawing the window** (every frame, as in mockup v2)

1. **Band** (height 58·u): `kBandTop→kBandBottom` gradient, 3 px white bottom line, **no red line**. Title with `LogoText(dl, g_title, 30*u, ..., IM_COL32_WHITE, Rgba(200,225,255), "POWER PROS WII 2008")` and below it `"TEXTURE STUDIO"` in `kYellow` with `g_bold` 14·u. On the right: combo "Mod: <name> ▾" (`ImGui::BeginCombo`, `mods` list, on change → `replacements = FindReplacements`, `Refilter`), indicator "● Enabled in the game" (green) or "○ Not enabled" with an "Enable" pill (`SetModEnabled(config, id, true)`, refresh `mods`), green pill "+ New mod" → popup with `InputText(newModName)`, buttons "Create" (`CreateMod`, error in red under the field if it fails; once created, select it) and "Cancel".
2. **Body**: left panel "CATEGORIES" (230·u wide): "Todo" and each group of `GroupOrder()` that has textures, with its count; the selected group expands with its subgroups (sorted by name, with count). "Captures" with "Session n · N" at the end (selecting one → `onlySeen` filter with that session: add `int session = 0` to the state and check that `seenIn` contains `session`). Selection: blue gradient background `kBlueBottom→Rgba(28,112,214)` rounded on the right.
3. **Centre top**: panel with `InputTextWithHint("##buscar", "Buscar por nombre, pack o hash")`, checkboxes "Only replaced" and "Seen in capture"; any change → `Refilter`.
4. **Grid**: panel with header "<group> › <subgroup> · N textures · M replaced"; `ImGuiListClipper` by rows (columns = width / (110·u)); each cell 100·u: checkerboard background, thumbnail fitted keeping its aspect ratio, `kPanelBorder` border (yellow and 3 px if selected), green "✓" badge at the top right if `replacements.count(name)`, orange "👁" badge (use "o" if the font lacks the emoji) at the top left if `!seenIn.empty()`, `WxH` size at the bottom. Click → `selected`; double click → export that texture.
5. **Detail card** (height 230·u): original and replacement (or "No replacement") at 160·u on a checkerboard, yellow arrow between them; click on an image → zoomed popup (modal window at 80 % of the window, image fitted, `NEAREST`). Data: "Pack" (list of packs from `locations`, "also in …"), "Format" (`FormatName`, "palette of N colours" / "palette in another pack (grey)"), "File" (`tex1_…png` name in monospace, "Copy" button), "Status" ("Replaced in "<mod>" · WxH (×k)" or "Original"). Actions: "Export PNG" (save-file dialog `SDL_ShowSaveFileDialog`, default name `<name>.png`), "Import PNG…" (`SDL_ShowOpenFileDialog` with PNG/DDS filters → `ImportOne`; result in `toast`, red if `!ok`), "Remove replacement" (deletes the file from `replacements`, `Forget`), "Open folder" (`ShellExecuteW` on the replacement's or the mod's folder), checkbox "Apply to all palettes" (only if `key.hasPalette`).
6. **Bottom bar** (56·u, background `Rgba(13,21,36)`, 3 px blue `kBlueBottom` top line): "⬇ Export category" (`SDL_ShowOpenFolderDialog` → `Export(catalog, visible, carpeta)`, toast "N textures exported to …"), "⬆ Import folder…" (`SDL_ShowOpenFolderDialog` → `ImportFolder` → `report`, `showReport = true`), "🎮 Capture in game" (see Step 6), "📦 Package .zip" (`SDL_ShowSaveFileDialog` → `WriteZip`). On the right, `toast` or "Index: N textures · your game's project.bin · ready".
7. **Import report** (modal): table with file, texture, result (green ✓ / red ✗) and message; summary "N imported, M with problems".
8. Without an active mod, the actions that write ask the player to create one ("Create or choose a mod above").

SDL3 dialogs are asynchronous: use the same `DialogResult` pattern (mutex + `ready` + `path`) as `tools/setup/setup.cpp` and process the result at the start of the next frame.

- [ ] **Step 6: Capture**

"Capture in game" button: if there is no `paths.game`, an error toast. Otherwise, `capture.Start(paths.game, paths.userData / "Cache" / "texture_dumps", &error)`; `capturing = true`; while `capture.Running()`, show a modal "Play up to the screen you want and close the game. The textures that appear will be marked." When it ends: `auto [n, files] = capture.Collect(userData / "Cache/texture_studio/captures")`; if `n == 0` → toast "The game showed no new textures"; otherwise → `catalog.AddCapture(n, files)`, add to `sessions`, select "Captures › Session n", `Refilter`.

- [ ] **Step 7: Test the UI by hand**

Run: `local/build/texture-studio/TextureStudio.exe --config local/wiicompiled-mlb/build/UserData/Config.toml --userdata local/analysis/game-probe/UserData --mods local/analysis/game-probe/mods --game local/analysis/game-probe/WiiCompiled.exe`

(Warn the user beforehand that a window will open.) Check with screenshots (PrintWindow, like `scratchpad/gamerun.ps1`):
- the progress bar and then the "Menús" grid;
- "Menús › Menú principal" shows the label atlas with its real colours;
- searching "nyy" filters to Estadios › Yankees, Uniformes and Cartas;
- create the mod "Prueba Studio", export the label, import it upscaled ×4 (with `PIL` in the scratchpad: `Image.resize(..., NEAREST)` and a painted box), see ✓ and the comparison;
- "Package .zip" produces a zip that Explorer opens.

- [ ] **Step 8: Commit** — `Texture Studio: user interface (style B)`.

---

### Task 11: Runtime patch (launcher button and dumping via environment variable)

**Files:**
- Modify (working tree, then patch): `local/wiicompiled-mlb/src/runtime/src/main.cpp`, `local/wiicompiled-mlb/src/runtime/src/launcher.cpp`
- Create: `tools/patches/wiicompiled-texture-studio.patch`
- Modify: `tools/wiicompiled-translate.ps1` (add `'wiicompiled-texture-studio'` after `'wiicompiled-match-benchmark-gameplay'`)

- [ ] **Step 1: Dumping via environment variable** — in `main.cpp`, right before `mods::Apply(auroraConfig);`:

```cpp
        // Texture Studio capture: WIICOMPILED_TEXTURE_DUMPS=1 dumps every unmatched texture for this run
        // only, without touching the player's Config.toml.
        if (const char* dumps = std::getenv("WIICOMPILED_TEXTURE_DUMPS"); dumps != nullptr && std::string_view(dumps) == "1") {
            auroraConfig.allowTextureReplacements = true;
            auroraConfig.allowTextureDumps = true;
        }
```

- [ ] **Step 2: Button in the launcher** — in `launcher.cpp`:

```cpp
constexpr int kOpenTextureStudio = -4;
constexpr const char* kTextureStudioHelp =
    "Abre Power Pros Wii 2008 Texture Studio: mira las texturas del juego, expórtalas para editarlas "
    "(Photoshop, escalado HD) y guárdalas como un mod de texturas sin tocar el juego.";

void OpenTextureStudio() {
#if defined(_WIN32)
    const auto exeDir = RuntimeConfigFile::ExecutableDirectory();
    if (!exeDir) return;
    const std::filesystem::path studio = *exeDir / "TextureStudio.exe";
    if (!std::filesystem::exists(studio)) {
        RT_LOG(RT_TAG_RUNTIME) << "launcher: Texture Studio is not installed (" << RuntimeConfigFile::PathToUtf8(studio) << ")" << std::endl;
        return;
    }
    wchar_t self[MAX_PATH]{};
    GetModuleFileNameW(nullptr, self, MAX_PATH);
    const std::wstring args = L"--config \"" + RuntimeConfigFile::ResolveConfigPath().wstring() + L"\" --userdata \"" +
                              RuntimeConfigFile::ApplicationDataDirectory().wstring() + L"\" --mods \"" +
                              mods::Directory().wstring() + L"\" --game \"" + std::wstring(self) + L"\"";
    ShellExecuteW(nullptr, L"open", studio.wstring().c_str(), args.c_str(), exeDir->wstring().c_str(), SW_SHOWNORMAL);
#endif
}
```

and in the HERRAMIENTAS tab, after "EDITAR ROSTER":

```cpp
    toolsTab.options.push_back({"EDITOR DE TEXTURAS", kTextureStudioHelp, {"Abrir"}, 0, false, kOpenTextureStudio});
```

and in `apply`:

```cpp
        if (o.mod == kOpenTextureStudio) {
            OpenTextureStudio();
            return;
        }
```

When building, check that `ResolveConfigPath`, `ApplicationDataDirectory` and `ExecutableDirectory` are the real names in `runtime_config.h` (lines 204, 266 and 292) and adjust if they differ.

- [ ] **Step 3: Build the game** — `.\tools\wiicompiled-build.ps1` (if the exe is in use, rename it to `WiiCompiled.old.exe`; never close the user's process).

- [ ] **Step 4: Test**
  - `scratchpad/quickrun.ps1` with `$env:WIICOMPILED_TEXTURE_DUMPS='1'`: after 40 s there are files in `game-probe/UserData/Cache/texture_dumps` even though `Config.toml` has `texture_dumps` unset.
  - `.\tools\test-launcher.ps1` passes (all three passes).
  - In the launcher, HERRAMIENTAS shows "EDITOR DE TEXTURAS"; with `TextureStudio.exe` copied next to `WiiCompiled.exe` in `local/wiicompiled-mlb/build`, "Abrir" opens it with the game's paths.

- [ ] **Step 5: Generate the patch** — with the method of `scratchpad/regen-bench.sh`: worktree at the pin + every patch up to `wiicompiled-match-benchmark-gameplay`, copy `runtime/src/main.cpp` and `runtime/src/launcher.cpp`, `git diff --cached --binary > tools/patches/wiicompiled-texture-studio.patch`. Register the patch in `tools/wiicompiled-translate.ps1`. Run `scratchpad/verify-chain.sh`: it must print `IDENTICAL`.

- [ ] **Step 6: Commit** — `Launcher: open Texture Studio; WIICOMPILED_TEXTURE_DUMPS for captures`.

---

### Task 12: Setup, documentation and full in-game test

**Files:**
- Modify: `tools/setup/Make-Payload.ps1`, `tools/setup/LocalBuild.ps1`, `docs/mods.md`, `docs/superpowers/specs/2026-10-14-texture-studio-design.md`
- Create: `docs/texture-studio.md`

- [ ] **Step 1: Make-Payload** — after "Setup window…":

```powershell
Write-Host 'Texture Studio...'
& "$root\tools\texture-studio\build.ps1" -Source $Source -Output (Join-Path $root 'local\build\texture-studio')
Copy-Item (Join-Path $root 'local\build\texture-studio\TextureStudio.exe') $workspace
```

- [ ] **Step 2: LocalBuild** — after copying `powerupplus`:

```powershell
$studio = Join-Path $workspace 'TextureStudio.exe'  # texture mods (launcher > HERRAMIENTAS > EDITOR DE TEXTURAS)
if (Test-Path $studio) { Copy-Item $studio $game -Force }
```

and in the `if ($Shortcut)` block, a second shortcut:

```powershell
    $studioLink = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'Power Pros Wii 2008 Texture Studio.lnk'))
    $studioLink.TargetPath = Join-Path $game 'TextureStudio.exe'
    $studioLink.WorkingDirectory = $game
    $studioLink.Save()
```

- [ ] **Step 3: Documentation**
  - `docs/texture-studio.md` (for players, in Spanish): what it is, how to open it, the workflow for an HD pack (export category → chaiNNer/Photoshop → import folder → enable mod), size rules, palettes and "Apply to all palettes", in-game capture, sharing the `.zip`, what cannot be replaced (THP videos), and the rule of not sharing unmodified original textures.
  - `docs/mods.md`: in "Texturas", link `docs/texture-studio.md` as the recommended way; keep `packwii.py` as the advanced tool.
  - Spec: replace "saves an index in `UserData/Cache/texture_studio/index.bin`" with what was measured in Task 6 (in-memory index, N s).

- [ ] **Step 4: Regenerate the package and test the installation**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\setup\Make-Payload.ps1 -Zip
```

and the test installation (`LocalBuild.ps1 -Iso … -Install local\analysis\setup-test`). Check that `Game\TextureStudio.exe` exists and that the package passes the content review.

- [ ] **Step 5: Full in-game test** (warn the user: visible window, do not touch the controller)
  1. Open the Studio from the test installation, create the mod "Prueba HD".
  2. Export `Menús › Menú principal`; upscale ×4 the label of `env_mainmenu.pack` with a visible coloured box; import the folder.
  3. Export a texture from `Estadios › Yankees (NYY)` (the largest one), upscale ×4 with a visible pattern, import it.
  4. Enable the mod; start the game with `gamerun.ps1` up to the main menu: the modified label is shown in HD.
  5. For the stadium: a short probe up to a screen with Yankee Stadium (for example, the Exhibition stadium select), or the Studio capture to locate a texture visible on that screen and repeat with it.
  6. "Capture in game": a new session with the menu textures marked.
  Save the screenshots in the scratchpad and describe them in the report.

- [ ] **Step 6: Commit and push**

```bash
git add tools/setup tools/texture-studio docs
git commit -m "Texture Studio: ship it with the Setup; player guide

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
git push origin master:main
```
