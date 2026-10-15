# MLB Power Pros 2008 Recomp

*English version: [README.en.md](README.en.md)*

Recompilación nativa no oficial de MLB Power Pros 2008 para Wii (USA, `RL8E54`) sobre el runtime de [Wiicompiled](https://github.com/patchzyy/Wiicompiled).

## Instalar y jugar (Windows 10/11, 64 bits)

1. Descarga `MLB Power Pros 2008 Setup.zip` desde la página de *Releases* de este repositorio y descomprímelo en una carpeta tuya. *(Todavía no hay una release publicada; hasta entonces el paquete se genera con `tools/setup/Make-Release.ps1 -Zip`.)*
2. Abre `MLBPowerPros2008-Setup.exe`, pulsa **ELEGIR DISCO** y selecciona tu copia del juego (ISO, NKit, RVZ, WBFS, WIA, GCZ o CISO).
3. Pulsa **INSTALAR**. El Setup comprueba que sea un volcado limpio de `RL8E54`, lo extrae, traduce el código del juego y lo compila **en tu PC**. La primera vez tarda unos minutos.
4. Pulsa **JUGAR** (o usa el acceso directo del escritorio). Antes de cada partida aparece el launcher para elegir API gráfica, pantalla, resolución, audio y controles.

Desde el launcher (AJUSTES → MODS / HERRAMIENTAS) también se activan mods y se abren las herramientas incluidas:

- **Editor de rosters** (PowerUp+ adaptado a 2008): `docs/roster-2008.md`.
- **Power Pros Wii 2008 Texture Studio**, para hacer mods de texturas, también en HD: `docs/texture-studio.md`.
- Tipos de mods y cómo instalarlos: `docs/mods.md`.

**No se incluye ni se descarga nada del juego.** Ni este repositorio ni sus releases contienen la imagen del disco, el ejecutable, assets ni código traducido: el Setup solo trae herramientas (traductor, compilador, código fuente del runtime) y todo lo del juego se genera en tu equipo a partir de tu propia copia. No pidas ni compartas archivos del juego.

Para quien empaqueta una release: `tools/setup/Make-Release.ps1` arma el paquete desde un clon limpio con `Make-Payload.ps1` (ver sus cabeceras) y comprueba que no contenga nada del juego; `tools/setup/LocalBuild.ps1` es lo que ejecuta el Setup en la PC del jugador.

El launcher, el Setup, el Texture Studio y el complemento de Blender están en español y en inglés: usan el idioma de Windows (o de Blender) y se cambian con su opción **IDIOMA / LANGUAGE** o la píldora **ES | EN**. La documentación en inglés está en `docs/en/` y en `README.en.md`.

## Discord

La presencia usa el nombre **MLB Power Pros 2008**. Hace falta un ID de aplicación de Discord propio para este juego; no se incluye uno y se ignora el ID heredado de WiiCompiled para evitar anunciar otra aplicación. Hasta configurar ese ID, Rich Presence queda inactivo.

En `UserData/Config.toml`, junto a los demás ajustes de la instalación:

```toml
[discord]
enabled = true
client_id = "" # Sustituir por el ID propio de la aplicación de Discord.
```

Reinicia el juego después de cambiarlo. Los créditos de WiiCompiled se conservan.

## Desarrollo (Windows)

El traductor y el runtime son los de Wiicompiled, fijados en `config/tools.lock.json` y con los parches de `tools/patches/wiicompiled-*.patch`. Detalles, parches y mediciones en `docs/wiicompiled-feasibility.md`.

```powershell
.\tools\bootstrap.ps1                                   # dtk y NKit verificados por SHA256
.\tools\phase0.ps1 -Image '<tu copia>.iso' -DolphinTool '<Dolphin>\DolphinTool.exe'   # extrae a local/disc
.\tools\wiicompiled-translate.ps1 -Build                # clona local/vendor/Wiicompiled, aplica parches, traduce
.\tools\wiicompiled-build.ps1 -RunSeconds 30            # compila y prueba
.\tools\wiicompiled-bench.ps1 -Api vulkan               # tiempo de fotograma en la demo del título
```

- Release: `tools/setup/Make-Release.ps1` arma el Setup desde un clon limpio; `tools/setup/LocalBuild.ps1` es lo que corre en la PC del jugador.
- Mods y roster: `docs/mods.md`, `docs/roster-2008.md`, `tools/projectbin.py`, `tools/roster/`, `tools/powerupplus.ps1`.
- Texturas: `docs/texture-studio.md`, `tools/texture-studio/` (`build.ps1`; `TextureStudio.exe --selftest`), `tools/packwii.py`.
- Diseños y planes de trabajo: `docs/superpowers/`.
- Ingeniería inversa: **`docs/ingenieria-inversa.md`** (referencia del juego por sistema; PDF con `tools/build_re_pdf.py`), `docs/reverse-engineering-tools.md` (Ghidra, dtk), `function_data_refs.py`, `dol_to_elf.py`, `sample_host_thread.cpp`.

## Estructura

- `tools/`: traducción, compilación, Setup, launcher, mods y análisis.
- `tools/patches/`: parches reproducibles sobre Wiicompiled y PowerUp+.
- `config/`: identidad del juego, mapa de funciones y versiones fijadas.
- `assets/launcher/`: arte propio del launcher (no es contenido del juego).
- `docs/`: notas técnicas y resultados comprobables.
- `local/`: disco, herramientas descargadas, código generado, builds y partidas. Excluido de Git.

El runtime anterior (módulo ModernGekko/DolRecomp, sus parches, sondeos e informes de rendimiento) está en el tag de git `moderngekko-era`.

**Este repositorio no contiene ni distribuye nada del juego:** ni la imagen del disco, ni el ejecutable, ni assets (texturas, modelos, audio, video, fuentes), ni código generado a partir de él, ni partidas guardadas. Para usarlo hace falta una copia propia y legal de MLB Power Pros 2008 (RL8E54). `tools/check_no_game_data.py` rechaza commits con tipos de archivo del juego, contenido binario, archivos grandes o volcados de datos; se instala como hook con `python tools/check_no_game_data.py --install-hook`.

La integración adopta GPLv3. Ver `LICENSE` y `THIRD_PARTY.md`.
