# Medición del coste nativo y alternativa de compilación

Ampliación posterior con runtime de 27 parches: una opción que omite consultas al gestor de mods vacío registró +7,74% y +11,09% con la misma DLL Clang, en dos parejas del primer out. Es un experimento separado del cambio de compilador; resultados, auditoría y límites en `empty-mod-hooks-report.md`.

9 de octubre de 2026. Proyecto local: `D:\MLBPowerPros2008Recomp`.

Ampliación: se resolvieron las tres diferencias de alineación y se midió otra escena con el runtime de 26 parches. La pareja del menú principal registró +66,44% de avance, con mediana de 56,44% de velocidad normal. La corrección y sus límites están en `lockstep-alignment-report.md`; los resultados anteriores del primer out se conservan con su runtime original de 25 parches.

## Por qué cambiar la prioridad

Las mediciones anteriores cronometraban algunas etapas del despacho. Para buscar un cambio de mayor alcance se tomó una muestra del hilo de CPU del proceso real, incluyendo el trabajo fuera de esas etapas. La decisión de probar otro compilador parte de esta medición, siguiendo el enfoque de medir primero y contrastar comportamiento con el intérprete antes de aceptar resultados.

`host-sample-20261009-164932-687` contiene 4.051 muestras durante 75,001 s del hilo `CPU-GPU thread` (PID 21056, TID 9332). Ese hilo consumió 62,969 s de CPU en usuario y 6,672 s en kernel. Las suspensiones breves acumularon 0,574 s; perturban la ejecución y esta captura no se usa para comparar velocidad.

| Ubicación de la instrucción muestreada | Muestras | Porcentaje |
| --- | ---: | ---: |
| DLL del código traducido | 2.510 | 61,96% |
| Ejecutable del runtime | 906 | 22,36% |
| ntdll | 363 | 8,96% |
| Controlador AMD | 72 | 1,78% |
| ucrtbase | 64 | 1,58% |

Los porcentajes son fracciones de muestras de un hilo, no tiempo exclusivo de funciones, reparto total de CPU/GPU ni porcentaje del port completado. Las etiquetas de función se resuelven al símbolo anterior del mapa del enlazador: pueden incluir trabajo en línea, alias y huecos. El coste dentro de la DLL está repartido entre muchos bloques DOL; ningún bloque representa por sí solo la mayoría.

La captura usa el runtime anterior a las correcciones del comparador. Su `report.json` conserva los hashes de binarios y mapas usados al resolver símbolos. El mapa del ejecutable se reemplazó en una compilación posterior: no se puede volver a resolver esta captura con el mapa nuevo. La sesión asociada `boot-probe-20261009-164852-502` perdió su resultado final por una carrera del cierre del proceso y no se cuenta como prueba completa de integración. El muestreo de hilo tiene evidencia independiente.

## Variante preparada

Se compiló con Clang 22.1.8 el DOL (74 bloques), los helpers de CPU y la interfaz de la DLL. Los 478 objetos REL de MSVC se reutilizan sin cambios. Es una variante híbrida, no una recompilación completa con un backend nuevo. Se conserva el C generado, `/O2`, cálculo flotante estricto y la interfaz ABI 3 / CPU ABI 4.

| Variante | Tamaño DLL | SHA256 |
| --- | ---: | --- |
| MSVC 19.43.34810.0 | 610.599.424 bytes | `60a0611c6e528583f67b985cc31d290973cf96666685523eec8c1ab316702865` |
| Clang DOL / MSVC REL | 552.097.792 bytes | `09296c1d72e4bb44080572964a1b664f148e2142cf691c04503258596f119357` |

Los manifiestos de ambas compilaciones identifican el mismo conjunto de entradas: `29616140c2a31a4fd38b42773aaeca7083f0f8f617832a70e0d4ce3e0a576b71`. Incluyen hashes de fuentes, headers, tablas, binarios de referencia, compilador y los 478 objetos REL. La disminución de tamaño no demuestra una mejora de velocidad.

LLVM se extrajo exclusivamente en `local/tools/llvm-22.1.8`, sin instalación global. El instalador descargado de la [publicación oficial LLVM 22.1.8](https://github.com/llvm/llvm-project/releases/tag/llvmorg-22.1.8) coincide con el SHA256 del asset: `16e5709785fef73c854646241c4a92c5cd574318d1b33c63330dd7721903e55c`. Su metadata está en `local/tools/llvm-release-asset.json`. El intento previo con GCC no produjo una DLL y no cuenta como resultado de ejecución.

## Validación y medición

Ambas DLL pasan las 2.352 referencias de memoria DOL y los 72 casos REL disponibles. Eso valida esas rutinas y guards, no todas las instrucciones del juego. La comparación paso a paso y sus límites se describen en `lockstep-validation-report.md`.

Las pruebas de velocidad usan Vulkan, el mismo runtime, entradas físicas aisladas y el estado del primer out SHA256 `5158bc08a5e58986bf5313277e0676b4cad0b77cecacbdf442313f67020eed14`. La espera optimizada del planificador está activada en ambas; CacheBatch, perfiles y comparación paso a paso están desactivados. Se mide avance de fotogramas del juego por segundo real, no FPS renderizados. El comparador rechaza cambios de runtime, estado, entradas, fuentes, objetos REL, diagnósticos activos y cierres incompletos.

Se hicieron cuatro sesiones de 120 s en orden MSVC, Clang, Clang, MSVC, sin compilar ni tomar muestras de hilo durante esos intervalos. Cada comparación usa aproximadamente 110 s de muestras después del inicio:

| Pareja | Variante | Sondeo | Fotogramas / segundo real | Mediana de velocidad normal |
| --- | --- | --- | ---: | ---: |
| 1 | MSVC | `boot-probe-20261009-172642-631` | 17,537 | 30,785% |
| 1 | Clang DOL / MSVC REL | `boot-probe-20261009-172910-634` | 27,171 | 45,258% |
| 2, orden invertido | Clang DOL / MSVC REL | `boot-probe-20261009-173146-119` | 27,352 | 45,305% |
| 2, orden invertido | MSVC | `boot-probe-20261009-173409-985` | 16,874 | 29,044% |

Los cocientes son **1,54942 (+54,94%)** y **1,62097 (+62,10%)**. Las dos sesiones Clang se mantienen cerca de 27,2–27,4 fotogramas del juego por segundo real, frente a 16,9–17,5 con MSVC. Es una mejora consistente en estas dos parejas de esta pantalla y este equipo; no demuestra ese porcentaje en el menú, bateo, defensa o partido completo. La velocidad sigue lejos del 100% normal. No se suman ganancias de tandas anteriores.

Las cuatro sesiones cerraron con salida 0, sin terminación forzada ni órdenes fallidas, y guardaron las capturas completas de MEM1/MEM2. En cada snapshot coinciden los 200.212 campos de reubicación y los 7.820.936 bytes de código REL. Las cuatro capturas finales se revisaron: muestran la misma escena de lanzamiento, marcador 0–0 y un out. La revisión visual no sustituye la comparación de CPU.

Evidencia privada:

- `local/analysis/compiler-speed-comparison-20261009-173155-715226.json`.
- `local/analysis/compiler-speed-comparison-20261009-173723-947290.json`.
- `local/analysis/compiler-probe-integration-validation.json`, que también recoge los dos sondeos de comparación paso a paso.
- `local/analysis/clang-module-fixture-build.log`: los ejecutables de prueba se compilaron con Clang y ambas suites pasaron; la DLL y el conjunto de fuentes conservaron sus hashes.

La alternativa permanece seleccionable explícitamente con `-ClangModule`; MSVC conserva su selección habitual. CacheBatch acepta las dos DLL MSVC comprobadas (la histórica y la reenlazada con mapa) y rechaza Clang, cuyo bucle no se ha validado para esa opción. Las 8.130 pruebas del helper de CacheBatch se volvieron a aprobar; eso no atribuye un resultado de velocidad de batching a la DLL nueva.

Las tres direcciones pendientes quedaron alineadas y coinciden en las nuevas auditorías de ambas DLL. No se alteraron las traducciones ni se filtraron las diferencias: se compara la misma vuelta del bucle. Clang completó 3.453 comparaciones y MSVC 3.336, con cero avisos dentro de la ventana auditada. Este resultado no valida entradas omitidas ni caminos sin visitar. Detalles en `lockstep-alignment-report.md`.

## Otra escena: menú principal

Se restauró `menu-state.sav`, SHA256 `049c95362219a74f0c099791a683cce4f1c494ecaa1515613d4b2095f9ff8beb`, usando el runtime corregido SHA256 `9589bde07ca254148ad1137fab3e6f6961ecd856ccfa65715a6d1e1456dfe6cf`. Las DLL, fuentes y los 478 objetos REL conservaron sus hashes. Ambas sesiones duraron 120 s, con Vulkan, entradas aisladas, scheduler acelerado activado y batching, lockstep y perfiles desactivados. No se compiló durante los intervalos.

| Variante | Sondeo | Fotogramas / segundo real | Mediana de velocidad normal |
| --- | --- | ---: | ---: |
| MSVC | `boot-probe-20261009-182057-742` | 19,509 | 34,959% |
| Clang DOL / MSVC REL | `boot-probe-20261009-182321-585` | 32,470 | 56,438% |

El cociente de avance es **1,66435 (+66,44%)**: 2.145 fotogramas en 109,949 s frente a 3.567 en 109,856 s. Se distingue este cociente de la mediana de velocidad que informa el runtime. Es una pareja consecutiva del menú en este equipo; no caracteriza la variabilidad ni todos los modos del juego. No se combina con los porcentajes históricos del primer out.

Ambas sesiones cerraron con salida 0, sin terminación forzada ni órdenes fallidas, MEM1/MEM2 completos y cero verificaciones de código fallidas. En ambas coinciden los 200.212 campos de reubicación y los 7.820.936 bytes de código REL. Se inspeccionaron ambas capturas finales: menú principal con Exhibition seleccionado. La comparación offline de REL y la revisión visual no sustituyen una auditoría de CPU de esta escena.

Evidencia: `local/analysis/compiler-speed-comparison-20261009-182730-864789.json` y `local/analysis/lockstep-alignment-validation.json`. La variante permanece experimental. La siguiente prioridad es medir qué bloques del DOL/REL dominan el coste con esta variante antes de decidir ampliar Clang al REL; sigue pendiente el rendimiento del juego completo.

## Reproducir

La variante requiere la compilación MSVC conservada y el LLVM privado indicado. `tools/build-clang-module.cmd` verifica primero las entradas y objetos MSVC, compila la variante y registra su manifiesto. `probe-boot.ps1 -RelModule -OptimizedModule -ClangModule` selecciona explícitamente esa DLL; la selección habitual conserva MSVC. Los manifiestos se copian al directorio de cada sondeo antes de iniciarlo.

`tools/compare_compiler_probe_speed.py BASELINE CANDIDATE` comprueba condiciones y entradas antes de generar una comparación. `tools/check_compiler_probe_comparison.py` comprueba el cociente y 32 rechazos de resultados contaminados o incompatibles.

`tools/check_host_sample_analysis.py` verifica fracciones de muestras, conversión de unidades de CPU y ocho rechazos de datos o mapas incorrectos. El muestreador se compila desde `tools/host-sampler`. Para futuras capturas deben conservarse los mapas del mismo binario y marcarse el sondeo con `host-sampling.json`; el comparador de velocidad rechaza ese marcador.

La cobertura sigue en 552 bloques / 9.021.384 bytes enlazados. La ejecución aún utiliza apoyo del intérprete/JIT; el port nativo completo no está validado.
