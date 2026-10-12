# Dependencias de esta prueba

El código propio de esta integración se publica bajo GPLv3; consultar `LICENSE`. Los binarios y assets de la copia del juego no se incluyen en el repositorio.

| Dependencia | Versión o revisión usada | Ubicación de trabajo | Uso |
|---|---|---|---|
| [DolRecomp](https://github.com/AH64-dll/DolRecomp) | `71c3122a92bf25a9fbe91fe7c662ad70125fba59`, GPLv3 | `local/vendor/DolRecomp` | Traducción y helpers de CPU para comprobaciones |
| [decomp-toolkit](https://github.com/encounter/decomp-toolkit) | 1.8.4 | `local/tools` | Análisis y extracción |
| [NKit](https://github.com/Nanook/NKit) | 3.1.0 | `local/tools/nkit` | Expansión de la imagen |
| [Unicorn](https://github.com/unicorn-engine/unicorn) | 2.1.4 | `local/python` | Referencia independiente para tests de PowerPC |
| [LLVM / Clang](https://github.com/llvm/llvm-project/releases/tag/llvmorg-22.1.8) | 22.1.8, Apache-2.0 con LLVM Exceptions | `local/tools/llvm-22.1.8` | Compilador privado del experimento DOL; sin instalación global |
| [Dolphin](https://github.com/dolphin-emu/dolphin) | Ejecutable ya instalado, identificado por SHA256 | `D:\Dolphin-x64` | Extracción inicial |
| [ModernGekko](https://github.com/ExpansionPak/ModernGekko) | `a2e4e2b026a68d4848f20ebf16f0e0ddeb573957`, GPL-3.0-or-later | `local/vendor/ModernGekko` | Runtime de diagnóstico y formato de módulos |
| [RecompCore](https://github.com/ExpansionPak/RecompCore) | `cf8ceb81b47d6172164cd0572f57aa7624719f33`, licencias por archivo | Submódulo `vendor/dolphin` de ModernGekko | Servicios de hardware y helpers de CPU de GXRuntime |
| [WiiCompiled](https://github.com/patchzyy/Wiicompiled) | `6fa24737d3362b6cba8162671745262751f457b8`, GPLv3 | `local/vendor/Wiicompiled` | Traductor y runtime actuales (con los parches de `tools/patches/wiicompiled-*`); sus scripts `Prepare-*` arman las herramientas y dependencias del Setup |
| [nod / nodtool](https://github.com/encounter/nod) | v2.0.0-alpha.10, SHA256 `1e150e33…948d`, MIT/Apache-2.0 | `local/tools/nodtool` | Lectura y extracción de la imagen del jugador en el Setup |
| [llvm-mingw](https://github.com/mstorsjo/llvm-mingw), [CMake](https://cmake.org), [Ninja](https://ninja-build.org) | 20260616, 4.3.3 y 1.13.2 (fijados por Wiicompiled) | Setup: `toolkit/` | Compilación local en la PC del jugador |
| [SDL3](https://libsdl.org), [Dear ImGui](https://github.com/ocornut/imgui), Dawn y demás dependencias de aurora | Versiones fijadas por aurora/Wiicompiled | Setup: `workspace/Dependencies` | Runtime del juego y ventana del Setup |
| [ModernGekko-Template](https://github.com/ExpansionPak/ModernGekko-Template) | `c2553a99584b2045dbe46a70e1570994dae8beef` | `local/vendor/ModernGekko-Template` | Referencia de integración; no enlazado en nuestro módulo |

Se mantienen los archivos de licencia de cada descarga. El repositorio no incluye copias de estas dependencias. La release del Setup redistribuye solo las herramientas y fuentes indicadas como "Setup", con sus licencias en `licenses/` y `toolkit/README-LICENSES.txt`; nunca contenido del juego. El parche local de DolRecomp solo corrige la dependencia de enlace de una prueba.
