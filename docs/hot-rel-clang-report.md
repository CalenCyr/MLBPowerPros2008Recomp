# Cinco bloques REL recompilados con Clang

9 de octubre de 2026. Trabajo en `D:\MLBPowerPros2008Recomp`. Se construyó una DLL privada que conserva el DOL Clang y sustituye cinco objetos REL MSVC por versiones Clang del mismo código generado. Se conserva la versión anterior y la serie activa de 27 parches. La cobertura sigue en 552 bloques enlazados; esto no representa cinco bloques nuevos de cobertura ni un port completo.

## Selección basada en mediciones

El perfil existente `host-sample-20261009-164527-499` contiene 3.294 posiciones del hilo CPU-GPU durante 60,024 s. La DLL ocupa 1.597 muestras (48,48%). Para resolver sus direcciones, `map-clang-module.cmd` enlazó privadamente los 560 objetos existentes y produjo un mapa LLD. Se comprobó que las secciones ejecutables de la DLL privada coinciden byte a byte con la original, además de dirección base, timestamp y disposición. El archivo PE completo tiene otro hash; no se presenta como idéntico. Evidencia: `local/analysis/clang-module-map-20261009-211233-466865/result.json`.

El analizador acepta ahora mapas MSVC y LLD y excluye símbolos de datos, absolutos y límites fuera de secciones ejecutables. Las etiquetas son las más cercanas a la posición muestreada: no delimitan tiempo exclusivo de funciones, especialmente con código integrado y alias. El informe anterior sin resolver queda conservado como `report-unresolved.json`. No se volvió a medir ni se usó el sondeo instrumentado para calcular velocidad.

Los cinco bloques seleccionados sumaron 128 muestras, el 3,89% del total de posiciones. No es el porcentaje completo de coste REL ni una mejora potencial garantizada. Los bloques DOL también concentran muchas muestras y siguen siendo candidatos importantes.

| Bloque REL | Muestras | Entradas comparadas con el intérprete |
|---|---:|---:|
| `chunk_0085_text0_806C9654` | 14 | 2 |
| `chunk_0086_text0_806CD654` | 15 | 3 |
| `chunk_0092_text0_806E5654` | 32 | 102 |
| `chunk_0093_text0_806E9654` | 25 | 43 |
| `chunk_0094_text0_806ED654` | 42 | 26 |

## Construcción y comprobación

`tools/build-hot-rel-clang.cmd` comprueba las fuentes, compilador, DLL de referencia y hashes de los objetos antes de compilar. Usa Clang 22.1.8 con `/O2 /Ob2 /DNDEBUG -MD /bigobj /fp:strict /wd4102`. Conserva los 74 objetos DOL, los helpers y 473 objetos REL MSVC; reemplaza solo cinco de los 560 objetos de enlace. No cambia las fuentes generadas ni relaja el cálculo de coma flotante. El manifiesto registra los objetos nuevos y los conservados.

DLL candidata: `local/analysis/hot-rel-clang-20261009-211914-701572/gRL8E54_recomp.dll`, SHA256 `eea531ea91d5dc1d067b7bbaeb053487691e98184b5c505138c814ba5d7bc217`, 547.662.848 bytes. Referencia: `local/build/runtime-module-rel-clang/gRL8E54_recomp.dll`, SHA256 `09296c1d72e4bb44080572964a1b664f148e2142cf691c04503258596f119357`, 552.097.792 bytes. La candidata ocupa 4.434.944 bytes menos. Ambas conservan el mismo fingerprint de fuentes `29616140c2a31a4fd38b42773aaeca7083f0f8f617832a70e0d4ce3e0a576b71`.

Pasaron 2.352 referencias de memoria DOL y 72 casos independientes de seis funciones REL, sin fallback de instrucciones en esos casos. Estas referencias no cubren completamente los cinco bloques cambiados.

La auditoría separada `boot-probe-20261009-212105-917` completó **3.637 comparaciones con el intérprete sin diferencias**, de 3.675 comprobaciones. Omitió 10 por fallback y 28 por ejecución vacía. Alcanzó 176 entradas dentro de los cinco bloques cambiados, repartidas como indica la tabla. Conservó los tres retornos de bucle exigidos, sin límites alcanzados, infracobros de ciclos ni diferencias notificadas. La ventana solicitada fue de 5 a 6 millones de despachos; terminó en 5.050.634, antes del límite superior. Las rutas omitidas y no visitadas siguen sin validar. No se obtuvo captura gráfica en esta auditoría y no se usa para medir velocidad.

El sondeo de auditoría cerró correctamente y coincidieron los 200.212 campos de reubicación y 7.820.936 bytes de código REL capturados. Es una comprobación de rutas alcanzadas, no equivalencia de todo el juego. Se mantiene el apoyo del intérprete/JIT.

## Comparación de velocidad

Se usan dos parejas de 120 segundos desde el mismo estado del primer out, Vulkan, mismo ejecutable, scheduler acelerado y omisión de consultas al gestor vacío con cero mods. No se activan muestreo, perfiles, auditoría ni agrupación de caché durante las mediciones. La segunda pareja invierte el orden. El comparador verifica la procedencia de los cinco objetos y rechaza condiciones distintas, fuentes modificadas, perfiles, cierres fallidos y sondeos excluidos. Pasaron sus 39 casos de rechazo y los casos de mapas.

| Pareja | DLL | Sondeo | Fotogramas del juego / segundo real | Mediana de velocidad normal |
|---|---|---|---:|---:|
| 1 | Referencia | `boot-probe-20261009-212335-740` | 28.971721 | 51.79% |
| 1 | Candidata | `boot-probe-20261009-212620-696` | 31.376414 | 52.56% |
| 2 | Referencia | `boot-probe-20261009-213222-802` | 29.421086 | 50.27% |
| 2 | Candidata | `boot-probe-20261009-212939-889` | 30.881051 | 51.75% |

Los cocientes fueron **+8,30% y +4,96%**. Se conserva la candidata como **experimento opcional**, sin sustituir la DLL anterior ni cambiar opciones por defecto. Son dos parejas cortas: no establecen una ganancia general o estadísticamente concluyente. La segunda pareja se ejecutó candidata → referencia.

Las cuatro mediciones cerraron correctamente, sin órdenes fallidas ni fallos de verificación, con MEM1/MEM2 completas y coincidencia de código/reubicaciones REL. Se revisaron las cuatro capturas finales: 0–0, primer inning, un out y corredor en primera. La auditoría separada no produjo captura. Consolidado: `local/analysis/hot-rel-clang-validation.json`. Las mediciones corresponden a avance de fotogramas del juego por segundo real en esta escena y este equipo; no son FPS renderizados, porcentaje del port ni una ganancia garantizada para otras escenas.

## Reproducción

Desde la carpeta del proyecto:

```powershell
.\tools\map-clang-module.cmd
.\tools\build-hot-rel-clang.cmd
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -ClangModule -ModulePath 'local/analysis/hot-rel-clang-20261009-211914-701572/gRL8E54_recomp.dll' -SchedulerIdleSkip -SkipEmptyModHooks -LoadState 'local/analysis/boot-probe-20261008-205240-719/control/artifacts/pitch-result-state.sav' -SnapshotMemory -Screenshot -CaptureIntervalSeconds 10
```

El constructor crea una carpeta nueva en cada ejecución; sustituir la ruta por la que devuelva. Para la referencia se omite `-ModulePath`. Las capturas requieren revisión visual, además de cierre y validación REL. `tools/compare_hot_rel_probe_speed.py REFERENCIA CANDIDATA` produce la comparación con guards. El mapa y las DLL privadas permanecen bajo `local/`; la imagen original y los archivos sincronizados no se modifican.
