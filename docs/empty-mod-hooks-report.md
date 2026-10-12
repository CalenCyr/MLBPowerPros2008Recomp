# Omitir consultas al gestor de mods vacío

Actualización posterior: Ghidra 12.1.4 y Java 21 ya se prepararon en el proyecto, con pruebas MCP x64 y una prueba directa de PowerPC aprobadas. Tras el reinicio, la conexión activa Codex reconoce Ghidra como disponible. Véase `reverse-engineering-tools.md`; el apartado REA de esta investigación conserva el estado previo a la instalación.

9 de octubre de 2026. Proyecto en `D:\MLBPowerPros2008Recomp`; 27 parches reproducibles, 19 de RecompCore y 8 del frontend. Se conservan el código generado y ambas DLL del experimento Clang/MSVC.

## Evidencia que orientó el cambio

La sesión `boot-probe-20261009-195340-918` restauró el primer out con Clang DOL / MSVC REL, scheduler acelerado y diagnóstico de etapas. Registró 3.711 direcciones, sin muestras descartadas. Se observaron 470.124.169 despachos fuera del intervalo REL y 43.386.615 dentro; esos contextos no identifican costes exclusivos de funciones.

El muestreo simultáneo `host-sample-20261009-195501-387` recogió 3.100 posiciones del hilo CPU-GPU durante 56,952 s antes de que terminara el proceso. Hubo 16 intervalos sin ciclos y un intento fallido; las suspensiones acumularon 0,372 s. La DLL apareció en 44,13% de las muestras y el ejecutable en 30,13%. Las etiquetas más próximas del mapa situaron 3,26% en `ModManager::Dispatch` y 2,06% en `ModManager::HandlesAddress`. Son fracciones de muestras de un hilo con diagnóstico activo, sin atribución exclusiva de CPU ni un porcentaje de mejora. No se usa esta sesión para comparar velocidad.

La lectura del código confirmó la causa evitable: el frontend enlaza callbacks del gestor aun cuando no haya cargado ningún mod. Cada `dolrecomp_call` del DOL consulta ese callback antes de despachar código original; el core consulta además si una dirección necesita interceptarse. El C generado permanece intacto.

## Cambio y límites

`moderngekko-empty-mod-hooks.patch` añade una opción experimental de inicio. Con `STATICRECOMP_POWERPROS_SKIP_EMPTY_MOD_HOOKS=1` y `ModManager::Empty()==true`, el frontend conserva a null los callbacks de llamada, dirección y rango y su contexto. La DLL y el core emplean sus ramas existentes sin callback. El modo predeterminado conserva las conexiones anteriores.

Si existe cualquier mod cargado se conservan todos los callbacks, incluidos los de un mod que sólo atiende eventos y necesita `runtime_start`. No se usa `HasGuestInterception()` como sustituto de `Empty()`. Los mods se cargan antes de configurar el core, el gestor es propiedad privada de Runtime y la interfaz actual no ofrece carga de mods en vivo; si esa arquitectura cambia deberá revisarse esta decisión de inicio.

El lanzador acepta `-SkipEmptyModHooks`, restaura la variable de entorno del padre después de crear el proceso y guarda la opción solicitada junto con la confirmación del runtime y el número de mods cargados. El sondeo utiliza `--no-mods`. La confirmación registra explícitamente si se omitieron los callbacks; pedir la opción no basta para atribuirle un efecto.

## Pruebas reproducibles

`tools/check_empty_mod_hooks.py` compila el fragmento real de configuración y el gestor real de mods. La prueba previa falló en las tres configuraciones vacías que seguían conectando callbacks; pasó después de la corrección. Las 14 comprobaciones incluyen gestor vacío, opción predeterminada/inválida, mods rechazados, nueva configuración después de descargar, parches, hooks y un mod de eventos cuyo aviso de inicio conserva el estado del invitado. También ejecuta la parte de descriptores adjuntos de las pruebas upstream: dependencias, ABI, imports, hooks de retorno, eventos y descarga. No ejecuta la carga de DLL de mods ni el arranque de hardware en ese harness.

Resultado: `empty-mod-hooks-check-20261009-200300-632779/result.json`; los 14 resultados están en `build/Testing/Temporary/LastTest.log`. Pasaron la compilación del runtime y la reproducción completa en `runtime-patch-replay-20261009-200350`.

`tools/compare_empty_mod_hooks_speed.py` exige runtime, módulo, estado y condiciones idénticos y la confirmación OFF/ON con cero mods cargados. Sus fixtures comprueban el cociente y 31 rechazos. Los comparadores generales rechazan la opción activada para que no contamine otras mediciones; las seis suites de comparación pasaron tras ampliar ese guard.

La auditoría de bloques exige declarar `--allow-empty-mod-hooks` para comprobar esta opción, con la misma confirmación de inicio. Los fixtures del auditor validan esa declaración y 41 rechazos de registros incompletos o contaminados. Esto no cambia los registros, memoria ni MMIO que compara el auditor.

## Medición y auditoría en el juego

Se completaron dos parejas de 120 s, OFF→ON y ON→OFF, desde el mismo estado privado del primer out, sin pulsar controles. Ambas usan Vulkan, Clang DOL / MSVC REL, scheduler acelerado y cero mods cargados. No se activaron perfiles, muestreo del host, batching ni lockstep durante la medición de velocidad.

| Pareja | Opción | Sondeo | Ventana medida (s) | Fotogramas del juego | Fotogramas del juego / s real | Mediana de velocidad normal |
|---|---|---|---:|---:|---:|---:|
| 1 | OFF | `boot-probe-20261009-200501-603` | 109.759 | 3013 | 27.450971 | 46.64% |
| 1 | ON | `boot-probe-20261009-200721-907` | 110.297 | 3262 | 29.574651 | 51.33% |
| 2 | OFF | `boot-probe-20261009-201251-574` | 109.898 | 3000 | 27.298027 | 47.26% |
| 2 | ON | `boot-probe-20261009-201032-901` | 110.074 | 3338 | 30.325000 | 52.55% |

Los cocientes ON/OFF fueron **1.077363 (+7.74%)** y **1.110886 (+11.09%)**. Las medianas ON fueron **51.33% y 52.55% de velocidad normal**. Son dos comparaciones de esta escena y este PC, con variación entre ejecuciones; no son FPS renderizados, garantía de ganancia en todos los modos ni porcentajes que se sumen a la mejora histórica de Clang. Las cuatro capturas finales se inspeccionaron: primer inning, marcador 0–0, un out y corredor en primera.

En una sesión separada de 90 s, `boot-probe-20261009-201511-691`, se desactivó el scheduler acelerado y se auditó la opción ON contra el intérprete con ventana configurada de 5–6 millones de despachos. El contador final fue 5.098.584; no se alcanzó el límite superior de 6 millones. Se registraron **3.505 comparaciones completas sin diferencias**, con 39 entradas omitidas (13 por fallback y 26 sin bloque ejecutado). Las tres entradas exigidas `0x80081CB4`, `0x800BFB38` y `0x800C1188` alcanzaron sus límites con ciclos coincidentes. Las omitidas y rutas no visitadas permanecen sin validar; no demuestra equivalencia de todo el juego.

Las cinco sesiones cerraron con salida 0, sin terminación forzada, órdenes fallidas ni verificaciones de código fallidas, con MEM1/MEM2 completos. Coincidieron todos los **200.212 campos de reubicación** y **7.820.936 bytes de código REL**. Cada directorio conserva los registros del comprobador de cierre, inspector REL y validador de reubicaciones. Los dos JSON de comparación son `local/analysis/empty-mod-hooks-speed-comparison-20261009-200959-904537.json` y `local/analysis/empty-mod-hooks-speed-comparison-20261009-201510-662211.json`; el resultado consolidado está en `local/analysis/empty-mod-hooks-validation.json`.

Ejecutable de esta tanda: SHA256 `40353ecb8ccc32f3c5ea86daf89010826be4b9a837bfd9defb0f731fe812715a`. DLL conservada: SHA256 `09296c1d72e4bb44080572964a1b664f148e2142cf691c04503258596f119357`. Estado privado: SHA256 `5158bc08a5e58986bf5313277e0676b4cad0b77cecacbdf442313f67020eed14`. No cambió la cobertura de 552 bloques enlazados y sigue siendo necesario el intérprete/JIT.

### Repetir la comprobación

Desde la raíz del proyecto, con el runtime y la DLL ya compilados:

```powershell
$py = 'python'
$state = 'local/analysis/boot-probe-20261008-205240-719/control/artifacts/pitch-result-state.sav'
$off = ./tools/probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -ClangModule -SchedulerIdleSkip -LoadState $state -SnapshotMemory -Screenshot -CaptureIntervalSeconds 10 -PassThru
$on = ./tools/probe-boot.ps1 -Seconds 120 -Graphics Vulkan -RelModule -OptimizedModule -ClangModule -SchedulerIdleSkip -SkipEmptyModHooks -LoadState $state -SnapshotMemory -Screenshot -CaptureIntervalSeconds 10 -PassThru
& $py tools/compare_empty_mod_hooks_speed.py $off.probe_directory $on.probe_directory
$audit = ./tools/probe-boot.ps1 -Seconds 90 -Graphics Vulkan -RelModule -OptimizedModule -ClangModule -SkipEmptyModHooks -LoadState $state -SnapshotMemory -Lockstep -LockstepStart 5000000 -LockstepLimit 6000000 -LockstepTracePC 4294967295 -CaptureIntervalSeconds 10 -PassThru
& $py tools/check_lockstep_probe.py $audit.probe_directory --require-entry 0x80081CB4 --require-entry 0x800BFB38 --require-entry 0x800C1188 --allow-empty-mod-hooks
```

Repetir la pareja en orden ON→OFF para comprobar el efecto del orden. Validar cada directorio con `check_probe_shutdown.py`, `inspect_runtime_rel.py` y `validate_runtime_relocations.py`; revisar también ambos booleanos de coincidencia REL y las capturas. No usar la auditoría para medir rendimiento. La opción permanece **desactivada por defecto**.

## Uso de reverse-engineer-anything

Se aplicó la skill solicitada para separar observaciones, inferencias y límites de la investigación. El servidor REA está conectado (6.2.0), pero su inspección nativa no está disponible: Ghidra no está configurado y el Java encontrado es un JRE 8; IDA no está configurado y Hopper no admite este host Windows. Se conserva el estado resumido en `local/analysis/rea-native-availability.json`.

No se abrió ni decompiló ningún binario mediante REA y no se cambió su configuración. Esta corrección usa las fuentes completas disponibles, el mapa del mismo ejecutable y la medición del proceso real. Las etiquetas de la DLL Clang no se resolvieron por función porque esa DLL no tiene mapa. El ejecutable y mapa originales del muestreo se preservaron antes de recompilar en `host-sample-20261009-195501-387/preserved/`.
