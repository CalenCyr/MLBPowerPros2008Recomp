# Hilo GPU separado (dual core) y coste gráfico

Fecha: 9 de octubre de 2026. Serie de **29 parches reproducibles**.

## Observación

El Dolphin fijado define `DEFAULT_CPU_THREAD = false` en escritorio, y el runtime no cambia ese valor. El código traducido, el core y el backend Vulkan corren en un único `CPU-GPU thread`.

El muestreo `host-sample-20261009-193251-398` (3.251 posiciones, ejecutable con la búsqueda REL sin heap) se tomó junto al sondeo `boot-probe-20261009-233205-725`, que queda excluido de las comparaciones. `tools/sample_host_thread.cpp` guarda ahora `stacks.csv`: hasta ocho valores de la pila que caen dentro del ejecutable, cerca de RSP. Son pistas de llamador y pueden incluir entradas antiguas. Con el mapa del mismo ejecutable:

| Ruta de espera (pista de pila) | Muestras |
|---|---:|
| `Vulkan::StreamBuffer::WaitForClearSpace` → `WaitForFenceCounter` → `WaitForCommandBufferCompletion` | 8,52% |
| `CommandBufferManager::CreateDescriptorPool` ← `AllocateDescriptorSet` | ~2,8% |

`RtlAllocateHeap` cayó al 0,09% (antes 4,19%), lo que confirma el cambio de `docs/rel-refresh-scratch-report.md`. La DLL ocupa el 53,9% de las muestras y el ejecutable el 25,6%.

## Límite sin gráficos

`boot-probe-20261009-233526-219`, con backend `Null` y las demás condiciones iguales, avanzó **38,01 fotogramas/s** (mediana 64,9% de velocidad normal). Con Vulkan en single core se observaron 32,4–33,2. Si el trabajo gráfico costara cero, el avance subiría como mucho alrededor de 15%. El límite principal sigue siendo la ejecución de CPU. La sesión `Null` sirve como cota, no como comparación válida de velocidad.

## Opción experimental `-DualCore`

`tools/probe-boot.ps1` escribe siempre `[Core] CPUThread` en el perfil privado: `False` por defecto y `True` con `-DualCore`. Lockstep rechaza la opción. `recompcore-dual-core-diagnostic.patch` imprime `CPU thread dual_core=0|1` desde Dolphin, y el resultado registra `dual_core_requested` y `dual_core_confirmed`. Los comparadores generales rechazan sesiones con dual core. `tools/compare_dual_core_speed.py` exige mismo ejecutable, DLL, estado y opciones, más la confirmación del modo en stderr.

| Pareja | Modo | Sondeo | Fotogramas / s real | Mediana de velocidad normal |
|---|---|---|---:|---:|
| 1 | Single | `boot-probe-20261009-231739-668` | 32,41 | 55,27% |
| 1 | Dual | `boot-probe-20261009-232000-296` | 33,54 | 60,99% |
| 2 | Dual | `boot-probe-20261009-232258-838` | 35,86 | 66,17% |
| 2 | Single | `boot-probe-20261009-232518-543` | 32,94 | 55,05% |

Cocientes: **+3,51% y +8,85%**. Evidencia: `local/analysis/dual-core-speed-comparison-20261009-232247-452368.json` y `-232741-565557.json`. Las cuatro sesiones cerraron con salida 0, sin órdenes fallidas, con MEM1/MEM2 completas y coincidencia de los 200.212 campos de reubicación y del código REL. Se revisaron capturas de la sesión dual core: primer inning, 0–0, un out, sin defectos visibles.

La variación entre parejas es grande y el modo dual core hace que la temporización CPU/GPU no sea determinista. La opción queda **desactivada por defecto**. No se ejecutó auditoría lockstep en este modo, que la rechaza. Son mediciones cortas de avance de fotogramas en una escena; no son FPS renderizados ni rendimiento del partido completo.

## Siguiente paso

La DLL concentra la mayor parte del tiempo, pero sus símbolos corresponden a bloques C de 0x4000 bytes PPC. Se está compilando una variante con `-gline-tables-only` para atribuir muestras a direcciones PPC mediante los comentarios por instrucción del C generado, después de verificar que `.text` sea idéntico a la DLL medida.

## Con el módulo todo LLVM (10 de octubre, 34 parches)

Mismo estado y opciones, DLL `runtime-module-llvm-all`, comparador `tools/compare_dual_core_speed.py`. Con la CPU más rápida, la espera de GPU pesa más en el hilo único: ~12% de las muestras en `StreamBuffer::WaitForClearSpace`, con IR 3x.

| Pareja | Modo | Sondeo | Fotogramas / s real |
|---|---|---|---:|
| 1 | Single | `boot-probe-20261010-164428-651` | 44,20 |
| 1 | Dual | `boot-probe-20261010-164648-926` | 50,76 |
| 2 | Dual | `boot-probe-20261010-164909-802` | 48,84 |
| 2 | Single | `boot-probe-20261010-165130-682` | 44,71 |

Cocientes: **+14,85% y +9,22%** (`dual-core-speed-comparison-20261010-165358-*.json`). Las cuatro sesiones cerraron con salida 0. Las sesiones dual confirman `dual_core=1`, `fallback=0` y `smc_failed=0`. La captura dual muestra la misma escena sin defectos.

Sigue **desactivada por defecto**, por la temporización no determinista y porque el lockstep la rechaza.
