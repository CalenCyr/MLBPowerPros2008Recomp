# Descartar búsquedas fuera del REL — 9 de octubre de 2026

El runtime conserva ahora los límites de las secciones REL activas. Una dirección que cae fuera de ese intervalo evita el recorrido de todas las secciones. Este descarte beneficia a las consultas de direcciones del código principal DOL y de otras zonas de memoria. Dentro del intervalo se conserva la búsqueda exacta: los huecos no se aceptan como secciones, y el orden de resolución permanece igual.

El parche `recompcore-rel-bounds.patch` actualiza los límites únicamente cuando cambia el mapa de secciones, junto con su generación e invalidación de verificaciones. La inicialización del core vacía también estos límites. El extremo superior usa 64 bits y es exclusivo. Un mapa vacío rechaza direcciones REL, pero conserva el intento de redescubrimiento antes de devolver un fallo. El lookup de bloques DOL, las comprobaciones de código, la caché de instrucciones y la política de fallback siguen activos.

El cambio es general para mapas fijos o dinámicos. En este juego la DLL experimental continúa exigiendo las seis posiciones REL comprobadas. No se editaron traducciones generadas ni se amplió la cobertura: siguen siendo 552 bloques y 9.021.384 bytes enlazados experimentalmente.

## Comprobaciones del código real

`check_rel_detector.py` extrae y compila ahora también `ResolveNativeAddress` y `GetAddressLookupIndex`, además del detector y la conversión anterior. Las dos configuraciones, fija y dinámica, pasaron con la captura privada `boot-probe-20261009-042340-490`:

- Resolución directa DOL y MEM2; todas las secciones REL en su primer y último byte, con o sin índice de sección solicitado.
- Rechazo de direcciones fuera del intervalo, extremos de 32 bits, direcciones fuera de RAM y huecos entre secciones. Un fallo conserva los valores de salida.
- Redescubrimiento desde un mapa vacío: una entrada de bloque REL por sí sola no permite aceptar una dirección.
- Descarga, rechazo mientras está descargado y recarga del REL.
- Cambios dinámicos que mueven el inicio hacia abajo y el final hacia arriba, más allá del intervalo anterior.
- Conservación de la precedencia de la primera sección en un mapa dinámico con rangos solapados. Esto prueba el comportamiento de resolución existente, sin validar ejecución del juego en ese mapa.
- La configuración fija rechaza código y BSS desplazados. Se mantienen los rechazos de tablas, versiones, tamaños y metadatos inválidos.

Las pruebas aíslan métodos reales con una estructura de estado mínima. No ejecutan las instrucciones REL ni prueban la inicialización completa del core. La actualización de sus miembros pasó la compilación del runtime completo, cuyo registro es `local/analysis/moderngekko-rel-bounds-build.log`. La reproducción de los 19 parches sobre las revisiones fijadas coincide con las fuentes compiladas: `runtime-patch-replay-20261009-045310`.

El ejecutable anterior tiene SHA256 `3a3c28a78a3d00536b08caaad434abdfde996744603fa448623f59fe870fe8dd`; el nuevo, `52a861969f433a5d3ddc8fc8e8126ad9f9242d327c12e84b6a97935d230fb7c5`. La DLL conserva SHA256 `393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6`.

## Comparación corta real

Dos pruebas consecutivas de 120 segundos restauraron el mismo estado del primer out, 0–0, con corredor en primera. Se usaron Vulkan, la misma DLL optimizada, entradas físicas aisladas, capturas cada 10 segundos y perfilado desactivado. La opción experimental del planificador estuvo activada en ambas; permanece desactivada por defecto. La compilación se hizo entre las pruebas, sin coincidir con sus mediciones.

| Runtime | Sondeo | Ventana medida | Fotogramas avanzados | Avance por segundo real | Mediana de velocidad normal |
| --- | --- | ---: | ---: | ---: | ---: |
| Anterior, 18 parches | `boot-probe-20261009-044909-339` | 110,377 s | 1.837 | 16,643 | 28,26% |
| Nuevo, 19 parches | `boot-probe-20261009-045301-227` | 110,051 s | 1.984 | 18,028 | 30,14% |

La razón observada fue `1.0832264047168554`: **+8,3% de avance de fotogramas en esta comparación**. Es una única pareja de sesiones en una pantalla concreta. No mide FPS renderizados, todo el partido ni tiempo de CPU atribuible a la búsqueda. No establece una ganancia garantizada en otras escenas y no se suma a los porcentajes de cambios anteriores. Todavía falta rendimiento jugable.

Ambas sesiones cerraron con salida 0, sin terminación forzada ni órdenes fallidas, con MEM1/MEM2 completos y cero verificaciones de código fallidas. Pasó la comprobación de cierre en las dos. Coincidieron los 200.212 campos de reubicación y los 7.820.936 bytes de código REL de ambas capturas. Se inspeccionaron visualmente las imágenes finales: escena de lanzamiento, marcador 0–0, un out y corredor en primera. No se enviaron controles para avanzar el inning.

Contadores del runtime nuevo: 374.830.961 despachos nativos, 24.336.792 callbacks de instrucciones, 441.301 invocaciones JIT, 312.801 excepciones nativas y 1.455.521 esperas omitidas por la opción experimental del planificador. Estos totales incluyen inicio, restauración y apagado. Se conserva el apoyo JIT y no se ha completado un port exclusivamente nativo.

Evidencia privada: `local/analysis/rel-bounds-runtime-speed-comparison.json` y `local/analysis/rel-bounds-validation.json`. El segundo conserva los resultados de las pruebas del detector junto con hashes de las capturas revisadas. Las comprobaciones de métodos y esta escena no sustituyen una suite general del runtime, un partido completo, validación de audio o controles de bateo y defensa.

## Reproducir

```powershell
python tools/check_rel_detector.py local/analysis/boot-probe-20261009-045301-227 --fixed-layout
python tools/check_rel_detector.py local/analysis/boot-probe-20261009-045301-227
python tools/check_runtime_patches.py
python tools/compare_runtime_probe_speed.py local/analysis/boot-probe-20261009-044909-339 local/analysis/boot-probe-20261009-045301-227
```

Los sondeos y assets son privados y deben existir previamente. El comparador exige las mismas condiciones y ejecutables distintos; no permite comparar esta mejora con una prueba que cambie también la DLL o la opción del planificador.
