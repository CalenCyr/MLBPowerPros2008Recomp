# Comparación de ejecución y correcciones de la referencia

Actualización posterior de la misma fecha: las tres diferencias descritas en este informe se resolvieron al alinear retornos dentro de bucles. Las dos auditorías posteriores registran cero avisos y 3.453 / 3.336 comparaciones completas, con las tres entradas incluidas. Detalles y alcance en `lockstep-alignment-report.md`. Las cifras siguientes documentan la investigación anterior.

9 de octubre de 2026. Hay 25 parches reproducibles: 18 de RecompCore y 7 del frontend ModernGekko. Las traducciones C generadas permanecen intactas.

## MEM2 debe volver al estado anterior al bloque

El verificador original registraba escrituras de MEM1, caché local y memoria virtual, pero no de MEM2. Las funciones de escritura de la DLL tampoco proporcionaban un diario de esa región. Así, la ejecución de referencia podía leer MEM2 después de las escrituras nativas, en lugar de la memoria inicial del bloque; sus propias escrituras podían contaminar la ejecución canónica.

`recompcore-lockstep-exram.patch` guarda MEM2 antes del bloque nativo, conserva su resultado, restaura la imagen inicial para el intérprete, compara ambas imágenes y repone siempre el resultado nativo. La comparación limita a 32 los ejemplos impresos, conservando el número total de bytes distintos. Rechaza cambios de dirección o tamaño. Esta copia completa es costosa y sólo ocurre con el verificador activado; no constituye una optimización de ejecución normal.

`check_lockstep_exram.py` compila el helper real y comprueba preimagen, escrituras exclusivas de la referencia, restauración del resultado nativo, tamaños 1/7/32/257/65.536, casos sin MEM2, capturas repetidas y límite de ejemplos. Pasó en `lockstep-exram-check-20261009-170813-004205`.

## La referencia acumulaba comparaciones flotantes

Los helpers de `fcmpo` y `fcmpu` aplicaban `FPCC_MASK`, una máscara desplazada 12 bits, al campo `FPRF`, cuyo valor ya está desplazado a cero. La máscara no borraba los cuatro bits de comparación y la asignación OR acumulaba comparaciones anteriores. Por ejemplo, mayor seguido de igual conservaba ambos bits.

`recompcore-interpreter-fpcc.patch` aplica la máscara al registro FPSCR completo y desplaza el resultado al campo correspondiente. Conserva el bit de clase, excepciones y redondeo. Se corrige el intérprete de referencia y esa ruta de fallback; no se ignoran los avisos ni se alteran las traducciones C para coincidir con una referencia errónea.

`check_interpreter_fpcc.py` compila los dos helpers reales con los bitfields reales de Dolphin. Pasaron 2.048 casos: 32 valores previos de FPRF, ocho campos CR, ambas instrucciones y cuatro parejas finitas. Las excepciones usan un stub y este lote no valida NaN. Evidencia: `interpreter-fpcc-check-20261009-172241-881555`.

## Sondeos y límites

Se restauró el mismo estado privado del primer out con Vulkan. La ventana empieza en el despacho nativo 5.000.000 y termina en el 6.000.000; sólo se alcanzó una parte de ella durante cada sondeo de 90 s. El verificador compara entradas únicas por defecto, con tope de 20.000 pasos por bloque, sin whitelist ni filtros. Todas las opciones de rendimiento y otros perfiles estaban desactivados.

| DLL / referencia | Sondeo | Comprobaciones | Avisos | Límite de pasos alcanzado |
| --- | --- | ---: | ---: | ---: |
| MSVC, MEM2 corregida, FPCC anterior | `boot-probe-20261009-171133-463` | 2.372 | 14 | 0 |
| Clang DOL / MSVC REL, MEM2 y FPCC corregidos | `boot-probe-20261009-172206-370` | 3.482 | 3 | 0 |
| MSVC, MEM2 y FPCC corregidos | `boot-probe-20261009-172419-063` | 3.608 | 3 | 0 |

Los 11 avisos exclusivos de FPSCR del primer sondeo desaparecen en los posteriores. No es una comparación exhaustiva de los mismos bloques: cada ejecución alcanzó entradas y duración de simulación diferentes. Los dos sondeos posteriores registran las mismas tres parejas de direcciones pendientes:

- `0x80081CB4 → 0x80081CE0`: r31 y un byte MEM1.
- `0x800BFB38 → 0x800C1188`: varios registros y memoria de pila.
- `0x800C1188 → 0x800C1188`: registros e índices de bucle.

No se atribuyen automáticamente a errores de traducción. El comparador usa un criterio heurístico para alinear los bucles con ciclos; debe verificarse si compara el mismo punto lógico antes de corregir esos bloques. En `80081CB4`, el C generado puede repetir llamadas dentro del mismo bloque y volver varias veces a `80081CE0`; el intérprete se detiene en la primera llegada porque ese retorno no coincide exactamente con la cabecera de la rama hacia atrás. Es una causa plausible del índice nativo 9 frente al índice de referencia 0, pendiente de una prueba dirigida de alineación. Tampoco se descartan los avisos por compartir compilador o por no mostrar un fallo visual.

Ambas sesiones posteriores cerraron con salida 0, ninguna orden fallida, MEM1/MEM2 completos y cero verificaciones de código fallidas. El sondeo Clang no produjo la captura final de pantalla solicitada; por el coste del verificador apenas avanzó el contador de fotogramas. Estas sesiones sirven para comparar bloques y no para validar velocidad ni jugabilidad.

El primer sondeo anterior a la corrección MEM2 (`170058-937`) y la ejecución `170803-370`, cuya variable vacía produjo un tope de pasos cero, no se usan como evidencia de equivalencia. El lanzador ahora fija los valores explícitos y exige que el runtime confirme ventana y tope antes de aceptar el resultado.

La compilación del runtime pasó y la serie completa se reprodujo contra las revisiones fijadas en `runtime-patch-replay-20261009-172251`. Todavía no hay una demostración de equivalencia de todas las instrucciones ni ejecución exclusivamente nativa del juego.
