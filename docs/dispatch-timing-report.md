# Medir las etapas del despacho nativo — 9 de octubre de 2026

El parche `recompcore-dispatch-timing.patch` añade un diagnóstico opcional para medir la resolución de entrada, ejecución del módulo y conversión de regreso. La serie alcanza **21 parches reproducibles: 14 del core y 7 del frontend**. Esta tanda aporta medición; no se le atribuye una mejora de velocidad.

`tools/probe-boot.ps1 -ProfileDispatchTiming` activa el diagnóstico y guarda `dispatch-timing.csv` al cerrar. Sin esa opción está desactivado: no consulta el reloj ni acumula muestras de tiempo durante los despachos. El sondeo establece el entorno del proceso hijo y restaura el valor anterior del padre. La rama sin medición conserva las operaciones de despacho existentes. No se modificaron las instrucciones generadas, la DLL del juego ni la cobertura de 552 bloques y 9.021.384 bytes enlazados experimentalmente.

## Alcance de la medición

Se toma una muestra cada 4.096 despachos en cada uno de dos contextos: dentro o fuera del intervalo que contiene las secciones REL. Estar dentro no demuestra pertenencia a una sección: puede incluir huecos o datos. La clasificación solo agrupa muestras; la resolución y los guards reales conservan su implementación.

Las tres etapas usan intervalos de tiempo transcurrido en el hilo que ejecuta el código del juego. La ejecución del módulo incluye sus callbacks de instrucciones. Los agregados son de tamaño fijo y el archivo se escribe únicamente al cerrar. Una calibración de 10.000 pares vacíos de consultas al reloj informa el coste de medición; no se resta automáticamente.

Los porcentajes corresponden únicamente a la suma de esas tres etapas muestreadas. No representan todo el tiempo de CPU, el presupuesto de un fotograma, FPS renderizados, cobertura nativa ni porcentaje de finalización. Quedan fuera los guards previos al despacho, planificador, JIT, hilo gráfico y otras tareas. Las muestras periódicas pueden estar sesgadas e incluyen pausas del sistema, preparación, restauración y apagado. Falta un perfil completo que compare CPU y GPU y atribuya tiempo a funciones concretas.

WPR rechazó el inicio de una captura completa con `0xc5585011`, por la política de perfilado del sistema; una consulta posterior confirmó que no quedó una captura activa. No se alteró la política. Este diagnóstico interno permite avanzar con un alcance menor y explícito.

## Resultado de la prueba corta

`boot-probe-20261009-150640-247` restauró el estado privado del primer out: 0–0 y corredor en primera. Ejecutó 120,01 segundos con Vulkan, DLL optimizada, entrada física aislada y la opción experimental del planificador activada. No se enviaron controles para avanzar el inning. Hubo 354.305.137 despachos nativos: 326.036.471 fuera del intervalo REL y 28.268.666 dentro.

| Etapa | Media cruda fuera del intervalo REL | Media cruda dentro del intervalo REL | Fracción cruda de las tres etapas |
| --- | ---: | ---: | ---: |
| Resolución de entrada | 52,21 ns | 55,93 ns | 13,86% |
| Ejecución del módulo, incluyendo callbacks | 299,35 ns | 351,78 ns | 80,14% |
| Conversión de regreso | 22,67 ns | 23,47 ns | 6,00% |

Se reunieron **86.499 muestras por etapa**: 79.598 fuera y 6.901 dentro. La calibración del par de consultas al reloj fue **21,11 ns**. La conversión de regreso está muy cerca de ese coste; su fracción cruda no permite atribuir un coste real de esa magnitud a la conversión. Los máximos contienen valores mucho mayores que las medias y no se interpretan como costes exclusivos de funciones.

La ejecución del módulo y sus callbacks es la siguiente zona que conviene investigar dentro de este subconjunto. Falta separar las funciones y callbacks que concentran tiempo antes de escoger una sustitución nativa o un cambio de generación. Este informe no identifica todavía una función concreta ni promete una ganancia.

`tools/analyze_dispatch_timing.py` comprueba filas, contadores, stride, calibración, límites de agregados y coincidencia de despachos con el contador de cierre. Escribió el informe privado `boot-probe-20261009-150640-247/dispatch-timing-report.json`. SHA256 del CSV: `4ae3d7f5c2b79c24d8064e4bb223cc06db0731f53f423d5e6fcaab26f69cff89`.

## Integración y pruebas

La compilación Release pasó en `local/analysis/moderngekko-dispatch-timing-build.log`. La reproducción contra revisiones fijadas coincidió con las fuentes actuales: `runtime-patch-replay-20261009-150551/result.json`, 21 parches. Ejecutable: SHA256 `e7bd7269c12432c59e814e3463bc5ad0f3d6267bf1fa3e6995e4c8d732e0053c`. La DLL conserva SHA256 `393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6`.

- `check_dispatch_timing.py` compiló el helper real y el fragmento real de despacho con un módulo y conversiones sintéticos. Comprobó desactivación, reset, muestreo separado, entradas/resultados conservados en ramas muestreadas y normales, ausencia de REL, índices inválidos y fallo de escritura. No sustituye la ejecución real ni prueba por sí solo la resolución REL.
- `check_dispatch_timing_report.py` comprobó aritmética, calibración y 13 rechazos de perfiles corruptos.
- `check_runtime_probe_comparison.py` pasó con 23 rechazos de condiciones incompatibles; `check_scheduler_probe_comparison.py`, con 8. Las comparaciones de velocidad rechazan sondeos con este perfil activado para evitar confundir medición con rendimiento.
- El sondeo con medición cerró con salida 0, sin terminación forzada, órdenes fallidas ni fallos de verificación de código. Pasó la comprobación de cierre y coincidieron los 200.212 campos de reubicación y los 7.820.936 bytes de código REL. La captura final se revisó: lanzamiento, 0–0, un out y corredor en primera.
- `boot-probe-20261009-151007-293` comprobó el valor predeterminado en el menú principal durante 60,48 segundos, con Vulkan y la misma DLL/ejecutable. Planificador y medición estaban desactivados. Cerró correctamente, con memoria completa y sin fallos; coincidieron todos los campos y bytes REL. La imagen revisada conserva el menú con Exhibition seleccionado. No se produjo un CSV de tiempos.
- Ambas pruebas comprobaron la restauración del entorno padre. En la prueba predeterminada se eliminó del hijo un valor de perfilado heredado, por lo que no activó accidentalmente la medición.

Evidencia consolidada privada: `local/analysis/dispatch-timing-validation.json`. Conserva resultados, hashes de capturas revisadas y rechazos sobre los sondeos reales. La opción del planificador sigue desactivada por defecto. El juego continúa utilizando intérprete/JIT de apoyo; siguen pendientes rendimiento jugable, audio, bateo y defensa del jugador, partido completo y ejecución exclusivamente nativa.

## Repetir el diagnóstico

Desde la carpeta del proyecto, con los datos privados disponibles:

```powershell
python tools/check_dispatch_timing.py
python tools/check_dispatch_timing_report.py
python tools/check_runtime_patches.py
.\tools\probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -Screenshot -SnapshotMemory -LoadState 'ruta\al\estado.sav' -ProfileDispatchTiming
python tools/analyze_dispatch_timing.py 'ruta\al\nuevo-sondeo'
python tools/check_probe_shutdown.py 'ruta\al\nuevo-sondeo'
python tools/inspect_runtime_rel.py 'ruta\al\nuevo-sondeo'
python tools/validate_runtime_relocations.py 'ruta\al\nuevo-sondeo'
```

La muestra de este informe añadió `-SchedulerIdleSkip`; hay que mantener esa condición al intentar reproducirla. Para comparar velocidad se deben ejecutar sondeos separados con el perfil desactivado y condiciones iguales. Las capturas requieren revisión visual.
