# DOL traducido con el backend LLVM de DolRecomp

Fecha: 10 de octubre de 2026. Experimento opcional; la DLL Clang/C sigue siendo la referencia. Serie de runtime: **31 parches**.

## Motivo

`docs/ppc-line-profile-report.md` mostró que el C generado mantiene `ctx->gpr[]`, `cr` y `downcount` en memoria en cada instrucción. Cada bloque empieza con un `switch` que tiene un `case` por instrucción, así que LLVM no puede promover ese estado a registros. El backend LLVM de DolRecomp (anidado en ModernGekko, `71ce7f9`) sí promueve el estado a SSA.

## Construcción

- LLVM 20.1.8 oficial para Windows, verificado contra el SHA256 publicado y fijado en `config/tools.lock.json`. `tools/build-dolrecomp-llvm.cmd` compila el generador con `DOLRECOMP_ENABLE_LLVM=ON`; el paquete trae la ruta de `diaguids.lib` de su máquina de compilación y el script la corrige. Pasan las 32 pruebas de DolRecomp.
- Generación: `dolrecomp --cpu broadway --backend llvm --runtime recompcore --native-abi off --targets x86-64-v2`. Produce 6.594 objetos COFF, uno por región de función, en lugar de 74 bloques C. Los fallbacks registrados son los 1.648 datos incrustados y ninguna instrucción. El informe SMC es igual al del backend C.
- `tools/build-llvm-dol-module.cmd [generado] [build]` enlaza esos objetos con los **mismos 478 objetos REL MSVC**; el guard `--check-rel-objects` pasa. Solo cambia el DOL.
- `runtime/module/llvm_module_export.c` incluye `module_export.c` sin modificarlo. Añade una caché por dirección delante de `dolrecomp_find_original`, que en el header LLVM es una cadena lineal de `if` sobre 6.594 regiones. Sin la caché, la primera sesión avanzó solo 5,26 fotogramas/s, con 2,5 µs por despacho. Mantiene el orden de `dolrecomp_call`: reemplazo, `host_call`, original y alias físico.
- `runtime/module/llvm_support.c` aporta `ppc_native_region_available`, ausente en GXRuntime, con la misma semántica que DolRecomp. También instala un diagnóstico de `SIGABRT` que imprime la pila.
- `tools/module_build_manifest.py` registra `main.h`, los objetos LLVM, los fallbacks y SMC, con el modo `llvm_dol_msvc_rel`. `check_rel.c` toma el número de bloques esperado del build (7.072).

Pruebas del módulo: las 2.352 referencias DOL y los 72 casos REL pasan sin fallback.

## Fallo con la ABI nativa por defecto

Con `--native-abi unrestricted`, el valor por defecto, el proceso abortaba al apagar en 4 de 4 sesiones (`0xC0000409`). El handler de `SIGABRT` y el desensamblado del ejecutable lo localizaron:

- `CPUManager::Run` mantiene el `std::thread timing` en **XMM7**, registro no volátil en Win64, a lo largo del bucle de CPU.
- Al llegar al `join`, el handle estaba corrupto y `_Thrd_join` falló con `_NO_SUCH_PROCESS`.
- Con un `fprintf` que obliga a guardar el objeto en memoria, el fallo desaparece.

Un escaneo de las 6.594 funciones LLVM no encontró escrituras a XMM6–15 sin guardar en el prólogo. Además, los objetos LLVM no traen `.pdata`/`.xdata`. Con `--native-abi off`, el mismo ejecutable cerró correctamente en 2 de 2 sesiones y en todas las posteriores, a la misma velocidad. **Se usa `--native-abi off`.** La causa exacta dentro de la ABI nativa queda sin aislar: puede ser un desajuste de argumentos en pila entre bloques. Conviene reportarla aguas arriba.

## Velocidad

Dos parejas de 120 s desde el estado del primer out, con orden invertido. Mismo ejecutable (`903545f0…`), Vulkan, scheduler acelerado y omisión de hooks con cero mods. Comparador: `tools/compare_llvm_dol_speed.py`, que exige mismas condiciones, modos de manifiesto `clang_dol_msvc_rel` → `llvm_dol_msvc_rel` y objetos REL idénticos.

| Pareja | DLL | Sondeo | Fotogramas / s real | Mediana de velocidad normal |
|---|---|---|---:|---:|
| 1 | Clang/C | `boot-probe-20261010-010418-566` | 32,41 | 55,29% |
| 1 | LLVM | `boot-probe-20261010-010637-736` | 37,86 | 65,52% |
| 2 | LLVM | `boot-probe-20261010-010857-241` | 37,84 | 64,58% |
| 2 | Clang/C | `boot-probe-20261010-011116-025` | 32,50 | 54,41% |

Cocientes: **+16,81% y +16,42%** (`local/analysis/llvm-dol-speed-comparison-20261010-011345-*.json`). Las cuatro sesiones cerraron con salida 0, sin órdenes fallidas ni fallos de verificación de código, con MEM1/MEM2 completas. En las sesiones LLVM coinciden los 200.212 campos de reubicación y el código REL. Las capturas (primer inning, 0–0, un out) no muestran defectos. Como referencia, con backend `Null` la DLL Clang llegaba a 38,0: con LLVM y Vulkan ya se roza esa cota, y el trabajo gráfico pasa a pesar proporcionalmente más.

## Auditoría lockstep

Variante instrumentada: `--instrumentation lockstep`, en `local/build/runtime-module-rel-llvm-noabi-lockstep/`. Ventana de 5 a 6 millones de despachos desde el estado del primer out.

**Primera auditoría** (`boot-probe-20261010-010148-447`): 11 divergencias en 3.092 comparaciones. Se clasificaron así:

1. **Alineación (9 casos).** El verificador comparaba en la primera llegada del intérprete al PC final, salvo en cabeceras de bucle. Las regiones LLVM encadenan llamadas y vuelven a pasar por el mismo PC. Por ejemplo, `OSRestoreInterrupts` (`0x800A0988`) se alcanzaba antes por otra llamada, con otro `lr` y otra pila. `recompcore-lockstep-align-cycles.patch` añade `STATICRECOMP_LOCKSTEP_ALIGNCYCLES` (`probe-boot.ps1 -LockstepAlignCycles`): en cualquier PC final exige también `interp_cycles >= native_charge`. Si no se alinea, el límite de pasos lo cuenta como fallo, así que no oculta diferencias. Resultado: 2 informes en 3.158 comparaciones.
2. **Error real del backend LLVM, corregido.** `stfs`/`lfs` usaban `fptrunc`/`fpext` del host, que redondean y aplanan subnormales con FTZ/DAZ de MXCSR, configurado según FPSCR[NI]. Gekko/Dolphin usan `ConvertToSingle`/`ConvertToDouble`: truncado bit a bit, subnormales desplazados y NaN sin silenciar. Se manifestaba en `0x80018F90`/`0x80018FB0`: el nativo escribía `0x0`/`0x80000000` al FIFO GX donde el intérprete escribía `0x00000001`/`0x803281D8`. `psq_st` de float redondeaba en lugar de aplicar `ConvertToSingleFTZ`. Corrección en `tools/patches/dolrecomp-llvm-gekko-single.patch`, aplicada por `build-dolrecomp-llvm.cmd`. La referencia de la prueba `paired_single` de DolRecomp guardaba los subnormales como `+0`; se alineó con Dolphin y GXRuntime, que conservan el signo. Pasan las 32 pruebas del generador.
3. **Efecto lateral del DSP (1 caso, `0x800BA138`).** La región pertenece al audio: `DSPSendMailToDSP` (`0xCC005000`), `DSPCheckMailToDSP`, mezcla y `DCInvalidateRange`. `recompcore-lockstep-mem2-pre.patch` añade a cada byte de MEM2 su valor previo (`P=`) y el contador `mem2_shadow_untouched`. En `boot-probe-20261010-020450-521`, los **463 bytes divergentes tienen `I == P`**: la repetición del intérprete no escribió ninguno. El búfer lo sobrescribe el HLE de audio al recibir el correo, y la repetición solo captura las escrituras MMIO, sin ejecutarlas. Con `DSPThread = False` persiste igual, lo que cuadra con un HLE síncrono.
4. **Sin clasificar (`0x8009D1D8`, `OSLoadContext`).** Tres bytes de MEM1 con +1. Apareció dos veces antes de la corrección del generador y ninguna en las tres auditorías posteriores. Queda pendiente.

**Auditoría con el generador corregido** (`boot-probe-20261010-015558-870` y `-020450-521`): **1 informe en 3.060 y 3.064 comparaciones**, el caso DSP del punto 3. Sin límites alcanzados, cargas insuficientes ni filtros. El checker `check_lockstep_probe.py` sigue rechazando la sesión porque exige cero informes; no se ha añadido ninguna excepción.

Control: la DLL C con `-LockstepAlignCycles` (`boot-probe-20261010-021644-937`) dio 1 informe y 4 límites alcanzados, en salidas por excepción (`end=0x00000800`), donde la carga de ciclos del backend C no es exacta. Las auditorías del backend C siguen en el modo por defecto, que daba 0 informes.

**Estado: la DLL LLVM queda opcional.** Para sustituir a la DLL Clang faltan: tratar los efectos de hardware en la repetición (ejecutar el HLE o excluir de forma explícita los bytes escritos por el hardware), cerrar el caso `0x8009D1D8` y repetir auditorías en otras escenas.

### Cobertura en otras escenas (32 parches)

`recompcore-lockstep-align-range.patch` limita `ALIGNCYCLES` a un rango de entradas. `probe-boot.ps1 -LockstepAlignCycles` usa por defecto el DOL (`0x80000000:0x80575580`, configurable con `-LockstepAlignRange`), y el REL, que es C, mantiene la regla por defecto. Con la DLL Clang, la escena de pelota en juego daba 0 informes en modo por defecto y 8 con alineación total. Con el rango, solo queda una salida por excepción (`0x800597C8` → `0x800`), conocida en el C.

| Estado | Comparaciones | Informes LLVM | Clasificación |
|---|---:|---:|---|
| Primer out, ventanas 10M/20M/30M | 3.059–3.165 | 1 cada una | DSP (`I == P` en 463/393/311 bytes) |
| `menu-state` | 848 | 1 | DSP (46/46) |
| `match-intro-state` | 2.910 | 1 | DSP (250/250) |
| `help-page-state` | 1.529 | 1 | DSP (222/222) |
| `wave-one-state` (pelota en juego) | 3.705–4.213 | 8–13 | DSP + funciones REL `0x80C6xxxx`/`0x808C70xx` |

Las divergencias de `wave-one-state` están en código **REL** (C de MSVC, igual en ambas DLL), que nunca ejecuta código LLVM: las llamadas al DOL vuelven al despachador. La traza de `0x80C700A4` (un recorrido recursivo que marca bytes de visibilidad) da **el mismo estado inicial, carga 259 frente a 265 y `matched=0` con la DLL Clang** (`boot-probe-20261010-031139-554`) y con la LLVM (`-031402-166`). No es una regresión del backend LLVM. Causa: el C del REL (fork `71c3122`) carga 6 ciclos en el bucle de 12 instrucciones `0x80C701F8`, así que la alineación por ciclos detiene al intérprete varias iteraciones antes. La auditoría C anterior no había comprobado esa entrada. Esto afecta a la temporización del REL en las dos DLL, no al resultado de las operaciones. Traducir el REL con el backend LLVM, que carga por instrucción, lo resolvería.

En la escena de pelota en juego aparecieron también diferencias de FP en `0x808C703C`/`0x808C7064` (REL), pero en otra ejecución la misma entrada coincidió (`boot-probe-20261010-030742-727`). Se consideran del mismo tipo, por alineación, hasta trazarlas.

### Velocidad con el generador corregido

| Pareja | DLL | Sondeo | Fotogramas / s real | Mediana de velocidad normal |
|---|---|---|---:|---:|
| 1 | Clang/C | `boot-probe-20261010-020701-497` | 32,78 | 55,10% |
| 1 | LLVM | `boot-probe-20261010-020921-649` | 37,97 | 65,61% |
| 2 | LLVM | `boot-probe-20261010-021140-192` | 38,28 | 65,02% |
| 2 | Clang/C | `boot-probe-20261010-021358-472` | 32,67 | 54,94% |

Cocientes: **+15,83% y +17,16%** (`llvm-dol-speed-comparison-20261010-021626-*.json`). Las cuatro sesiones cerraron con salida 0. En las sesiones LLVM coinciden REL y reubicaciones. Las capturas no muestran defectos. Ejecutable de 31 parches.

## REL también con LLVM (módulo `llvm_all`)

El REL enlazado (49.500 regiones, 0 fallbacks) se generó con `tools/generate-llvm.cmd rel … 4` (caché en `local/cache/`, `-j4`; con `-j10` se agotó la RAM). El enlace de ~56.000 objetos necesitó `BUILD_JOBS=2`.

El backend LLVM emite un rango de código por función (26.213 en el REL). El validador de ModernGekko exige que cada sección ejecutable del REL quepa en un solo rango y rechazaba el módulo (`invalid REL module metadata`). `tools/gen_runtime_module_tables.py` ahora fusiona rangos contiguos: las tablas C salen idénticas byte a byte, el REL LLVM queda en 1 rango (igual que C) y el DOL LLVM pasa de 3.534 a 3, con la misma cobertura.

Para aislar el REL, la base es el DOL LLVM + REL MSVC reconstruido con esas mismas tablas (`local/build/runtime-module-llvm-dol-coalesced`). Comparador: `compare_llvm_dol_speed.py --baseline-mode llvm_dol_msvc_rel --candidate-mode llvm_all`, que exige los mismos objetos DOL LLVM.

| Pareja | DLL | Sondeo | Fotogramas / s real | Mediana de velocidad normal |
|---|---|---|---:|---:|
| 1 | DOL LLVM + REL MSVC | `boot-probe-20261010-091754-032` | 39,98 | 66,97% |
| 1 | todo LLVM | `boot-probe-20261010-092012-849` | 43,23 | 72,55% |
| 2 | todo LLVM | `boot-probe-20261010-092232-409` | 43,89 | 75,24% |
| 2 | DOL LLVM + REL MSVC | `boot-probe-20261010-092450-722` | 40,38 | 68,42% |

Cocientes: **+8,12% y +8,69%** (`llvm-dol-speed-comparison-20261010-092717-*.json`). Las cuatro sesiones cerraron con salida 0, sin fallback, sin fallos de verificación ni de SMC, con MEM1/MEM2 completas. Los fallbacks JIT son los mismos vectores de excepción en ambas DLL. Las capturas muestran la misma escena (primer inning, 0–0, un out); solo cambia el fotograma de la animación del bate. Ejecutable de 32 parches.

**Comparación directa con la DLL Clang/C** (`--baseline-mode clang_dol_msvc_rel --candidate-mode llvm_all`, mismo runner de 33 parches):

| Pareja | DLL | Sondeo | Fotogramas / s real | Mediana de velocidad normal |
|---|---|---|---:|---:|
| 1 | Clang/C | `boot-probe-20261010-161121-254` | 31,34 | 54,97% |
| 1 | todo LLVM | `boot-probe-20261010-161343-886` | 42,35 | 71,36% |
| 2 | todo LLVM | `boot-probe-20261010-161603-405` | 42,35 | 73,75% |
| 2 | Clang/C | `boot-probe-20261010-161821-840` | 34,18 | 59,10% |

Cocientes: **+35,1% y +23,9%** (`llvm-dol-speed-comparison-20261010-162051-*.json`). La dispersión viene de la base Clang (31,3 frente a 34,2); todo LLVM repite 42,35. El producto de los dos saltos medidos por separado (~1,16 × 1,08 ≈ 1,25) cae dentro de ese intervalo.

La base coalescida (≈40,2) parecía superar a la DLL DOL LLVM anterior (≈38,1), pero eran sesiones distintas. Medidas en parejas ABBA el mismo día, la DLL anterior (`runtime-module-rel-llvm-noabi`) dio 39,75/40,26 y la coalescida 39,25/39,95: cocientes 0,987 y 0,992 (`llvm-dol-speed-comparison-20261010-110320-*.json`). **Fusionar rangos no cambia la velocidad**; la diferencia venía de la sesión. Solo es necesario para el validador del REL.

### Lockstep con todo LLVM

Variante instrumentada: `generate-llvm.cmd rel local/generated/dolrecomp-llvm-noabi-lockstep/rel-linked 4 lockstep` y el DOL lockstep anterior, en `local/build/runtime-module-llvm-all-lockstep/`. Como ya no hay C en el módulo, la alineación por ciclos cubre DOL y REL: `-LockstepAlignCycles -LockstepAlignRange 0x80000000:0x81800000`.

| Estado | Ventana | Sondeo | Comparaciones | Informes | Clasificación |
|---|---|---|---:|---:|---|
| `wave-one-state` (pelota en juego) | 3M–4M | `boot-probe-20261010-104846-778` | 2.575 | 1 | DSP (`0x800BA138`, `I == P` en 258/258 bytes de MEM2) |
| Primer out | 5M–6M | `boot-probe-20261010-105135-326` | 2.116 | 1 | DSP (`0x800BA138`, `I == P` en 459/459) |

Con REL C, la misma escena daba 8–13 informes en funciones REL `0x80C6xxxx`/`0x808C70xx`, por la carga de 6 ciclos en bucles de 12 instrucciones. Con REL LLVM desaparecen: sin límites alcanzados, cargas insuficientes ni filtros. Queda solo el efecto lateral del HLE del DSP, sin cambios en el verificador.

### Repetición de escrituras de hardware en MEM2 (33 parches)

En nativo, una escritura MMIO llega al hardware real. En la repetición, el intérprete la captura y la suprime, para no emitirla dos veces. El correo al DSP (`DSP_MAIL_TO_DSP_LO`, `0xCC005002`) hace que el HLE de AX escriba en MEM2 de forma síncrona. Esa escritura solo existe en el lado nativo.

`recompcore-lockstep-hw-mem2.patch` resuelve esto. En cada escritura MMIO nativa dentro del alcance del verificador, copia MEM2 antes, compara después y guarda los bytes que cambió el hardware. Cuando el intérprete emite la misma escritura (mismo ordinal, registro, tamaño y dato), vuelve a aplicar ese delta. Es la misma regla que ya se usa para las lecturas MMIO, cuyo valor la repetición toma del lado nativo. Si la secuencia no coincide, no se aplica nada y la comparación MMIO lo informa como antes.

`[lockstep] hw_mem2: writes= bytes= replayed=` resume el resultado y `probe-boot.ps1` lo guarda en `lockstep_counters`. `check_lockstep_probe.py` exige `replayed == writes`.

La copia completa de MEM2 por escritura MMIO solo ocurre en modo lockstep. Las escrituras del hardware en MEM1 no se registran: MEM1 solo se compara en los desplazamientos que escribió el código nativo. Si aparece un caso así, el mismo mecanismo cubriría MEM1.

Todo LLVM, alineación DOL+REL, 120 s:

| Estado | Ventana | Sondeo | Comparaciones | Informes | Escrituras hw / bytes |
|---|---|---|---:|---:|---:|
| `wave-one-state` | 3M–4M | `boot-probe-20261010-151645-624` | 2.574 | 0 | 1 / 258 |
| Primer out | 5M–6M | `boot-probe-20261010-151904-711` | 2.124 | 0 | 1 / 463 |
| `menu-state` | 3M–4M | `boot-probe-20261010-152123-750` | 811 | 0 | 1 / 46 |
| `match-intro-state` | 3M–4M | `boot-probe-20261010-152342-992` | 2.063 | 0 | 1 / 250 |
| `help-page-state` | 3M–4M | `boot-probe-20261010-152602-013` | 1.066 | 0 | 1 / 222 |

En todas las escenas, la escritura es `0xCC005002` en la entrada `0x800BA138`. Los bytes coinciden con los casos DSP anteriores (`I == P`), y no hay límites alcanzados, cargas insuficientes, filtros ni lista blanca.

**Primera validación estricta.** Con registros de todas las fronteras (`-LockstepTracePC 4294967295`), `boot-probe-20261010-152854-204` pasa `check_lockstep_probe.py --allow-empty-mod-hooks`: 2.569 entradas únicas, 2.555 fronteras comparadas y todas exactas. El alcance es acotado: las entradas saltadas por fallback y los caminos no visitados no quedan validados.

Control con la DLL C en modo por defecto, mismo estado y ventana (`boot-probe-20261010-153111-576`): 0 escrituras hw y 12 informes. Todos están en las entradas REL `0x80C6xxxx`/`0x808C70xx` de la carga de ciclos del C descrita arriba. Esta vez la ventana las alcanzó (5.120 comparaciones frente a 4.255 en `-024920-810`). El parche no las causa, porque no registró ninguna escritura.

El caso `0x8009D1D8` (`OSLoadContext`) no apareció en ninguna de estas auditorías.

### Arranque en frío tras el arreglo de `sthbrx`/`lhbrx`

Módulo `runtime-module-llvm-fixed-lockstep`, sin estado guardado, alineación DOL+REL, 120 s (`boot-probe-20261010-205911-983`): 878 comparaciones y 1 informe. La divergencia del Bluetooth (`0x8010676C`) ya no aparece.

El informe restante, `0x8000403C` (`__start`), es un artefacto del verificador, no del código traducido:
- `__OSCacheInit` lee L2CR. El código nativo LLVM lo hace con `ppc_mfspr` → `HookSPRRead`, que devuelve `ppc.spr[SPR_L2CR] = 0`, igual que el intérprete de Dolphin. Por eso entra en la inicialización del L2 y escribe L2CR = `0x80000000` al final.
- La repetición restaura GPR, memoria y algunos SPR, pero no el arreglo `ppc.spr`. El intérprete lee el L2CR que dejó el nativo (`0x80000000`, traza `boot-probe-20261010-211012-667`, paso 169), salta la inicialización y llega más lejos en el `memset` posterior con los mismos ciclos.
- Una traza temporal en `HookSPRRead` (ya retirada) confirmó que el nativo lee 0.
- La DLL C no lo informa porque ejecuta `mfl2cr` por fallback y el verificador salta esas entradas.

`recompcore-lockstep-spr-restore.patch` (36 parches) corrige el verificador:
- copia `ppc.spr` antes del bloque nativo y la restaura para la repetición;
- compara los SPR que no se comparaban (salvo los temporizados y los que viven en `CPUState`);
- al terminar, deja los valores nativos.

| Prueba | Sondeo | Comparaciones | Informes |
|---|---|---:|---:|
| Arranque en frío | `boot-probe-20261010-213619-181` | 878 | 0 |
| `wave-one-state` 3M–4M | `boot-probe-20261010-213906-405` | 2.568 | 0 |

El arranque en frío tiene 33 límites de pasos, así que esas entradas no quedan validadas.

## Caché de objetos por IR (`dolrecomp-llvm-ir-cache.patch`)

La caché de `pipeline.c` usa como clave el hash del código del generador, así que cualquier cambio en el generador regeneraba los ~56.000 chunks, unos 50 minutos. Con `DOLRECOMP_LLVM_TIMINGS=1`, una muestra de 2.266 chunks del DOL tardó:

| Etapa | Tiempo total |
|---|---:|
| Bajada a IR | 6,2 s |
| Optimización | 249 s |
| Generación de código | 235 s |

El parche añade un segundo nivel de caché. La clave es el SHA-256 del bitcode sin optimizar, junto con:
- la versión de LLVM;
- el hash de las fuentes del pipeline (`DOLLLVM_PIPELINE_HASH`);
- los niveles de optimización y de generación de código;
- la semántica de coma flotante;
- el perfil PGO.

Tras un cambio en el generador, todos los chunks se vuelven a bajar a IR, que es barato, y solo se optimizan y compilan los que cambiaron. `generate-llvm.cmd` lo activa en `local/cache/dolrecomp-llvm-ir`. Es la misma idea de Wiicompiled: retraduce todo, pero solo recompila los fragmentos cuyo contenido cambió.

Verificación con dos pasadas de 60 s sobre el DOL, borrando la caché de trabajos entre ambas:
- La segunda pasada acertó en caché 718 de 718 chunks.
- Los objetos servidos desde la caché son idénticos byte a byte a los compilados desde cero (738 de 738).
- Los 32 tests del generador pasan.
- La pila de 4 parches se aplica sobre una copia limpia del commit fijado.

Para que la caché sea útil, primero hay que llenarla con una generación completa por variante (normal y lockstep).

La variante normal ya está llenada en `local/cache/dolrecomp-llvm-ir` (62 min, 56.094 entradas). Sus objetos son idénticos byte a byte a los de `local/generated/dolrecomp-llvm-fixed`: 6.594 de 6.594 en el DOL y 49.500 de 49.500 en el REL.

Medición de la vuelta completa tras un cambio trivial en el generador (un comentario en `emitter.cpp`, que cambia el hash del código y deja fallar la caché de trabajos entera):

| Parte | Antes | Con caché por IR |
|---|---:|---:|
| DOL (6.594 chunks) | ~5 min | 58 s |
| REL (49.500 chunks) | ~45 min | 21 min |

Ningún chunk se volvió a optimizar: no apareció ninguna entrada nueva en la caché. El tiempo restante del REL viene de las fases del generador anteriores a LLVM. El REL tiene 1,95 M instrucciones, 6,5 veces las del DOL, pero tardó unas 21 veces más, así que alguna fase crece más que linealmente. Durante la medición había además una comparación de 49.500 archivos en paralelo. Queda pendiente perfilar `dolrecomp.exe` sobre el REL.

## Reproducción

```powershell
.\tools\build-dolrecomp-llvm.cmd
.\tools\generate-llvm.cmd dol local/generated/dolrecomp-llvm-noabi/dol 4
.\tools\build-llvm-dol-module.cmd local/generated/dolrecomp-llvm-noabi/dol local/build/runtime-module-rel-llvm-noabi
.\tools\generate-llvm.cmd rel local/generated/dolrecomp-llvm-noabi/rel-linked 4
$env:BUILD_JOBS = 2; .\tools\build-llvm-dol-module.cmd local/generated/dolrecomp-llvm-noabi/dol local/build/runtime-module-llvm-all local/generated/dolrecomp-llvm-noabi/rel-linked
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -ClangModule -ModulePath local/build/runtime-module-rel-llvm-noabi/gRL8E54_recomp.dll -SchedulerIdleSkip -SkipEmptyModHooks -LoadState <estado> -SnapshotMemory -Screenshot -CaptureIntervalSeconds 10
```

La generación y la compilación deben ejecutarse dentro del entorno `vcvars64`; los scripts `.cmd` lo cargan.
