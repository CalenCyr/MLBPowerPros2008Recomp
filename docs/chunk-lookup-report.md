# Reutilizar la búsqueda de bloques — 9 de octubre de 2026

El parche `recompcore-fixed-chunk-lookup.patch` simplifica `ChunkIndexOf` cuando el runtime exige posiciones REL fijas. Calcula una vez el índice del bloque y lo reutiliza: un bloque DOL puede devolver directamente ese resultado, y un bloque REL conserva la comprobación de pertenencia al mapa activo y el redescubrimiento cuando corresponda.

Esto es válido porque el detector de posiciones fijas acepta únicamente secciones cuya dirección runtime coincide con su dirección enlazada. La búsqueda posterior a la conversión da el mismo índice. El redescubrimiento cambia secciones y estados de verificación, pero no modifica la tabla de bloques enlazados. Para posiciones dinámicas se conserva el método anterior, incluyendo la precedencia del REL sobre una entrada DOL solapada.

La inicialización del mapa, los hashes, la invalidación de caché, `DispatchableAt` y `FastDispatchableAt` conservan su implementación. Reutilizar el índice no permite despachar bloques no verificados, fallidos, de un módulo inactivo o sujetos a fallback obligatorio. Una entrada de bloque REL por sí sola tampoco permite ejecutar un módulo descargado. No se tocaron instrucciones generadas ni se aumentó la cobertura de 552 bloques y 9.021.384 bytes enlazados experimentalmente.

## Pruebas del código real

`check_rel_detector.py` extrae y compila ahora `ChunkIndexOf`, `FastDispatchableAt` e `IsForcedFallbackAddress`, además del detector y métodos de resolución. Pasaron ambas configuraciones con el snapshot privado `boot-probe-20261009-045301-227`:

- Índices DOL, MEM2 y REL; se conserva la interpretación existente de direcciones no alineadas dentro de la misma instrucción.
- Bloque REL verificado aceptado y bloques DOL/REL no verificados o fallidos rechazados por el guard rápido.
- Fallback obligatorio y extremo superior exclusivo de su intervalo.
- Módulo inactivo, tabla vacía y direcciones sin bloque rechazados.
- Un lookup DOL solapado con REL conserva los resultados de cada configuración, incluida la conversión dinámica.
- REL descargado rechazado aunque se marque su entrada como verificada; DOL sigue disponible.
- Recarga del REL redescubierta y estado de verificación restablecido a no verificado.
- Se mantienen las pruebas anteriores de secciones, límites, huecos, descarga, posiciones desplazadas y metadatos inválidos.

Estas pruebas usan los métodos reales y un estado mínimo. Los casos de verificación alteran su estado de forma controlada: prueban el guard de despacho, no el algoritmo de hashing ni la ejecución de código alterado. La integración real que sigue comprueba los hashes y snapshots válidos. No se ejecutó una suite general del runtime ni un partido completo.

La compilación incremental pasó en `local/analysis/moderngekko-chunk-lookup-build.log`. La reproducción de los 20 parches coincide con las fuentes compiladas: `runtime-patch-replay-20261009-050500`.

Ejecutable anterior: SHA256 `52a861969f433a5d3ddc8fc8e8126ad9f9242d327c12e84b6a97935d230fb7c5`. Nuevo: `82e5d73d838b01a17c037e27d6c89b5af303bca671f99dfa452404fe13ee71fc`. La DLL optimizada conserva SHA256 `393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6`.

## Comparación corta e integración

Dos sesiones consecutivas de 120 segundos restauraron el mismo estado privado del primer out, 0–0, con corredor en primera. Ambas usaron Vulkan, la DLL optimizada, entradas físicas aisladas, capturas cada 10 segundos y perfilado desactivado. La opción experimental del planificador estuvo activada por igual; conserva su valor desactivado por defecto. La compilación se realizó entre las sesiones.

| Runtime | Sondeo | Ventana medida | Fotogramas avanzados | Avance por segundo real | Mediana de velocidad normal |
| --- | --- | ---: | ---: | ---: | ---: |
| Anterior, 19 parches | `boot-probe-20261009-050020-915` | 110,338 s | 1.904 | 17,256 | 28,93% |
| Nuevo, 20 parches | `boot-probe-20261009-050451-248` | 110,024 s | 2.002 | 18,196 | 30,39% |

La razón observada fue `1.0544777727962733`: **+5,4% de avance de fotogramas en esta comparación**. Una única pareja de sesiones no establece cuánto corresponde al cambio frente a variaciones del equipo, ni una mejora garantizada en otras escenas. La medida no es FPS renderizados, tiempo de CPU ni rendimiento de un partido completo. No se suma a los porcentajes anteriores. Sigue faltando velocidad jugable.

Ambas pruebas terminaron con salida 0, sin terminación forzada, órdenes fallidas ni verificaciones de código fallidas, con MEM1/MEM2 completos. Pasó la comprobación de cierre en las dos. Coincidieron los 200.212 campos de reubicación y los 7.820.936 bytes de código REL de ambas capturas. Las imágenes finales se revisaron visualmente y conservaron la escena de lanzamiento, 0–0, un out y corredor en primera. No se enviaron controles para avanzar el inning.

Contadores del runtime nuevo: 380.541.692 despachos nativos, 24.550.838 callbacks de instrucciones, 445.274 invocaciones JIT, 315.621 excepciones nativas y 1.468.827 esperas omitidas por la opción experimental del planificador. Incluyen preparación, restauración y apagado; no atribuyen tiempo de CPU a este cambio. El juego sigue requiriendo apoyo del runtime.

Evidencia privada: `local/analysis/chunk-lookup-runtime-speed-comparison.json` y `local/analysis/chunk-lookup-validation.json`. La segunda conserva los resultados de las pruebas de métodos y hashes de capturas revisadas. El rendimiento jugable, audio, bateo y defensa del jugador, partido completo y ejecución exclusivamente nativa siguen pendientes.

Para repetir las comprobaciones con los datos privados ya existentes:

```powershell
python tools/check_rel_detector.py local/analysis/boot-probe-20261009-050451-248 --fixed-layout
python tools/check_rel_detector.py local/analysis/boot-probe-20261009-050451-248
python tools/check_runtime_patches.py
python tools/compare_runtime_probe_speed.py local/analysis/boot-probe-20261009-050020-915 local/analysis/boot-probe-20261009-050451-248
```
