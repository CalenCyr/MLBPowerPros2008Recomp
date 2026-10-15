# MLB Power Pros 2008 Recomp

*Versión en español: [README.md](README.md)*

Unofficial native recompilation of MLB Power Pros 2008 for Wii (USA, `RL8E54`) on top of the [Wiicompiled](https://github.com/patchzyy/Wiicompiled) runtime.

## Install and play (Windows 10/11, 64-bit)

1. Download `MLB Power Pros 2008 Setup.zip` from this repository's *Releases* page and unzip it into a folder of your choice. *(There is no published release yet; until then the package is built with `tools/setup/Make-Payload.ps1 -Zip`.)*
2. Open `MLBPowerPros2008-Setup.exe`, press **CHOOSE DISC** (**ELEGIR DISCO**) and select your copy of the game (ISO, NKit, RVZ, WBFS, WIA, GCZ or CISO).
3. Press **INSTALL** (**INSTALAR**). The Setup checks that it is a clean dump of `RL8E54`, extracts it, translates the game code and compiles it **on your PC**. The first time it takes a few minutes.
4. Press **PLAY** (**JUGAR**) (or use the desktop shortcut). Before each session the launcher appears so you can choose the graphics API, display, resolution, audio and controls.

From the launcher (SETTINGS (AJUSTES) → MODS / TOOLS (HERRAMIENTAS)) you can also enable mods and open the included tools:

- **Roster editor** (PowerUp+ adapted to 2008): `docs/en/roster-2008.md`.
- **Power Pros Wii 2008 Texture Studio**, for making texture mods, also in HD: `docs/en/texture-studio.md`.
- Mod types and how to install them: `docs/en/mods.md`.

**Nothing from the game is included or downloaded.** Neither this repository nor its releases contain the disc image, the executable, assets or translated code: the Setup only ships tools (translator, compiler, runtime source code) and everything from the game is generated on your computer from your own copy. Do not ask for or share game files.

For whoever packages a release: `tools/setup/Make-Payload.ps1` builds the package (see its header) and checks that it contains nothing from the game; `tools/setup/LocalBuild.ps1` is what the Setup runs on the player's PC.

The launcher, the Setup, Texture Studio and the Blender add-on are in Spanish and English: they follow Windows' (or Blender's) language and can be switched with their **IDIOMA / LANGUAGE** option or the **ES | EN** pill. The English documentation is in `docs/en/` and `README.en.md`.

## Discord

The presence uses the name **MLB Power Pros 2008**. It needs a Discord application ID of its own for this game; none is included, and the ID inherited from WiiCompiled is ignored to avoid advertising another application. Until that ID is configured, Rich Presence stays inactive.

In `UserData/Config.toml`, next to the other installation settings:

```toml
[discord]
enabled = true
client_id = "" # Replace with this game's own Discord application ID.
```

Restart the game after changing it. The WiiCompiled credits are kept.

## Development (Windows)

The translator and the runtime are Wiicompiled's, pinned in `config/tools.lock.json` and with the patches in `tools/patches/wiicompiled-*.patch`. Details, patches and measurements in `docs/en/wiicompiled-feasibility.md`.

```powershell
.\tools\bootstrap.ps1                                   # dtk and NKit verified by SHA256
.\tools\phase0.ps1 -Image '<your copy>.iso' -DolphinTool '<Dolphin>\DolphinTool.exe'   # extracts to local/disc
.\tools\wiicompiled-translate.ps1 -Build                # clones local/vendor/Wiicompiled, applies patches, translates
.\tools\wiicompiled-build.ps1 -RunSeconds 30            # compiles and tests
.\tools\wiicompiled-bench.ps1 -Api vulkan               # frame time in the title demo
```

- Release: `tools/setup/Make-Payload.ps1` builds the Setup; `tools/setup/LocalBuild.ps1` is what runs on the player's PC.
- Mods and roster: `docs/en/mods.md`, `docs/en/roster-2008.md`, `tools/projectbin.py`, `tools/roster/`, `tools/powerupplus.ps1`.
- Textures: `docs/en/texture-studio.md`, `tools/texture-studio/` (`build.ps1`; `TextureStudio.exe --selftest`), `tools/packwii.py`.
- Designs and work plans: `docs/superpowers/`.
- Reverse engineering: **`docs/en/ingenieria-inversa.md`** (game reference by system; PDF with `tools/build_re_pdf.py`), `docs/en/reverse-engineering-tools.md` (Ghidra, dtk), `function_data_refs.py`, `dol_to_elf.py`, `sample_host_thread.cpp`.

## Structure

- `tools/`: translation, compilation, Setup, launcher, mods and analysis.
- `tools/patches/`: reproducible patches on top of Wiicompiled and PowerUp+.
- `config/`: game identity, function map and pinned versions.
- `assets/launcher/`: the launcher's own art (not game content).
- `docs/`: technical notes and verifiable results.
- `local/`: disc, downloaded tools, generated code, builds and saves. Excluded from Git.

The previous runtime (ModernGekko/DolRecomp module, its patches, probes and performance reports) is in the git tag `moderngekko-era`.

**This repository neither contains nor distributes anything from the game:** not the disc image, the executable, assets (textures, models, audio, video, fonts), code generated from it, or save files. To use it you need your own legal copy of MLB Power Pros 2008 (RL8E54). `tools/check_no_game_data.py` rejects commits with game file types, binary content, large files or data dumps; install it as a hook with `python tools/check_no_game_data.py --install-hook`.

The integration adopts GPLv3. See `LICENSE` and `THIRD_PARTY.en.md`.
