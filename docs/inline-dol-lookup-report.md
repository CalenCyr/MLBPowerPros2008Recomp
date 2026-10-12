# Búsqueda directa de bloques DOL verificados

9 de octubre de 2026. Proyecto en `D:\MLBPowerPros2008Recomp`. Se probó un candidato con 28 parches y se retiró de la versión activa por resultados de velocidad inconsistentes. La versión activa conserva 27 parches: 19 del core y 8 del frontend. Las DLL, el código generado y las ABI permanecen iguales.

## Causa y cambio

El muestreo `host-sample-20261009-164527-499` recogió 3.294 posiciones del hilo CPU-GPU durante 60,024 s, con 0,377 s acumulados de suspensión. La DLL apareció en 48,48% y el ejecutable en 25,65% de las muestras. El mapa del mismo ejecutable atribuyó aproximadamente 3,4% a `ChunkIndexOf` y 4,2% a `Run`. Estas fracciones son muestras de un hilo, sin atribución exclusiva del tiempo ni una ganancia de rendimiento implícita. El sondeo simultáneo `boot-probe-20261009-204500-788` tiene una marca explícita `host-sampling.json` para excluirlo de las comparaciones de velocidad.

La lectura del código confirmó que, con REL integrado, el bucle rápido volvía a llamar al método general incluso para un bloque DOL ya verificado. `recompcore-inline-dol-lookup.patch` permite consultar directamente la tabla de instrucciones para ese caso en la configuración de REL fijo. Conserva el estado de verificación actual en cada consulta.

Los bloques REL, las entradas sin bloque, las direcciones fuera de memoria y los rangos de fallback forzado conservan la ruta general. Esta ruta mantiene el descubrimiento y la descarga/recarga del REL. La configuración de REL reubicable también conserva su ruta anterior. No cambian los ciclos, la temporización, las excepciones ni las interrupciones del invitado.

## Comprobación de las fuentes

`check_inline_dol_lookup.py` compila las lambdas reales de `Run` antes y después del cambio junto con los métodos reales de SMC y resolución REL. Usa las capturas y metadatos de las comprobaciones existentes del detector. Compara tanto el resultado como los estados de verificación, hashes efectivos, generación, límites y contenido del mapa REL.

La ejecución completa `inline-dol-lookup-check-20261009-205308-846856` pasó **1.540 comparaciones con REL fijo y 1.540 con REL reubicable**, además de las comprobaciones del detector: fronteras, gaps, memoria principal/MEM2, módulos inactivos, rangos forzados, estados sin verificar/fallidos, precedencia, descarga, recarga y mapas rechazados. Una ejecución anterior con más direcciones aleatorias se interrumpió durante el costoso escaneo de memoria de la variante dinámica; su variante fija completó 41.860 comparaciones. La evidencia de la comprobación completa está en su `result.json`.

Los 28 parches se reprodujeron sobre las revisiones fijadas en `runtime-patch-replay-20261009-205326`. La compilación pasó; registro `inline-dol-lookup-build.log`. El comparador de revisiones conserva el rechazo de perfiles y auditorías en pruebas de velocidad; una nueva declaración explícita permite mantener la opción de gestor vacío activada en ambas revisiones, exigiendo cero mods y confirmación de inicio. Pasaron sus pruebas de cociente, 24 rechazos generales y 10 adicionales; el guard de cola pasó 15 rechazos.

Ejecutable anterior: SHA256 `40353ecb8ccc32f3c5ea86daf89010826be4b9a837bfd9defb0f731fe812715a`. Nuevo: `e9d5afa2e71d6b25ed521f08800db2294d8c3c2c3b13a2fbe632fef2a350c124`. DLL conservada: `09296c1d72e4bb44080572964a1b664f148e2142cf691c04503258596f119357`. El ejecutable, mapa y fuente anteriores se conservaron en `host-sample-20261009-164527-499/preserved/`, con hashes en `preserved-provenance.json`.

## Herramientas de ingeniería inversa

Tras el reinicio del usuario, la conexión activa REA reconoce Ghidra 12.1.4 y Java 21. Evidencia: `rea-reconnected-20261009.json`. Se aplicó la skill reverse-engineer-anything solicitada para relacionar observaciones, fuentes y validación. Este cambio se obtuvo de las fuentes completas y del muestreo real; no se decompiló una función adicional ni se ejecutó el binario del juego dentro de Ghidra.

La cobertura sigue en 552 bloques enlazados. El port completo y la equivalencia de todo el juego continúan sin validar; se mantiene el intérprete/JIT.

## Resultado y decisión

Se hicieron dos parejas desde el mismo estado del primer out, con Vulkan, Clang DOL/MSVC REL, scheduler acelerado y omisión de consultas al gestor vacío en ambas revisiones. No hubo muestreo, perfiles ni lockstep durante las mediciones.

| Pareja | Versión | Sondeo | Fotogramas del juego / segundo real | Mediana de velocidad normal |
|---|---|---|---:|---:|
| 1 | Anterior | `boot-probe-20261009-204909-668` | 28.383037 | 50.64% |
| 1 | Candidato | `boot-probe-20261009-205453-395` | 28.787148 | 48.48% |
| 2 | Anterior | `boot-probe-20261009-210315-715` | 29.880645 | 51.95% |
| 2 | Candidato | `boot-probe-20261009-205728-216` | 28.696230 | 50.16% |

Los cocientes candidato/anterior fueron **+1,42% y −3,96%**. No prueban una ventaja consistente; el candidato se **retiró de la configuración activa**. El ejecutable, mapa, fuente y parche experimentales se conservan para una investigación futura. Se restauraron exactamente el ejecutable anterior (hash comprobado), su mapa y su fuente; la serie activa de 27 parches volvió a pasar la reproducción completa. No se hizo una auditoría adicional contra el intérprete del candidato retirado.

Una orden de parada redundante quedó sin consumir en la primera referencia: el primer Stop ya estaba procesado y el core había cerrado con código 0. El comparador la contabiliza explícitamente sin alterar las evidencias; sigue rechazando órdenes de captura, entrada, memoria o estado pendientes, y cierres fallidos. Pasaron las siete suites de comparación; después de ampliar los guards volvieron a pasar las suites afectadas.

La primera tentativa de referencia inversa (`boot-probe-20261009-210006-231`) mostró la pantalla de título en vez del partido, aunque la orden de carga había sido aceptada. Se excluyó mediante `benchmark-exclusion.json` y no se calculó ni usó su cociente. El ejecutable se había lanzado desde la carpeta de conservación; desde la carpeta habitual, con un nombre distinto y el mismo hash, la repetición sí restauró el primer out. Esto sugiere una dependencia de la carpeta o del entorno de carga, cuya causa exacta no se investigó. La segunda pareja tiene por tanto un intervalo y esa tentativa excluida entre sus dos ejecuciones; tampoco se trata como una prueba estadística concluyente. Las próximas comparaciones exigen la misma carpeta de ejecutable cuando ambas rutas están registradas, y rechazan cualquier sondeo marcado como excluido. La aceptación de una orden no demuestra por sí sola la restauración; deben revisarse las capturas.

Las cuatro sesiones válidas cerraron sin fallos, con capturas completas MEM1/MEM2, y coincidieron los 200.212 campos de reubicación y 7.820.936 bytes de código REL. Sus capturas finales se revisaron visualmente: primer inning, 0–0, un out y corredor en primera. Consolidado: `local/analysis/inline-dol-lookup-validation.json`. Los cambios conservados en las herramientas hacen que las próximas mediciones detecten estas condiciones; no aumentan la cobertura de 552 bloques.

Comprobación final del candidato ya conservado y de la fuente activa restaurada: `inline-dol-lookup-check-20261009-210859-872580/result.json`, 1.540 comparaciones fijas y 1.540 dinámicas sin diferencias. También coinciden los datos del panel, el HTML de vista previa, la cobertura y la serie activa de parches.
