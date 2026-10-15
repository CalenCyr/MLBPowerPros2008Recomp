# Fase 0 — análisis inicial

*English version: [en/phase0-report.md](en/phase0-report.md)*

Fecha: 7 de octubre de 2026. Proyecto: `D:\MLBPowerPros2008Recomp`.

> **Informe histórico**: describe el punto de partida. Hoy el juego es jugable de forma nativa sobre Wiicompiled (`docs/wiicompiled-feasibility.md`), y `project.bin` y el roster están descifrados (`docs/ingenieria-inversa.md`). Los informes y scripts de DolRecomp/ModernGekko que cita (`cpu-translation-report.md`, `runtime-integration-report.md`, `recompile.ps1`) están en el tag de git `moderngekko-era`. Lo que aquí figura como pendiente (extractor de `project.bin`, archivo de rosters, framerate) ya está resuelto en esos documentos.

**Estado (en su momento): análisis reproducible; fase 0 aún abierta. No hay un port nativo jugable.** Se prepararon el proyecto, las herramientas, la extracción, el inventario del disco y el análisis estructural de DOL/REL. Un análisis posterior estimó 48.175 funciones y produjo una primera traducción compilada; ver `docs/cpu-translation-report.md`. Faltan la validación de límites de funciones, la medición de framerate y el análisis de los contenedores propios del juego.

## Entrada e integridad

- Fuente: copia propia del usuario en formato NKit (`.nkit.iso`).
- Tamaño: 1.254.588.416 bytes.
- SHA256: `87eca8f56d2684a7b32c014213400e9c212b3f84009c7c7ca38a1f7ea73adeb2`.
- Cabecera: Wii, `RL8E54`, USA/NTSC-U, revisión exterior 0, título interno `MLB Power Pros`.
- Marcador en offset `0x200`: `NKIT v01`.
- Extracción DATA con DolphinTool: completada. Las 28 entradas de archivo del FST coinciden con los tamaños de los archivos extraídos.
- Expansión con NKit 3.1.0: creó `local/images/MLB Power Pros 2008 (USA).iso`, legible por dtk.
- **No es una restauración verificada del disco original.** NKit informó que no encuentra la partición de actualización identificada por `940B57BB`, sustituyó su espacio por ceros y reportó `VerifyFailed`. dtk informó `Redump: Not found`. No se ha demostrado que esa partición sea la única diferencia del disco.
- ISO expandido: CRC32 `42117b18`, SHA1 `b424c7786e1f6bdb45b0adb7069084e4de425560`.
- Una repetición con `--skip-if-completed` reutilizó el ISO existente y NKit mostró `Unverified (NoVerify)`; dtk volvió a verificarlo y reportó la misma ausencia de coincidencia con Redump. El registro NKit más reciente corresponde a esa repetición.
- El DOL y el REL extraídos directamente del NKit son idénticos por SHA256 a los extraídos del ISO expandido. Esto verifica la consistencia de esas dos rutas de extracción, no la autenticidad respecto de un dump original.
- La cabecera interna de DATA indica revisión 1; la cabecera exterior indica 0. Se conserva esa discrepancia como dato de entrada.

La imagen original no se modificó. Los resultados y el contenido extraído permanecen en `local/`, excluido de Git.

## Código

| Componente | Archivo, bytes | Text, bytes | Data, bytes | BSS, bytes |
|---|---:|---:|---:|---:|
| `main.dol` | 2.299.840 | 1.200.448 | 1.099.136 | 954.200 |
| `ovl_main.rel` | 11.229.928 | 7.820.936 | 1.806.784 | 154.196 |

Las cifras de text/data provienen de las tablas binarias de secciones. BSS ocupa memoria al cargar; no representa bytes adicionales almacenados en el archivo. Total de text: **9.021.384 bytes**. El REL contiene aproximadamente el 87 % de ese código y es imprescindible para la recompilación.

- Punto de entrada del DOL: `0x8000403C`.
- `main` identificado por dtk: `0x8005E4C4`.
- REL: módulo 1, formato versión 3, 17 entradas en la tabla original de secciones, incluidas entradas vacías.
- SHA256 del DOL: `789c208f1611c4b150d272eb32cbd461d24aebbc5d7c11a420102d868ff1c5f7`.
- SHA256 del REL: `dcc37a1a4824702feff5bcaa6aae7cefdedfc3b5d832fbf3de92b982a59b4edc`.
- `dtk dol info` identificó 433 direcciones únicas con nombres en secciones de código y 200 funciones en tablas de excepciones. **Estas cifras no son el total de funciones**, ni deben sumarse entre sí.
- `dtk rel info` identificó entradas de ciclo de vida del módulo (`_prolog`, `_epilog`, `_unresolved`) y funciones del runtime C++. El posterior `dtk dol split` identificó 5.067 definiciones de función en el DOL y 43.108 en el REL; son límites inferidos, aún sin validación manual.

Registros: `local/analysis/dol-info.txt`, `local/analysis/rel-info.txt`, `local/analysis/inventory.json`.

## Símbolos, compilador y SDK

No hay archivos `.map`, `.sym`, `.elf` ni `.sel` directamente en el FST. Esto no descarta datos internos en `project.bin`. Tampoco se han comparado todavía otras entregas de la saga.

El DOL contiene identificadores de Metrowerks, del runtime CodeWarrior y MetroTRK. Es evidencia de esa familia de toolchain; **no identifica una versión exacta de MWCC**.

Se localizaron etiquetas de módulos RVL SDK con fechas de compilación diferentes:

| Módulos | Fecha observada |
|---|---|
| THP, EXI, SI, DVD, VI, AI, AX, DSP, SC, ENC, KPAD | 8 de agosto de 2007 |
| RFL | 5 de septiembre de 2007 |
| PAD | 3 de octubre de 2007 |
| GX, NAND | 11 de diciembre de 2007 |
| OS | 30 de enero de 2008 |
| HBM | 7 de febrero de 2008 |

Muchas etiquetas llevan el identificador `0x4199_60831`; HBM muestra `0x4199_60726`. Son módulos con distintos builds, no una única versión del SDK demostrada. Los offsets y el resto de candidatos quedan en `local/analysis/strings-candidates.json`.

## Assets

El listado completo está en `docs/fst-inventory.csv` y en `local/analysis/fst-dolphin.txt`.

| Archivo o grupo | Observación comprobada | Pendiente |
|---|---|---|
| `project.bin` | 406.388.736 bytes; no identifica un contenedor estándar por su primera cabecera | Documentar tabla de entradas, compresión y posibles rosters/modelos/texturas |
| `movie/*.thp` | Tres archivos con firma THP | Integrar reproducción cuando haya runtime |
| `sound/SeData.bin` | Cabecera KSS SE Link Data, fecha 28/04/2008 | Estructura de enlaces y efectos |
| `sound/TrSeData.bin` | Cabecera KSS BGM Link Data, fecha 06/05/2008 | Índices de música |
| `sound/WaveData.bin` | Cabecera KSS Wave Link Data, fecha 28/04/2008 | Metadatos y formato de muestras |
| `sound/strbgm.bin` | 321.687.552 bytes | Códec, entradas y streaming |
| `sound/voice0.bin` a `voice17.bin` | 18 bancos | Códec e índices |
| `opening.bnr` | Archivo de presentación del disco | Analizar su contenedor si se necesita |

KSS es una etiqueta observada, no una identificación concluyente de un proveedor de middleware. No se ha localizado aún un archivo de rosters separado. No se implementó un extractor de `project.bin` ni un override de assets.

## Framerate, input y online

No se lanzó el juego ni se midió su framerate en menús o partidos. No se afirma que sea 30 o 60 fps. Medir FPS, velocidad de emulación y cadence de lógica/render por separado antes de diseñar interpolación.

El escaneo de strings ASCII del DOL y el REL no encontró los patrones `DWC_`, `gamespy`, `nwfc`, `Nintendo WFC`, `nhttp`, `SOStartup`, `SOConnect` ni `SOInit`. **La ausencia de strings no demuestra que no exista online.** Faltan comprobación de menús/manual y análisis de referencias/código antes de escoger redirección WFC o netplay por inputs.

Hay evidencia de SDK PAD, KPAD y WPAD. La asignación de gestos y controles se decidirá con el comportamiento real del juego.

## Herramientas y reproducción

- [decomp-toolkit](https://github.com/encounter/decomp-toolkit), versión 1.8.4, commit `a0c455e46cab58e1d2e0885623f85089ff0499db`.
- [NKit](https://github.com/Nanook/NKit), CLI Windows x64 3.1.0.
- DolphinTool de la instalación existente en `D:\Dolphin-x64`; su hash se registra en `local/analysis/tool-versions.json`. El ejecutable no declara una versión de archivo, por lo que se identifica por su SHA256.
- Descargas de dtk/NKit fijadas y verificadas por SHA256 en `config/tools.lock.json`.
- `tools/bootstrap.ps1` prepara herramientas; `tools/phase0.ps1` extrae y analiza; `tools/analyze_disc.py` valida FST y tablas de secciones, calcula hashes y genera el inventario.

Validación de este flujo de fase 0: preparación repetible sin nuevas descargas, ejecución completa del inventario sobre la extracción real, lectura de DOL/REL por dtk, comprobación de tamaños del FST y comparación de DOL/REL entre extracción directa y expandida. La posterior traducción PPC a C se realiza con `tools/recompile.ps1` y se documenta en `docs/cpu-translation-report.md`.

## Próximos entregables y riesgos

1. Cerrar fase 0: análisis completo de funciones/saltos/relocaciones, medición en Dolphin, comprobación de online y primera documentación de `project.bin`. Mantener explícito el estado de verificación del disco.
2. Fase 0.5: probar los traductores candidatos con **DOL y REL**, registrar commit, comandos, resultados y requisitos; después seleccionar runtime. La recomendación del brief sigue siendo una hipótesis.
3. Fase 1: generar C/C++, compilar y registrar opcodes y saltos sin resolver. La primera traducción ya compila; ver `docs/cpu-translation-report.md` para cobertura y límites.
4. Fase 2: demostrar arranque nativo y carga/relocación del módulo antes de comprometer mejoras gráficas o netplay.

La estimación temporal de 6–12 meses del brief no se ha validado. Con el inventario actual, una nueva fecha de entrega sería especulativa. El próximo punto útil para estimar es una prueba de traducción de los 9 MB de text y un arranque mínimo del runtime.

Riesgos observados: la mayoría del código está en un REL sin nombres de gameplay identificados; assets y audio usan grandes bancos propios; el disco expandido no verifica contra Redump; aún no hay datos dinámicos de framerate/input. Precisión PPC, self-modifying code, determinismo y compatibilidad GX siguen sin evaluar.

Se realizó una primera prueba de traducción y compilación con [DolRecomp](https://github.com/AH64-dll/DolRecomp), descrita en `docs/cpu-translation-report.md`. Se compiló y probó [ModernGekko](https://github.com/ExpansionPak/ModernGekko) con el DOL recompilado; ver `docs/runtime-integration-report.md`. [Wiicompiled](https://github.com/patchzyy/Wiicompiled)/aurora y [NWiiRecomp](https://github.com/BlackLineInteractive/NWiiRecomp) siguen sin pruebas de ejecución con este juego. La integración de comprobación usa GPLv3; el runtime definitivo aún no se ha escogido.
