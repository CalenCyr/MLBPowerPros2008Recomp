# Contributing

*Versión en español: [CONTRIBUTING.es.md](CONTRIBUTING.es.md)*

Contributions are very welcome: bug reports, testing on other hardware, code, reverse engineering, docs and translations.

## Three rules

1. **Nothing from the game goes into the repository.** No disc images, executables, assets (textures, models, audio, video, fonts), translated or generated code, saves, roster `.dat` files or byte dumps. Mods made from game data are shared by their authors, not here. Install the guard once in your clone:
   ```
   python tools/check_no_game_data.py --install-hook
   ```
2. **Runtime changes are patches.** Wiicompiled is pinned (`config/tools.lock.json`); changes to it live in `tools/patches/wiicompiled-*.patch` and must apply cleanly on top of the previous ones (`tools/wiicompiled-translate.ps1 -Fresh`).
3. **Say what you measured.** A fix or a feature says how it was checked (a test, a measurement, a step in the game) and what was not checked.

## Reporting a bug

Open an issue with:
- what you were doing and what happened (a screenshot or short clip helps; crop it to the game window);
- your GPU, driver and graphics API (Direct3D 12 / Vulkan), and your controller;
- the release or commit you are on;
- the log, if the game closed or the Setup failed (`setup.log` next to the installed game).

## Building

See "Building from source" in the [README](README.md). Everything the build downloads or generates stays in `local/`, which git ignores.

## Docs

User-facing text and docs exist in Spanish and English: a change to `docs/<name>.md` goes with its `docs/en/` counterpart, and new launcher / Setup / tool text goes through `Tr("es", "en")`.

## License

By contributing you agree that your contribution is licensed under the GNU GPL v3, like the rest of the project.
