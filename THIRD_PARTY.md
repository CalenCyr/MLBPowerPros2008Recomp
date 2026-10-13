# Dependencias de esta prueba

El código propio de esta integración se publica bajo GPLv3; consultar `LICENSE`. Los binarios y assets de la copia del juego no se incluyen en el repositorio.

| Dependencia | Versión o revisión usada | Ubicación de trabajo | Uso |
|---|---|---|---|
| [DolRecomp](https://github.com/AH64-dll/DolRecomp) | `71c3122a92bf25a9fbe91fe7c662ad70125fba59`, GPLv3 | `local/vendor/DolRecomp` | Solo `-RegenerateMap`: reutiliza su análisis ya generado en `local/` |
| [decomp-toolkit](https://github.com/encounter/decomp-toolkit) | 1.8.4 | `local/tools` | Análisis y extracción |
| [NKit](https://github.com/Nanook/NKit) | 3.1.0 | `local/tools/nkit` | Expansión de la imagen |
| [Dolphin](https://github.com/dolphin-emu/dolphin) | Ejecutable ya instalado, identificado por SHA256 | `D:\Dolphin-x64` | Extracción inicial |
| [ModernGekko](https://github.com/ExpansionPak/ModernGekko) | `a2e4e2b026a68d4848f20ebf16f0e0ddeb573957`, GPL-3.0-or-later | `local/vendor/ModernGekko` | Solo `-RegenerateMap`: firmas SDK (`totaldb.dsy`) de su Dolphin |
| [RecompCore](https://github.com/ExpansionPak/RecompCore) | `cf8ceb81b47d6172164cd0572f57aa7624719f33`, licencias por archivo | Submódulo `vendor/dolphin` de ModernGekko | Contiene ese `totaldb.dsy` |
| [WiiCompiled](https://github.com/patchzyy/Wiicompiled) | `6fa24737d3362b6cba8162671745262751f457b8`, GPLv3 | `local/vendor/Wiicompiled` | Traductor y runtime actuales (con los parches de `tools/patches/wiicompiled-*`); sus scripts `Prepare-*` arman las herramientas y dependencias del Setup |
| [nod / nodtool](https://github.com/encounter/nod) | v2.0.0-alpha.10, SHA256 `1e150e33…948d`, MIT/Apache-2.0 | `local/tools/nodtool` | Lectura y extracción de la imagen del jugador en el Setup |
| [llvm-mingw](https://github.com/mstorsjo/llvm-mingw), [CMake](https://cmake.org), [Ninja](https://ninja-build.org) | 20260616, 4.3.3 y 1.13.2 (fijados por Wiicompiled) | Setup: `toolkit/` | Compilación local en la PC del jugador |
| [PowerUp+](https://github.com/ogura-connection/PowerUpPlus) / [PowerUp](https://github.com/CSho27/PowerUp) | `eb1a2c2`, GPLv3 | `local/vendor/PowerUpPlus`; copia de trabajo con `tools/patches/powerupplus-2008.patch` en `local/powerupplus`; Setup: `workspace/powerupplus` → `Game/powerupplus` | Formato del roster de 2007 (definiciones de campos de `GSPlayer.cs` y tabla de caracteres), base de la conversión a 2008 (`tools/roster`, `runtime/src/roster_fields.inc`); el parche le agrega importar y exportar rosters de 2008 (`tools/powerupplus.ps1`). El Setup redistribuye su compilación autocontenida (interfaz web y servidor, con sus librerías CSV/JSON) junto con su licencia, el commit y el parche en `licenses/`. No incluye su partida base de 2007 ni sus rosters `.dat`, que son contenido del juego |
| [.NET SDK](https://dotnet.microsoft.com) | 10.0.401 (`dotnet-install.ps1 -Channel 10.0`), MIT | `local/tools/dotnet10`; Setup: runtime de .NET y ASP.NET Core (MIT) dentro de `Game/powerupplus` | Compilar PowerUp+, que apunta a .NET 10; la compilación autocontenida lleva su runtime |
| MoonInning UI pack | Arte original aportado por el autor del proyecto (no es contenido del juego) | `assets/launcher` (procesado por `tools/launcher/prepare_mooninning_art.py`) | Fondos del launcher |
| [SDL3](https://libsdl.org), [Dear ImGui](https://github.com/ocornut/imgui), Dawn y demás dependencias de aurora | Versiones fijadas por aurora/Wiicompiled | Setup: `workspace/Dependencies` | Runtime del juego y ventana del Setup |

Se mantienen los archivos de licencia de cada descarga. El repositorio no incluye copias de estas dependencias. La release del Setup redistribuye solo las herramientas y fuentes indicadas como "Setup", con sus licencias en `licenses/` y `toolkit/README-LICENSES.txt`; nunca contenido del juego. El runtime anterior basado en ModernGekko/DolRecomp, sus parches y sus informes están en el tag de git `moderngekko-era`.
