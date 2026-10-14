# MLB Power Pros 2008 (Wii) — Referencia de ingeniería inversa

Lo que se sabe del juego por dentro, ordenado por sistema: direcciones, estructuras, formatos de archivo, hilos y el flujo de escenas. Sale del trabajo del proyecto de recompilación nativa y está pensado para la comunidad de mods y para futuros desarrolladores.

- **Versión:** `RL8E54` (EE. UU., NTSC-U). Todas las direcciones son de esta versión.
  - `main.dol` SHA-256 `789c208f1611c4b150d272eb32cbd461d24aebbc5d7c11a420102d868ff1c5f7`
  - `ovl_main.rel` SHA-256 `dcc37a1a4824702feff5bcaa6aae7cefdedfc3b5d832fbf3de92b982a59b4edc`
- **Qué no es:** no es una decompilación. El juego está recompilado entero (traducido de PowerPC a C++), pero casi todo su código sigue sin nombre (`func_8003A248`…). Lo de aquí se descubrió al arreglar fallos concretos o al construir herramientas (mods, roster, benchmark).
- **Fiabilidad:** cada dato indica de dónde sale. "Desensamblado" y "ejecución" están comprobados en el binario o en el juego corriendo. "Observado" es comportamiento visto sin leer el código que lo produce.
- **Sin contenido del juego:** este documento no incluye bytes, recursos ni código del juego, solo descripciones.
- **Cómo generar el PDF:** `python tools/build_re_pdf.py` (lo escribe en `local/docs/`).

## Índice

1. [Ejecutable y mapa de memoria](#1-ejecutable-y-mapa-de-memoria)
2. [Arranque y sistema operativo](#2-arranque-y-sistema-operativo)
3. [Hilos y ritmo](#3-hilos-y-ritmo)
4. [Motor de sonido y comentarista](#4-motor-de-sonido-y-comentarista)
5. [Disco y `project.bin`](#5-disco-y-projectbin)
6. [Roster: `game_data.pack` y formato de jugador](#6-roster-game_datapack-y-formato-de-jugador)
7. [Escenas, menús y preparación de un partido](#7-escenas-menús-y-preparación-de-un-partido)
8. [Gráficos (GX y VI)](#8-gráficos-gx-y-vi)
9. [Mandos](#9-mandos)
10. [Partidas guardadas, NAND, SYSCONF y ES](#10-partidas-guardadas-nand-sysconf-y-es)
11. [Bibliotecas y funciones identificadas](#11-bibliotecas-y-funciones-identificadas)
12. [Peculiaridades del juego que importan al portarlo](#12-peculiaridades-del-juego-que-importan-al-portarlo)
13. [Cómo seguir investigando](#13-cómo-seguir-investigando)

---

## 1. Ejecutable y mapa de memoria

El juego es un DOL pequeño y un módulo REL grande con casi todo el juego.

| | Archivo | Texto | Datos | BSS |
|---|---:|---:|---:|---:|
| `sys/main.dol` | 2.299.840 | 1.200.448 | 1.099.136 | 954.200 |
| `files/ovl_main.rel` | 11.229.928 | 7.820.936 | 1.806.784 | 154.196 |

- **Entrada:** `__start` en `0x8000403C`; `main` en `0x8005E4C4`.
- **Funciones:** el REL tiene el 87 % del código. Hay 48.177 funciones en el mapa: 5.065 en el DOL y 43.112 en el REL. Solo 1.794 tienen nombre (casi todas del SDK, en el DOL).
- **Áreas de datos pequeños:** `r13` (`_SDA_BASE_`) = `0x80322060` y `r2` (`_SDA2_BASE_`) = `0x80323940`. Las fija `__init_registers` (`0x800041A8`).
- **REL `ovl_main.rel`:**
  - Módulo 1, formato de REL versión 3.
  - Cargado en `0x80575580`, con su BSS en `0x8102B0C0`.
  - `_prolog` `0x80AA0718`, `_epilog` `0x80AA0794`, `_unresolved` `0x80AA07DC`.
- **Detalle del BSS del REL** (ejecución):
  - El REL ocupa un hueco libre entero de `0xAB5B20` bytes en el montón principal y termina en `0x8102B0A0`.
  - El BSS va justo después, tras una cabecera de bloque de `0x20` bytes: en `0x8102B0C0`.
  - Si el BSS queda `0x20` más abajo, sus últimas variables pisan la cabecera del bloque siguiente y rompen la lista libre del montón.
- **Tope de la arena:** `0x817FFD40`. Dolphin coloca el FST (`0x2C0` bytes) arriba del todo de MEM1.
  - El juego dimensiona su montón principal con toda la arena y lo llena casi al byte.
  - Con una arena más baja, una carga de 278 KB devuelve NULL. Entonces el juego copia un paquete `PACKWII` a `0x80000000` y destruye las variables globales del sistema.
- **Montón principal** (desensamblado de `0x80051474`):
  - Objeto en `0x802B57A8`; búsqueda first-fit por la lista libre (`+0x10`).
  - Cabecera de bloque de `0x20` bytes antes de los datos:

| Offset | Campo |
|---|---|
| `+0x00` | banderas (`0x80000000` libre, `0x40000000` usado) |
| `+0x08` | tamaño de datos |
| `+0x0C` / `+0x10` | enlaces de la lista libre |
| `+0x14` / `+0x18` | bloque anterior / siguiente en memoria |

- **Objetos únicos del juego**, punteros dentro del BSS del REL:
  - `0x81033268`: gestor de escenas (sección 7)
  - `0x8104E1D8`: configuración del partido
  - `0x8103D118`: datos comunes del partido

Fuentes: `docs/phase0-report.md`, `config/wiicompiled/rl8e54.yml`, `tools/patches/wiicompiled-mlb-overlay-loader.patch`, `wiicompiled-rel-bss-address.patch`, `wiicompiled-match-benchmark.patch`.

## 2. Arranque y sistema operativo

**Secuencia:**
1. `__start` llama a `__init_registers` y a `__init_cpp` (`0x800A8730`), y luego a `main`.
2. `main` carga `ovl_main.rel` del DVD, lo enlaza (`OSLink`) y llama a su `_prolog`.
3. Pantallas: aviso de la correa del Wii Remote (pide A), "NOW LOADING" (mientras carga el REL y lee más de `project.bin`), comprobación de memoria ("The Wii system memory is being checked."), logo de 2K Sports, vídeo de introducción, menú principal.

**Cargador del REL, `0x80051474`** (reconstruido en `hle/mlb/rel_loader.cpp`):
- Recibe el índice de módulo en `r4` y devuelve 1 si lo carga bien.
- Tabla de módulos en `0x8020B920`, entradas de `0x28` bytes:

| Offset | Campo |
|---|---|
| `+0x0C` | puntero al nombre de archivo |
| `+0x10` | contador de usos |
| `+0x14` | dirección del módulo; si no es 0, ya está cargado y solo suma un uso |
| `+0x18` | tamaño |
| `+0x1C` | dirección del BSS |
| `+0x20` | tamaño del BSS |

- Pasos de la carga:
  1. `DVDOpen` `0x800A9764`
  2. reserva con `HeapAlloc` `0x8005A804` (alineado a `0x20`)
  3. `memset` + `DCFlushRange` `0x8009C488`
  4. `DVDReadPrio` `0x800A9CDC` con prioridad 2
  5. `DVDClose` `0x800A9A10`
  6. reserva el BSS
  7. `OSLink` `0x800A1678`
  8. llama a `_prolog` (cabecera del módulo `+0x34`)
- Si algo falla libera con `HeapFree` `0x8005A76C`.

**Memoria baja:** la cabecera de disco en `0x80000000` lleva `RL8E` + `54`. El juego la sobrescribe una vez en marcha, así que el código de juego no se puede leer de ahí después del arranque.

**SYSCONF:**
- `OSInit` (`0x8009AA90`) espera mientras `SCCheckStatus` (`0x800D1AB0`) devuelve "ocupado"; la lectura la lanza `SCInit` (`0x800D1A10`).
- Estado del trabajo en `0x8031B788` (1 ocupado, 3 lectura terminada, 0 listo).
- Bloque de control en `0x802D3E40` y búfer de SYSCONF en `0x802D3FE0` (`0x4000` bytes).
- Si el SYSCONF no es válido (lo comprueba `0x800D2064`), el juego crea uno vacío con las marcas `SCv0` y `SCed` y arranca con valores por defecto.

**STM:** `__OSInitSTM` (`0x800A5B6C`) guarda su bandera de inicio en `r13-0x6DDC` (`0x8031B284`). En `+4` y `+8` van los descriptores de `/dev/stm/immediate` y `/dev/stm/eventhook`.

**Variables globales del SDK localizadas:**

| Dirección | Qué es |
|---|---|
| `0x802B6CD0` | `__OSErrorTable` (en `+0x40`, la de coma flotante) |
| `0x802B7078` | `DefaultThread` |
| `0x802B7390` | `RunQueue` |
| `0x802B7490` | `IdleThread` |
| `0x8031B1F0` | cola de alarmas (`r13-0x6E70`) |
| `0x8031B248` | puntero a la tabla de interrupciones |
| `0x8031B268` | contador de `OSDisableScheduler` |
| `0x8031A5D8` | `SwitchThreadCallback` |
| `0x8031B290` / `0x8031B298` | aviso y callback del botón de apagado |
| `0x8031B740`, `0x8031B744` | IPC: inicializado, búfer bajo/alto |
| `0x80308898` | `btm_cb` (Bluetooth) |

**Objeto de hilo (`OSThread`):** `+0x2C8` estado (u16), `+0x2CC` suspensiones, `+0x2D0` prioridad, `+0x2DC` cola de espera.

Fuentes: `docs/wiicompiled-feasibility.md`, `config/wiicompiled/rl8e54-data.csv`, `hle/mlb/sc_check_status.cpp`, `wiicompiled-mlb-stm-sda.patch`, `wiicompiled-mlb-bringup.patch`.

## 3. Hilos y ritmo

- **El juego va a 60 fotogramas por segundo** y espera al retrazo vertical (`VIWaitForRetrace`, `0x800B327C`). No dibuja fotogramas de más.
- **Hilos de sonido:** el juego tiene un hilo temporizador que despierta al hilo de sonido cada 5 ms (sección 4). Mide el tiempo en vueltas: cada vuelta vale 5 ms.
- **El hilo principal casi nunca se bloquea:**
  - Durante "NOW LOADING" gira en un bucle que no se bloquea. En consola, los otros hilos avanzan porque la interrupción de VI da paso al hilo de más prioridad listo.
  - Al empezar un partido, mientras los jugadores van a sus posiciones, calcula 17-20 ms seguidos (un fotograma entero) sin ceder.
- **Interrupciones:** el código del juego llama a menudo a `OSDisableInterrupts` (`0x800A0944`), `OSEnableInterrupts` (`0x800A0958`) y `OSRestoreInterrupts` (`0x800A096C`). En consola, una interrupción pendiente (por ejemplo, un temporizador vencido) se atiende justo al reactivarlas.
- **Funciones de hilos del SDK:**

| Función | Dirección |
|---|---|
| `OSCreateThread` | `0x800A4448` |
| `OSResumeThread` | `0x800A4B50` |
| `OSInitThreadQueue` | `0x800A3E90` |
| `SelectThread` | `0x800A41CC` |
| `OSSleepThread` | `0x800A4F7C` |
| `OSWakeupThread` | `0x800A5068` |
| `OSSleepTicks` | `0x800A526C` |

- **Espera de la biblioteca de Miis (RFL):** `RFLWaitAsync` (`0x800876A0`) gira sobre `RFLiIsWorking` (`0x80087B94`), que lee el indicador `+0x1B34` del gestor (puntero en `0x8031B168`).
- **Para portarlo:** el juego da por hecho que los temporizadores llegan a tiempo y que las interrupciones cortan cualquier cálculo. Con hilos cooperativos hay que ofrecer puntos de cambio (tras `GXCopyDisp` y al reactivar interrupciones) y recuperar los periodos perdidos.

Fuentes: desensamblado de `0x80027A54`/`0x80027BF8`; `wiicompiled-preemption-point.patch`, `wiicompiled-periodic-sleep.patch`, `docs/wiicompiled-feasibility.md`.

## 4. Motor de sonido y comentarista

Investigado en octubre de 2026 para arreglar el petardeo del comentarista (desensamblado, puntos de vigilancia de memoria y ejecución). Las funciones AX sin nombre se identificaron por su comportamiento, no por firma.

**Archivos de sonido en el disco:**

| Archivo | Contenido |
|---|---|
| `sound/SeData.bin` | "KSS SE Link Data" |
| `sound/TrSeData.bin` | "KSS BGM Link Data" |
| `sound/WaveData.bin` | "KSS Wave Link Data" |
| `sound/strbgm.bin` | música en stream (321.687.552 bytes) |
| `sound/voice0.bin` … `voice17.bin` | 18 bancos de voz del comentarista |

- "KSS" es la etiqueta que aparece en los archivos; no está confirmado de qué middleware viene.
- En el REL también hay JAudio2/JASystem (`JAS*`, `JAU*`).
- La salida del juego va en bloques de 3 ms a 32 kHz.

### Hilos

| Dirección | Qué es | Prioridad |
|---|---|---|
| `0x80027A54` | **Hilo de sonido.** Bucle: trabajo de sonido y `OSSleepThread(r13-0x7378)` hasta el siguiente aviso. Objeto de hilo en `0x80242888` | 4 |
| `0x80027BF8` | **Temporizador de sonido.** Bucle: `OSSleepTicks(5 ms)` y `OSWakeupThread(r13-0x7378)` | 3 |

- Se crean juntos con `OSCreateThread`, pilas de `0x1000` bytes, y se arrancan con `OSResumeThread`.
- El periodo sale del reloj del bus: `[0x800000F8] / 4 / 1000 × 5` ticks = 5 ms (303.750 ticks a 243 MHz).
- **El juego cuenta el tiempo en vueltas, no con un reloj:** en consola son 200 vueltas por segundo, y si llegan tarde el audio que depende de ellas se alarga.
- Cada vuelta, en orden:
  1. `0x800329BC`, `0x80027CD4`, `0x80028290`, `0x80027F60`, `0x8002809C`, `0x80027EAC`
  2. `0x8002F660`
  3. el gestor de streams `0x80038E50`
  4. `0x80035A3C`
  5. el proceso de canales `0x8002C604`
- Cada 4 vueltas llama además a `0x80007360` y `0x800073B0`. El contador de vueltas está en `r13-0x73C0`.

### Canales y voces AX

- **55 canales** en `0x80236930`, de 596 (`0x254`) bytes cada uno. El puntero a la voz AX (`AXVPB`) está en `+584`.
- El comentarista usa el **canal 19**.
- **Cola de órdenes de sonido** en `0x80297C20`: entradas de 28 bytes (tipo, canal, valor).
  - El tipo 8 cambia el ratio de remuestreo; ratio 0 = pausa.
  - Despachador: `0x8002D038`.
- `0x8002C480(canal, modo)`: 0 consulta, 1 reserva, 2 libera. La parada sigue la cadena `0x8002C480` → `0x8002C310` → `AXSetVoiceState`.
- **Funciones AX localizadas:**

| Función | Dirección |
|---|---|
| `AXSetVoiceSrc` | `0x800BBD38` |
| `AXSetVoiceSrcRatio` | `0x800BBDBC` |
| `AXSetVoiceState` | `0x800BB99C` |
| `AXSetVoiceAddr` | `0x800BBB08` |
| `AXAcquireVoice` | `0x800B8CC0` |
| `AXFreeVoice` | `0x800B8C44` |
| `__AXSetupDsp` | `0x800BA458` |

- Tarea DSP de AX en `0x802C12A0`; imagen del microcódigo en `0x80225E00`.
- Callbacks de la tarea: init `0x800BA3E4`, resume `0x800BA3F0`, done `0x800BA444`, request `0x800BA454`.

### Streams del comentarista

- **Tabla de 4 objetos de stream** en `0x802A1A78`. `0x80038E50` recorre los 4 y llama al gestor `0x80038F08` para cada uno válido.
- Un objeto es válido si tiene `0x5A5A5A5A` en `+0x824` y `0x8A8A8A8A` en `+0x1960`. `+0x820` es su índice.
- **Estado en `+0x828`.** El gestor salta por la tabla `0x801559E0` y guarda lo que devuelve cada caso como estado siguiente:

| Estado | Destino | Qué hace |
|---|---|---|
| 0 | `0x80038F4C` | limpia el stream (libera lo apuntado por `+0x898`, `+0x8A0`, `+0x89C`, `+0x894`) |
| 1 | `0x800398BC` | carga; depende de `+0x848` (petición de DVD) mediante `0x8003B398` |
| 2 | `0x80039B94` | lee la cabecera de la frase y prepara su reloj; devuelve 3 |
| 3 | `0x8003A048` | arranca la reproducción |
| 4 | `0x8003A248` | reproduce: avanza el reloj; devuelve 4 o 5 |
| 5 | `0x800392E8` | fin de frase |
| 6 | `0x800392E0` | salida sin cambios |
| 7 | `0x800391C0` | `+0x8C0 = 5000`, pasa a 8 |
| 8 | `0x800391D4` | `+0x8C0 = 5000`, pasa a 3 |

- **Voces:** DSP-ADPCM mono a 22.050 Hz. Se remuestrean a 32 kHz con interpolación lineal; el ratio AX es la frecuencia × 2,048 (`0xB066` para 22.050 Hz).
- Hay **dos voces de stream** que se alternan, cada una con su búfer circular de 64 KB, y se reproduce una voz por frase o nombre.
- **Cabecera de frase** (bloque de `0x800` bytes antes de los datos):

| Offset | Contenido |
|---|---|
| `+0x00` | bytes de datos de la frase |
| `+0x04` | `(0xB4 o 0x78) << 16 \| 22050`: banderas y frecuencia |
| `+0x10` | **duración en milisegundos** (p. ej. `0x0A0F` = 2.575 ms) |
| `+0x88` | longitud en nibbles ADPCM |
| `+0xB0` | escala de predicción inicial |

- **Reloj de cada frase:**
  - `0x80039B94` (estado 2) copia la duración a `+0x858`; si es 0, la calcula con `0x80038430`. La ajusta por `+0x8F8`/`+0x8FA` (`(x + 0x100) >> 8`) y la guarda en `+0x874` (duración total) y `+0x85C`. Después pone `+0x858 = 0` y `+0x8C0 = 5000`.
  - `0x8003A248` (estado 4) **suma 5 a `+0x858` en cada vuelta**. Al llegar a `+0x874 − 10`, para la voz con `0x8002C7CC(+0x834)` y pasa al estado 5.
  - `0x8003A248` también avanza las posiciones del búfer (`+0x888`, `+0x8AC`, `+0x8B8`) según `+0x904` y `+0x8FC`.
  - `0x80038358(índice)` devuelve los ms que le quedan a la frase (`max(0, +0x874 − +0x858)`) en estado 4, `0xFFFF` en otros estados y 0 si el stream no existe.
  - Tras cada vuelta del estado 4, el gestor llama a `0x8002670C` con `+0x854`. Es un stub vacío (`blr`).
- **Cómo para el juego una frase:** pausa (ratio 0) y después libera y reasigna la voz. Lo hace 2-4 bloques (6-12 ms) después de que se acaben los datos, mientras el decodificador ADPCM mantiene su último nivel. Por eso el DSP original aplica una rampa a cero (*depop*).
- **Saturación:** las frases del comentarista llegan a ±32767 en los propios datos del disco: 11 de 12 frases decodificadas por separado saturan. No es un fallo de la recompilación.

**Fallo encontrado y su causa (para portadores):** si el temporizador de 5 ms no despierta 200 veces por segundo, el reloj de las frases va lento. Entonces la frase se para entre 1,2 y 1,7 veces tarde: suena el relleno de ceros y el principio de la frase siguiente, y luego se corta. Se oye como chasquidos y palabras cortadas.

Fuentes: desensamblado (`0x80027A54`, `0x80027BF8`, `0x80038E50`-`0x8003A41C`); `wiicompiled-periodic-sleep.patch`, `wiicompiled-audio-depop.patch`, `config/wiicompiled/rl8e54-data.csv`, `docs/wiicompiled-feasibility.md`.

## 5. Disco y `project.bin`

- **Disco:** `RL8E54`, título interno `MLB Power Pros`. El FST tiene 28 archivos, sin `.map`, `.sym` ni `.elf`. Los principales:
  - `sys/main.dol`, `files/ovl_main.rel`
  - `files/project.bin` (406.388.736 bytes)
  - `files/sound/*`
  - `files/movie/*.thp` (3 vídeos)
  - `opening.bnr`

**`project.bin`** (todo big-endian; verificado sobre sus 2.424 entradas):

| Offset | Contenido |
|---|---|
| `0x00` | versión = 2 |
| `0x04` | tamaño de sector = `0x800` |
| `0x0C` | huecos de la tabla hash = `0x1211` |
| `0x10` | tabla hash, en `0x40` |
| `0x14` | tabla de registros, en `0x6000` |
| `0x28` | tabla de orden, en `0x26000` |
| `0x2C` | tabla de nombres, en `0x2B000` |
| `0x34` | inicio de los datos, en `0x3D800` (el archivo acaba justo en `0x18390000`) |

- **Registros** de `0x1C` bytes: 0, offset del nombre, tamaño en sectores, alineación (`0x800`), 0, 0, tamaño en bytes.
- **Tabla de orden:** pares (registro, sector de inicio relativo a `0x3D800`), ordenados por sector. El par 0 no se usa y la lista acaba en (0, 0).
- **Nombres:** rutas terminadas en NUL que empiezan por `/`.
- **Tipos:** `.pack` (2.356 empiezan por `PACKWII `, 2 por `PACKPS2`), `.dat` y `.arc`. Dentro, los `.pack` son bloques con etiqueta (`SURF`, `SURG`…) y punteros relativos; ese formato interno **sigue sin documentar**.
- **Montaje:** `0x800431E8` monta `/PROJECT.BIN` (cadena en `0x80155DD0`) llamando a `0x80059E7C`.
- **Gestor de recursos de DVD:** `0x80042C28` solo procesa su cola cuando `DVDGetDriveStatus` dice que la unidad está libre. Al arrancar, el juego lanza `DVDInquiryAsync` y luego consulta el estado.
- **Entradas conocidas:**
  - `/game_data.pack` (roster, sección 6)
  - `/ClaimTheTitle.pack`, `team_logo.pack`
  - `env_title_logo`, `env_mainmenu`, `env_teamnameNN`
  - `PWM_mdl_uniform_MLB_<equipo>_<n>.pack`: uniformes. Cambiar el de CHC por el de NYY pone la gorra "NY" a los Cubs.
- **Para mods:** un `project.bin` reconstruido solo cambia los tamaños de los registros (`+0x08` sectores, `+0x18` bytes) y los sectores de inicio. La cabecera, la tabla hash y los nombres no cambian (`tools/projectbin.py`).

**Funciones DVD:**

| Función | Dirección |
|---|---|
| `DVDInit` | `0x800A9F7C` |
| `DVDOpen` | `0x800A9764` |
| `DVDClose` | `0x800A9A10` |
| `DVDReadPrio` | `0x800A9CDC` |
| `DVDLowInquiry` | `0x800B0F40` |
| `DVDLowRead` | `0x800B1840` |
| `DVDLowSeek` | `0x800B19F0` |

- Respuesta de unidad comercial que espera el juego: `+0` = `0x00000002`, `+4` = `0x20060526`, `+8` = `0x41000000`.

Fuentes: `docs/phase0-report.md`, `docs/mods.md`, `tools/projectbin.py`, `wiicompiled-dvd-low-completion.patch`.

## 6. Roster: `game_data.pack` y formato de jugador

- **`/game_data.pack`** (dentro de `project.bin`, 278.176 bytes): `PACKWII ` + cabecera de `0x20` + **bloque de roster de `0x43E80` bytes**.
  - Es el mismo bloque que guarda MLB Power Pros 2007 en su partida (`pm2maus.dat`, offset `0x68C74`).
  - **Todos los modos lo leen al arrancar**, MLB Life incluido. En 2008 el roster base no está en la partida guardada.
  - Lo cambiado en el modo Edit no llega a MLB Life. Observado: el juego deja fuera de MLB Life a los jugadores marcados como editados.

**Bloque de roster:**

| Offset | Contenido |
|---|---|
| `0x00000` | 1.500 jugadores × `0xB0` (2008 usa 1.007) |
| `0x40740` | 32 alineaciones × `0x48`: 18 entradas de 4 bytes (u16 jugador; nibble alto del byte 2 = posición) |
| `0x41040` | 200 agentes libres × 8 bytes (2008 usa 25) |
| `0x41680` | 32 equipos × `0x140` (30 franquicias + All-Star AL y NL): 40 entradas × 8 bytes |

- Entradas vacías y huecos sin jugador: llevan un registro "vacío" fijo, no ceros.
- Agentes libres: vacío = `00000000000f1400`; usado = id + `000000001400`.
- Los All-Star apuntan al mismo registro que el equipo normal.
- El número de jugador decide su hueco y su salario.

**Registro de jugador (`0xB0` bytes).** Los bits se cuentan desde el más significativo del inicio. Hay dos notaciones: `0x50.3` es byte `0x50`, bit 3; `0x283` sin punto es el número de bit (el mismo sitio: `0x283` = `0x50 × 8 + 3`). "`/ 9`" indica el ancho en bits.

| Campo | Posición |
|---|---|
| ID de jugador | u16 en `0x00` (0 = hueco vacío) |
| ID de nombre especial | u16 en `0x02`; `≥ 0xF00` = nombre largo, y el juego no lee `0x04`-`0x15` |
| Apellido / nombre | `0x16` y `0x32`, 14 caracteres u16 cada uno (tabla de caracteres de 2007) |
| Necesarios para la alineación | bits `0x4E.1`, `0x4E.2`, `0x4F.0`, `0x92.0` = 1 en todo jugador de 2008. Sin ellos, la pantalla de alineación sale vacía y todos como "P" |
| No editado / editado | bits `0x50.3` = 1 y `0x50.4` = 0 en los jugadores originales |
| Cara | bit `0x2A4`, 8 bits |
| Piel y ojos | bit `0x2AC`, 4 bits |
| Forma de bateo / lanzamiento | `0x2E4` / 9 y `0x2ED` / 9 (eran 8 en 2007) |
| Posición principal, capacidad P/C | `0x2F6` / 4, `0x2FA` / 3, `0x2FD` / 3 |
| Roles de lanzador (abridor, relevo, cerrador) | `0x62.5`, `0x63.0`, `0x63.3`, 3 bits cada uno |
| Fecha de nacimiento | año `0x414` / 11 (2008 = año de 2007 + 1), mes `0x420` / 4, día `0x424` / 5 |
| Años en las mayores, AVG, RBI, HR | `0x42A` / 5, `0x42F` / 10, `0x440` / 10, `0x44A` / 10 |
| ERA | `0x460` / 14 |
| Voz | bit `0x492`, 14 bits (misma posición que 2007, numeración nueva; ver "Voces renumeradas") |
| Repertorio | `0x4A0`-`0x4FF`: 12 lanzamientos de 5 bits de tipo + 3 de movimiento |

**Cambios respecto a 2007:**
- Los bytes `0x00`-`0x5B` y `0x60`-`0x6E` son iguales, salvo la cara.
- El segundo campo "contra zurdos" (`0x6F.5`) desaparece: los bits de 2007 de `0x380` a `0x3BE` se mueven 3 posiciones atrás.
- 2008 añade un bit en `0x77.4`: los bits de `0x3BF` a `0x41A` se mueven 2 atrás.
- La frontera −3/−2 está en `0x77.7` (bateador de tirón).
- Habilidades confirmadas con jugadores reales:
  - "push hitter" `0x71.0` (Ichiro, Mauer, Helton…)
  - "free swinger" `0x71.7` (Soriano, Guillén…)
  - "pull hitter" `0x77.7` (42 jugadores: Giambi, A-Rod…)
- **Caras renumeradas:** +0 / +1 / +2 / +7 / +12 para las caras de 2007 por debajo de 28 / 106 / 161 / 177 / resto. Coinciden 707 de 729 jugadores compartidos.
- **Piel y ojos:** 2008 inserta un tono en la posición 2, y los ojos marrones suman 6 (en 2007, 5).
- **Nombres largos nuevos** (IDs especiales): Van Benschoten 3867, Pignatiello 3893, E. Patterson 3895, Saltalamacchia 3896, Sonnanstine 3897, Chamberlain 3899, S. Rodriguez 3900, Lillibridge 3901.
- La tabla completa de unos 140 campos está en `kRosterFields` (`wiicompiled-mods.patch`) y en `PowerPros2008Fields.cs` (PowerUp+ parcheado). Los 127 bits que PowerUp no nombra (incluido el rasgo oculto) están en `kRosterUnnamedRuns`, en tramos.

**Getters del registro en el código (desensamblado).** El juego lee cada campo con una función pequeña: `lwz rX, D(r3)` + extracción del campo + `blr`, una tras otra desde `0x8082B000` (`ovl_main.rel` + `0x2B5A80`) en el orden del registro. Es la lista de campos tal como la ve el juego, con posición, ancho y signo:
- Coinciden con la tabla de arriba la forma de bateo y la de lanzamiento (9 bits), clutch `0x6F.5`/3, ánimo `0x70.1`/2, todas las habilidades de bateo de `0x70.3` a `0x73.0` (push hitter `0x71.0`, free swinger `0x71.7`…), las de defensa y las de lanzador hasta `0x80.7`, y el nacimiento.
- **"Table setter" `0x70.0` sigue vivo en 2008:** getter `0x8082B068` (`srwi 31`), setter del modo Edit en `0x8085EF74` (limita a 0–1) y dos funciones de juego que lo leen junto a "rally hitter": `0x80985E4C` y `0x80A30C54`. Ningún jugador de 2008 lo tiene, pero funciona si se le da a uno.
- Algunos campos que PowerUp trata como un solo bit son de **2 bits** para el juego. El otro bit viaja como "bit sin nombre", así que el conversor conserva el valor completo:
  - `0x73.5`/2 (deslizarse de cabeza): solo aparecen 0 y 2; el bit que modela PowerUp es el correcto.
  - `0x75.4`/2 con signo ("cannon arm" para PowerUp): +1 en 96 jugadores (Carpenter, Randy Johnson, Dye…) y −1 en 11 (Furcal, Rollins, Eckstein…). No aparece en la ficha del jugador: es un rasgo oculto.
  - `0x77.0`/2 y `0x77.2`/2 con signo (corredor y defensor agresivos): solo 0 y +1.
  - `0x78.4`/2 con signo: **habilidad nueva de 2008, partido nocturno** (Gd/Pr Night Game). +1 en 11 (Figgins, Cora, Easley…), −1 en 16 (Giambi, Kendall, Dellucci…).

**Comprobado en pantalla** (Arrange → un equipo → Fielder Select → stick C, "Player ABL"; capturas de Cora, Varitek, Casey, J.D. Drew, Eckstein y Rios cruzadas con sus bits):

| Bits de 2008 | Lo que muestra el juego | En PowerUp |
|---|---|---|
| `0x73.5`/2 | HD 1st Slide (valor 2) | WillSlideHeadFirst, bien |
| `0x73.7` | Tough Runner | IsToughRunner, bien |
| `0x74.4` | **Cannon Arm** (en los mensajes de MLB Life, "Laser Beam") | lo llama CanBarehandCatch (corregido para 2008) |
| `0x75.2` | Gd Block | IsGoodBlocker, bien |
| `0x75.4`/2 con signo | **nada en ninguna pestaña**: rasgo oculto. +1 en pitchers potentes y bateadores corpulentos, −1 en infielders pequeños; podría ser la complexión (sin confirmar) | **mal:** lo llama HasCannonArm |
| `0x76.2`/2 | Slugger (+1) / Slap Hitter (−1) | SlugOrSlap, bien |
| `0x76.4`/2 | Aggressive (+1) / Patient Hitter (−1) | bien |
| `0x76.6`/2 | Aggressive (+1) / Cautious Stealer (−1) | bien |
| `0x77.0`/2 | Aggressive Runner (+1) | IsAggressiveBaserunner, bien |
| `0x77.2`/2 | Aggressive Fielder (+1) | IsAggressiveFielder, bien |
| `0x77.4` | **Gd Eye**, bit nuevo de 2008 | no existe |
| `0x77.5` | **Barehand Catch** | sin nombre (Bit_77_7); en 2008 lo recibe CanBarehandCatch |
| `0x78.0`/2, `0x78.2`/2 | Gd/Pr Day Game, Gd/Pr Rain | bien |
| `0x78.4`/2 | **Gd (+1) / Pr (−1) Night Game**, nueva de 2008 | no existe |

- Los mismos jugadores tienen estos bits en 2007, así que en 2007 PowerUp también se equivoca de nombre.
- **Para 2008 se corrige por significado, y 2007 se deja como está.** Los rosters que genera PowerUp ya usan las casillas por su nombre (su roster 2025 marca "Cannon arm" a Tatis, Arenado, Salvador Pérez y Betts). Por eso la tabla de 2008 (`MOVED` en `powerup_to_2008.py`) lleva "Barehand catch" a `0x77.5` y "Cannon arm" a `0x74.4`. El rasgo oculto se conserva del registro de 2008, o vale 0 en un jugador nuevo, y los restos de la partida base de 2007 ya no se copian.
- Resultado con el roster 2025: antes, 0 brazos cañón, 117 barehand al azar y 100 rasgos ocultos basura; ahora, los 4 brazos cañón reales y nada más.
- En PowerUp+, un roster de 2008 importado de nuevo muestra cada casilla con su habilidad real (Rios: Cannon Arm; Eckstein: Barehand). La ida y vuelta sigue idéntica byte a byte. Los rosters de 2008 importados antes de este cambio hay que importarlos de nuevo.
- **Gd Eye y Night Game se editan en PowerUp+** (sección General, marcadas "(2008)"). Una importación de 2008 los lee del registro original.
  - La exportación de 2008 los escribe en dos huecos del formato de 2007 que la conversión ya no usa (`MOD_2008`: `0x77.7` → `0x77.4` y `0x78.6`/2 → `0x78.4`/2).
  - El conversor del juego solo los toma de un mod con `roster_ids = "2008"`. Un `.dat` genérico de 2007 se convierte igual que antes.
  - La exportación de 2007 los deja vacíos, así que una partida de 2007 se escribe bit a bit como antes.
- Comprobado: Payton (Pr Night Game) cambiado en el editor a Gd Night Game y Gd Eye, guardado, exportado y convertido. En el roster del juego cambian exactamente esos bits; el runtime da lo mismo que Python.
- Al copiar un jugador (necesario para editar uno importado), PowerUp no copiaba Day Game, Rain, la fecha de nacimiento, la edad, los años en las mayores ni las estadísticas. Sin fecha, la exportación fallaba. Ahora se copian.
- La ficha se abre en el juego desde Arrange → crear equipo → Fielder Select (o Pitcher Select) → stick C. Para automatizarlo, `WIICOMPILED_PAD_SCRIPT` acepta los bits `0x10000`–`0x80000` como stick C (parche `wiicompiled-pad-script-cstick`).

**Voces renumeradas.** 2008 conserva el orden de las voces de 2007, pero inserta y quita algunas. Entre dos jugadores presentes en ambos juegos cuyos huecos miden lo mismo, las voces se corresponden una a una, salvo que un nombre conocido de 2008 lo contradiga. Así se ubican 810 de las 968 voces de PowerUp, en 206 tramos (`VOICE_RUNS`). Ocultando el 10 % de los jugadores de referencia, los 739 casos caen en su voz real. Ryan Braun y dos "Great" tienen su voz regrabada en otro sitio.

Fuentes: `docs/roster-2008.md`, `tools/roster/powerup_to_2008.py`, `tools/roster/align_2007_2008.py --voices`, `wiicompiled-mods.patch`, `wiicompiled-roster-flags.patch`, `wiicompiled-roster-voices.patch`, desensamblado de `ovl_main.rel`.

## 7. Escenas, menús y preparación de un partido

**Gestor de escenas** (puntero en `0x81033268`; objeto con vtable `0x80D4EB88`):

| Offset | Campo |
|---|---|
| `+0x400` | objeto de la escena actual (su fase en `+0x38`, un campo de control en `+0x48`) |
| `+0x404` | ID de la escena siguiente |
| `+0x408` | ID de la escena actual |
| `+0x410` | u8: transición en curso |
| `+0x413` | u8: confirmar el cambio |

**IDs de escena conocidos:**

| ID | Escena |
|---|---|
| 1, 2 | pantallas de arranque y correa (fases 5 y 6 esperan una pulsación) |
| 3 | vídeo de apertura (`+0x48 = 3` lo cierra limpiamente) |
| 4 | pantalla de título ("Press +"; sin pulsar nada arranca la demo CPU contra CPU) |
| 409 | el campo: partido en juego |
| 419 | escena previa al arranque (aparece en los registros antes de la 1) |

**Preparar un partido desde código** (como hace el benchmark: Yankees contra Colorado en Coors Field, CPU contra CPU):
1. Escribir `0x4D4C4208` ("MLB\x08") en `r13-32744`.
2. Llamar a `0x80C8BAF0`, el inicializador de partidos del juego.
3. `config = *(0x8104E1D8)`, `common = *(0x8103D118)`.
4. Equipos: `config+19 = 3` (Yankees), `config+20 = 27` (Rockies).
5. Para cada lado (0, 1): escribir el ID del equipo en `common+1752+lado·2204` y `common+1753+lado·2204`, y llamar a `0x80973828(lado, equipo)`. Cada lado ocupa 2.204 (`0x89C`) bytes.
6. `0x807A8BE8(27)` devuelve el estadio del equipo (Coors Field); se escribe en `config+31` y `common+4`.
7. `config+18 = 0`, `config+13 = 0` (Exhibition), `config+14 = 0` (ningún mando humano), `config+26 = 3`, `config+27 = 3`, `common+976 = 0` (u16), `common+978 = 0` (u8).
8. Siguiente escena = 409 y `+0x413 = 1`.

**Puntos de código ligados a menús:**
- **Home Run (Practice):** `0x8057BEEC`, tabla de saltos de 10 entradas acotada con `cmplwi r3, 9`.
- **Vista de fildeo:** `0x8092F450`, tabla de 9 entradas indexada por un byte, sin comparación previa.
- **Exhibition → LINEUP:** `0x80663264` llama por `bctrl` a `0x80664C30`.
  - En `0x80664C18` hay cinco funciones seguidas que dtk tomó por una sola. `C20`, `C28` y `C30` son getters de dos instrucciones llamados solo desde la vtable `0x80D5183C`.
  - Quedan unos 450 candidatos parecidos sin revisar.
- **Mandos por modo:** Exhibition, Home Run y otros modos piden Nunchuk o mando Clásico. Sin Nunchuk se ofrece "Power Pros via Wii Remote".

Fuentes: `wiicompiled-match-benchmark.patch` (`match_benchmark.cpp`), `docs/wiicompiled-feasibility.md`.

## 8. Gráficos (GX y VI)

- `GXInit` `0x800C25CC`, `GXCopyDisp` `0x800C61F8`.
- Variables globales de GX:
  - `FifoObj` `0x802D2AC0`
  - `gxData` `0x802D2B40` (el puntero `__GXData` está en `0x8031C398`)
  - FIFO de la GPU `0x802D3140`, de la CPU `0x802D3164`, de listas de pantalla `0x802D3188`
  - cola de `GXDrawDone` `0x8031B6F8`
- Variables globales de VI:
  - inicializado `0x8031B400`
  - formato de TV `0x8031B470`
  - callbacks post/pre retrazo `0x8031B47C` / `0x8031B480`
  - cola de `VIWaitForRetrace` `0x8031B488`
  - contador de retrazos `0x8031B4AC`
  - `HorVer` `0x802BD070` (`+0x30` = siguiente framebuffer)
- **Cómo dibuja:**
  - Todo el 3D va por listas de pantalla (display lists); la interfaz escribe directo en el FIFO.
  - Los modelos con esqueleto usan `GX_VA_PNMTXIDX` directo, con POS/NRM/CLR0/TEX0 en `GX_INDEX16` (vértices de 9 bytes).
- **Carga por fotograma:**
  - Menús: 200-450 dibujos.
  - Partido: de 208 a 1.012.
  - Vista de fildeo: 650-990.
  - Unas 35 copias EFB por fotograma en partido; unas 17 van a texturas ya leídas en el mismo fotograma.
- **Pantalla de la correa:** compone la imagen, la copia con `GXCopyTex` a `0x90000840` en 512×480 y la dibuja como textura de 512×512 sobre un quad de pantalla completa. El hardware no comprueba el tamaño, así que la copia rellena las filas de arriba.
- **TLUT:** el juego vuelve a inicializar el mismo objeto TLUT en cada dibujo, sin destruirlo.
- **Saltos con máscara:** el juego usa tablas de saltos acotadas con `rlwinm` en vez de `cmplwi` (p. ej. `0x80031218`).

Fuentes: `config/wiicompiled/rl8e54-data.csv`, `docs/wiicompiled-feasibility.md`, `wiicompiled-aurora-partial-efb-copy.patch`, `wiicompiled-tlut-reinit-cache.patch`.

## 9. Mandos

- **Mando de GameCube:**
  - `PADRead` `0x800B76BC`; las llamadas del juego a `PADInit`/`PADRead` están en `0x80040B14` / `0x80040BC8`.
  - El juego divide el stick principal entre **88** y el C-stick entre **64**. Las guías reales llegan a ~87 y ~74, así que un ±127 completo se satura al ~69 % del recorrido.
- **Objetos de entrada:** son clases C++ con vtable. Con `base` = búfer de `PADRead` − 1648: mando GC en `base+1104`, KPAD en `base+560`, entrada combinada en `base+16`. Cada uno guarda un anillo de muestras.
- **Entero a coma flotante:** `0x80040268` convierte con el truco de CodeWarrior. Usa la constante `0x4330000080000000` de `r2-31664` (`0x8031BD90`); si esa constante se corrompe, todas las conversiones con signo fallan.
- **KPAD/WPAD:** enlazados igual que en Mario Kart Wii.
  - `KPADRead` `0x80104C4C`, `KPADInitEx` `0x80105378`
  - callback de muestreo `0x801056A4`
  - `WPADiInitSub` `0x80108ABC`, `WPADInit` `0x80108CCC`
- **Bits:** Wii Remote A = `0x800`; Nunchuk C = `0x4000`, Z = `0x2000`; GC A = `0x100`, A+Start = `0x1100`.

Fuentes: `wiicompiled-mlb-pad-stick-range.patch`, `config/wiicompiled/rl8e54-data.csv`, `docs/wiicompiled-feasibility.md`.

## 10. Partidas guardadas, NAND, SYSCONF y ES

- **Título:** `00010000/524c3845` (título de disco). La partida es `title/00010000/524c3845/data/pm3usma.dat`.
- MLB Life, Season y League escriben partida.
- **NAND:** el juego usa las bibliotecas NAND/ISFS del SDK sobre IOS.
  - `NANDInit` `0x800D0640`, `libState` `0x8031B778`.
  - El directorio propio (`0x802D3AE0`) lo pide a `ESP_GetDataDir` (`0x80064044`).
- **Peticiones a ES (`/dev/es`):**
  - ioctlv 22 `ES_GetConsumption`: un título de disco no tiene entradas.
  - ioctlv 29 `ES_GetTitleDir`: `"/title/%08x/%08x/data"`.
  - ioctlv 27 `ES_DIGetTicketView`: `0xD8` bytes. `+0x0C` ID de consola, `+0x10`/`+0x14` ID de título, `+0x18` máscara de acceso `0xFFFF`.
- **SYSCONF:** sección 2.

Fuentes: `wiicompiled-mlb-nand-es.patch`, `hle/mlb/sc_check_status.cpp`, `docs/mods.md`.

## 11. Bibliotecas y funciones identificadas

**Fechas de compilación de los módulos del SDK** (etiquetas en el binario):

| Módulos | Fecha |
|---|---|
| THP, EXI, SI, DVD, VI, AI, AX, DSP, SC, ENC, KPAD | 8 ago 2007 |
| RFL | 5 sep 2007 |
| PAD | 3 oct 2007 |
| GX, NAND | 11 dic 2007 |
| OS | 30 ene 2008 |
| HBM (menú HOME) | 7 feb 2008 |

- **Compilador:** Metrowerks CodeWarrior (hay identificadores de su runtime y de MetroTRK); la versión exacta no está identificada.
- **Bibliotecas presentes:**
  - JSystem de Nintendo: J3D, J2D, JAudio2/JAS, JStudio, JMessage, JGadget
  - menú HOME (`homebutton::*` desde `0x80064248`, `nw4hbm`)
  - pila Bluetooth de Broadcom
  - MetroTRK
  - SDK RVL
- **Ausentes:** no hay NHTTP, DWC/GameSpy ni sockets (no se encontraron sus cadenas), ni reverb AXFX.
- **Cómo se nombraron las 1.794 funciones** (`config/wiicompiled/rl8e54-functions.map`, formato `<dirección> <nombre>`):
  1. Firmas de la base de Dolphin (`totaldb.dsy`), aceptando solo coincidencias únicas: 1.375 funciones, entre ellas `gx.a` 108, `os.a` 105 y `dvd.a` 63.
  2. Alineación del orden de enlace con el mapa de Mario Kart Wii entre anclas comunes: 118 más (≈97 % de precisión en pruebas de ocultación).
  3. Nombres de dtk.
- **Equivalencias con Mario Kart Wii** (útiles para portar código o ganchos de MKW): `InsertAlarm` `0x8009B448`, `OSSaveContext` `0x8009CCD8`, `__OSThreadInit` `0x800A3C0C`, `__OSTimeToSystemTime` `0x800A53A4`, `OSLoadContext` `0x8009CD58`. `config/wiicompiled/rl8e54-data.csv` traduce 65 direcciones de datos de MKW a MLB, cada una con la instrucción que lo demuestra.
- **Sin dirección todavía:** `VIInit`/`VIConfigure`, `PADInit`, `OSInitAudioSystem`, `__OSInterruptInit`, `OSGetCurrentThread` y algunas más. Algunas pueden no existir porque el enlazador las eliminó.

## 12. Peculiaridades del juego que importan al portarlo

| Peculiaridad | Consecuencia |
|---|---|
| El sonido mide el tiempo en vueltas de 5 ms | Si el temporizador se retrasa, el comentarista se corta y suenan chasquidos (sección 4) |
| El hilo principal no cede durante cálculos largos ni en "NOW LOADING" | Con hilos cooperativos, los demás se quedan sin turno; hacen falta puntos de cambio |
| El montón ocupa toda la arena casi al byte | El tope de la arena tiene que ser `0x817FFD40`, y el BSS del REL tiene que quedar en `0x8102B0C0` |
| El juego borra el código de juego de la memoria baja | No sirve para saber qué juego corre después del arranque |
| Copia 512×480 sobre una textura de 512×512 | Una copia parcial es válida; el emulador no debe rechazarla |
| Tablas de saltos sin comparación previa | Un traductor estático debe reconocer el índice acotado con `rlwinm` |
| Getters dentro de otras funciones, llamados por vtable (`0x80664C20`-`0x80664C38`) | Hay que añadirlos al mapa de funciones o el salto indirecto falla |
| Stick de GC dividido entre 88/64 | Un mando moderno necesita escalar el recorrido |
| `OSInit` espera al SYSCONF y `RFLWaitAsync` gira en bucle | Los callbacks de IOS deben llegar mientras el juego espera |

## 13. Cómo seguir investigando

- **Mapa de funciones:** `config/wiicompiled/rl8e54-functions.map`. Añadir un nombre al mapa lo lleva al código traducido la próxima vez que se traduce.
- **Datos del SDK de MKW a MLB:** `config/wiicompiled/rl8e54-data.csv`, con la prueba de cada fila.
- **Herramientas** (`docs/reverse-engineering-tools.md`):
  - `tools/identify_sdk_functions.py`
  - `tools/align_sdk_by_anchors.py`
  - `tools/function_data_refs.py`
  - `tools/projectbin.py` (lee y reconstruye `project.bin`)
  - `tools/roster/` (convierte rosters)
- **Puntos de vigilancia en el juego recompilado:** `WIICOMPILED_DEBUG_WATCH=<dirección>` informa de cada escritura en esa dirección, con la pila de llamadas. Así se encontró el reloj de las frases.
- **Diagnóstico de audio:** `WIICOMPILED_AUDIO_DUMP=<archivo>` guarda la mezcla final para medir chasquidos.
- **Pendiente de investigar:**
  - formato interno de los `.pack` (`SURF`, `SURG`…)
  - estructura de los equipos y las alineaciones más allá de lo mapeado
  - lógica de MLB Life
  - los ~450 candidatos de getters en mitad de funciones
  - nombres de las funciones del REL (43.088 sin nombre)

Al añadir algo a este documento, indica de dónde sale (desensamblado, ejecución u observación) y la versión `RL8E54`.
