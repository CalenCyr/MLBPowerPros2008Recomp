# Búsqueda REL sin asignaciones de heap

Fecha: 9 de octubre de 2026. Serie de **28 parches reproducibles**.

## Coste identificado

El muestreo `host-sample-20261009-195501-387` (3.100 posiciones del hilo CPU-GPU) se resolvió contra las tablas de exportación de las DLL del sistema. `RtlAllocateHeap` y `RtlFreeHeap` sumaron **5,8%** de las muestras; las operaciones de `std::vector<ActiveRelSection>` y `RefreshRelSections` añadieron cerca de 1,9%. Son fracciones de muestras de un hilo, no costes exclusivos.

Causa en el código: `OnICacheInvalidate` llama a `ResolveNativeAddress` para cada línea de caché invalidada. Las direcciones de datos no están en el REL activo ni en un bloque DOL, así que cada una ejecuta `RefreshRelSections`, que creaba dos vectores locales en el heap en cada llamada.

## Cambio

`tools/patches/recompcore-rel-refresh-scratch.patch` sustituye los dos vectores locales por buffers miembro que conservan su capacidad (`clear()` + `swap()`). El recorrido, las comprobaciones, la detección de cambios y el reinicio de bloques REL son los mismos. El C generado y la DLL no cambian.

`tools/probe-boot.ps1` abre ahora `$process.Handle` tras iniciar el proceso: en Windows PowerShell 5.1, sin eso, `exit_code` quedaba nulo y los comparadores rechazaban sesiones que habían cerrado correctamente.

## Pruebas

- Reproducción completa de 28 parches: `runtime-patch-replay-20261009-215808`.
- `tools/check_rel_detector.py`, en modo dinámico y con `--fixed-layout`: todas las comprobaciones pasaron (incluyen varias llamadas sucesivas a `RefreshRelSections`, descarga, recarga y cambio de posición). Se añadieron los dos miembros al fixture.
- Las cuatro sesiones de medición cerraron con salida 0, sin órdenes fallidas ni fallos de verificación de código, con MEM1/MEM2 completas. En las cuatro coincidieron los 200.212 campos de reubicación y los bytes de código REL.
- Capturas finales de las candidatas revisadas: primer inning, 0–0, un out, misma escena.

No se ejecutó una auditoría lockstep: el cambio está en el runtime anfitrión y no altera el código traducido. La auditoría anterior sigue siendo la referencia de las rutas comprobadas.

## Comparación de velocidad

Dos parejas de 120 s desde el estado del primer out: Vulkan, DLL Clang DOL / MSVC REL sin cambios (`09296c1d…`), scheduler acelerado y omisión de hooks con cero mods. Referencia: ejecutable anterior (`40353ecb…`, conservado como `moderngekko-run-before-rel-scratch.exe`). Candidata: `012075d8…`. La segunda pareja invierte el orden.

| Pareja | Ejecutable | Sondeo | Fotogramas del juego / s real | Mediana de velocidad normal |
|---|---|---|---:|---:|
| 1 | Referencia | `boot-probe-20261009-220417-442` | 29,98 | 51,60% |
| 1 | Candidata | `boot-probe-20261009-220638-390` | 33,17 | 53,47% |
| 2 | Candidata | `boot-probe-20261009-220909-666` | 33,21 | 56,87% |
| 2 | Referencia | `boot-probe-20261009-221129-513` | 29,98 | 50,27% |

Cocientes: **+10,63% y +10,78%**. Comparaciones en `local/analysis/rel-refresh-scratch-pair1.json` y `rel-refresh-scratch-pair2.json`, generadas por `tools/compare_runtime_probe_speed.py --allow-empty-mod-hooks`.

Son dos parejas cortas en una escena y un equipo; miden avance del contador de fotogramas, no FPS renderizados. No se suman a ganancias anteriores. La cobertura sigue en 552 bloques y se mantiene el apoyo del intérprete/JIT.

## Siguiente coste

En el mismo muestreo, `ZwWaitForMultipleObjects` (6,8%) y `NtGdiDdDDIWaitForSynchronizationObjectFromCpu` (1,8%) muestran el hilo CPU-GPU esperando a la GPU. Además, CPU y GPU comparten hilo. Es el siguiente candidato que hay que medir.
