# Diagnóstico de rendimiento — 8 de octubre de 2026

Investigación posterior: se identificó la espera dentro de `SelectThread` y se implementó una opción experimental con guardas. Una comparación corta registró +10,8% de avance de fotogramas; véase `scheduler-idle-report.md`. Después se simplificó la conversión de direcciones para el REL con posiciones fijas; véase `fixed-rel-translation-report.md`. Los resultados que siguen corresponden al diagnóstico anterior de 16 parches.

El usuario acordó priorizar código, reemplazos nativos y rendimiento medido. Las pruebas cortas desde estados guardados sustituyen las sesiones dedicadas a avanzar manualmente cada inning. Un partido completo sigue siendo una comprobación posterior. El acuerdo está guardado en `AGENTS.md`.

## Cambio comprobado

El parche `recompcore-fallback-profile.patch` añade un diagnóstico opcional al callback de instrucciones. Se activa con `STATICRECOMP_FALLBACK_PROFILE` indicando un archivo CSV; `probe-boot.ps1 -ProfileFallback` lo configura para el proceso hijo y conserva el entorno del proceso padre. Sin esa opción, el sondeo desactiva tanto este diagnóstico como las muestras de despachos nativos heredadas del entorno.

Se cuentan por separado las llamadas a la ruta rápida de caché y las que requieren sincronización de CPU e intérprete. Se muestrea cada llamada número 1.024 de cada categoría, con un máximo de 4.096 pares dirección/instrucción por categoría. Se contabilizan las muestras descartadas al alcanzar ese límite. El CSV se escribe al cerrar, sin escritura de archivos en el bucle de instrucciones. Los ciclos, las instrucciones originales y los archivos C generados permanecen iguales.

La serie del runtime contiene ahora 16 parches: nueve del core y siete del frontend. La reproducción completa sobre las revisiones fijadas pasó en `runtime-patch-replay-20261009-030941`. La compilación incremental del ejecutable pasó; registro privado `moderngekko-profile-build.log`.

`check_fallback_profile.py` compila el helper real extraído de las fuentes parcheadas. Comprueba modo desactivado, reinicio, categorías separadas, límite de memoria, muestras descartadas y acumulación de sitios existentes después de llenar el mapa. Resultado aprobado en `fallback-profile-check-20261009-031141-080764`. `check_fallback_profile_report.py` comprueba contabilización con descartes y rechaza nueve perfiles corruptos, incluyendo truncamiento y discordancia con el contador final.

## Prueba corta real

`boot-probe-20261009-031431-953` ejecutó 120,01 segundos solicitados después de la preparación, con Vulkan, DLL optimizada y el estado privado del primer out con marcador 0–0. La imagen final conserva esa pantalla. No se enviaron controles ni se avanzó deliberadamente el inning.

La sesión terminó con salida 0, sin terminación forzada, sin órdenes fallidas y con MEM1/MEM2 completas. `check_probe_shutdown.py` pasó. Los 200.212 campos de reubicación y 7.820.936 bytes del código REL coinciden con la referencia. `analyze_fallback_profile.py` verificó los totales, la contabilización de muestras y las siete instrucciones muestreadas contra la captura final de MEM1.

| Ruta del callback | Llamadas observadas | Porcentaje de callbacks | Muestras guardadas |
| --- | ---: | ---: | ---: |
| Caché rápida | 19.023.046 | 99,6512% | 18.577 |
| Sincronización e intérprete | 66.582 | 0,3488% | 65 |
| Total | 19.089.628 | 100% | 18.642 |

No se descartaron muestras. El total coincide con `instruction_hook_fallbacks`. Las operaciones rápidas observadas fueron `dcbf`, `dcbi` y `dcbst`. Las muestras lentas señalan `mtdec` en `0x80099E90` (59), `mfwpar` en `0x80099F40` (3) y `mtwpar` en `0x80099F48` (3).

El contador general de callbacks no equivale a pasos completos del intérprete: la mayoría de estas llamadas ya utiliza la ruta rápida existente. Esa ruta aún tiene coste y debe medirse antes de descartarla como candidato. Este cambio mejora el diagnóstico; no demuestra un aumento de velocidad.

## Candidato para la siguiente investigación

La muestra existente de despachos nativos, activada cada 4.096 despachos, registró `0x800A4318` como el sitio más frecuente de los 16 publicados, con 12.105 muestras. El C generado contiene allí un bucle de tres instrucciones: cargar una variable relativa a r13, compararla con cero y repetir mientras sea cero. Se infiere que espera a que cambie un estado; aún no se ha identificado con certeza qué evento lo modifica.

El siguiente paso de rendimiento debe medir tiempo de CPU y estudiar los productores de esa variable, las interrupciones y la sincronización antes de elegir una optimización. No se configuró ese sitio como bucle de inactividad ni se omitieron sus iteraciones. Su frecuencia por sí sola no prueba cuánto tiempo de CPU consume.

La búsqueda estática en los comentarios de instrucción del DOL localizó escrituras directas al mismo desplazamiento de r13 en `0x800A3DA0`, `0x800A3F7C`, `0x800A4070`, `0x800A42B0`, `0x800A4398`, `0x800A4C40` y `0x800A5114`, todas en `chunk_0040_text1_800A3360.c`. Esto acota la investigación del productor; no descarta escrituras indirectas ni demuestra por sí solo cuál despierta la espera en esta escena.

## Evidencia y límites

Informe reproducible privado: `local/analysis/boot-probe-20261009-031431-953/fallback-profile-report.json`.

- Ejecutable: SHA256 `07fab8ab0d5cab83faf1c724f63ef87002d55b9a0a5bb54946d9f0b85892dded`.
- DLL optimizada: SHA256 `393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6`.
- Estado restaurado: SHA256 `5158bc08a5e58986bf5313277e0676b4cad0b77cecacbdf442313f67020eed14`.

Los totales abarcan preparación, restauración y apagado además de la ventana solicitada. El muestreo periódico puede introducir sesgo. Las frecuencias no son tiempo de CPU, FPS, cobertura nativa ni porcentaje de finalización. Las muestras de despachos publican solo los 16 sitios más frecuentes. La coincidencia de instrucciones con la captura final no prueba que nunca cambiaran durante la sesión. La base mantiene `BUILD_TESTING=OFF`: se verificaron el helper específico, la compilación y esta integración real; no se ejecutó una suite general del runtime.

El módulo conserva 552 bloques y 9.021.384 bytes enlazados experimentalmente. Este diagnóstico no aumenta esa cobertura ni completa el port. Continúan pendientes rendimiento jugable, validación amplia de CPU/REL, controles de bateo y defensa, audio, partido completo y arranque exclusivamente nativo.

## Reproducir

```powershell
Set-Location D:\MLBPowerPros2008Recomp
.\tools\runtime.ps1 -Python 'ruta\a\python.exe' -SkipDependencies
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -ProfileFallback -Screenshot -SnapshotMemory -LoadState 'ruta\al\estado.sav'
python .\tools\check_probe_shutdown.py .\local\analysis\boot-probe-<identificador>
python .\tools\analyze_fallback_profile.py .\local\analysis\boot-probe-<identificador>
python .\tools\inspect_runtime_rel.py .\local\analysis\boot-probe-<identificador>
python .\tools\validate_runtime_relocations.py .\local\analysis\boot-probe-<identificador>
python .\tools\check_fallback_profile.py
python .\tools\check_fallback_profile_report.py
```

La DLL optimizada y el estado privado deben existir previamente. `runtime-rel.ps1 -ReuseGenerated -Optimize -ModuleOnly` prepara esa DLL cuando la traducción privada ya está disponible. Una restauración valida ese estado, sin demostrar un nuevo arranque desde cero.
