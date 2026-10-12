# Espera del planificador — 8 de octubre de 2026

Ampliación del 9 de octubre: la opción pasó un arranque fresco hasta la introducción y una comparación automatizada en el menú principal. Esta última registró +14,8% de avance de fotogramas; es otro escenario, separado del +10,8% anterior. La opción permanece desactivada por defecto.

Se implementó una opción experimental para acelerar la espera de la cola vacía del planificador de RL8E54. Una comparación corta desde el mismo estado registró un **10,8% más de avance de fotogramas del juego**. La opción sigue desactivada por defecto; no demuestra rendimiento jugable ni completa el port.

## Identificación y cambio

El inventario local de dtk coloca `0x800A4318` dentro de `SelectThread`, desde `0x800A41CC` y con 552 bytes. La espera lee `r13 - 28144`, compara con cero y vuelve a leer mientras siga vacío. El inicio del DOL fija r13 a `0x80322060`, situando la palabra vigilada en `0x8031B270`. Las escrituras cercanas establecen o eliminan bits `1 << (31 - prioridad)` al manipular las colas; de ahí se infiere que es la máscara de prioridades con tareas listas. Los nombres proceden del inventario local, no de una decompilación completa. La identificación y propietarios de siete escrituras directas están en `local/analysis/scheduler-idle-static-report.json`; no se descartan escrituras indirectas.

El parche `recompcore-scheduler-idle.patch` permite usar `CoreTiming::Idle()` después de un despacho nativo que vuelve a esa espera. Ese servicio existente termina el intervalo hasta el siguiente evento y conserva su sincronización de GPU configurada. El módulo conserva la ejecución del PC y los registros; no se editan las traducciones C ni se cambia el algoritmo del partido.

La ruta exige opción explícita, identidad `RL8E54`, ausencia de lockstep, downcount positivo, PC exacto, interrupciones habilitadas, r13 esperado, ausencia de excepciones, RAM suficiente, máscara vacía y coincidencia de las tres instrucciones (`800D9210`, `2C000000`, `4182FFF8`). Una tarea lista o un código distinto conserva la ejecución ordinaria. El entorno del proceso hijo usa `STATICRECOMP_POWERPROS_SCHEDULER_IDLE=1`; el sondeo lo restaura en el padre y lo desactiva cuando no se solicita.

La serie contiene 17 parches: diez del core y siete del frontend. Reproducción completa aprobada en `runtime-patch-replay-20261009-033741`. La compilación incremental del ejecutable pasó (`moderngekko-scheduler-idle-build.log`). `check_scheduler_idle.py` compiló el guard real y comprobó las condiciones rechazadas, incluidos los 32 bits de prioridades listas y la firma alterada; evidencia `scheduler-idle-check-20261009-033406-191601`.

## Comparación comprobada

Se ejecutaron consecutivamente dos pruebas de 120 segundos, Vulkan, entradas físicas aisladas, misma DLL optimizada, mismo ejecutable, misma pantalla restaurada y capturas cada diez segundos. El perfil de fallback quedó desactivado en ambas. Solo se cambió la opción de espera del planificador.

| Medida | Desactivada | Activada |
| --- | ---: | ---: |
| Sondeo | `033518-880` | `033758-565` |
| Ventana útil entre muestras | 109,758 s | 110,187 s |
| Fotogramas del juego avanzados | 1.653 | 1.839 |
| Avance de fotogramas por segundo real | 15,0604 | 16,6898 |
| Mediana de velocidad informada | 24,8717% | 28,4946% |
| Esperas aceleradas, sesión completa | 0 | 1.352.549 |

Los identificadores completos son `boot-probe-20261009-033518-880` y `boot-probe-20261009-033758-565`. El cociente de avance es `1,10819001062576`, aproximadamente +10,8%. La diferencia de medianas es otra medida y no se utiliza para calcular ese cociente.

Ambas sesiones restauraron visualmente la pantalla 0–0, un out y corredor en primera. Terminaron con salida 0, sin cierre forzado, órdenes fallidas ni verificaciones de código fallidas; MEM1/MEM2 completas. Pasaron `check_probe_shutdown.py`, la comparación de 200.212 campos de reubicación y los 7.820.936 bytes del código REL.

`compare_scheduler_probe_speed.py` comprueba ejecutable, módulo, estado, backend, perfil, duración solicitada, cadencia de capturas, ausencia de entrada interactiva y contadores que demuestran que la opción fue ejercitada. `check_scheduler_probe_comparison.py` aprobó la aritmética y ocho rechazos de condiciones incompatibles. La comparación antigua de DLL ahora también rechaza cambios en ejecutable, diagnóstico o esta opción cuando esos campos están registrados; pasan sus comprobaciones actualizadas.

Evidencia: `local/analysis/scheduler-speed-comparison-20261009-034049-930807.json`. Ejecutable SHA256 `ff8fc6cbbd2988d03f48c3e993cb7e97d65350892cce02192fe5e24a0b3d5b7b`; DLL SHA256 `393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6`; estado SHA256 `5158bc08a5e58986bf5313277e0676b4cad0b77cecacbdf442313f67020eed14`.

## Límites y reproducción

### Arranque fresco y menú — 9 de octubre de 2026

`boot-probe-20261009-035405-536` ejecutó 120,41 segundos desde cero, sin `LoadState`, con Vulkan y el mismo ejecutable/DLL. La captura final muestra la secuencia de introducción animada. Cerró con salida 0, sin terminación forzada, órdenes fallidas ni fallos de verificación, con MEM1/MEM2 completas. Se registraron 4.527.394 esperas aceleradas. Coincidieron los 200.212 campos de reubicación y los 7.820.936 bytes del REL. Esto amplía la validación del puente de diagnóstico durante el arranque; sigue utilizando callbacks y JIT, y no demuestra arranque exclusivamente nativo ni entrada al partido desde cero.

La nueva herramienta `tools/benchmark-scheduler.ps1` ejecuta secuencialmente una referencia y una variante activada por cada estado privado solicitado. Comprueba previamente todos los estados, rechaza un runtime simultáneo, verifica el cierre y el REL, y compara condiciones equivalentes. Guarda el progreso, los directorios de sondeo, resultados o errores y una marca separada de revisión visual. El sondeo ofrece ahora `-PassThru` para devolver un resultado estructurado; su salida habitual se conserva. `compare_scheduler_probe_speed.py --output` permite guardar el informe en el lote y rechaza sobrescribir informes existentes.

El lote `scheduler-benchmark-20261009-035857-929` pasó una comparación de 90 segundos por variante desde `menu-state.sav`, SHA256 `049c95362219a74f0c099791a683cce4f1c494ecaa1515613d4b2095f9ff8beb`. No envió controles. Ambas capturas finales fueron inspeccionadas: menú principal, Exhibition seleccionado. La revisión quedó registrada con los hashes de las imágenes en `result.json` del lote.

| Medida del menú principal | Desactivada | Activada |
| --- | ---: | ---: |
| Sondeo | `035859-157` | `040052-798` |
| Ventana útil | 80,114 s | 80,120 s |
| Fotogramas avanzados | 1.381 | 1.586 |
| Avance por segundo real | 17,2380 | 19,7954 |
| Mediana de velocidad informada | 29,2194% | 34,8949% |
| Esperas aceleradas, sesión completa | 0 | 1.248.212 |

El cociente es `1,148355111711987`, aproximadamente +14,8%. Ambas sesiones terminaron con salida 0, sin órdenes fallidas, cierre forzado ni fallos de verificación. Los snapshots están completos y el REL coincide. El lote comprueba SHA256 de ejecutable, módulo y estado, backend, perfil, duración solicitada y cadencia. Sigue siendo un único par consecutivo para esa pantalla, con la referencia ejecutada primero; no es una estimación estadística del rendimiento de todo el juego. El resultado del menú no reemplaza ni se suma al del partido.

Se comprobaron el parser de ambos scripts PowerShell, las ocho condiciones incompatibles de la comparación, el rechazo de otro lote con runtime activo y la validación de todos los estados antes de iniciar un lote. Una solicitud con un estado válido y otro inexistente no creó un lote parcial ni lanzó el runtime. También se comprobó que `--output` rechaza un informe existente sin cambiar su SHA256. Evidencias privadas: `scheduler-benchmark-preflight-check.json`, `scheduler-benchmark-missing-state-check.json` y `scheduler-report-preservation-check.json`.

Ejemplo para repetir una comparación automatizada:

```powershell
.\tools\benchmark-scheduler.ps1 -Seconds 90 -Python 'ruta\a\python.exe' -LoadState 'ruta\al\estado.sav'
```

Admite entre uno y ocho estados y 60–300 segundos por variante. Su estado `complete` indica comprobaciones automáticas terminadas; las imágenes requieren revisión visual independiente. No envía controles para avanzar el partido. Se conservaron los 17 parches y el mismo ejecutable/DLL; no se recompilaron fuentes sin cambios ni se repitieron las referencias de CPU sin una razón nueva.

`boot-probe-20261009-034107-302` restauró el estado Colorado 5–Boston 0 con dos outs y abrió el menú de pausa mediante +. Las capturas periódicas muestran el menú, pero la captura específica solicitada no se guardó al coincidir con ellas. La orden procesada por sí sola no prueba que exista su imagen.

La secuencia automática posterior `boot-probe-20261009-034348-403` duró 60,44 segundos, sin capturas periódicas. Neutral → + → neutral abrió pausa con PLAY seleccionado; A → neutral regresó al campo, conservando 5–0 y dos outs. Se inspeccionaron `scheduler-pause.png` y `scheduler-resume.png`. Las nueve órdenes de la secuencia fueron procesadas, sin pendientes ni fallidas. La sesión aceleró 918.781 esperas y terminó con salida 0, sin cierre forzado, MEM1/MEM2 completas y código REL coincidente. La sesión previa de 90 segundos también pasó cierre y comparación REL. Estas pruebas comprueban esa respuesta de entrada, sin validar un inning completo. Para capturas específicas encadenadas se usaron intervalos de frames neutros y se desactivaron las capturas periódicas.

Son comparaciones consecutivas de pantallas esperando entrada en este equipo, sin repeticiones estadísticas ni atribución de tiempo de CPU al bucle. No son FPS renderizados ni una medición de todo el partido. Los contadores de sesión incluyen inicio, restauración y apagado. La base mantiene `BUILD_TESTING=OFF`; las comprobaciones cubren el guard específico, la compilación y las integraciones descritas. Continúan pendientes más escenas y transiciones, bateo, defensa, audio, partido completo y ejecución exclusivamente nativa. La cobertura sigue en 552 bloques y 9.021.384 bytes enlazados experimentalmente.

```powershell
Set-Location D:\MLBPowerPros2008Recomp
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -CaptureIntervalSeconds 10 -Screenshot -SnapshotMemory -LoadState 'ruta\al\estado.sav'
# Al terminar la referencia, repetir con el mismo estado y esta única opción adicional:
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -SchedulerIdleSkip -CaptureIntervalSeconds 10 -Screenshot -SnapshotMemory -LoadState 'ruta\al\estado.sav'
python .\tools\compare_scheduler_probe_speed.py <sondeo-desactivado> <sondeo-activado>
python .\tools\check_scheduler_idle.py
python .\tools\check_scheduler_probe_comparison.py
```

Requiere el ejecutable con la serie actual de parches, la DLL optimizada y un estado privado compatible. La opción permanece explícita mientras se amplía su validación.
