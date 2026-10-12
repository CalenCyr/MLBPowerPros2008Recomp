# Localizar el tiempo dentro del módulo — 9 de octubre de 2026

El parche `recompcore-dispatch-timing-sites.patch` amplía la medición del despacho con su dirección de entrada runtime. La serie alcanza **22 parches reproducibles: 15 del core y 7 del frontend**. Esta tanda aporta localización del tiempo muestreado, sin atribuirle una mejora de velocidad ni aumentar la cobertura enlazada.

La opción existente `-ProfileDispatchTiming` produce el CSV de tres etapas y un archivo complementario `dispatch-timing.csv.sites.csv`. No cambia el periodo: una muestra cada 4.096 despachos en cada contexto, dentro o fuera del intervalo que contiene las secciones REL. El archivo complementario agrupa las mismas muestras de la etapa de ejecución del módulo por contexto y dirección de entrada. El módulo incluye los callbacks que ejecute; esa dirección puede estar dentro de una función y no identifica por sí sola el comienzo ni el coste exclusivo de una función.

El registro conserva hasta 4.096 parejas de contexto/dirección. Al alcanzar el límite sigue actualizando direcciones conocidas y contabiliza las muestras nuevas, tiempo total y máximo como descartados en cada contexto. La acumulación por dirección ocurre después de medir la ejecución; no queda incluida en el intervalo del módulo. El diagnóstico sigue desactivado por defecto. Solo las muestras activadas realizan esta búsqueda y posibles asignaciones de memoria; los archivos se escriben al cerrar. El límite controla entradas, no garantiza un tamaño exacto en bytes del contenedor.

`tools/analyze_dispatch_sites.py` comprueba formato, duplicados, alineación, valores uint64, máximos, límite de entradas y sumas por contexto. Las muestras, tiempos y máximos deben coincidir exactamente con la etapa del módulo del informe anterior, incluidos los descartados. Ordena por tiempo crudo acumulado y añade comentarios del código generado a las 25 primeras direcciones. Los comentarios ayudan a localizar el código y no validan su comportamiento ni asignan nombres originales a las funciones.

Los tiempos son intervalos transcurridos, con callbacks, coste del reloj y pausas del sistema. El muestreo periódico puede favorecer unas rutas y omitir otras. Incluye preparación, restauración y apagado. La lista no representa todo el tiempo de CPU, FPS, rendimiento de un partido, coste exclusivo de funciones o porcentaje de finalización. Las comparaciones de velocidad siguen rechazando pruebas con medición activada.

## Pruebas de implementación

`check_dispatch_timing.py` compila el helper y fragmento de despacho reales con un módulo y conversiones sintéticos. Conserva los casos anteriores y añade correspondencia de muestras por dirección runtime, sumas con la etapa del módulo, límite de 4.096 entradas, descarte separado, actualización de una entrada conocida con el contenedor lleno y rechazo de contexto inválido. Comprueba fallo de escritura del archivo complementario aunque el CSV principal se haya podido guardar. No sustituye la ejecución real del juego ni la resolución real del REL.

`check_dispatch_sites.py` comprueba aritmética, ordenación, contabilización de descartados y 16 rechazos de perfiles corruptos. La compilación Release del runtime pasó en `local/analysis/moderngekko-dispatch-sites-build.log`; la reproducción de 22 parches coincide con las fuentes en `runtime-patch-replay-20261009-153925/result.json`. Se conserva la DLL optimizada y todo el código generado. El juego continúa utilizando intérprete/JIT de apoyo.

## Repetición

```powershell
python tools/check_dispatch_timing.py
python tools/check_dispatch_sites.py
python tools/check_runtime_patches.py
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -Screenshot -SnapshotMemory -CaptureIntervalSeconds 10 -LoadState 'ruta\al\estado.sav' -SchedulerIdleSkip -ProfileDispatchTiming
python tools/analyze_dispatch_sites.py 'ruta\al\nuevo-sondeo'
python tools/check_probe_shutdown.py 'ruta\al\nuevo-sondeo'
python tools/inspect_runtime_rel.py 'ruta\al\nuevo-sondeo'
python tools/validate_runtime_relocations.py 'ruta\al\nuevo-sondeo'
```

Hay que revisar también las capturas finales. Para una comparación de velocidad se utilizan sondeos separados con medición desactivada y condiciones iguales. La opción del planificador sigue desactivada por defecto.

## Resultado observado

`boot-probe-20261009-154149-251` ejecutó 120.44 segundos desde el estado del primer out, con Vulkan, módulo optimizado, entrada aislada, planificador experimental activado y sin enviar controles de juego. Se registraron **3096 direcciones** y **73501 muestras de la etapa del módulo**, sin descartados. Las sumas y máximos coinciden con el CSV de etapas y sus despachos observados con el contador de cierre. El módulo acumuló 26121500 ns crudos muestreados; esa suma incluye el coste del reloj y no es el tiempo total de ejecución del juego.

| Dirección de entrada runtime | Muestras | Media cruda | Fracción del tiempo del módulo muestreado |
| --- | ---: | ---: | ---: |
| `0x800C1188` | 959 | 1132.43 ns | 4.16% |
| `0x800BC468` | 222 | 4477.03 ns | 3.80% |
| `0x80126C28` | 1256 | 526.43 ns | 2.53% |

Se revisaron los fragmentos generados de las dos primeras entradas. `0x800C1188` incrementa los índices de un bucle y puede ejecutar más código hasta devolver al despachador. `0x800BC468` entra en una ruta que prepara registros y usa memoria y operaciones de coma flotante. Las instrucciones de esas direcciones son solo el comienzo del intervalo medido: las medias no son el coste de `addi` ni de `or`.

También aparecen las entradas `0x8009C488` y `0x8009C4A8`: 33 y 12 muestras respectivamente, juntas alrededor del 4,03% del tiempo del módulo muestreado. El código contiene un bucle `dcbf` que avanza 32 bytes y termina con `sc`; es un candidato para estudiar una ruta nativa que conserve caché, excepciones y presupuesto de ciclos. La evidencia es limitada y todavía no se ha reemplazado esa rutina. No se atribuye un coste exclusivo a toda la función.

Una entrada, `0x801298A0`, acumuló 474.500 ns, de los que 451.100 ns corresponden a su muestra máxima: aproximadamente el 95%. Su posición en la lista está dominada por un único intervalo largo; no basta para priorizarla como cuello de botella. El resto de la lista tampoco permite concluir cuál es la función más costosa sin agrupar rutas y repetir mediciones.

La calibración del par de consultas al reloj fue 21.87 ns. Los porcentajes de fases y direcciones conservan el alcance parcial explicado arriba. No se compara la velocidad de este sondeo con uno sin medición.

## Integración observada

La prueba con perfilado cerró con salida 0, sin terminación forzada, órdenes fallidas ni fallos de verificación de código. La imagen revisada conserva lanzamiento, 0–0, un out y corredor en primera. `boot-probe-20261009-154454-373` comprobó el menú durante 60.02 segundos con medición y planificador desactivados. Cerró correctamente y la captura conserva Exhibition seleccionado. No produjo ninguno de los dos CSV de tiempos. Ambas pruebas tienen memoria completa y coinciden en los 200.212 campos de reubicación y los 7.820.936 bytes de código REL.

Ejecutable SHA256: `af951a20cff530877ea3f3f60b4b9a3ca601c46cf1954b2330d08280ba3c59d5`. DLL sin cambios: `393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6`. CSV por direcciones SHA256: `9af87e8021174fba310518cfddf8bf6addf4bb326ecbb4eeb528c4d426bf50ba`. Evidencia consolidada privada: `local/analysis/dispatch-sites-validation.json`; informe completo: `local/analysis/boot-probe-20261009-154149-251/dispatch-sites-report.json`.

Siguen pendientes rendimiento jugable, audio, bateo y defensa del jugador, partido completo y ejecución exclusivamente nativa. Se mantienen 552 bloques y 9.021.384 bytes enlazados experimentalmente.
