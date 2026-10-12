# MLB Power Pros 2008 Recomp

Actualización del 10 de octubre, **31 parches**: el DOL traducido con el **backend LLVM** de DolRecomp (LLVM 20.1.8, `--native-abi off`, parche `dolrecomp-llvm-gekko-single`), enlazado con los mismos 478 objetos REL MSVC, registró **+15,83% y +17,16% de avance** en dos parejas del primer out (32,7 → 38,1 fotogramas/s; ~65% de velocidad normal). La auditoría lockstep, con la nueva alineación por ciclos, encontró y permitió corregir un error real (conversiones `stfs`/`lfs`/`psq_st` no exactas). Ahora deja **1 informe en ~3.060 comparaciones**: un búfer de MEM2 escrito por el HLE de audio (463 de 463 bytes intactos en la repetición). La DLL LLVM sigue siendo **opcional y no validada del todo**. Detalles en `docs/llvm-dol-report.md`.

Actualización del 9 de octubre, **29 parches**: nueva opción experimental `-DualCore` (hilo GPU separado; el Dolphin fijado usa single core por defecto). Dos parejas con el mismo ejecutable registraron **+3,51% y +8,85%** de avance en el primer out; queda desactivada por defecto porque no es determinista. Con backend `Null` el avance fue 38,01 fotogramas/s: el trabajo gráfico explica a lo sumo ~15% y el límite sigue siendo la CPU. Detalles en `docs/dual-core-report.md`.

Actualización del 9 de octubre, **28 parches reproducibles**: la búsqueda de secciones REL ya no asigna memoria del heap en cada invalidación de caché sobre direcciones de datos. El muestreo situaba cerca del 5,8% del hilo CPU-GPU en `RtlAllocateHeap`/`RtlFreeHeap`. Dos parejas con orden invertido registraron **+10,63% y +10,78% de avance** en el primer out, con la misma DLL. Pasaron las pruebas del detector REL, la reproducción de los parches, el cierre y la coincidencia de código/reubicaciones REL en las cuatro sesiones. No cambia la cobertura (552 bloques). Detalles en `docs/rel-refresh-scratch-report.md`.

Actualización del 9 de octubre: se recompilaron cinco bloques REL con Clang estricto, conservando las fuentes y 473 objetos REL MSVC. Pasaron 2.424 referencias y 3.637 comparaciones con el intérprete sin diferencias (38 entradas omitidas; los cinco bloques alcanzados). Dos parejas del primer out registraron +8,30% y +4,96% de avance. La DLL queda como candidata opcional; se conservan los 27 parches, la DLL anterior y los 552 bloques de cobertura. No hay equivalencia ni rendimiento del juego completo validados. Detalles en `docs/hot-rel-clang-report.md`. Las mediciones siguientes son históricas.

Actualización del 9 de octubre: Ghidra ya está disponible en la conexión activa. Se probó una búsqueda directa de bloques DOL con 3.080 comparaciones de fuentes sin diferencias; las mediciones dieron +1,42% y −3,96%, así que el candidato se retiró y se restauró la versión anterior de 27 parches. Se conservan guards nuevos para las mediciones, sus evidencias y el experimento. Detalles en `docs/inline-dol-lookup-report.md`. Las mediciones siguientes son históricas.

Actualización del 9 de octubre, **27 parches reproducibles**: la opción experimental `-SkipEmptyModHooks` evita consultar el gestor cuando no hay mods cargados; conserva los callbacks si existe cualquier mod. Dos parejas con orden invertido registraron **+7,74% y +11,09% de avance** y medianas de **51,33% y 52,55% de velocidad normal** en la escena del primer out. Pasaron 14 comprobaciones, compilación, reproducción, cierre y REL; la auditoría separada completó **3.505 comparaciones sin diferencias** y omitió 39 entradas. La opción permanece desactivada por defecto, la cobertura sigue en 552 bloques y se mantiene intérprete/JIT. Detalles en `docs/empty-mod-hooks-report.md`. Las mediciones que siguen son históricas.

Proyecto local en `D:\MLBPowerPros2008Recomp` para estudiar un port de Wii a PC por recompilación estática.

Herramientas de análisis preparadas: Ghidra 12.1.4 y Java 21 dentro del proyecto, REA comprobado mediante una conexión MCP nueva y una función original PowerPC analizada directamente. Tras el reinicio, la conexión activa de Codex reconoce Ghidra como disponible. Procedimiento, evidencia y límites en `docs/reverse-engineering-tools.md`.

Actualización del 9 de octubre: quedaron resueltas las tres diferencias pendientes al corregir la alineación de la referencia en retornos dentro de bucles. Dos auditorías registraron **3.453 y 3.336 comparaciones completas sin diferencias**, dentro de la ventana comprobada; las entradas omitidas no se cuentan como validadas. Pasaron 22 casos del clasificador real y la reproducción de **26 parches**. Véase `docs/lockstep-alignment-report.md`.

La variante Clang del DOL conserva los 478 objetos REL de MSVC. La nueva pareja del menú principal registró **+66,44% de avance**, pasando de **34,96% a 56,44% de velocidad normal**. Ambas sesiones cerraron correctamente, conservaron código/reubicaciones REL y sus capturas se revisaron. Las dos parejas anteriores del primer out registraron +54,94% y +62,10%, alrededor de 45,3% de velocidad normal. Son mediciones por escena; no se suman porcentajes ni demuestran rendimiento del juego completo. La cobertura permanece en 552 bloques y la ejecución mantiene intérprete/JIT. Clang es experimental y requiere `-ClangModule`; véase `docs/compiler-experiment-report.md`.

Prioridad acordada con el usuario el 8 de octubre de 2026: avanzar código y rendimiento mediante pruebas cortas desde estados guardados. No dedicar cada avance a jugar manualmente los innings. El partido completo queda como comprobación de integración posterior. El acuerdo persistente está en `AGENTS.md`.

Nuevo diagnóstico opcional: distingue las instrucciones atendidas por la ruta rápida de caché de las que necesitan sincronizarse con el intérprete y registra sus direcciones por muestreo. En una prueba corta, el 99,65% de los callbacks usó la ruta rápida; esto mide llamadas, no tiempo de CPU ni porcentaje del port. Resultados y siguientes candidatos en `docs/performance-profile-report.md`.

Nueva opción experimental `-SchedulerIdleSkip`: acelera la espera de la cola vacía del planificador con comprobaciones de código y estado. Una comparación desde la misma pantalla registró un 10,8% más de avance de fotogramas, con la misma DLL y ejecutable. Sigue desactivada por defecto y requiere más validación. Resultados, límites y reproducción en `docs/scheduler-idle-report.md`; no se suman sus porcentajes a los de la comparación anterior de DLL.

Ampliación del 9 de octubre: pasó un arranque fresco hasta la introducción y un lote automático del menú principal, que registró +14,8% de avance en esa pantalla. `tools/benchmark-scheduler.ps1 -Seconds 90 -Python 'ruta\a\python.exe' -LoadState 'ruta\al\estado.sav'` ejecuta ambas variantes y comprueba cierre, REL y condiciones. Las capturas necesitan revisión visual; estos resultados no son porcentajes de finalización ni FPS renderizados.

El runtime con posiciones REL fijas ahora evita recorrer las secciones para convertir direcciones que ya coinciden. Pasaron las pruebas del detector y conversión para posiciones fijas y dinámicas, la reproducción de los 18 parches y las comprobaciones de cierre/REL en dos sesiones cortas. La diferencia de velocidad fue +1,4%; una sola comparación no permite considerarla una mejora concluyente. Detalles en `docs/fixed-rel-translation-report.md`.

Nuevo cambio: guardar los límites del REL permite descartar búsquedas fuera del módulo. Pasaron las pruebas de resolución, descarga, recarga y cambios de posición, la compilación y los **19 parches reproducibles**. Una comparación corta registró **+8,3% de avance de fotogramas** en la escena del primer out; la mediana fue 30,14% de velocidad normal. Ambas sesiones cerraron correctamente y conservaron la coincidencia de código/reubicaciones REL. El resultado se limita a esa comparación; véase `docs/rel-bounds-report.md`. No aumenta los 552 bloques enlazados ni completa el port.

Cambio anterior: se reutiliza el índice del bloque en la configuración de posiciones fijas, conservando los guards de verificación, fallback y módulo REL activo. Pasaron las pruebas fija/dinámica, la compilación, la reproducción de **20 parches** y los dos sondeos con cierre/REL correctos. La comparación corta registró **+5,4% de avance de fotogramas**, con mediana de 30,39% de velocidad normal. Este resultado se limita a esa pareja de sesiones; no se suman porcentajes. Véase `docs/chunk-lookup-report.md`.

Medición anterior, 21 parches: `-ProfileDispatchTiming` mide por muestreo la resolución de entrada, ejecución del módulo y conversión de regreso. La serie alcanza **21 parches reproducibles**. Dos sondeos validaron medición activada/desactivada, cierre, código/reubicaciones REL y pantallas restauradas. La ejecución del módulo, incluyendo callbacks, concentró el 80,14% del tiempo crudo de esas tres etapas; es un subconjunto del trabajo y no representa todo el tiempo de CPU. La medición queda desactivada por defecto y se rechaza en comparaciones de velocidad. Esta tanda aporta diagnóstico, sin atribuirle una ganancia. Véase `docs/dispatch-timing-report.md`.

Medición anterior, 22 parches: la medición por dirección de entrada permitió localizar 3.096 sitios del módulo sin perder muestras. Pasaron la compilación, reproducción de **22 parches**, pruebas de límites/contadores y dos sondeos con medición activada y desactivada, cierre correcto y coincidencia REL. La lista señala rutas de cálculo y un bucle de caché para investigar; las direcciones representan intervalos del módulo con callbacks, no costes exclusivos de funciones. Esta tanda aporta diagnóstico, sin una nueva ganancia de velocidad ni cambio de cobertura. Véase `docs/dispatch-sites-report.md`.

Último cambio: `-CacheBatch` agrupa las iteraciones intermedias de un bucle de caché dentro del callback nativo, manteniendo cada invalidación, ciclos y retorno del código generado. Pasaron **8.130 casos diferenciales**, compilación, reproducción de **23 parches** y dos sondeos con cierre/REL correctos y capturas revisadas. La comparación OFF/ON registró **+5.7% de avance** en esa pantalla, con mediana de 27.72% de velocidad normal. La opción sigue experimental y desactivada por defecto, limitada a la DLL comprobada. No cambia la cobertura y el resultado no se suma a mejoras anteriores. Véase `docs/cache-batch-report.md`.

Estado: módulo experimental DOL/REL para Windows x64, con 552 bloques y 9.021.384 bytes de código enlazados. Pasan 2.352 referencias de memoria DOL y 72 casos de seis funciones REL sin fallback en esos casos. La ejecución del juego sigue usando intérprete/JIT de apoyo. Exhibition llegó al primer inning de Boston contra Colorado en Fenway Park; A completó dos lanzamientos de calentamiento y registró un strike frente al bateador CPU. El partido completo, bateo, defensa, audio y rendimiento siguen pendientes. El 100% enlazado no significa port terminado. Resultados y límites en `docs/runtime-integration-report.md` y `docs/cpu-translation-report.md`.

Actualización de Exhibition: se comprobaron 1 Player, Controller Setup, equipos, local/visitante, uniformes, estadio, opciones y Play Ball con entrada aislada. Boston contra Colorado cargó en Fenway Park hasta el calentamiento del primer inning. Se guardaron estados privados para reanudar. La sesión de 900 segundos cerró con salida 0 y capturas completas. El partido completo sigue pendiente.

Avance posterior del partido: se observaron contacto de la CPU, pelota en el campo, corredor en primera, carreras y el segundo out. El último estado jugable guardado muestra Colorado 5–Boston 0 y dos outs en la parte alta del primer inning. Se consultó la ayuda original del controlador A Type para ataque y defensa. Las tres sesiones nuevas cerraron sin terminación forzada ni órdenes fallidas. La defensa manual, el bateo del jugador y un inning completo siguen pendientes.

La nueva DLL optimizada conserva el cálculo estricto y pasa las referencias de CPU disponibles. Una comparación de una misma pantalla, sin controles, registró un 71% más de avance de fotogramas del juego frente a la DLL inicial. El runtime informó alrededor del 25% de velocidad normal: todavía falta rendimiento jugable. La medición no representa FPS renderizados ni todo el partido.

El documento aportado por el usuario se usa como referencia de alcance. La ubicación en el disco D es una instrucción directa del usuario. La imagen original permanece en `D:\Dolphin-x64\MLB Power Pros 2008 (USA).nkit.iso`.

## Reproducir el análisis en Windows

Desde PowerShell:

```powershell
Set-Location D:\MLBPowerPros2008Recomp
.\tools\bootstrap.ps1
.\tools\phase0.ps1 -Image 'D:\Dolphin-x64\MLB Power Pros 2008 (USA).nkit.iso' -DolphinTool 'D:\Dolphin-x64\DolphinTool.exe'
```

Se necesita Python 3.10 o superior en PATH, o pasar `-Python` con la ruta de su ejecutable. `-Convert` expande el NKit con NKit 3.1.0, conserva el resultado en `local/images/` y verifica el ISO con dtk. La extracción y el inventario pueden hacerse sin convertir.

Un código de salida cero de NKit o dtk no demuestra una coincidencia con Redump: consultar los registros de verificación. El ISO expandido actual no coincide con Redump; NKit señaló que falta una partición de actualización y rellenó su espacio con ceros. La extracción directa permite avanzar con el análisis, sin dar por verificada la integridad completa del disco.

Los informes están en `docs/`. Los binarios, assets, herramientas descargadas, registros con strings y resultados generados se guardan exclusivamente en `local/`, excluido de Git. No se distribuye contenido del juego.

## Estructura

- `tools/`: preparación y análisis reproducible.
- `config/`: identidad del proyecto y versiones fijadas de herramientas.
- `docs/`: resultados y pendientes comprobables.
- `recompiler/`: compilación de las traducciones C como bibliotecas de comprobación.
- `runtime/checks/`: pruebas de ejecución nativa de rutinas del DOL, aún sin runtime de juego.
- `runtime/module/`: módulo compatible con ModernGekko, pruebas de su interfaz y diagnóstico de inicio.
- `patches/`, `mods-api/`, `netplay/`: componentes futuros, aún sin implementación.
- `local/`: datos privados de trabajo y herramientas descargadas.

ModernGekko se está probando como puente de diagnóstico. La elección final sigue pendiente del arranque, de la integración del REL y de medir cuánto código necesita fallback.

## Traducir y comprobar CPU

Con Visual Studio 2022 C/C++, CMake, CTest, Git y Python:

```powershell
.\tools\recompile.ps1
```

`-SkipDtkAnalysis -ReuseGenerated` permite volver a comprobar los resultados existentes sin repetir el análisis ni generar otra vez el C. Los archivos generados nunca se editan a mano. Unicorn se usa únicamente para crear la referencia de pruebas; las rutinas nativas se ejecutan sin intérprete.

La integración adopta GPLv3. Ver `LICENSE` y `THIRD_PARTY.md`.

## Preparar la primera integración de runtime

```powershell
.\tools\runtime.ps1
```

Las revisiones están fijadas en `config/runtime.lock.json`. Las dependencias, el perfil privado del runtime y todos los módulos del juego se mantienen en `local/`.

## Probar el módulo experimental DOL y REL

Con la captura privada enlazada ya obtenida en este equipo:

```powershell
.\tools\runtime-rel.ps1 -Python 'ruta\a\python.exe'
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -Screenshot -SnapshotMemory -RelModule
```

Para continuar una prueba desde un estado privado del mismo runtime, añadir `-LoadState 'ruta\al\estado.sav'`. El resultado registra su ruta y SHA256; hay que comprobar visualmente la pantalla restaurada. Una sesión reanudada no valida el arranque desde cero. Crear un archivo vacío `finish-requested` en el directorio del sondeo activo solicita su cierre con las capturas finales y el procedimiento normal de apagado.

`-ReuseGenerated` reutiliza la traducción y referencia preparadas. La DLL combinada está en `local/build/runtime-module-rel/Release/`; la DLL inicial, con solo el DOL, se conserva en `local/build/runtime-module/Release/`. `probe-boot.ps1` usa la inicial si no recibe `-RelModule`. La combinación actual exige las seis direcciones de sección comprobadas; no fuerza al juego a cargar el REL en ellas. `tools/check_probe_shutdown.py` verifica salida, contadores y cierre; `--require-inflight-wc24` exige además una transferencia activa al apagar.

Para preparar y seleccionar la compilación optimizada por separado:

```powershell
.\tools\runtime-rel.ps1 -Python 'ruta\a\python.exe' -ReuseGenerated -Optimize -ModuleOnly -Jobs 2
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -Screenshot -LoadState 'ruta\al\estado.sav'
```

`-Optimize` usa `/O2` y conserva `/fp:strict`; `-ModuleOnly` comprueba el módulo, revisiones y parches sin recompilar el ejecutable base. La DLL se guarda en `local/build/runtime-module-rel-optimized/Release/`. El sondeo registra qué módulo y SHA256 usó. Para comparar dos sesiones sin controles desde un mismo estado y con igual duración, backend y perfil, ejecutar `python tools/compare_probe_speed.py <sondeo-inicial> <sondeo-optimizado>`. Sus muestras necesitan al menos 30 segundos de avance en ejecución; usar capturas periódicas para reunirlas.

Para investigar callbacks de instrucciones, añadir `-ProfileFallback` a una prueba corta con el runtime actualizado. El sondeo registra también el SHA256 del ejecutable, guarda `fallback-profile.csv` y activa las muestras de despachos nativos. `python tools/analyze_fallback_profile.py <sondeo>` valida los totales frente al contador final, comprueba el muestreo y genera un informe privado con comentarios del código generado. Con snapshots completos verifica además las instrucciones muestreadas contra MEM1. El diagnóstico está desactivado por defecto; sus frecuencias incluyen inicio, restauración y apagado, y no sustituyen una medición de tiempo de CPU.

Para observar menús, el sondeo permite hasta 900 segundos y capturas periódicas con `-CaptureIntervalSeconds 30`. Usa el perfil privado `local/runtime-probe-user/`, sin asignaciones físicas de teclado o ratón. `prepare-probe-input.ps1` conserva ajustes desconocidos y acepta la normalización del INI que hace el runtime. Las órdenes se publican completas con `send-probe-command.ps1`; escribir directamente en la cola puede hacer que se lean parcialmente.

El envío rechaza sondeos que ya tienen `result.json`. Publicar antes del plazo no garantiza que alcance a ejecutarse: comprobar `processed/`, `failed/`, órdenes pendientes y capturas. En la ayuda del controlador, el pulso de − de 60 fotogramas produjo el cambio de página que no se observó con pulsos más cortos.

```powershell
.\tools\probe-boot.ps1 -Seconds 900 -Graphics Vulkan -RelModule -CaptureIntervalSeconds 30 -Screenshot -SnapshotMemory
# En otra consola, sustituir <identificador> por el directorio del sondeo activo:
.\tools\send-probe-command.ps1 -ProbeRoot '.\local\analysis\boot-probe-<identificador>' -Name '0050-plus.ini' -Content "command=pad_frames`nport=0`nframes=30`nwii_plus=1"
```
