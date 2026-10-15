# Phase 0 — initial analysis

*Versión en español: [../phase0-report.md](../phase0-report.md)*

Date: October 7, 2026. Project: `D:\MLBPowerPros2008Recomp`.

> **Historical report**: it describes the starting point. Today the game is natively playable on top of Wiicompiled (`docs/en/wiicompiled-feasibility.md`), and `project.bin` and the roster are decoded (`docs/en/reverse-engineering.md`). The DolRecomp/ModernGekko reports and scripts it cites (`cpu-translation-report.md`, `runtime-integration-report.md`, `recompile.ps1`) are in the git tag `moderngekko-era`. What is listed here as pending (`project.bin` extractor, roster file, framerate) is already resolved in those documents.

**Status (at the time): reproducible analysis; phase 0 still open. There is no playable native port.** The project, the tools, the extraction, the disc inventory and the structural analysis of the DOL/REL were prepared. A later analysis estimated 48,175 functions and produced a first compiled translation; see `docs/cpu-translation-report.md`. Validation of function boundaries, framerate measurement and analysis of the game's own containers are still missing.

## Input and integrity

- Source: the user's own copy in NKit format (`.nkit.iso`).
- Size: 1,254,588,416 bytes.
- SHA256: `87eca8f56d2684a7b32c014213400e9c212b3f84009c7c7ca38a1f7ea73adeb2`.
- Header: Wii, `RL8E54`, USA/NTSC-U, outer revision 0, internal title `MLB Power Pros`.
- Marker at offset `0x200`: `NKIT v01`.
- DATA extraction with DolphinTool: completed. The 28 file entries in the FST match the sizes of the extracted files.
- Expansion with NKit 3.1.0: created `local/images/MLB Power Pros 2008 (USA).iso`, readable by dtk.
- **It is not a verified restoration of the original disc.** NKit reported that it cannot find the update partition identified by `940B57BB`, replaced its space with zeros and reported `VerifyFailed`. dtk reported `Redump: Not found`. It has not been shown that this partition is the only difference on the disc.
- Expanded ISO: CRC32 `42117b18`, SHA1 `b424c7786e1f6bdb45b0adb7069084e4de425560`.
- A rerun with `--skip-if-completed` reused the existing ISO and NKit showed `Unverified (NoVerify)`; dtk verified it again and reported the same lack of a Redump match. The most recent NKit log corresponds to that rerun.
- The DOL and REL extracted directly from the NKit are identical by SHA256 to those extracted from the expanded ISO. This verifies the consistency of those two extraction paths, not authenticity with respect to an original dump.
- The internal DATA header indicates revision 1; the outer header indicates 0. That discrepancy is kept as an input fact.

The original image was not modified. The results and the extracted content remain in `local/`, excluded from Git.

## Code

| Component | File, bytes | Text, bytes | Data, bytes | BSS, bytes |
|---|---:|---:|---:|---:|
| `main.dol` | 2,299,840 | 1,200,448 | 1,099,136 | 954,200 |
| `ovl_main.rel` | 11,229,928 | 7,820,936 | 1,806,784 | 154,196 |

The text/data figures come from the binary section tables. BSS takes up memory at load time; it does not represent additional bytes stored in the file. Total text: **9,021,384 bytes**. The REL contains approximately 87% of that code and is essential for the recompilation.

- DOL entry point: `0x8000403C`.
- `main` identified by dtk: `0x8005E4C4`.
- REL: module 1, format version 3, 17 entries in the original section table, including empty entries.
- DOL SHA256: `789c208f1611c4b150d272eb32cbd461d24aebbc5d7c11a420102d868ff1c5f7`.
- REL SHA256: `dcc37a1a4824702feff5bcaa6aae7cefdedfc3b5d832fbf3de92b982a59b4edc`.
- `dtk dol info` identified 433 unique addresses with names in code sections and 200 functions in exception tables. **These figures are not the total number of functions**, nor should they be added together.
- `dtk rel info` identified module lifecycle entries (`_prolog`, `_epilog`, `_unresolved`) and C++ runtime functions. The later `dtk dol split` identified 5,067 function definitions in the DOL and 43,108 in the REL; these are inferred boundaries, not yet manually validated.

Logs: `local/analysis/dol-info.txt`, `local/analysis/rel-info.txt`, `local/analysis/inventory.json`.

## Symbols, compiler and SDK

There are no `.map`, `.sym`, `.elf` or `.sel` files directly in the FST. This does not rule out internal data in `project.bin`. Other releases in the series have not been compared yet either.

The DOL contains Metrowerks, CodeWarrior runtime and MetroTRK identifiers. This is evidence of that toolchain family; **it does not identify an exact MWCC version**.

RVL SDK module tags with different build dates were located:

| Modules | Observed date |
|---|---|
| THP, EXI, SI, DVD, VI, AI, AX, DSP, SC, ENC, KPAD | August 8, 2007 |
| RFL | September 5, 2007 |
| PAD | October 3, 2007 |
| GX, NAND | December 11, 2007 |
| OS | January 30, 2008 |
| HBM | February 7, 2008 |

Many tags carry the identifier `0x4199_60831`; HBM shows `0x4199_60726`. These are modules with different builds, not a single demonstrated SDK version. The offsets and the rest of the candidates are in `local/analysis/strings-candidates.json`.

## Assets

The full listing is in `docs/fst-inventory.csv` and in `local/analysis/fst-dolphin.txt`.

| File or group | Verified observation | Pending |
|---|---|---|
| `project.bin` | 406,388,736 bytes; its first header does not identify a standard container | Document entry table, compression and possible rosters/models/textures |
| `movie/*.thp` | Three files with a THP signature | Integrate playback once there is a runtime |
| `sound/SeData.bin` | KSS SE Link Data header, dated April 28, 2008 | Structure of links and effects |
| `sound/TrSeData.bin` | KSS BGM Link Data header, dated May 6, 2008 | Music indices |
| `sound/WaveData.bin` | KSS Wave Link Data header, dated April 28, 2008 | Metadata and sample format |
| `sound/strbgm.bin` | 321,687,552 bytes | Codec, entries and streaming |
| `sound/voice0.bin` to `voice17.bin` | 18 banks | Codec and indices |
| `opening.bnr` | Disc banner file | Analyze its container if needed |

KSS is an observed tag, not a conclusive identification of a middleware vendor. A separate roster file has not been located yet. No `project.bin` extractor or asset override was implemented.

## Framerate, input and online

The game was not launched and its framerate in menus or matches was not measured. No claim is made that it is 30 or 60 fps. Measure FPS, emulation speed and logic/render cadence separately before designing interpolation.

The ASCII string scan of the DOL and the REL did not find the patterns `DWC_`, `gamespy`, `nwfc`, `Nintendo WFC`, `nhttp`, `SOStartup`, `SOConnect` or `SOInit`. **The absence of strings does not prove that there is no online mode.** Checking the menus/manual and analyzing references/code are still needed before choosing WFC redirection or input-based netplay.

There is evidence of the PAD, KPAD and WPAD SDKs. The mapping of gestures and controls will be decided based on the game's actual behavior.

## Tools and reproduction

- [decomp-toolkit](https://github.com/encounter/decomp-toolkit), version 1.8.4, commit `a0c455e46cab58e1d2e0885623f85089ff0499db`.
- [NKit](https://github.com/Nanook/NKit), Windows x64 CLI 3.1.0.
- DolphinTool from the existing installation in `D:\Dolphin-x64`; its hash is recorded in `local/analysis/tool-versions.json`. The executable does not declare a file version, so it is identified by its SHA256.
- dtk/NKit downloads pinned and verified by SHA256 in `config/tools.lock.json`.
- `tools/bootstrap.ps1` prepares the tools; `tools/phase0.ps1` extracts and analyzes; `tools/analyze_disc.py` validates the FST and section tables, computes hashes and generates the inventory.

Validation of this phase 0 flow: repeatable preparation without new downloads, full run of the inventory on the real extraction, reading of the DOL/REL by dtk, check of FST sizes and comparison of the DOL/REL between direct and expanded extraction. The later PPC to C translation is done with `tools/recompile.ps1` and documented in `docs/cpu-translation-report.md`.

## Next deliverables and risks

1. Close phase 0: full analysis of functions/branches/relocations, measurement in Dolphin, online check and first documentation of `project.bin`. Keep the disc verification status explicit.
2. Phase 0.5: test the candidate translators with **DOL and REL**, record commit, commands, results and requirements; then select a runtime. The brief's recommendation remains a hypothesis.
3. Phase 1: generate C/C++, compile and record unresolved opcodes and branches. The first translation already compiles; see `docs/cpu-translation-report.md` for coverage and limits.
4. Phase 2: demonstrate native boot and module loading/relocation before committing to graphics improvements or netplay.

The brief's 6–12 month time estimate has not been validated. With the current inventory, a new delivery date would be speculative. The next useful point for estimating is a translation test of the 9 MB of text and a minimal runtime boot.

Observed risks: most of the code is in a REL with no identified gameplay names; assets and audio use large proprietary banks; the expanded disc does not verify against Redump; there is still no dynamic framerate/input data. PPC accuracy, self-modifying code, determinism and GX compatibility remain unevaluated.

A first translation and compilation test was done with [DolRecomp](https://github.com/AH64-dll/DolRecomp), described in `docs/cpu-translation-report.md`. [ModernGekko](https://github.com/ExpansionPak/ModernGekko) was compiled and tested with the recompiled DOL; see `docs/runtime-integration-report.md`. [Wiicompiled](https://github.com/patchzyy/Wiicompiled)/aurora and [NWiiRecomp](https://github.com/BlackLineInteractive/NWiiRecomp) have still not been tested running this game. The verification integration uses GPLv3; the final runtime has not been chosen yet.
