# Primera integración del runtime

Actualización del 9 de octubre: se recompilaron cinco bloques REL con Clang estricto, conservando las fuentes y 473 objetos REL MSVC. Pasaron 2.424 referencias y 3.637 comparaciones con el intérprete sin diferencias (38 entradas omitidas; los cinco bloques alcanzados). Dos parejas del primer out registraron +8,30% y +4,96% de avance. La DLL queda como candidata opcional; se conservan los 27 parches, la DLL anterior y los 552 bloques de cobertura. No hay equivalencia ni rendimiento del juego completo validados. Detalles en `hot-rel-clang-report.md`. Las mediciones siguientes son históricas.

Actualización del 9 de octubre: Ghidra ya está disponible en la conexión activa. Se probó una búsqueda directa de bloques DOL con 3.080 comparaciones de fuentes sin diferencias; las mediciones dieron +1,42% y −3,96%, así que el candidato se retiró y se restauró la versión anterior de 27 parches. Se conservan guards nuevos para las mediciones, sus evidencias y el experimento. Detalles en `inline-dol-lookup-report.md`. Las mediciones siguientes son históricas.

Actualización del 9 de octubre, **27 parches reproducibles**: la opción experimental `-SkipEmptyModHooks` evita consultar el gestor cuando no hay mods cargados; conserva los callbacks si existe cualquier mod. Dos parejas con orden invertido registraron **+7,74% y +11,09% de avance** y medianas de **51,33% y 52,55% de velocidad normal** en la escena del primer out. Pasaron 14 comprobaciones, compilación, reproducción, cierre y REL; la auditoría separada completó **3.505 comparaciones sin diferencias** y omitió 39 entradas. La opción permanece desactivada por defecto, la cobertura sigue en 552 bloques y se mantiene intérprete/JIT. Detalles en `empty-mod-hooks-report.md`. Las mediciones que siguen son históricas.

Trabajo local: `D:\MLBPowerPros2008Recomp`. La imagen original y el espejo del proyecto permanecen intactos.

**Actualización, 9 de octubre de 2026:** la serie alcanza **26 parches reproducibles**. Las tres diferencias restantes correspondían a vueltas distintas de bucles al comparar el código nativo con la referencia. Se corrigió la alineación conservando las comprobaciones de registros, memoria y MMIO. Pasaron 22 casos, compilación, reproducción y auditorías Clang/MSVC con 3.453/3.336 comparaciones completas y cero diferencias en la ventana 5–6 millones de despachos. Hay 37 entradas omitidas por sesión; no se consideran validadas. Detalles en `lockstep-alignment-report.md`. Se mantienen los 552 bloques enlazados y la necesidad de intérprete/JIT.

La nueva comparación del menú registró **+66,44% de avance** con Clang DOL / MSVC REL y una mediana de **56,44% de velocidad normal**, frente a 34,96% con MSVC. Ambas sesiones cerraron sin órdenes fallidas, conservaron los 200.212 campos de reubicación y 7.820.936 bytes de código REL y sus capturas se revisaron. Es una pareja de esa pantalla, no rendimiento garantizado del partido completo. Véase `compiler-experiment-report.md`. Las mediciones que siguen son históricas.

La variante registró **+54,94% y +62,10% de avance de fotogramas del juego** en dos parejas con orden invertido, desde el mismo estado privado del primer out y sin perfiles activos. Sus medianas fueron **45,26% y 45,30% de velocidad normal**. Las cuatro sesiones cerraron correctamente, sin órdenes fallidas, con coincidencia de 200.212 campos y 7.820.936 bytes de código REL y capturas revisadas. El resultado corresponde a esa pantalla en este equipo; no implica rendimiento jugable ni equivalencia completa. Las suites Clang recompiladas conservaron las 2.352 referencias DOL y 72 casos REL aprobados.

**Cambio anterior, 9 de octubre de 2026:** la serie alcanza 23 parches reproducibles. La opción experimental `-CacheBatch` agrupa iteraciones del bucle de caché conservando invalidaciones por línea, ciclos y retorno del código original. Pasaron 8.130 casos diferenciales, guards, compilación, reproducción y dos sondeos OFF/ON con cierre y REL correctos, cuyas capturas se revisaron. Se ejercitó en 141237 lotes. La comparación corta registró +5.7% de avance en la escena del primer out; no garantiza una ganancia en otras escenas. La opción permanece desactivada por defecto y exige la DLL comprobada. Detalles en `cache-batch-report.md`; permanecen los 552 bloques y el apoyo del intérprete/JIT.

**Medición anterior, 22 parches:** La medición agrupa ahora las muestras de ejecución del módulo por dirección runtime de entrada, con límite de memoria y contabilidad de descartados. En una prueba corta se registraron 3.096 direcciones sin descartar muestras. Pasaron las pruebas del helper y fragmento reales, comprobación de sumas y máximos, compilación y reproducción, más dos sondeos con medición activada/desactivada y cierre/REL correctos. Las capturas se revisaron. La lista orienta la investigación hacia rutas de cálculo y un bucle de caché, sin atribuir costes exclusivos de funciones ni una ganancia de velocidad. Detalles en `dispatch-sites-report.md`; permanecen los 552 bloques y el apoyo del intérprete/JIT.

**Medición anterior, 21 parches:** El diagnóstico opcional `-ProfileDispatchTiming` mide tres etapas del despacho. La ejecución del módulo, incluyendo sus callbacks, concentró el 80,14% del tiempo crudo de esas etapas muestreadas; no equivale a todo el tiempo de CPU. Pasaron la compilación, reproducción, pruebas del helper y fragmento de despacho, análisis y rechazo de perfiles en comparaciones de velocidad. Dos sondeos validaron las opciones activada y predeterminada desactivada, cierre, snapshots REL y capturas revisadas. Esta tanda aporta diagnóstico, sin atribuirle una mejora de velocidad. Detalles en `dispatch-timing-report.md`; permanecen los 552 bloques y el apoyo del intérprete/JIT.

**Búsqueda anterior, 20 parches:** Se reutiliza la búsqueda del índice de bloque con posiciones REL fijas, manteniendo la comprobación de módulo activo y los guards de verificación/fallback. Pasaron las pruebas fija/dinámica, descarga/recarga, bloques fallidos y fallback obligatorio, la compilación y dos sondeos con cierre y REL correctos. La comparación registró +5,4% de avance de fotogramas en la escena del primer out y una mediana de 30,39% de velocidad normal. Es una única pareja de sesiones, sin ganancia garantizada en otras escenas. Detalles en `chunk-lookup-report.md`; permanecen los 552 bloques y la misma cobertura enlazada.

**Límites anteriores, 19 parches:** guardar los límites de las secciones REL evita recorrerlas para consultas fuera del módulo. Pasaron las pruebas de resolución fija/dinámica, descarga, recarga, límites desplazados y precedencia de secciones, más la compilación y dos sondeos con cierre y REL correctos. La comparación registró +8,3% de avance de fotogramas en la escena del primer out y una mediana de 30,14% de velocidad normal. Es una única comparación de esa escena, sin ganancia garantizada para el partido completo. Detalles en `rel-bounds-report.md`.

**Conversión anterior, 18 parches:** se eliminó una búsqueda de secciones innecesaria al convertir direcciones en la configuración REL con posiciones fijas. Pasaron las pruebas de conversión fija/dinámica, la compilación y dos sesiones cortas con comprobación de cierre y REL. La diferencia de velocidad fue +1,4%, demasiado pequeña para concluir una mejora reproducible con una sola comparación. La mediana fue 29,17% de velocidad normal en esa pantalla. Detalles en `fixed-rel-translation-report.md`. Las mediciones de 17 parches que siguen son anteriores a ambos cambios.

**Antecedentes, 17 parches, 9 de octubre de 2026:** los 552 bloques DOL/REL están enlazados en una DLL experimental con ubicación REL protegida. La compilación optimizada conserva sus 2.352 referencias de memoria DOL y 72 casos de seis funciones REL aprobados. Hay 17 parches reproducibles. La opción experimental para la espera de la cola vacía registró +10,8% de avance de fotogramas en la pantalla del partido y +14,8% en el menú principal, en comparaciones separadas. Pasaron el guard, pausa/regreso, un arranque fresco hasta la introducción y el nuevo lote automático de comparación; véase `scheduler-idle-report.md`. La opción permanece desactivada por defecto. Las medianas informadas fueron 28,5% de velocidad normal en la prueba del partido y 34,9% en la del menú; todavía falta rendimiento jugable. La comparación anterior de DLL registró aproximadamente +71%; corresponde a otro cambio y no se suman esos porcentajes. El último estado jugable guardado sigue mostrando Colorado 5–Boston 0 con dos outs. La prioridad es código y rendimiento mediante pruebas cortas. Un inning completo, bateo del jugador, defensa manual, audio y ejecución exclusivamente nativa siguen pendientes. Las secciones históricas conservan sus resultados anteriores.

## Segundo out y ayuda del controlador — 8 de octubre de 2026

`boot-probe-20261008-220609-864` restauró el estado optimizado de dos strikes. Una secuencia A de 5 fotogramas, liberación de 25, A de 5 y espera neutral de 360 dio paso al segundo out y otro bateador, todavía Colorado 2–Boston 0 (`progress-0011.png`). Tres secuencias adicionales avanzaron a 4–0 (`progress-0034.png`); otras tres, con esperas de 180, dejaron 5–0 y dos outs (`progress-0054.png`). No se alcanzó el cambio de turno. El estado `last-pitch-state.sav` tiene 41.743.202 bytes y SHA256 `50244fc60c4c2c8a6e008e476c6c0bdbc55779f8d634e15693e258eda9fffe3d`.

La sesión duró 600,46 s, cerró con salida 0, sin terminación forzada, cero órdenes fallidas y MEM1/MEM2 completos. Pasó la comprobación de cierre. Contadores: 1.592.529.404 despachos nativos, 103.734.654 callbacks, 1.833.931 invocaciones JIT, 1.261.524 excepciones nativas y cero verificaciones de código fallidas. La captura coincide en los 200.212 campos de reubicación y los 7.820.936 bytes de código REL.

`boot-probe-20261008-221749-005` restauró visualmente ese estado. Un pulso de + abrió el menú de pausa (`progress-0011.png`). El stick del Nunchuk permitió seleccionar Controller; A abrió la ayuda de **A Type** (`progress-0050.png` y captura final). La página original del juego indica A para swing, B para Big Swing y stick para Sweetspot Cursor. Se consultó esa información, pero no se probaron todavía esas acciones al bate. La sesión duró 600,43 s y cerró con salida 0, sin terminación forzada, cero órdenes fallidas y memoria completa; pasó la comprobación de cierre. Las órdenes `0080`–`0082` llegaron después del plazo y quedaron pendientes: no se atribuye un cambio de página ni un estado guardado a ellas.

`boot-probe-20261008-223136-421` repitió la navegación al Controller con las órdenes preparadas al comienzo. Los pulsos cortos de −, stick y cruceta no produjeron un cambio visible de página. El último pulso de − durante 60 fotogramas y una espera neutral de 30 sí dejó la página **Defence Control**, comprobada en la captura final. No hay evidencia suficiente para atribuir los intentos anteriores a un fallo del mapeo: el parser y la conexión de botones contienen los controles esperados, y el pulso largo cambió la página.

La ayuda A Type del juego muestra: stick para Type of Pitch / Course / Fielder Movement; A para Pitch; Z para Pitch Out; stick + B para Change to Second Breaking Ball; B para Throw to Cut-off Man; cruceta para Throw to Each Base. Estas indicaciones orientan la siguiente prueba; no validan selección del lanzamiento, dirección ni defensa manual durante una jugada. La página de ataque muestra A para Swing, B para Big Swing y stick para Sweetspot Cursor. No se ha bateado todavía con Boston.

Se guardó `last-help-state.sav` (22.154.047 bytes; SHA256 `d11743d9088aad533f7212534a38e1c735eaec33807ee24b6d2018445e29d8d1`). Su restauración futura queda pendiente. El último estado jugable repetible sigue siendo `last-pitch-state.sav` del sondeo `220609-864`, restaurado visualmente en las dos sesiones siguientes.

La sesión de ayuda duró 900,24 s, cerró con salida 0, sin terminación forzada, cero órdenes fallidas, ninguna orden pendiente y MEM1/MEM2 completos. Pasó la comprobación de cierre. Contadores: 2.240.786.479 despachos nativos, 205.036.798 callbacks, 3.157.731 invocaciones JIT, 1.733.132 excepciones nativas y cero verificaciones de código fallidas. Los 200.212 campos y los 7.820.936 bytes de código REL coinciden. Esta sesión consultó menús; su duración no representa 900 segundos de partido activo.

`send-probe-command.ps1` ahora rechaza órdenes cuando existe el resultado final del sondeo. La comprobación contra una sesión realmente terminada confirmó el rechazo sin crear archivo en la cola; también pasó el análisis de sintaxis. La protección evita publicar órdenes después del resultado final, pero no garantiza que una orden enviada antes del plazo tenga tiempo de completarse. No se modificaron traducciones C, módulo, runtime ni los 15 parches en esta tanda; no se repitieron pruebas de CPU porque esos componentes no cambiaron.

## Compilación optimizada y comparación de velocidad — 8 de octubre de 2026

`POWERPROS_OPTIMIZE_MODULE` habilita `/O2` en MSVC conservando `/fp:strict`. La versión inicial sigue disponible con `/Od`; no se editaron traducciones C ni fuentes del runtime. `runtime-rel.ps1 -Optimize -ModuleOnly -ReuseGenerated` prepara el módulo en `local/build/runtime-module-rel-optimized/`, comprueba las fuentes y revisiones fijadas, ejecuta las dos suites de CPU y valida los 15 parches. La reproducción completa de parches pasó en `runtime-patch-replay-20261008-213814`. Los registros de compilación y pruebas usan el prefijo `runtime-module-rel-optimized`. Mantener cálculo estricto y pasar estas pruebas concretas no demuestra equivalencia de todas las instrucciones de coma flotante.

La DLL inicial mide 640.383.488 bytes y tiene SHA256 `f2510c23f887c17fd310a73f92349e4c587cd11c3f3f989d239b5135e314cecd`; la optimizada mide 610.599.424 bytes y tiene SHA256 `393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6`. `probe-boot.ps1 -RelModule -OptimizedModule` selecciona explícitamente la segunda y exige su configuración de optimización. Los resultados nuevos registran ruta, SHA256 y modo del módulo. La selección por defecto conserva la versión inicial.

La comparación se hizo después de terminar la compilación, con dos sesiones consecutivas de 120 s, Vulkan, entradas físicas aisladas y el mismo estado del primer out (SHA256 `5158bc08a5e58986bf5313277e0676b4cad0b77cecacbdf442313f67020eed14`). No se pulsaron controles. Ambas pantallas finales se inspeccionaron y ambas sesiones cerraron correctamente.

| Módulo | Sondeo | Ventana medida | Avance de fotogramas del juego | Fotogramas del juego / segundo real | Mediana de velocidad informada |
| --- | --- | ---: | ---: | ---: | ---: |
| Inicial | `boot-probe-20261008-214050-507` | 110,084 s | 974 | 8,848 | 14,99% |
| Optimizado | `boot-probe-20261008-214553-879` | 110,269 s | 1.668 | 15,127 | 25,19% |

El cociente es **1,70965**, aproximadamente **70,97% más rápido** en esta pantalla y este equipo. Se mide el avance del contador de fotogramas del juego entre muestras en ejecución; no son FPS renderizados ni una medición de todo el partido. Una pareja consecutiva no establece variabilidad estadística. Sigue habiendo apoyo del intérprete/JIT. Evidencia: `local/analysis/module-speed-comparison-20261008-214941-778728.json`. `compare_probe_speed.py` rechaza estados o condiciones distintos, controles enviados, órdenes pendientes y muestras demasiado cortas; `check_probe_speed_comparison.py` comprueba cálculo y rechazos con fixtures independientes.

## Carreras y lanzamientos con el módulo optimizado — 8 de octubre de 2026

`boot-probe-20261008-211058-551` restauró visualmente el primer out. Tres lanzamientos con A de 60 fotogramas avanzaron a Colorado 1–Boston 0; cuatro lanzamientos adicionales dejaron Colorado 2–Boston 0, un out y corredor en primera. Una prueba del stick del Nunchuk no produjo un cambio visible de selección de lanzamiento; no se considera validada. El estado `more-play-state.sav` tiene 40.052.271 bytes y SHA256 `7348fe1085165bf9afb16881b8e383b8f89cf33b35b3293d11a4da85ab7926e6`. La sesión duró 900,06 s y cerró con salida 0, sin terminación forzada, cero órdenes fallidas y MEM1/MEM2 completos; pasó la comprobación de cierre.

`boot-probe-20261008-215121-864` usó la DLL optimizada y restauró ese estado, comprobado en `progress-0020.png`. Se probaron dos secuencias de A durante 5 fotogramas, liberación durante 25, A durante 5 y espera neutral de 240/180. La primera dejó un strike (`progress-0024.png`); la captura final muestra dos strikes, un out, corredor en primera y marcador 2–0. Esto comprueba respuesta a la secuencia; no demuestra que sea el control óptimo o que el segundo pulso determine la precisión. Se guardó `optimized-two-pitch-state.sav` (40.022.806 bytes; SHA256 `6b59fdd8f994f0524c4208c379005cf1976b2bd375bcbc0107c00cf4408db5ae`) para continuar.

La sesión optimizada duró 300,31 s, cerró con salida 0, sin terminación forzada, cero órdenes fallidas, captura final y MEM1/MEM2 completos. Pasó `check_probe_shutdown.py`. Contadores: 812.774.781 despachos nativos, 50.928.080 callbacks de instrucciones, 921.902 invocaciones JIT, 654.163 excepciones nativas y cero verificaciones de código fallidas. Los 200.212 campos de reubicación y los 7.820.936 bytes de código REL coinciden en la captura. Los contadores y esta comparación de memoria no equivalen a cobertura nativa del juego. Siguen pendientes cambio de turno, bateo del jugador, defensa manual, audio y partido completo.

## Pelota en juego y primer out — 8 de octubre de 2026

`boot-probe-20261008-203348-395` restauró el estado del primer strike con su SHA256 registrado. Las órdenes de A durante 60 fotogramas, separadas por esperas neutrales de 180–240 fotogramas, permitieron observar dos strikes (`progress-0013.png`), contacto de la CPU, la pelota y los jugadores en el campo (`progress-0015.png`), la indicación H y el corredor en primera (`progress-0016.png`). El juego regresó al lanzamiento frente al siguiente bateador, sin outs y con marcador 0–0. No se envió movimiento ni tiro de un defensor: la escena comprueba renderización y avance de la jugada, no control manual de la defensa.

La segunda serie de tres pulsos de A dejó al siguiente bateador con dos strikes. Se guardó `wave-two-state.sav` (40.036.333 bytes; SHA256 `49fd72f9145b08d1504ca8494fb94cb62c2cad86ac98bacf62f41f54cfb64b85`). La sesión duró 900,17 s y cerró con salida 0, sin terminación forzada, cero órdenes fallidas y MEM1/MEM2 completos. `check_probe_shutdown.py` pasó. Los contadores finales registran 1.408.675.077 despachos nativos, 90.858.693 callbacks de instrucciones, 1.637.159 invocaciones JIT, 1.156.102 excepciones nativas y cero fallos de verificación de código. Los 200.212 campos y los 7.820.936 bytes de código REL vuelven a coincidir. Las órdenes tardías `0070`–`0072` quedaron pendientes después del intervalo; no se atribuye ningún resultado a ellas.

`boot-probe-20261008-205240-719` restauró visualmente el estado de dos strikes. Un pulso de A y una espera neutral dieron paso al **primer out**, con corredor en primera, nuevo bateador, cero bolas/strikes y marcador 0–0 en la parte alta del primer inning (`progress-0024.png`). Se guardó `pitch-result-state.sav` (39.415.954 bytes; SHA256 `5158bc08a5e58986bf5313277e0676b4cad0b77cecacbdf442313f67020eed14`). Esta prueba duró 300,21 s y cerró con salida 0, sin terminación forzada, cero órdenes fallidas y capturas completas. Contadores: 512.335.435 despachos nativos, 30.887.706 callbacks, 558.896 invocaciones JIT, 396.120 excepciones nativas y cero fallos de verificación. La solicitud de finalización anticipada se creó después del intervalo; el resultado conserva `finish_requested=false`.

El siguiente punto repetible es ese estado con un out. Siguen sin comprobarse un inning completo, bateo del jugador, defensa manual, audio y rendimiento jugable. El módulo continúa compilado con `/Od` y la ejecución mantiene intérprete/JIT de apoyo. No se modificaron traducciones, runtime ni parches durante estas dos pruebas; no se repitieron las suites de CPU sin cambios nuevos que lo justificaran.

## Exhibition y reanudación privada — 8 de octubre de 2026

El sondeo fresco `boot-probe-20261008-155321-473` alcanzó el título, el menú principal y **Exhibition / Game Setup / 1 Player**. También apareció el modo de demostración automático, con estadio y alineación de Angels; eso no valida un partido controlado por el usuario. Los pulsos de cinco frames no dieron una respuesta fiable; + y A de 60 frames permitieron salir de la demostración y entrar en Exhibition. Una orden temprana no pudo abrirse; se conserva en `control/failed/`. La sesión de 900 segundos terminó con salida 0 y sin terminación forzada.

Se guardó el estado privado del menú en `control/artifacts/menu-state.sav` (33.488.431 bytes; SHA256 `049c95362219a74f0c099791a683cce4f1c494ecaa1515613d4b2095f9ff8beb`). El sondeo `boot-probe-20261008-161227-504` lo restauró con el mismo runtime y módulo. La pantalla fue comprobada visualmente; esa reanudación no cuenta como otro arranque fresco.

Con las asignaciones físicas desactivadas, A avanzó por Exhibition, 1 Player y Controller Setup. En Team Select, una orden del stick del Nunchuk a la derecha durante 15 frames cambió **Boston → New York Yankees**. A confirmó Yankees, pasó el foco a CPU y confirmó Colorado; después apareció **Road / Home**. Las capturas `controller-settled.png`, `team-move.png`, `team-confirm.png` y `game.png` documentan la secuencia. No se probaron todavía lanzamientos, bateo ni un partido completo.

Esta segunda sesión duró 900,22 segundos, terminó con código 0, sin terminación forzada, y tuvo cero órdenes registradas como fallidas. Registró 1.273.901.636 despachos nativos, 91.827.329 callbacks de fallback, 2.537.615 invocaciones al JIT, 1.939.842 excepciones nativas y cero verificaciones de código fallidas. Los contadores no representan porcentajes de cobertura ni de rendimiento. La captura coincide en los 200.212 campos de reubicación y los 7.820.936 bytes de código REL.

El sondeo posterior `boot-probe-20261008-162927-571` volvió a recorrer Exhibition y llegó a la elección de uniformes de Boston/Colorado. Guardó `exhibition-state.sav` (23.034.761 bytes; SHA256 `0df92992801ea926a1e7e38fef88ef0df927c7044175c88d1137a3ec7de24d89`). Su cierre fue forzado: quedaron órdenes de control sin procesar detrás del primer apagado, sin contadores finales de shutdown. Esto no invalida las capturas, pero impide dar por fiable el cierre con órdenes interactivas pendientes.

`boot-probe-20261008-164903-213` restauró ese estado y reprodujo otro fallo: la segunda orden de apagado terminó en `failed/` con `could not open command file`, aunque el archivo contenía `command=stop`. La cola convertía cualquier error de apertura en una orden inválida y la descartaba. `check_automation_queue.py` reproduce un bloqueo temporal real de Windows con permiso de renombrado: compila el parser y el bucle de la cola del código fijado, sustituyendo solamente la ejecución de hardware por un recibo en archivo. Antes de corregirlo falla la recuperación; las órdenes malformadas ya se rechazan correctamente. El nuevo parche reintenta la apertura en el siguiente ciclo sin adelantar órdenes posteriores ni cambiar el parser. Pasan ambos casos; evidencias en `automation-queue-check-20261008-170801-662928` (antes) y `automation-queue-check-20261008-171009-335617` (después).

El runtime recompilado conserva **14 parches reproducibles**: ocho del core y seis del frontend. La serie completa se aplicó sobre copias fijadas (`runtime-patch-replay-20261008-171135`). Pasan las dos pruebas registradas del módulo combinado. La base completa mantiene `BUILD_TESTING=OFF`; no se afirma que se haya ejecutado su suite general.

La comprobación real `boot-probe-20261008-171339-993` restauró visualmente los uniformes y terminó anticipadamente por `finish-requested` después de 86,90 s. Salida 0, sin terminación forzada, cero órdenes fallidas, MEM1/MEM2 completas y cero verificaciones de código fallidas. Registró 167.022.186 despachos nativos, 9.338.404 callbacks de fallback y 158.905 invocaciones al JIT. Este resultado verifica el cierre de esa sesión; no cubre el bloqueo por órdenes interactivas pendientes de la sesión larga anterior.

`probe-boot.ps1 -LoadState` registra la ruta y SHA256 del estado solicitado; la inspección de imagen confirma la restauración. Un archivo `finish-requested` en el directorio activo solicita finalizar antes del plazo, conservando el apagado y las capturas finales normales. Los estados y resultados permanecen bajo `local/`; no se alteran archivos C generados ni la imagen original.

## Resultado comprobado

Se creó y compiló `local/build/runtime-module/Release/gRL8E54_recomp.dll`, un módulo Windows x64 para la ABI 3 de ModernGekko y la ABI 4 de su CPU. Usa los 74 fragmentos originales de la traducción del DOL y los helpers de CPU de GXRuntime. No se editaron los archivos C generados. Las bibliotecas anteriores de comprobación se conservan por separado.

El módulo pasó las **2.352 referencias de memcpy/memset del PowerPC original** a través de su interfaz pública de despacho. La prueba instala un callback que rechaza cualquier fallback de instrucciones. Esto comprueba esas rutinas y la compatibilidad de su estado de CPU; no comprueba el resto del juego.

La herramienta `powerpros_startup_probe.exe` carga las secciones del DOL en MEM1 y comienza en `0x8000403C`. Tras tres despachos nativos se detiene en `0x8009C574`, instrucción `0x7C70FAA6`: `mfspr r3, 1008` (HID0, identificado en `RecompCore/Source/Core/Core/PowerPC/Gekko.h`). Falta el servicio de ese registro de hardware. La herramienta devuelve **2** para indicar una frontera pendiente, nunca éxito de arranque.

Esta prueba aislada usa registros iniciales a cero y no implementa el entorno completo de inicio de Wii. La base de diagnóstico completa sí supera esa frontera HID0 y ejecuta el DOL, como se detalla a continuación. **No se ha validado todavía el loop principal del gameplay, un partido jugable, audio ni entrada.**

Registros privados:

- `local/analysis/runtime-module-build.log`
- `local/analysis/runtime-module-checks.log`
- `local/analysis/startup-probe.log`
- `local/analysis/moderngekko-submodules.log`
- `local/analysis/moderngekko-configure.log`

## Ejecución en la base completa

Se compiló `local/build/moderngekko/Release/moderngekko-run.exe` con Visual Studio 2022 x64 y todas sus dependencias fijadas. El flujo `tools/runtime.ps1 -SkipDependencies` volvió a configurar, compilar y comprobar el módulo y la base. Se restauró `/EHsc` en la configuración C++ para conservar el desenredo de excepciones de MSVC.

La prueba `boot-probe-20261008-004919-889` esperó 15,86 segundos de preparación, observó `state=running` y comenzó después su ventana de 30 segundos. Comenzó en `0x8000403C` y los primeros ocho despachos nativos regresaron al runtime. El proceso terminó con código 0, sin terminación forzada, tras capturar MEM1/MEM2 y completar la parada.

| Contador final | Valor | Interpretación |
|---|---:|---|
| Despachos nativos | 187.354.042 | Invocaciones completadas de bloques de la DLL; no equivale a funciones diferentes ni instrucciones |
| Pasos de fallback de la ruta principal del intérprete | 0 | No incluye los callbacks de instrucciones ni el JIT |
| Callbacks de instrucciones pendientes | 4.504.953 | El entorno sí ejecutó instrucciones mediante fallback |
| Invocaciones al JIT de fallback | 68.833 | Confirma ejecución emulada; no mide instrucciones ni porcentaje de tiempo |
| Excepciones del código nativo | 37.021 | Contador observado; no demuestra que todas sean correctas ni errores |
| Fragmentos que fallaron su verificación de código | 0 | En esta ejecución; no demuestra ausencia de cambios de código en el juego completo |

Antes de la captura, la base informó `frame_count=491`, `present_count=1016`, `fps=0`, `vps=0`. Son eventos del backend de diagnóstico sin imagen comprobada; **no se usan para establecer el framerate original ni confirmar menús correctos**. Los contadores finales también incluyen los segundos usados para leer memoria y completar el cierre.

Se obtuvieron 24 MiB de MEM1 y 64 MiB de MEM2 mientras el juego estaba pausado. `tools/inspect_runtime_rel.py` comparó identificador, versión, tabla de secciones y tamaños con `ovl_main.rel`: **no encontró una cabecera coincidente en esa captura**. Esto limita la observación a ese instante; no demuestra que el REL nunca se cargue, ni que una cabecera no haya sido liberada o modificada. Su carga y reubicación permanecen pendientes.

Todos los logs, trazas y capturas de memoria están en `local/analysis/boot-probe-20261008-004919-889/`, excluidos de Git. El archivo `result.json` mantiene `native_game_boot_validated=false`: ejecutar el DOL con servicios emulados aún no cumple el port nativo ni valida el loop principal.

## Primera imagen y observación del REL

La prueba Vulkan `boot-probe-20261008-005109-457` obtuvo una captura de la pantalla de instrucciones del Wiimote. El archivo privado `control/artifacts/game.png` se inspeccionó visualmente. Esto valida esa pantalla inicial en esta base; no valida menús, partidos, audio ni renderización nativa independiente de Dolphin.

Una segunda ejecución de 90 segundos (`boot-probe-20261008-005259-212`) avanzó a **NOW LOADING** y capturó un candidato de `ovl_main.rel` en MEM1, con cabecera en `0x80575580`. Coinciden ID 1, versión 3, 17 entradas y los tamaños de sus secciones. La sección ejecutable conserva el offset de archivo `0xD4` con la bandera de código; su dirección inferida en esta captura es `0x80575654`. La BSS todavía tiene entrada cero. No se da por terminada la reubicación.

La comparación contigua contra el REL original coincide en los primeros **9.502.739 bytes**, pero el archivo completo de 11.229.928 bytes no coincide. La captura, la pantalla de carga y esa diferencia son compatibles con una lectura aún en curso; esta es una inferencia, no una validación de la causa. Los datos y hashes están en `rel-memory-report.json` y `rel-payload-validation.json` dentro de ese sondeo.

Esta ubicación observada es distinta de la base virtual `0x80500000` usada al traducir el REL. Antes de incorporarlo al módulo nativo hay que verificar el estado final de sus secciones y traducir correctamente referencias y saltos entre direcciones virtuales y de ejecución. El código C generado sigue intacto.

## REL reubicado y logo de 2K Sports

El sondeo Vulkan de **120 segundos** `boot-probe-20261008-005615-342` llegó al logo de **2K Sports**, comprobado en su captura privada. Su snapshot conserva el módulo 1 con direcciones absolutas:

| Elemento | Dirección observada | Tamaño |
|---|---|---:|
| Cabecera REL | `0x80575580` | — |
| Tabla de secciones | `0x805755CC` | 17 entradas |
| Sección 1, código | `0x80575654` | 7.820.936 bytes |
| Sección 2 | `0x80CEACDC` | 484 bytes |
| Sección 3 | `0x80CEAEC0` | 12 bytes |
| Sección 4 | `0x80CEAED0` | 319.896 bytes |
| Sección 5 | `0x80D39080` | 1.486.392 bytes |
| Sección 6, BSS | `0x8102B0C0` | 154.196 bytes |
| Entrada `_prolog` | `0x80AA0718` | — |

Se contrastaron ID, versión, conteo y tamaños contra el REL original. Esto **observa el estado posterior al enlace**; no valida cada reubicación ni la ejecución nativa del REL. La DLL sigue cubriendo solo el DOL.

La tabla de secciones pasa de offset `0x4C` a puntero absoluto `0x805755CC`. El detector `RefreshRelSections` de la revisión fijada de RecompCore compara ese campo con el offset original; esa condición no reconoce esta cabecera después del enlace. Hay que adaptar y comprobar su detector antes de incorporar el REL a la DLL. El inspector privado ya acepta ambos estados y reproduce las direcciones anteriores en `rel-memory-report.json`.

Esta prueba **necesitó terminación forzada** después de agotar el plazo de cierre: código -1, sin contadores finales de shutdown. Los datos de memoria y la captura se guardaron antes y permanecen completos. No se presentan como contadores finales los valores parciales del progreso ni se da por resuelto el cierre en todos los estados del juego.

La siguiente integración debe conservar los offsets de todas las secciones, manejar el puntero absoluto de la tabla, mapear BSS por separado y comprobar referencias DOL/REL y despachos mediante las direcciones observadas. Los menús, partidos, audio, controles y mejoras siguen pendientes.

## Detector corregido y reubicaciones contrastadas — 8 de octubre de 2026

`recompcore-linked-rel-table.patch` adapta `RefreshRelSections` para aceptar tanto el offset original como el puntero absoluto a la tabla de la misma cabecera. Rechaza punteros a otras tablas, índices de sección inválidos, tamaños incorrectos, BSS sin asignar, offsets de archivo en una tabla enlazada y secciones fuera de MEM1. La base completa volvió a compilar con este octavo parche.

`tools/check_rel_detector.py` extrae y compila los métodos C++ reales del detector y de conversión a dirección de ejecución con una estructura de estado aislada. La captura `boot-probe-20261008-005615-342` produce exactamente las seis direcciones de la tabla anterior, incluida BSS. Pasan las comprobaciones de límites, compatibilidad con la tabla relativa, estabilidad del mapa y reinicio de los estados de verificación de chunks REL sin alterar los del DOL. La misma prueba contra el método original de la revisión fijada falla con `linked snapshot not detected`, reproduciendo el defecto. Esta prueba aislada no ejecuta funciones del juego.

`tools/validate_runtime_relocations.py` recorre las dos listas originales de importación, para el propio módulo 1 y para el DOL (módulo 0). Reconstruye las reubicaciones usando las direcciones de las seis secciones observadas en MEM1, con BSS independiente. Las reglas de los cuatro tipos presentes se contrastaron con `DolRecomp/src/frontend/container/rel.c`.

| Tipo de reubicación | Campos comparados |
|---|---:|
| ADDR32 | 61.928 |
| ADDR16_LO | 52.624 |
| ADDR16_HA | 37.181 |
| REL24 | 48.479 |
| **Total** | **200.212** |

Coinciden los **138.284 campos en código** y los **61.928 campos en datos**, sin diferencias. Además, el código completo reconstruido coincide byte a byte con los **7.820.936 bytes** de la sección 1. Ambos SHA-256 son `119197f763df225c5f9980debbb91067544b35a1cbcf5315a86a184286363323`. Las pruebas del verificador detectan alteraciones deliberadas de un salto REL24, de un puntero ADDR32 y de la tabla enlazada. Solo se modificaron copias de la captura en memoria de la herramienta.

La comparación valida el enlace observado en esa captura, **no la equivalencia de la traducción C ni la ejecución nativa del REL**. El código generado conserva su base de ensayo `0x80500000`, mientras la cabecera real está en `0x80575580`; la BSS también tiene su ubicación propia. El siguiente paso requiere adaptar esas referencias y verificar la traducción antes de activar su despacho. La DLL mantiene solo el DOL: **13,3067% de los bytes de código incorporados**, sin aumento por estas pruebas.

Después de recompilar, el sondeo de 30 segundos `boot-probe-20261008-044104-333` alcanzó el estado de ejecución y cerró con código 0, sin terminación forzada. Registró 187.083.333 despachos nativos, 4.529.230 callbacks de instrucciones, 69.208 invocaciones JIT y cero fallos de verificación de código. El módulo mantiene metadatos REL desactivados: este sondeo comprueba la base DOL, no la activación del detector REL durante el juego. No se capturó una imagen nueva. Las pruebas públicas de memoria del módulo volvieron a pasar.

Registros privados: `local/analysis/rel-detector-checks.json`, `rel-detector-checks-baseline.json`, `rel-relocation-checks.json` y `boot-probe-20261008-005615-342/rel-relocation-validation.json`. El parche nuevo se aplicó sobre una copia limpia del archivo de la revisión fijada y produjo el mismo contenido que el runtime compilado.

## Módulo combinado con REL nativo — 8 de octubre de 2026

`tools/prepare_linked_rel.py` reconstruye el REL desde el archivo original y sus listas de reubicación, usando las seis direcciones verificadas. Exige que los 200.212 campos y todo el código coincidan con la captura. Lo envuelve en un DOL privado de análisis para que el traductor fijado emita C a esas direcciones; **este contenedor no sustituye ningún asset ni se usa para arrancar el juego**. La carga real sigue leyendo `ovl_main.rel` original. La BSS conserva `0x8102B0C0` y `_prolog`, `0x80AA0718`. No se editaron los archivos C generados.

La traducción enlazada tiene 478 bloques, 1.955.234 palabras decodificadas y cero opcodes desconocidos. `gen_runtime_module_tables.py` combina sus rangos y hashes con los 74 bloques DOL. `local/build/runtime-module-rel/Release/gRL8E54_recomp.dll` contiene **552 bloques y 9.021.384 bytes de código representados: 100% enlazado en esta DLL experimental**. La DLL inicial se conserva aparte, con 13,3067%.

El detector de ubicación fija solo examina la cabecera comprobada y exige una tabla enlazada y las seis direcciones exactas. Esto evita búsquedas completas de MEM1 en cada dirección no cubierta y rechaza la traducción si el código o BSS se cargan en otra ubicación. La propia DLL verifica también identidad, versión, tabla, direcciones y tamaños antes de cada despacho REL. No se fuerza la ubicación del juego ni se ajustan a ciegas literales para otra distribución.

Se corrigieron los validadores de RecompCore y del frontend ModernGekko: ambos rechazaban metadatos de datos/BSS porque exigían que fueran código. Ahora permiten sus mapas separados, mantienen la exigencia de al menos una sección ejecutable y rechazan solapamientos e índices duplicados. La ABI mantiene su versión y estructura. Las pruebas usan el validador real del frontend y métodos extraídos del core; los diez parches completos se aplicaron sobre los archivos de las revisiones fijadas y coinciden con el código compilado (`runtime-patch-replay-20261008-050901/result.json`).

`reference_rel.py` ejecuta instrucciones PowerPC originales del snapshot con Unicorn, solo como herramienta de referencia. Se seleccionaron seis funciones cortas con límites inferidos por dtk, tres con direcciones absolutas y tres de enteros. Cada una volvió correctamente con doce entradas; **72/72 casos** de la DLL coinciden en los 32 registros generales, CR/XER/CTR/LR/PC y SHA-256 de los 24 MiB de MEM1. Un callback rechaza cualquier fallback de instrucciones y no se activó. La prueba adicional rechaza una BSS desplazada. No cubre todos los opcodes, coma flotante, temporización, gráficos ni el REL completo. Las **2.352 pruebas DOL** también pasan en la DLL combinada.

El primer intento del frontend rechazó el módulo antes de ejecutar el juego por su validador de metadatos de datos/BSS (`boot-probe-20261008-050558-570`). Tras corregirlo, la prueba Vulkan de 120 segundos `boot-probe-20261008-050910-754` alcanzó el estado de ejecución. `rel-dispatch.csv` registra ocho despachos nativos REL, comenzando en `0x80AA0718` y avanzando por bloques como `0x80584B18` y `0x80594E7C`. Uno de esos despachos registra una excepción de FPU no disponible; el core procesa esa frontera. Su corrección completa todavía requiere pruebas específicas de estados de FPU.

La captura muestra una **escena de la introducción con un campo de béisbol**. Es un fotograma comprobado, no una validación del video completo, sonido, menú ni partido. Los snapshots MEM1/MEM2 están completos. La nueva comparación de enlace vuelve a coincidir en los 200.212 campos y los 7.820.936 bytes de código, con SHA-256 `119197f763df225c5f9980debbb91067544b35a1cbcf5315a86a184286363323`.

La parada llegó a `platform loop returned`, pero el cierre final agotó su plazo y el sondeo terminó su propio proceso: **código -1 y sin contadores finales de shutdown**. Se conservan los datos y la imagen anteriores al cierre; los contadores parciales no se presentan como finales. La ejecución del juego mantiene callbacks de instrucciones y JIT. `native_game_boot_validated` sigue en `false`; un port exclusivamente nativo y jugable aún no está validado.

`tools/runtime-rel.ps1 -ReuseGenerated` volvió a preparar, comprobar y compilar el flujo completo. Los hashes de originales y del contenedor, las tres revisiones y los parches se verifican antes de compilar la base. Registros: `runtime-module-rel-build.log`, `runtime-module-rel-checks.log`, `rel-reference.json`, `moderngekko-rel-build.log` y el directorio del sondeo. La siguiente etapa es comprobar estados FPU y el resto del REL, resolver el cierre y avanzar hacia menús y gameplay con pruebas de equivalencia.

## Cierre con transferencia WiiConnect24 activa — 8 de octubre de 2026

Los registros nuevos separaron la parada de CPU, video e IOS. Las tres pruebas largas `boot-probe-20261008-141008-107`, `141537-241` y `141941-595` agotaron el plazo de cierre. La CPU y el backend de video sí terminaban; IOS quedaba esperando la cola de WiiConnect24. La prueba corta Vulkan de 30 segundos `141419-474` cerró correctamente. Alrededor de los dos minutos, el temporizador de WC24 inicia una tarea de descarga en el perfil privado, lo que explica la diferencia.

La reproducción `boot-probe-20261008-143008-665`, sin captura ni lectura de memoria, registró `scheduler task=1` y `entering download request`, y quedó en `stopping scheduler work`. La petición HTTP seguía activa mientras el destructor esperaba esa cola. Esto descarta que las capturas o la traducción REL fueran necesarias para reproducir la espera. `tools/check_probe_shutdown.py --require-inflight-wc24` rechazó ese resultado por necesitar terminación forzada.

`recompcore-wc24-shutdown-cancel.patch` añade una bandera atómica persistente para cancelar HTTP al destruir el dispositivo. Usa el callback de progreso de `Common::HttpRequest`; conserva el timeout y comportamiento normal de las peticiones durante la ejecución. La señal del temporizador no basta para la cancelación porque ese hilo la consume. No se editó C generado ni se sustituyó ninguna función del juego.

Con la corrección, `boot-probe-20261008-143346-422` ejecutó **120 segundos con Vulkan y DLL DOL+REL**, guardó MEM1/MEM2 y una captura, y terminó con **código 0, sin terminación forzada**. Su traza muestra una descarga activa al empezar el cierre, su retorno antes de completar la cola y finalmente `core state callback=0`. La prueba de regresión pasó exigiendo ese orden, además de la salida correcta y los contadores finales.

| Contador final | Valor |
|---|---:|
| Despachos nativos | 232.231.891 |
| Pasos de la ruta principal del intérprete | 0 |
| Callbacks de instrucciones | 18.735.920 |
| Invocaciones JIT | 232.038 |
| Excepciones nativas | 124.876 |
| Fallos de verificación de código | 0 |

Los contadores incluyen el tiempo de capturas y parada; no son porcentajes de ejecución nativa. La imagen nueva muestra **Power Pros Production**, sin validar todavía menú ni gameplay. La traza conserva ocho despachos REL observados. La comparación nueva vuelve a coincidir en los 200.212 campos y 7.820.936 bytes de código. Las suites del módulo pasan sus 2.352 casos DOL y 72 REL; la configuración actual de la base ModernGekko no registra tests en CTest, por lo que su evidencia aquí es la compilación y la prueba de integración real. Los 13 parches se reprodujeron completos sobre fuentes fijadas y coinciden con el código compilado (`runtime-patch-replay-20261008-143318/result.json`).

Esto resuelve la espera de cierre reproducida en estas pruebas. No valida todos los estados de apagado ni completa el port. Permanecen pendientes FPU y resto del REL, menús, partido, audio, controles y reducción del fallback.

La preparación ahora verifica la serie completa de parches. Verificar cada parche por separado en reversa daba falsos rechazos cuando un parche posterior cambiaba su contexto. `check_runtime_patches.py --prepare` avanza únicamente archivos iguales a una revisión fijada o a un estado intermedio reconocido; rechaza otros cambios antes de escribir en cualquiera de los dos repositorios. `check_runtime_patch_preparation.py` comprueba una copia limpia, una serie parcial y la conservación íntegra de cambios desconocidos. El flujo completo `runtime-rel.ps1 -ReuseGenerated` volvió a preparar, comprobar y compilar correctamente después de estos cambios.

## Menú principal y entrada aislada — 8 de octubre de 2026

`boot-probe-20261008-145416-968` ejecutó 900 segundos con Vulkan y DOL+REL. Sus capturas alcanzan la selección de equipos: Boston frente a Colorado, y después Houston. También aparece HOME en momentos inesperados. La sesión terminó con salida 0, sin terminación forzada y con snapshots completos. Esta sesión no valida los controles: no tenía archivos de configuración de entrada y el runtime cargaba las asignaciones físicas por defecto.

El código de `Wiimote::LoadDefaults` asigna A al clic izquierdo, HOME a Enter y direcciones al teclado. `GetInputOverrideFunction` deja de aplicar una sobreescritura cuando cambia su entrada física. Esto permite que el uso del escritorio interfiera con las órdenes del sondeo. Se preparó `local/runtime-probe-user/`, separado del perfil anterior, con mandos sin asignaciones físicas y Nunchuk adjunto. Una clave de dispositivo desconectado conserva incluso las secciones GC al guardar. La preparación rechaza ajustes desconocidos antes de escribir; acepta la normalización de espacios y comentarios del runtime. No se modificaron funciones del juego ni C generado.

En `boot-probe-20261008-151509-986`, también de **900 segundos**, `0050-skip-intro.ini` usa A y su captura muestra el título «Press +». `0060-title-plus.ini` da paso al menú principal. Tras A se observa «Nunchuk Style detected» y se entra en My Data; B devuelve al menú. El stick del Nunchuk cambia la selección de My Data a Arrange. Las pulsaciones de cruceta no movieron esa opción con el modo Nunchuk. Las capturas de estas órdenes no muestran el HOME inesperado de la sesión anterior.

Esto comprueba pantallas y respuesta básica, **no toda la navegación ni controles de gameplay**. Al detectar el modo Nunchuk, la selección pasó a My Data antes de entrar; falta comprobar esa transición y seleccionar Exhibition de forma repetible. No se alcanzó un partido. El perfil usa audio Null y no valida sonido. La DLL actual se compila sin optimización y las muestras de velocidad son bajas; no es evidencia de rendimiento jugable.

La sesión aislada guardó MEM1/MEM2 y cerró con **código 0, sin terminación forzada**. `check_probe_shutdown.py` pasó. Contadores finales: 1.274.606.407 despachos nativos, 102.513.694 callbacks de instrucciones, 2.718.853 invocaciones JIT, 2.039.943 excepciones nativas y cero fallos de verificación de código. Son contadores de toda la sesión y cierre, no porcentajes de cobertura o tiempo. Los 200.212 campos REL y los 7.820.936 bytes de código vuelven a coincidir en esta captura.

El sondeo ahora admite 900 segundos, captura cada intervalo solicitado y registra el tiempo ejecutado y el número de órdenes fallidas. `send-probe-command.ps1` publica por renombrado una orden ya completa: el envío anterior de `0061-after-home.ini` se leyó vacío durante su escritura. En la sesión aislada falló una captura periódica, `0000-progress-0012.ini`, con «could not open command file»; no fue una lectura vacía y su causa sigue pendiente. Las órdenes de botones y las capturas citadas sí se procesaron. Los archivos de preparación se prueban también contra un INI con HOME físico desconocido, que se rechaza sin cambiar sus bytes. Los 13 parches de runtime no cambiaron durante este trabajo.

La prueba posterior de 30 segundos `boot-probe-20261008-153809-208`, con backend Null, comprueba la preparación definitiva: los INI guardados conservan la clave del dispositivo desconectado en Wii y GC, la preparación los acepta al repetirla y el proceso cierra con salida 0. No aporta evidencia nueva de menús.

## Partido seleccionado y prioridad de apagado — 8 de octubre de 2026

`boot-probe-20261008-173857-417` restauró el estado privado de uniformes con SHA256 `0df92992801ea926a1e7e38fef88ef0df927c7044175c88d1137a3ec7de24d89`. Las órdenes aisladas de A confirmaron uniformes, Fenway Park, opciones y Play Ball. Las capturas muestran Boston (1P local) contra Colorado (CPU visitante), la introducción del estadio y el calentamiento del primer inning. Esta secuencia corresponde al partido elegido; no es la demostración automática del título. Se guardaron `play-ball-state.sav` y `match-intro-state.sav` para repetir la prueba.

La sesión ejecutó 900,41 segundos y terminó con salida 0, sin cierre forzado, cero órdenes fallidas y MEM1/MEM2 completos. `check_probe_shutdown.py` pasó. Contadores finales: 1.228.376.131 despachos nativos, 100.839.459 callbacks de instrucciones, 1.556.508 invocaciones JIT, 900.095 excepciones nativas y cero fallos de verificación de código. Los 200.212 campos REL y los 7.820.936 bytes de código vuelven a coincidir en el snapshot del calentamiento. Esto no valida el partido completo, audio, rendimiento ni ejecución exclusivamente nativa.

El bloqueo anterior con órdenes pendientes tiene una causa adicional a la apertura temporal de archivos: `pad_frames` espera fotogramas dentro del único hilo de automatización y puede impedir que ese hilo lea Stop. Se añadió `moderngekko-pad-stop-priority.patch`: durante esa espera comprueba cada 50 ms si existe una orden Stop válida, libera los controles y devuelve `pad_frames interrupted by a queued stop`. La orden Stop permanece en la cola para procesarse normalmente. Una orden malformada no interrumpe la espera.

`check_pad_frame_shutdown.py` compila el cuerpo real del despacho y el parser, con fronteras de CPU/entrada simuladas. La comprobación fallaba antes (`pad-frame-shutdown-check-20261008-174404-551934`) y pasa después (`174606-167199`): Stop interrumpe incluso con fotogramas inmóviles y libera el botón; un archivo inválido no provoca una interrupción falsa. Los 15 parches completos se reprodujeron sobre las fuentes fijadas (`runtime-patch-replay-20261008-174719`). La base y el ejecutable se compilaron correctamente; las dos pruebas de la ABI del módulo siguen pasando. La cancelación deliberada se registra como una orden fallida, no como una ejecución completada de `pad_frames`.

La comprobación real posterior `boot-probe-20261008-175806-715` restauró `match-intro-state.sav` (SHA256 `c9367b40dd8ca1bb607361b15be1fdb9ea3197b099d3fca3f82234255dee24f3`). La pantalla restaurada muestra dos lanzamientos de calentamiento. `0050-warmup-a.ini` y `0060-warmup-second-a.ini`, cada una con A durante 60 fotogramas, completaron el calentamiento y dieron paso al bateador de Colorado. `0080-first-live-pitch.ini` registró un strike: la captura `progress-0017.png` muestra una luz de strike y ninguna bola ni out. Se guardaron `first-inning-state.sav` y `first-strike-state.sav`. Esta evidencia valida una respuesta de lanzamiento limitada; no demuestra bateo, defensa o un inning completo.

Tras guardar ese punto se envió `0100-busy-neutral.ini`, sin botones y con 6.000 fotogramas. La cola dejó de procesar capturas mientras esa orden esperaba. Se solicitó el cierre anticipado y el runtime la canceló: es la única orden en `control/failed/`; las órdenes finales de screenshot, pause, seis lecturas, resume y ambos Stop sí se procesaron. La sesión duró 405,80 s, terminó con salida 0, sin terminación forzada y con MEM1/MEM2 completos. `check_probe_shutdown.py` pasó; los contadores registran 652.486.682 despachos nativos, 42.258.211 callbacks de instrucciones, 751.190 invocaciones JIT, 519.692 excepciones nativas y cero fallos de verificación. La cancelación figura en el resultado como una orden fallida esperada; no se oculta como si hubiera completado sus 6.000 fotogramas.

`first-strike-state.sav` ocupa 37.338.296 bytes y tiene SHA256 `f32e77a58823ef68f0fd1aaf6f9c4a08c3e8540e208988ef2b4dc5701167bf13`. El siguiente avance es comprobar más lanzamientos, bateo y defensa desde ese estado. La velocidad observada sigue siendo baja y el audio usa Null. El arranque exclusivamente nativo y la renderización nativa con aurora permanecen pendientes.

## Correcciones de la prueba

La primera versión del sondeo contaba el tiempo desde el lanzamiento, incluyendo el hash de assets y la preparación. Enviaba la parada antes de que la CPU empezara; sus registros no demostraban un bloqueo del juego. El sondeo actual espera un estado de ejecución antes de medir el intervalo.

El backend Null omite la creación de la interfaz ImGui. La configuración original activaba la precompilación de shaders y su interfaz de progreso, que accedía a un contexto inexistente. El parche `moderngekko-headless-shaders.patch` selecciona compilación síncrona sin precompilación en las pruebas sin ventana. El error de contexto desapareció y la CPU empezó a ejecutar.

La primera orden de cierre de Dolphin equivale a pulsar el botón de apagado de Wii cuando hay un hook STM instalado. Un juego pausado no responde a ese evento. El sondeo reanuda después de las capturas y, si hace falta, envía una segunda solicitud para cerrar directamente la base. Solo termina forzosamente su propio proceso cuando el plazo final se agota.

Los siete parches se aplicaron en orden sobre copias limpias de los archivos de las revisiones fijadas; resultado en `local/analysis/patch-validation-20261008-005335/result.json`. Los parches de etapas y progreso son diagnósticos, no sustituciones de funciones del juego. Las trazas nativas se habilitan mediante `STATICRECOMP_TRACE_FILE` solo para el proceso de prueba. Las alertas sin ventana se escriben en stderr para evitar cuadros de diálogo ocultos.

## Selección provisional

| Base inspeccionada | Evidencia del código | Decisión actual |
|---|---|---|
| [ModernGekko](https://github.com/ExpansionPak/ModernGekko) y su RecompCore | Interfaz de módulos, servicios de Wii, MMIO, video/audio y descubrimiento de secciones REL; contiene intérprete y JIT de fallback | Puente de diagnóstico para localizar dependencias de hardware y medir cobertura |
| [WiiCompiled](https://github.com/patchzyy/Wiicompiled) con aurora | Configuración concreta para Mario Kart Wii PAL, mapa de funciones, direcciones SDA y un REL fijado; también ofrece un ejemplo genérico de traducción de DOL | Referencia para la futura adaptación de servicios nativos; no se ha demostrado compatible con este juego |
| [ModernGekko-Template](https://github.com/ExpansionPak/ModernGekko-Template) | Su receta llama a ModernGekko y genera inicialmente el DOL | Referencia de integración; la receta sola no incorpora nuestro `ovl_main.rel` |

Revisiones exactas en `config/runtime.lock.json`. Las dependencias permanecen bajo `local/vendor/` y se conservan sus licencias.

La preparación usa las dependencias incluidas en la base, para no mezclar bibliotecas de MinGW con MSVC. Se conserva además un parche que añade la lista vacía de parámetros a dos lambdas `mutable` del ensamblador; MSVC 19.43 rechazaba la sintaxis abreviada. No cambia su comportamiento.

El uso de ModernGekko es provisional. Su código `HookInstructionFallback` ejecuta instrucciones pendientes mediante el intérprete; su core además crea un JIT para rangos sin cobertura. Una pantalla obtenida con esa base no bastaría para cumplir el objetivo del brief de ejecutar exclusivamente código recompilado.

Se añadió un parche de diagnóstico que cuenta invocaciones al JIT de fallback y registra sus primeros ocho puntos de entrada. El contador original `fallback_steps` solo se incrementa en las rutas del intérprete: un valor cero por sí solo no descarta uso de JIT. El nuevo contador mide invocaciones, no instrucciones ni porcentajes de tiempo. El parche no cambia la selección ni la ejecución del código.

## REL y límites

El módulo inicial cubre **solo el DOL** y se conserva para comparación. El módulo experimental separado incorpora el REL a su ubicación comprobada, con los límites de validación indicados arriba.

La ABI del runtime dispone de metadatos REL. Su implementación inspeccionada busca cabeceras y secciones en MEM1; hay que observar dónde carga realmente este juego el módulo antes de asegurar que eso basta. Las funciones compiladas usan direcciones virtuales fijadas durante la traducción; sus referencias deben conservar el significado correcto al cargarlo en otra dirección. No se fuerza una ubicación del REL a ciegas.

Los servicios completos compilan y ejecutan DOL y despachos REL con telemetría. La traducción experimental usa la distribución comprobada y pasa referencias limitadas de CPU. La espera de cierre con WC24 pendiente ya está corregida. Falta validar el resto del REL y el loop principal y reducir el fallback antes de hablar de un arranque exclusivamente nativo. La renderización nativa mediante aurora sigue pendiente.

## Reproducir

```powershell
Set-Location D:\MLBPowerPros2008Recomp
.\tools\runtime.ps1 -Python 'ruta\a\python.exe'
.\tools\probe-boot.ps1 -Seconds 30 -SnapshotMemory
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -Screenshot -SnapshotMemory
python .\tools\inspect_runtime_rel.py .\local\analysis\boot-probe-<identificador>
python .\tools\check_rel_detector.py .\local\analysis\boot-probe-20261008-005615-342
python .\tools\validate_runtime_relocations.py .\local\analysis\boot-probe-20261008-005615-342
python .\tools\check_runtime_relocations.py .\local\analysis\boot-probe-20261008-005615-342
.\tools\runtime-rel.ps1 -Python 'ruta\a\python.exe'
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -Screenshot -SnapshotMemory -RelModule
python .\tools\check_rel_detector.py .\local\analysis\boot-probe-20261008-005615-342 --fixed-layout
python .\tools\check_runtime_patches.py
python .\tools\check_runtime_patch_preparation.py
python .\tools\check_probe_shutdown.py .\local\analysis\boot-probe-20261008-143346-422 --require-inflight-wc24
.\local\build\runtime-module\Release\powerpros_startup_probe.exe .\local\disc\DATA\sys\main.dol
```

Requiere Visual Studio 2022 con C/C++, CMake, CTest, Git y Python. `-SkipDependencies` reutiliza los submódulos ya obtenidos. El script prepara y verifica el módulo antes de compilar la base; un fallo posterior no invalida las pruebas del módulo ni demuestra un arranque.
