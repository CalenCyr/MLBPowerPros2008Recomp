# Agrupar iteraciones del bucle de caché — 9 de octubre de 2026

Nota posterior de compatibilidad: el sondeo acepta también la DLL MSVC reenlazada con mapa, SHA256 `60a0611c6e528583f67b985cc31d290973cf96666685523eec8c1ab316702865`, después de repetir las 8.130 pruebas del helper y las suites DOL/REL. La comparación exige una DLL idéntica en ambos sondeos. La variante Clang se rechaza para CacheBatch; el experimento Clang se midió con batching desactivado. Esta ampliación del guard no demuestra una ganancia de batching con la DLL reenlazada.

El parche `recompcore-cache-batch.patch` añade una opción experimental `-CacheBatch` para el bucle `dcbf` de RL8E54 en `0x8009C4A4`. La serie alcanza **23 parches reproducibles: 16 del core y 7 del frontend**. La opción permanece desactivada por defecto y conserva el código generado y la DLL del juego.

## Cambio y condiciones

El callback nativo puede ejecutar varias invalidaciones consecutivas y los pares intermedios de incremento/decremento de registros. Conserva una llamada a `InvalidateICacheLine` por cada dirección, en el mismo orden y con el mismo comportamiento de desbordamiento uint32. El último par `addi`/`bdnz`, su comprobación de presupuesto y la llamada `sc` siguen ejecutándose en el C original. No se agrupan invalidaciones en un rango ni se omite ninguna línea.

La carga es cinco ciclos por `dcbf` en el contador del runtime y dos ciclos por par intermedio en el acumulador del módulo, como en el código anterior. El número de iteraciones no supera el siguiente retorno del bucle original con presupuesto 256. Se conservan los casos de acumulador cero, contador cero/uno y presupuesto agotado mediante la ruta existente, sin agrupar. Esto evita adelantar o retrasar la comprobación de eventos al final del segmento.

Se exigen la dirección e instrucción exactas, PC coherente, memoria suficiente y coincidencia actual de los cuatro opcodes `dcbf`, `addi`, `bdnz` y `sc`. Se rechaza agrupar con excepciones pendientes, caché de datos emulada, lockstep o perfilado de callbacks. El módulo debe identificar RL8E54. Las verificaciones normales del bloque y fallback siguen activas. El contador de callbacks disminuye cuando se agrupa; los contadores nuevos `cache_batch_runs` y `cache_batch_extra_lines` indican lotes y líneas adicionales ejecutadas dentro de ellos, sin atribuir tiempo de CPU.

La herramienta de sondeo exige específicamente la DLL optimizada SHA256 `393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6`, cuya generación usa presupuesto 256. Ese valor no forma parte del ABI general del módulo: la opción no se ofrece para otros módulos ni compilaciones con presupuestos diferentes. La variable interna `STATICRECOMP_POWERPROS_CACHE_BATCH=1` por sí sola no comprueba el SHA256 de la DLL; no sustituye la comprobación de la herramienta. Se comprobó el rechazo de `-CacheBatch -ProfileFallback` antes de lanzar el runtime. El entorno del hijo se establece según la opción y se restaura el del padre.

## Comprobaciones del código

`tools/check_cache_batch.py` extrae y compila el helper y el sitio real del callback junto con el bucle generado original. Pasaron **8.130 casos diferenciales**: acumuladores entre −270 y 0, contadores cero/uno y valores que cruzan el presupuesto, contador uint32 máximo, direcciones sin alinear y desbordamiento de direcciones. Coinciden la secuencia de invalidaciones, registros modificados, ciclos, siguiente PC, retorno y llegada a `sc`. También pasaron los rechazos de código alterado, memoria inválida, estados incompatibles, perfilado, lockstep y otro módulo.

El invalidator y la entrada de excepción de sistema son sintéticos en esa prueba. No ejecuta por sí sola las estructuras JIT reales, la caché completa ni hardware. Las sesiones de integración siguientes comprueban el runtime completo con snapshots y pantallas; no sustituyen un partido completo.

La compilación Release pasó en `local/analysis/moderngekko-cache-batch-build.log`. La reproducción de los 23 parches coincidió con las fuentes: `runtime-patch-replay-20261009-155916/result.json`. La DLL y sus traducciones permanecen intactas.

`tools/compare_cache_batch_speed.py` exige OFF/ON con mismo ejecutable, DLL, estado, duración, backend, entradas aisladas y opción del planificador; verifica que se haya ejercitado la agrupación, contadores y cierre. Pasaron el cálculo y 24 rechazos de condiciones inválidas en `check_cache_batch_comparison.py`. Las comparaciones generales rechazan agrupación activa para no mezclar esta opción con otros cambios: pasaron 24 rechazos de la comparación de runtime y los 8 anteriores de la comparación del planificador.

## Repetición

```powershell
python tools/check_cache_batch.py
python tools/check_cache_batch_comparison.py
python tools/check_runtime_patches.py
# Mismo estado y opciones; primera prueba sin CacheBatch, segunda con CacheBatch.
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -Screenshot -SnapshotMemory -CaptureIntervalSeconds 10 -LoadState 'ruta\al\estado.sav' -SchedulerIdleSkip
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -Screenshot -SnapshotMemory -CaptureIntervalSeconds 10 -LoadState 'ruta\al\estado.sav' -SchedulerIdleSkip -CacheBatch
python tools/compare_cache_batch_speed.py 'ruta\al\sondeo-OFF' 'ruta\al\sondeo-ON'
```

También se comprueban cierre y REL con las herramientas existentes y se revisan las dos capturas. El perfilado de tiempos debe estar desactivado durante la comparación de velocidad. Una diferencia de avance en una pareja de sesiones no demuestra una ganancia garantizada para otras escenas o el partido completo. No aumenta la cobertura enlazada ni equivale a FPS renderizados.

## Resultado de integración

Dos sesiones consecutivas de 120 segundos restauraron el mismo estado privado del primer out, 0–0 y corredor en primera. Usaron el mismo ejecutable y DLL, Vulkan, entradas físicas aisladas, capturas cada 10 segundos y la opción del planificador activada en ambas. El perfilado estaba desactivado y no se enviaron controles para avanzar el partido. La primera mantuvo CacheBatch OFF y la segunda ON.

| Opción | Sondeo | Ventana de muestras | Fotogramas avanzados | Avance por segundo real | Mediana de velocidad normal |
| --- | --- | ---: | ---: | ---: | ---: |
| OFF | `boot-probe-20261009-160451-166` | 110.054 s | 1680 | 15.265 | 25.08% |
| ON | `boot-probe-20261009-160808-020` | 110.123 s | 1777 | 16.136 | 27.72% |

La razón observada es `1.057072224965426`: **+5.7% de avance en esta pareja de sesiones**. Es una comparación corta en este equipo y escena; no establece variabilidad estadística ni una ganancia garantizada en el partido completo. No se suma a porcentajes anteriores. La mediana con la opción activada fue 27.72% de velocidad normal: sigue faltando rendimiento jugable.

La opción se ejercitó en **141237 lotes** y ejecutó **9796932 líneas adicionales** dentro de esos callbacks. Se evitó invocar por separado el callback para esas operaciones, conservando cada invalidación. El contador de callbacks incluye las llamadas realmente efectuadas, no las líneas adicionales. En la sesión OFF ambos contadores nuevos fueron cero. Los totales incluyen inicio, restauración y apagado; no atribuyen tiempo de CPU.

Ambas sesiones terminaron con salida 0, sin terminación forzada, órdenes fallidas ni fallos de verificación de código, con snapshots MEM1/MEM2 completos. Pasaron las comprobaciones de cierre y coincidieron los 200.212 campos de reubicación y los 7.820.936 bytes de código REL. Se revisaron ambas imágenes: escena de lanzamiento, 0–0, un out y corredor en primera. La captura de memoria no equivale a validación de todo el comportamiento nativo.

Ejecutable SHA256: `b20245b6082cf52aaf1249c4167001a053a1b6529db631d07b56639287051ab4`. La DLL conserva el SHA256 indicado anteriormente. Evidencia privada: `local/analysis/cache-batch-speed-comparison.json` y `local/analysis/cache-batch-validation.json`. La segunda conserva los casos diferenciales, resultados y hashes de capturas revisadas.

La opción queda experimental y desactivada por defecto. Continúan 552 bloques y 9.021.384 bytes enlazados, con apoyo del intérprete/JIT. Un arranque fresco con CacheBatch, más escenas, audio, bateo y defensa del jugador, partido completo y ejecución exclusivamente nativa siguen pendientes.
