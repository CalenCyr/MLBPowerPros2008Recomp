# Power Pros Wii 2008 Texture Studio

*Versión en español: [../texture-studio.md](../texture-studio.md)*

A program for creating **texture mods** for MLB Power Pros 2008. With it you can:

- see all of the game's textures, sorted by what they are;
- export them to PNG to edit them in another program (Photoshop, GIMP, Krita) or upscale them with AI (chaiNNer, Upscayl);
- put them back in, at the same size or bigger (HD).

The game is never modified: everything goes into a mod that you turn on or off in the launcher.

## Opening it

- From the game: launcher → SETTINGS (AJUSTES) → **TOOLS** (**HERRAMIENTAS**) → **TEXTURE EDITOR** (**EDITOR DE TEXTURAS**) → Open.
- Or with the **Power Pros Wii 2008 Texture Studio** desktop shortcut, if you created it during installation.

The first time it takes a second to read the textures from your copy of the game (about 9,700 different ones).

## The window

- **Top:** the mod you are working on, whether it is enabled in the game (**Enable** (**Activar**) button) and **+ New mod** (**+ Nuevo mod**).
- **Left:** categories.
  - Menus, Stadiums (by team, plus skies and original stadiums), Uniforms, Player cards, Logos, Faces, MLB Life, Season, Success…
  - At the end, the **captures** you've made.
- **Center:**
  - a search box by name, pack or hash;
  - the **Replaced only** (**Solo reemplazadas**) and **Seen in capture** (**Vistas en captura**) filters;
  - the thumbnails, with a green ✓ on the ones you've already replaced and an orange eye on the ones you saw while capturing. Double-click exports a texture.
- **Details panel:** the original texture next to your replacement.
  - Click either of them to see it full size.
  - Below you'll see the pack it comes from, its format, the file name and the **Export PNG** (**Exportar PNG**), **Import PNG...** (**Importar PNG...**), **Remove replacement** (**Quitar reemplazo**) and **Open folder** (**Abrir carpeta**) buttons.
- **Bottom:** **Export this view** (**Exportar esta vista**), **Import folder...** (**Importar carpeta...**), **Capture in game** (**Capturar en juego**) and **Package .zip** (**Empaquetar .zip**).

**Language:** the **ES | EN** pill in the top band switches the language right away and saves it in `Config.toml` (`[ui] language`), the same setting as the launcher. Until you choose, it follows Windows' language.

## Making an HD pack step by step

1. **+ New mod**: give it a name (it will be the `mods\<name>` folder).
2. Choose a category (for example, Menus › Main menu) and press **Export this view**. Choose a folder: subfolders with the original PNGs are created.
3. Edit those PNGs or run them through chaiNNer or Upscayl. **Don't change the file names**: the `tex1_…` name is what the game looks for.
4. **Import folder...** and choose the folder with your PNGs. It searches all subfolders and shows you a report: what was imported and what wasn't, and why.
5. **Enable** (top) and open the game.

For a single texture: select it, **Export PNG**, edit it and **Import PNG...**.

## Sizes

- You can make the texture bigger, but with the **same aspect ratio** (a 256×128 one can be 512×256, 1024×512…).
- Ideally, multiply by 2, 4 or 8. Another size with the same aspect ratio is accepted with a warning.
- Maximum: 4096 pixels per side.
- PNGs of any kind (paletted, grayscale, 16-bit) and the DDS files the game dumps are accepted. From Photoshop, save as PNG.

## Palettes

Many of the game's textures use a palette (16 or 256 colors). You don't have to worry about it: the replacement is a full-color image.

- About 300 textures have their palette in another pack. The Studio shows them **in gray**, but they can be exported and replaced all the same.
- If the game draws the same texture with several palettes, each variant is a separate replacement. **Apply to all palettes** (**Aplicar a todas las paletas**) (in the details panel) makes your image work for all of them.

## Upscaling with AI (optional, outside the Studio)

The Studio doesn't upscale images: you export, upscale with another program and import the folder again. Everything below is free, works offline on your graphics card and doesn't come with the game (everyone downloads it if they want).

**Programs** (open source):

| Tool | What for | License | Approx. download |
|---|---|---|---|
| Real-ESRGAN ncnn-vulkan | command-line upscaling engine; Vulkan, works on AMD, NVIDIA and Intel | MIT (Real-ESRGAN: BSD-3) | ~45 MB |
| Upscayl | simple window on top of that engine; supports custom models | AGPL-3.0 | ~150-200 MB |
| chaiNNer | node-based editor for batches; on AMD it uses the NCNN engine, not PyTorch (NVIDIA only) | GPL-3.0 | ~150 MB + engine (~0.5 GB with NCNN) |

**Models** (free, on OpenModelDB; check each one's license before redistributing it):

- **4x-AnimeSharp**: menus, logos, lettering, stadiums and characters; respects the drawing style. CC BY-NC-SA 4.0 (no commercial use). ~65 MB (.pth) or ~35 MB (NCNN).
- **4x-UltraSharp** (same license) or **RealESRGAN x4plus** (BSD): real photos, like the player cards.

**Steps with chaiNNer:** Load Images (the exported folder, including subfolders) → Upscale Image with Load Model → Save Image to another folder, **with the same file name**. Then **Import folder...** in the Studio. With Upscayl: input folder, model and ×4 scale, making sure it keeps the names.

**Tips:**

- At ×4 almost everything fits within the 4096 px maximum.
- If you see halos on transparent edges, upscale the alpha channel separately.
- Repeating textures (grass, stands, walls) can show seams: check them in the game and, if they are noticeable, leave them as the original or at ×2.
- Don't upscale the ones that show up in gray (their palette is in another pack): they would look gray in the game.
- Do it in parts: a ×4 multiplies the pixels by 16, so the whole game at ×4 is several GB, and video memory grows with whatever is on screen.

## Capture in game

It's for finding the texture of something you see on screen.

1. Press **Capture in game**: the game opens without the launcher.
2. Go to the screen you're interested in and close the game.
3. The Studio creates **Captures › Session N** (**Capturas › Sesión N**) with the textures that appeared and marks them with the eye.

Some textures only exist while playing (they aren't in any pack). They show up in **Seen in game only** (**Solo vistas en juego**) and can also be replaced. Videos can't be replaced.

## Sharing your mod

**Package .zip** creates a zip with your `mod.toml` and your images, nothing else. Whoever receives it unzips it into their `mods` folder and enables it in the launcher (MODS).

Don't share unmodified original textures: they are game content. Share only what you made.

## For advanced users

`TextureStudio.exe` also works from the command line:

```
TextureStudio.exe --new-mod <mods folder> <name>
TextureStudio.exe --export <project.bin> "<group>[/<subgroup>]" <folder>
TextureStudio.exe --import-folder <project.bin> <mod folder> <PNG folder>
TextureStudio.exe --selftest
```

The window can be opened on a specific view with `--view "Estadios/Yankees (NYY)"`, `--search <text>`, `--select <tex1_ name>` and `--mod <name>`.

To put textures inside the `.pack` files instead of using a texture mod, there is `tools/packwii.py` (see `docs/en/mods.md`).
