# Power Pros Wii 2008 Texture Studio — design

*Versión en español: [../../../superpowers/specs/2026-10-14-texture-studio-design.md](../../../superpowers/specs/2026-10-14-texture-studio-design.md)*

Date: October 14, 2026. Status: approved in conversation, pending written review.

## Goal

A desktop app to create **texture mods** for MLB Power Pros 2008 (Wii) without touching the original game:

- view each game texture with its context (menu, stadium, uniform, card…);
- export it to PNG to edit it elsewhere (Photoshop, GIMP, AI upscaling in chaiNNer);
- import it back, at its own size or larger (HD), converted to what the game needs;
- save everything as a mod that is enabled or disabled in the launcher and can be shared.

The inspiration is the HD packs of other games (for example, textures upscaled with AnimeSharp + chaiNNer keeping the style).

It **is not** an image editor: there is no drawing or retouching inside the app.

## Who uses it

Players without technical knowledge, with the game installed by the Setup. They must not need Python or the command line. Also the project author, to make complete packs.

## Verified technical basis

- The runtime already loads Dolphin-style replacements: files `tex1_<width>x<height>_<hash>[_<palette hash>]_<format>.png|.dds` inside `mods/<mod>/textures/` (and `UserData/texture_replacements/`), at any resolution. An enabled mod with `textures/` turns on replacements with no further settings (`mods.cpp`).
- `<hash>` is XXH64 (seed 0) of the bytes of the texture's base level; `<palette hash>` is XXH64 of the palette range between the minimum and maximum index the texture uses (`texture_replacement.cpp`). `$` is a wildcard for either of them.
- Verified on October 14, 2026 with the runtime dump up to the main menu (`docs/en/reverse-engineering.md`, section 5): the hash computed from the `.pack` matches the game's for the 39 pack textures seen, and the palette for 36 of 38. The game uses the pack bytes as they are.
- What does not come from packs: THP videos (I8 at 512×448 and 256×224, ignored) and a few non-power-of-two textures generated at run time (covered by the capture).

Consequence: the Studio never rewrites `.pack` or `project.bin`. It only writes PNGs with the right name into the mod folder.

## Architecture

Standalone C++20 app with Dear ImGui + SDL3 (SDL renderer), with the same style as the Setup and the launcher (`power_pros_ui.h`). Dependencies already pinned in the project: SDL3, ImGui, libpng + zlib, xxhash. No new libraries.

```
tools/texture-studio/
  CMakeLists.txt        compilación estática, como tools/setup
  studio.cpp            ventana, estado de la interfaz, acciones
  catalog.{h,cpp}       lee project.bin → packs → texturas; índice en caché
  gx.{h,cpp}            decodificadores GX (RGBA8, RGB5A3, I4, I8, C4, C8) y bloques
  names.{h,cpp}         nombres tex1_… (hash de textura y de paleta)
  categories.{h,cpp}    pack → categoría y nombre legible (tabla escrita a mano)
  pngio.{h,cpp}         leer cualquier PNG → RGBA 8 bits; escribir PNG RGBA; leer los DDS
                        sin comprimir que vuelca el runtime (formato a confirmar en el plan)
  modfolder.{h,cpp}     crear/elegir mod, escribir/quitar reemplazos, empaquetar .zip
  capture.{h,cpp}       lanzar el juego con volcado y leer la sesión
  selftest.cpp          autotest con datos sintéticos (sin datos del juego)
```

Each unit has a single responsibility and is tested separately. `catalog`, `gx` and `names` do not depend on the UI.

`tools/packwii.py` remains as the reference implementation and for local tests; the C++ decoders must produce the same pixels.

### Input data

- `UserData/Config.toml` next to the game executable: `[paths] dvd_root` → `<dvd_root>/files/project.bin`.
- `project.bin`: documented format (`tools/projectbin.py`, `docs/en/reverse-engineering.md` section 5).
- Inside each `PACKWII`: model and interface texture headers, palettes, texture sets; palette pairing by pointer or, failing that, by the colours that follow the pixels (like `packwii.py`).

### Index

- On opening: walks the 2,356 packs (about 392 MB) in a thread, with a progress bar, and keeps in memory per texture: pack, position, width, height, format, palette position, texture hash and palette hash. Measured: 9,657 distinct textures in 1.1 s, so it is not saved to disk (implementation decision of October 14, 2026).
- Identical textures in several packs are grouped by `tex1_…` name; the detail card shows "used in N packs".
- Thumbnails: decoded when they appear on screen and cached in memory (with a limit).

## Naming rules

| Case | Replacement name |
|---|---|
| No palette (RGBA8, RGB5A3, I4, I8) | `tex1_WxH_<hash>_<fmt>` |
| Known palette | `tex1_WxH_<hash>_<palette hash>_<fmt>` |
| Palette in another pack (~430) | `tex1_WxH_<hash>_$_<fmt>`; shown in grey |
| Palette variants seen in a capture | additionally, one file per captured `<palette hash>` |
| "Apply to all palettes" (option in the detail card) | `…_$_<fmt>` |

By default, exact name: uniforms could share pixels and change only the palette per team, and a wildcard would make them all the same.

## Import

- PNG of any kind (palette, grey, 16-bit, with or without alpha) → 8-bit RGBA. DDS is copied as is.
- Size: same aspect ratio as the original, up to 4096 px per side. Exact multiple (×2, ×4, ×8) recommended; another size with the same aspect ratio is accepted with a warning; another aspect ratio is rejected.
- Import folder: recursive walk, matches by `tex1_…` file name (what chaiNNer leaves when keeping names). Final report: imported, rejected (reason), unmatched.
- The replacement is written to `mods/<mod>/textures/<category>/<subgroup>/tex1_….png` (readable folders; the runtime searches recursively).

## Export

- One texture, one category or everything, as RGBA PNG at the original size, in `export/<category>/<subgroup>/tex1_….png` inside the folder the player chooses.
- Those with an unknown palette are exported in grey, flagged in the report.

## Mods

- Choose or create the active mod: `mods/<name>/mod.toml` (`name`, `version`) + `textures/`.
- Top bar: whether the mod is enabled in `Config.toml [mods] enabled`; "Enable" button.
- "Remove replacement" deletes the file from the mod.
- "Package .zip": only the mod's `mod.toml` and `textures/`. Never packs or unmodified textures.

## In-game capture

- "Capture in game" launches the game with the launcher skipped (`WIICOMPILED_SKIP_LAUNCHER=1`) and dumping enabled without touching the player's configuration (new environment variable in the runtime patch, see below).
- When the game closes, the dumps move to `UserData/Cache/texture_studio/captures/<n>/` and the Studio creates the session "Session n".
- The captured names mark with 👁 the catalog textures that were seen and add palette variants. Those that are in no pack form the category "Only seen in game" and are shown from the dump; they can be replaced just the same. Video frames are discarded.

## Interface

Style **B** of the mockup (`.superpowers/brainstorm/.../studio-layout-v2.html`): neutral dark panels, blue top band with the title "POWER PROS WII 2008 / TEXTURE STUDIO" with an outline, pill buttons, **no red stripe**. Mouse and keyboard, in Spanish.

- Top bar: title, active mod (drop-down), enable status, "+ New mod".
- Left: categories with a counter and subgroups (Menus, Stadiums › <stadium>, Uniforms › <team>, Player cards, Logos, Only seen in game, Captures › Session n).
- Centre: search (readable name, pack or hash), filters "Only replaced" and "Seen in capture", thumbnail grid with ✓ (replaced) and 👁 (seen in capture) badges and the size.
- Detail card: original and replacement side by side on a checkerboard background, zoomable; pack(s), format, file name, status; actions Export PNG, Import PNG…, Remove replacement, Open folder, Apply to all palettes.
- Bottom: Export category, Import folder…, Capture in game, Package .zip, index status.

## Integration

- **Make-Payload**: builds the Studio like the Setup and includes it in the package. It carries nothing from the game; the package content review still applies.
- **LocalBuild (Setup)**: installs it next to the game (`Game/TextureStudio.exe`) and creates its shortcut if requested.
- **Runtime patch** `wiicompiled-texture-studio`:
  - "TEXTURAS" button in the launcher that opens the Studio;
  - `WIICOMPILED_TEXTURE_DUMPS=1` enables replacements and dumping only for that run.

## Errors

They are shown in the window, without closing it:

- `Config.toml`, `dvd_root` or `project.bin` missing → "Install the game with the Setup";
- unreadable or corrupt PNG;
- wrong aspect ratio or size larger than 4096;
- mod folder without write permission;
- the mod is not enabled (button to enable it);
- the game could not be launched to capture.

## Tests

- **Selftest** (`TextureStudio.exe --selftest`, in the repo): decoders on synthetic textures with a known result, PNG normalisation, names and palette hash on synthetic data, size rules.
- **Local check** (not committed, uses the player's data): pixels identical to `packwii.py` for every texture; computed names equal to a real game dump.
- **In-game test**: ×4 replacement of the menu's "Exhibition" label and of a stadium texture, mod enabled, screenshot.
- **Setup**: regenerated package and a test installation with the Studio.

## Out of scope (first version)

Drawing or editing inside the app; integrated AI upscaling; THP videos; 3D models; changing stadiums; writing textures inside the `.pack` files (that stays in `tools/packwii.py`).

## Project rules that apply

- Nothing from the game in the repository, the package or the app: the app reads the player's `project.bin` at run time.
- Every new reverse-engineering document goes to `docs/en/reverse-engineering.md` (and the PDF).
- The runtime change is a reproducible patch in `tools/patches/`, registered in `tools/wiicompiled-translate.ps1`.
