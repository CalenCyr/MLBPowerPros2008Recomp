# Alinear retornos dentro de bucles

9 de octubre de 2026. La serie alcanza 26 parches reproducibles: 19 de RecompCore y 7 del frontend. Se mantiene el C generado y ambas DLL del experimento de compilador.

## Problema demostrado

Los tres avisos pendientes del informe anterior se producían en retornos de llamadas dentro de bucles fusionados por el código generado. El chunk continúa varias vueltas hasta consumir su presupuesto; la referencia se detenía en la primera llegada al mismo PC porque sólo reconocía la cabecera exacta de una rama hacia atrás.

La sesión diagnóstica `boot-probe-20261009-180218-129`, todavía con el criterio anterior, reprodujo los tres avisos y añadió ciclos y pasos a cada registro:

| Entrada → salida | Ciclos nativos | Ciclos de referencia al detenerse | Pasos de referencia |
| --- | ---: | ---: | ---: |
| `80081CB4 → 80081CE0` | 266 | 32 | 29 |
| `800BFB38 → 800C1188` | 281 | 21 | 21 |
| `800C1188 → 800C1188` | 260 | 52 | 49 |

El primer caso, por ejemplo, comparaba el índice nativo r31=9 con el índice de referencia r31=0. La traza y el código original muestran que ambos corresponden a vueltas distintas de la misma llamada. No se cambió la traducción para hacer coincidir esos valores.

## Corrección

`recompcore-lockstep-alignment.patch` reconoce también un retorno situado en el tramo recto anterior a una rama que vuelve a una dirección anterior al retorno. La referencia continúa hasta llegar a ese PC con el presupuesto de ciclos correspondiente. La inferencia nueva no atraviesa otra bifurcación o retorno y no trata llamadas enlazadas como ramas de bucle.

Se conserva la búsqueda de cabeceras exactas en la ventana original: una función llamada e integrada dentro del chunk puede aparecer entre la cabecera y su rama hacia atrás en la imagen lineal. Cortar toda la búsqueda al encontrar su retorno perdería cabeceras válidas. Los sondeos intermedios `180857-061` y `181049-981` detectaron esa regresión y no se cuentan como validación de la versión final. La prueba posterior incluye esas ventanas del DOL real para impedir que vuelva a ocurrir.

El criterio sigue siendo una ayuda heurística para alinear bloques. No demuestra por sí mismo equivalencia: después de la alineación se siguen comparando registros, memoria y operaciones MMIO, y se conserva la detección de límites y fallback.

## Pruebas

`tools/check_lockstep_alignment.py` extrae y compila el clasificador real. El lote comprueba retornos dentro del bucle, cabeceras exactas, llamadas hacia atrás, saltos hacia delante, límites de memoria, PC sin alinear y diez ventanas reales del DOL. La primera prueba falló en los casos de retornos antes de modificar el criterio; la ampliación detectó las cabeceras perdidas en el DOL. La versión final pasó 22 casos en `lockstep-alignment-check-20261009-181452-714221`.

La compilación del runtime pasó y la serie de 26 parches se reprodujo contra las revisiones fijadas en `runtime-patch-replay-20261009-181458`.

## Comparación en el juego

| DLL | Sondeo | Entradas intentadas | Comparaciones completas | Avisos | Límite de pasos alcanzado |
| --- | --- | ---: | ---: | ---: | ---: |
| Clang DOL / MSVC REL | `boot-probe-20261009-181520-766` | 3.490 | 3.453 | 0 | 0 |
| MSVC | `boot-probe-20261009-181713-513` | 3.373 | 3.336 | 0 | 0 |

Cada sesión omitió 10 entradas que usaron fallback y 27 con cargo de ciclos cero. No se consideran comparaciones completas. No hubo filtros, avisos de cobro insuficiente ni snapshots MEM2 inválidos. El contador de registros de frontera coincide exactamente con las comparaciones completas y no contiene entradas repetidas dentro de cada sondeo.

Las tres entradas originales aparecen en ambas auditorías con coincidencia de todos los registros y memoria comparados. La referencia completó 236 pasos/266 ciclos, 275 pasos/281 ciclos y 245 pasos/260 ciclos, respectivamente; los tres cargos coinciden exactamente con los nativos.

Ambas sesiones cerraron con salida 0, sin terminación forzada ni órdenes fallidas, MEM1/MEM2 completos y cero verificaciones de código fallidas. En ambos snapshots coinciden los 200.212 campos de reubicación y los 7.820.936 bytes de código REL. No se solicitaron capturas finales de pantalla: son auditorías de bloques, no sondeos visuales de jugabilidad.

`tools/check_lockstep_probe.py` comprueba el cierre, rechaza diagnósticos mezclados, avisos, límites o registros incompletos y exige que las entradas indicadas aparezcan con ciclos exactos. Evidencia de cada sesión en `lockstep-validation.json`, además de los logs y snapshots privados. El runtime usado tiene SHA256 `9589bde07ca254148ad1137fab3e6f6961ecd856ccfa65715a6d1e1456dfe6cf`; las DLL conservan los hashes de la tanda anterior.

`tools/check_lockstep_probe_validation.py` verifica con fixtures independientes la separación entre intentos, omisiones y comparaciones completas, más 37 rechazos de auditorías incompletas o contaminadas. La prueba detectó y corrigió que faltaba rechazar órdenes fallidas, snapshots finales incompletos y ciclos inválidos en entradas no exigidas explícitamente. Después se comprobaron de nuevo las dos auditorías reales con el guard ampliado. Evidencia consolidada en `local/analysis/lockstep-alignment-validation.json`.

El lanzador ofrece `-LockstepTracePC`: una dirección alineada registra sus pasos; `0xFFFFFFFFL` registra sólo el resumen de frontera de cada entrada comprobada. Estos registros indican ciclos, pasos, si se llegó al PC, si se alcanzó el límite y si coinciden los registros y la memoria. La comparación de velocidad continúa rechazando todo sondeo con lockstep activado.

La ventana auditada es 5.000.000–6.000.000 despachos nativos desde el mismo estado del primer out. Se comprueban entradas únicas durante 90 s, sin whitelist, filtro, scheduler acelerado, batching ni otros perfiles. El alcance se limita a las entradas realmente alcanzadas, sin atribuir equivalencia al juego completo ni ejecución exclusivamente nativa.
