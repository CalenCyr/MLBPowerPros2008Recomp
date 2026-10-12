# Primera traducción y compilación de CPU

7 de octubre de 2026. Carpeta de trabajo: `D:\MLBPowerPros2008Recomp`.

**Resultado:** el DOL y el REL de la imagen aportada se tradujeron a C y compilaron como bibliotecas Windows x64. También se ejecutaron dos rutinas reales del DOL traducido y se compararon con su PowerPC original. **El juego todavía no arranca:** faltan runtime, carga del módulo, gráficos, sonido y controles.

## Resultados comprobados

| Medida | DOL | REL |
|---|---:|---:|
| Definiciones de función detectadas por dtk | 5.067 | 43.108 |
| Palabras de 4 bytes recorridas por el traductor | 300.112 | 1.955.234 |
| Instrucciones desconocidas reportadas | 0 | 0 |
| Palabras clasificadas como datos embebidos | 1.648 | 0 |
| Unidades C generadas por bloques | 74 | 478 |
| Llamadas explícitas de respaldo a instrucciones | 401 | 0 |
| Compilación de todos los bloques a biblioteca | Correcta | Correcta |

El recuento aproximado es **48.175 funciones** según los límites inferidos por dtk. No es un recuento validado manualmente. DolRecomp divide el código en bloques de hasta 4.096 instrucciones: los 552 bloques generados **no son 552 funciones originales**. Se compilaron también los dos archivos de manifiesto que acompañan a esos bloques.

Se usó [DolRecomp](https://github.com/AH64-dll/DolRecomp) en el commit `71c3122a92bf25a9fbe91fe7c662ad70125fba59`, backend C y perfil Broadway. La versión exacta y el parche local están fijados en `config/recompiler.lock.json`.

El traductor fue compilado con Visual Studio 2022 x64. Sus **16 pruebas pasaron**. Se corrigió una dependencia en su configuración de build: `test_rel` necesita enlazar el backend porque el cargador REL usa `emit_guest_addr`. El cambio se conserva como parche separado; no se modificó código generado del juego.

Los artefactos están en `local/build/powerpros-cpu/Release/powerpros_dol_code.lib` y `powerpros_rel_code.lib`. Son artefactos locales derivados de la copia aportada, excluidos de Git. La compilación de comprobación usa `/Od`; todavía no es una build optimizada para jugar.

## Relocaciones y puntos pendientes

DolRecomp procesó el módulo 1, REL versión 3, con dos entradas de importación y **200.212 relocaciones aplicadas**. Para esta prueba se usó la base virtual `0x80500000`; su entrada quedó en `0x80A2B198`. Esa base fue elegida por la herramienta y no se ha demostrado que coincida con la carga real del juego. Falta conectar la carga y el dispatch entre DOL y REL en el runtime.

La base de títulos opcional de DolRecomp no se descargó. Por ello su etiqueta informativa dice GameCube REL, aunque el perfil de CPU seleccionado explícitamente fue **Broadway/Wii**. Esa etiqueta no cambia la identidad del disco `RL8E54`.

Las 401 llamadas de respaldo del DOL se distribuyen así:

| Operación | Sitios |
|---|---:|
| `mtspr` | 294 |
| `mfspr` | 93 |
| `dcbst` | 4 |
| `icbi` | 4 |
| `dcbi` | 3 |
| `dcbf` | 3 |

Son registros especiales y operaciones de caché que requieren implementación o hooks del runtime. **Cero opcodes desconocidos no equivale a cero necesidades del runtime.** No se han sustituido por operaciones vacías.

El detector de DolRecomp marcó 17 intervalos del DOL como candidatos a modificación de código. Es una advertencia estática, no una prueba de self-modifying code real. Además, dtk produjo dos advertencias de relocación `Rel14`, en los offsets `0x31D80C` y `0x31D844`. Ambas quedan pendientes de revisión; no se alteró el binario para silenciarlas.

## Ejecución nativa contra referencia PowerPC

El ejecutable de comprobación `local/build/native-checks/Release/powerpros_native_checks.exe` enlaza código traducido del DOL y helpers de CPU. Ejecuta las rutinas identificadas por dtk como `memset` (`0x800065BC`) y `memcpy` (`0x8000626C`). No es un lanzador del juego.

Se comprobaron **2.352 casos**, con distintos tamaños, valores de relleno y alineaciones de origen y destino. Se comparó toda la región de memoria de prueba, incluidos bytes fuera del destino solicitado, y se verificaron retorno, pila y registro preservado. Las ejecuciones nativas rechazaban cualquier llamada de respaldo a un intérprete: no se produjo ninguna.

La referencia se generó ejecutando los bytes PowerPC del DOL aportado con [Unicorn](https://www.unicorn-engine.org/docs/tutorial.html) 2.1.4, como herramienta externa de verificación. Unicorn no forma parte del runtime propuesto para el port. La fixture está asociada al SHA256 del DOL y se guarda en `local/analysis/memory-reference.bin`.

Un hallazgo: en 24 casos, el `memcpy` del DOL aportado modifica algunos bytes después de la longitud solicitada. Por ejemplo, con origen y destino alineados a `+1` y longitud 255, modifica seis bytes adicionales. Esa diferencia aparece tanto en la referencia PowerPC como en la ejecución nativa. Se conserva el comportamiento del binario aportado; reemplazarlo ciegamente por el `memcpy` del host cambiaría ese comportamiento. No se infiere de esto que todas las revisiones comerciales tengan el mismo resultado.

Resultado final de la comprobación: **2.352/2.352 casos coinciden con la referencia PowerPC**. Esta prueba cubre esas dos rutinas; no demuestra todavía precisión de física, paired singles, temporización, excepciones ni gameplay completo.

## Reproducir

Después de la extracción de fase 0, con Python 3.10+, Git, CMake, CTest y Visual Studio 2022 con herramientas C/C++:

```powershell
Set-Location D:\MLBPowerPros2008Recomp
.\tools\recompile.ps1
```

El script fija el commit, aplica el parche de build, comprueba hashes de entrada, analiza con dtk, traduce, compila y ejecuta la comparación nativa. Sus rutas de Python, CMake y CTest pueden especificarse como parámetros. Los datos del juego y todas las salidas quedan en `local/`.

Para volver a comprobar una traducción ya generada, sin repetir análisis ni reescribir el C:

```powershell
.\tools\recompile.ps1 -SkipDtkAnalysis -ReuseGenerated
```

Se ejecutaron los pasos de generación completos y, después, el flujo integrado de reutilización. Los registros y CSV de funciones/respaldo están en `local/analysis/`.

## Elección de stack y siguiente hito

DolRecomp es un **candidato validado para traducción y compilación de CPU**. No se ha escogido todavía un runtime definitivo ni se ha probado ModernGekko, Wiicompiled/aurora o NWiiRecomp con este juego. La fase 0.5 sigue abierta y el criterio de boot de fase 2 no se alcanzó.

El siguiente hito es cargar memoria y secciones, conectar los módulos y resolver los servicios de arranque del SDK, primero hasta un punto de entrada/control verificable. Después se podrá comparar el coste de adaptar un runtime existente. Los pendientes de fase 0 —framerate real, modo online, formatos internos e integridad completa del disco— siguen registrados en `docs/phase0-report.md`.
