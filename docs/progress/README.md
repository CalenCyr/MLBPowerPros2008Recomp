# Métricas de progreso de la recompilación

Datos comprobados al 9 de octubre de 2026, hora de Venezuela. El panel es una fotografía de ese estado; no actualiza porcentajes automáticamente ni consulta un servicio externo.

| Medida | Numerador / denominador | Resultado | Alcance |
|---|---|---:|---|
| Traducción y compilación | 552 / 552 bloques C generados | 100% | DOL y REL compilan. Incluye dependencias de servicios de hardware y fallback. No significa decompilación ni equivalencia del gameplay validada. |
| Código enlazado en DLL experimental | 9.021.384 / 9.021.384 bytes de código | 100% | 552 bloques DOL/REL; el REL exige la ubicación comprobada. No mide equivalencia del código, tiempo de CPU, horas de trabajo ni avance total del port. |
| Código en DLL inicial | 1.200.448 / 9.021.384 bytes de código | 13,3067% | Se conserva la DLL inicial DOL para comparación; mapa verde/gris en esa vista. |
| Casos DOL aprobados | 2.352 / 2.352 casos | 100% | Solo memcpy y memset. No representa un porcentaje del juego probado. |
| Casos REL aprobados | 72 / 72 casos | 100% | Seis funciones cortas con doce entradas; referencias PowerPC independientes, sin fallback de instrucciones en estos casos. |
| Campos de reubicación REL contrastados | 200.212 / 200.212 campos | 100% de coincidencia | Comparación fuera del juego contra la captura enlazada; no valida la traducción C ni aumenta el código integrado. |
| Cierre de la prueba larga | 900 s, Vulkan y módulo DOL+REL | Comprobado | Dos sesiones de 15 minutos con salida 0 sin terminación forzada. La prueba anterior de 120 s cubre una descarga WiiConnect24 activa al apagar. |
| Respuesta en Exhibition | +, A, B y stick del Nunchuk | Observada | Menús y lanzamientos repetidos con A. Contacto de CPU, escena de campo, corredor en primera, primer out y siguiente bateador. No valida defensa manual, bateo del jugador ni inning completo. |
| Auditoría de CPU del primer out | Clang: 3.453 comparaciones completas; MSVC: 3.336 | Sin diferencias en la ventana comprobada | 5–6 millones de despachos; 37 entradas omitidas por sesión. No es un porcentaje de funciones ni equivalencia del juego completo. |
| Velocidad del menú con Clang | Una pareja desde el mismo estado, 120 s por sesión | 56,44% de velocidad normal; +66,44% de avance frente a MSVC | MSVC: 34,96% normal. Avance del contador de fotogramas, no FPS renderizados. No se suman ganancias ni se extrapola a todos los modos. |
| Velocidad del primer out con Clang | Dos parejas con orden invertido | Aproximadamente 45,3% de velocidad normal | +54,94% y +62,10% de avance frente a MSVC en las comparaciones anteriores. Runtime histórico de 25 parches. |
| Primer out, consultas al gestor vacío omitidas | Dos parejas OFF/ON con orden invertido, runtime de 27 parches | 51,33% y 52,55% de velocidad normal; +7,74% y +11,09% de avance | Misma DLL Clang. Opción experimental desactivada por defecto; no valida el partido completo. |
| Auditoría de esa opción | 3.505 comparaciones completas, 39 omitidas | Sin diferencias en la ventana comprobada | Scheduler desactivado, 5–6 millones de despachos; no valida rutas omitidas o no visitadas. |
| Port completo jugable | Sin denominador definido ni validación de un partido completo | No calculado | Primer inning observado; bateo, defensa, audio, rendimiento y ejecución exclusivamente nativa pendientes. |

El mapa agrupa las funciones inferidas por dtk según su unidad de análisis: 261 grupos del DOL y 242 del REL. Sus áreas corresponden a la suma de los tamaños originales de esas funciones; se añade una región de 200 bytes de código del DOL que no está asignada a un grupo en ese inventario. Esos grupos **no son** los 552 bloques C generados ni una identificación validada de módulos originales de Konami.

La vista principal muestra los bloques enlazados de la DLL experimental en verde. La vista de la DLL inicial mantiene DOL verde y REL gris. El campo `integrated` de cada grupo conserva esa comparación inicial; los campos generales del JSON registran la nueva DLL experimental. Ningún color significa que todas las funciones de esa región hayan sido verificadas.

Fuentes locales de las métricas:

- `docs/empty-mod-hooks-report.md` y `local/analysis/empty-mod-hooks-validation.json`: dos parejas, auditoría, 14 casos y serie actual de 27 parches. Capturas del primer out revisadas.

- `docs/lockstep-alignment-report.md` y `local/analysis/lockstep-alignment-validation.json`: corrección de las tres diferencias, auditorías sin filtros, cierre/REL y serie de 26 parches.
- `docs/compiler-experiment-report.md` y `local/analysis/compiler-speed-comparison-20261009-182730-864789.json`: comparación del menú y resultados históricos del primer out. Las capturas finales del menú fueron inspeccionadas.
- `local/analysis/inventory.json`: tamaños de las secciones.
- `local/analysis/translation-audit.json` y `docs/cpu-translation-report.md`: traducción y compilación.
- `local/analysis/dol-functions.csv` y `rel-functions.csv`: agrupación y tamaños para el mapa.
- `runtime/module/module_export.c`, `config/project.json` y `docs/runtime-integration-report.md`: alcance del módulo y estado del arranque.
- `local/analysis/runtime-module-checks.log`: pruebas del módulo.
- `local/analysis/rel-detector-checks.json` y `boot-probe-20261008-005615-342/rel-relocation-validation.json`: detector y comparación del enlace observado.
- `local/analysis/rel-reference.json`, `runtime-module-rel-checks.log` y `boot-probe-20261008-050910-754/`: referencias REL, pruebas y ejecución de la DLL experimental.
- `local/analysis/boot-probe-20261008-143346-422/`: cierre correcto con transferencia WC24 activa, captura del logo y nueva comparación de reubicaciones.
- `local/analysis/boot-probe-20261008-151509-986/`: 900 segundos, menú principal, My Data, respuesta básica a órdenes aisladas y cierre correcto. La selección de equipos de `145416-968` tuvo interferencia potencial del teclado/ratón y no valida controles.

`progress-data.json` contiene los datos de esta fotografía. `power-pros-progress.html` contiene la visualización interactiva en el formato de fragmento del chat. La copia de inspección en `local/analysis/progress-preview.html` permite comprobar su presentación.

Actualización de Exhibition: las sesiones `162927-571` y `164903-213` necesitaron cierre forzado. Se corrigieron tanto la pérdida de órdenes por apertura temporal como la espera de `pad_frames` que bloqueaba la lectura de Stop. `173857-417` llegó desde uniformes al calentamiento de Boston/Colorado en Fenway Park y cerró correctamente tras 900,41 s; los campos `latest_long_probe_*` describen ahora esta sesión. `175806-715` completó el calentamiento y registró el primer strike con A. Cerró anticipadamente tras 405,80 s, con salida 0 y capturas completas, mientras había una orden neutral de 6.000 fotogramas pendiente. Esa orden es la única cancelación esperada en `control/failed/`; `latest_probe_*` describe esta comprobación. El estado privado del primer strike permite reanudar la siguiente prueba.

Actualización posterior: `203348-395` observó pelota en juego y corredor en primera, y cerró correctamente tras 900,17 s; los campos `latest_long_probe_*` corresponden a esa sesión. `205240-719` restauró los dos strikes, alcanzó el primer out y guardó `pitch-result-state.sav`, con siguiente bateador y marcador 0–0. Cerró correctamente tras 300,21 s, sin órdenes fallidas. Los campos `latest_probe_*` describen esta última comprobación. La validación de cierre con una orden pendiente se conserva como resultado histórico separado.

Validación del panel: suma de áreas igual al total de bytes de código; 504 regiones y opciones seleccionables; cambio de estado entre traducción e integración; comprobación anterior en navegador a 850 y 320 píxeles de ancho, sin desbordamiento horizontal. La actualización solo cambia etiquetas y datos de las nuevas pruebas; no modifica el mapa ni código del juego.
