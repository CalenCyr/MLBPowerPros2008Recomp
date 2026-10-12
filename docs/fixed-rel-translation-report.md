# Conversión de direcciones REL — 9 de octubre de 2026

El parche `recompcore-fixed-rel-translation.patch` simplifica la conversión de direcciones del código enlazado a direcciones del juego cuando el runtime se compila con `STATICRECOMP_REQUIRE_FIXED_REL_LAYOUT`.

El detector ya exige que las seis secciones del REL estén en sus posiciones enlazadas. En esa configuración, la conversión siempre devuelve la dirección recibida, tanto dentro como fuera del REL. Se elimina el recorrido de las secciones en `ResolveRuntimeAddress`; las compilaciones con posiciones dinámicas conservan ese recorrido. La verificación de pertenencia al código ejecutable en `ResolveNativeAddress`, la detección de secciones, sus hashes y la invalidación de caché conservan su implementación.

El cambio afecta una conversión usada por los despachos y callbacks del runtime. No añade bloques traducidos ni funciones decompiladas. La DLL del juego conserva SHA256 `393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6`.

## Comprobaciones

`check_rel_detector.py` compila los métodos reales extraídos del runtime, incluyendo ahora `TranslateRelAddress`. Ambas variantes, dinámica y fija, pasaron con la captura privada del menú `boot-probe-20261009-040052-798`:

- Las seis secciones, incluyendo BSS, y las conversiones de inicio y último byte.
- Direcciones inmediatamente anteriores y posteriores, huecos, DOL, MEM2 y extremos de 32 bits.
- Descarga del mapa y conversión de vuelta a identidad.
- Estabilidad del mapa y reinicio de verificación exclusivo de los bloques REL.
- Rechazo de tamaños, tablas, versiones y metadatos inválidos.
- La variante fija rechaza código o BSS desplazados; la dinámica acepta la tabla relativa anterior a OSLink.

Evidencia privada: `local/analysis/rel-detector-checks.json` y `rel-detector-checks-fixed.json`. Son pruebas del detector y conversión; no ejecutan las instrucciones del juego.

La serie completa de 18 parches pasó sobre las revisiones fijadas y coincide con las fuentes compiladas: `runtime-patch-replay-20261009-042350`. La compilación incremental pasó en `moderngekko-fixed-rel-translation-build.log`. El proyecto Release confirma la definición de posiciones fijas. El ejecutable nuevo tiene SHA256 `3a3c28a78a3d00536b08caaad434abdfde996744603fa448623f59fe870fe8dd`; el anterior, conservado de forma privada, `ff8fc6cbbd2988d03f48c3e993cb7e97d65350892cce02192fe5e24a0b3d5b7b`.

## Comparación de runtime

`compare_runtime_probe_speed.py` compara ejecutables distintos manteniendo iguales la DLL, estado, backend, perfil, duración, frecuencia de captura y opción del planificador. Exige cierre correcto, procedencia SHA256, entradas aisladas, perfilado desactivado y muestras de al menos 30 segundos. Rechaza pruebas terminadas antes de tiempo y verificaciones de código fallidas. `check_runtime_probe_comparison.py` pasó la aritmética, las variantes ON/ON y OFF/OFF y 22 casos de condiciones inválidas.

La comparación mide avance de fotogramas del juego en una pantalla concreta. No mide FPS renderizados ni tiempo de CPU atribuible a esta función. Las diferencias pequeñas pueden depender de variación entre sesiones y no prueban una mejora reproducible. El planificador experimental permanece desactivado por defecto; se mantuvo activado por igual en estas dos pruebas.

## Resultado de las pruebas reales

Dos sesiones consecutivas de 120 segundos restauraron el mismo estado del primer out, con marcador 0–0, Vulkan, DLL optimizada, entradas físicas aisladas y capturas cada 10 segundos. El perfilado estuvo desactivado. La compilación ocurrió entre las sesiones; no se ejecutó durante ninguna medición.

| Runtime | Sondeo | Ventana medida | Fotogramas avanzados | Avance por segundo real | Mediana de velocidad normal |
| --- | --- | ---: | ---: | ---: | ---: |
| Anterior, 17 parches | `boot-probe-20261009-042023-549` | 110,042 s | 1.847 | 16,784 | 28,63% |
| Nuevo, 18 parches | `boot-probe-20261009-042340-490` | 110,306 s | 1.878 | 17,025 | 29,17% |

La razón observada fue `1.0143547415009526`, aproximadamente **+1,4%**. Una sola comparación con una diferencia pequeña no permite distinguir el efecto del cambio de la variación del equipo. **No se considera una mejora de rendimiento concluyente.** Se conserva la simplificación porque elimina una búsqueda cuya respuesta está garantizada por el detector de posiciones fijas, con pruebas de ambas configuraciones aprobadas. No se suman estos porcentajes a los del planificador o la DLL.

Ambas sesiones cerraron con salida 0, sin terminación forzada, órdenes fallidas ni verificaciones de código fallidas, con MEM1/MEM2 completos. Pasó `check_probe_shutdown.py` en ambas. Los 200.212 campos de reubicación y los 7.820.936 bytes de código REL coincidieron con la referencia en las dos capturas. Las imágenes finales se revisaron visualmente: pantalla de lanzamiento, 0–0, un out y corredor en primera. No se enviaron controles para avanzar el partido.

Contadores del runtime nuevo: 354.330.442 despachos nativos, 23.121.981 callbacks de instrucciones, 418.646 invocaciones JIT, 296.840 excepciones nativas y 1.381.892 esperas omitidas por la opción experimental del planificador. Abarcan también inicio, restauración y apagado; no atribuyen tiempo de CPU al cambio de conversión.

Evidencia privada: `local/analysis/rel-identity-runtime-speed-comparison.json`, los resultados y capturas de ambos sondeos, y `local/analysis/rel-identity-validation.json`. La ejecución sigue necesitando apoyo del runtime y está lejos de la velocidad normal en esta escena. Rendimiento jugable, un partido completo y arranque exclusivamente nativo permanecen pendientes.

Para reproducir la comparación de los resultados guardados:

```powershell
python tools/compare_runtime_probe_speed.py local/analysis/boot-probe-20261009-042023-549 local/analysis/boot-probe-20261009-042340-490
python tools/check_runtime_probe_comparison.py
python tools/check_rel_detector.py local/analysis/boot-probe-20261009-042340-490 --fixed-layout
python tools/check_rel_detector.py local/analysis/boot-probe-20261009-042340-490
python tools/check_runtime_patches.py
```
