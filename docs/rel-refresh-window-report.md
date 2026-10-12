# Refresco REL sin reparseo con cabecera fija

Fecha: 10 de octubre de 2026. Serie de **34 parches reproducibles**.

## Coste identificado

Muestreo `host-sample-20261010-122318-963`: 3.237 muestras del hilo CPU-GPU, módulo todo LLVM, mapa privado `clang-module-map-20261010-162202-019404` con código ejecutable idéntico. `RefreshRelSections` sumaba el **2,26%**. A eso se añadían las operaciones de `std::vector<ActiveRelSection>` en VCRUNTIME/ucrtbase.

Causa: cada consulta que no cae en el REL activo ni en un bloque DOL vuelve a llamar a `RefreshRelSections`. Ocurre con las invalidaciones de caché de datos y con los PC de los vectores de excepción (`0x500`/`0x800`/`0xC00`, ~1M ejecuciones del JIT de respaldo). Con `POWERPROS_FIXED_REL_HEADER=0x80575580u`, el recorrido solo lee la cabecera y la tabla de secciones: `[cabecera, cabecera + max(0x40, fin_de_tabla))`, unos 212 bytes. El resto son metadatos constantes del módulo. Aun así, se reparseaba y comparaba en cada fallo.

## Cambio

`tools/patches/recompcore-rel-refresh-window.patch`, solo con cabecera fija:

- Copia esa ventana de bytes a un búfer miembro.
- Si coincide con la del último refresco y hay un mapa activo, el resultado sería idéntico y vuelve sin reparsear.
- Si el mapa está vacío o se limpió desde fuera, siempre reparsea. Antes de cargar el REL el coste es el de antes.
- La carga del módulo invalida la ventana.

El modo dinámico, sin cabecera fija, no cambia.

## Pruebas

- Reproducción completa de los 34 parches: `runtime-patch-replay-20261010-162929`.
- `tools/check_rel_detector.py` con el snapshot `boot-probe-20261009-045301-227`, en modo dinámico y con `--fixed-layout`: **ALL CHECKS PASSED** en los dos. Las pruebas incluyen descarga y recarga, tabla ajena y movimientos de sección; todas modifican los bytes de la ventana. Se añadieron los tres miembros nuevos al fixture.
  - La primera versión fallaba en `cold-map refresh`, porque el fixture vacía el mapa con la RAM sin cambios. Por eso la reutilización exige un mapa activo.
- El código traducido y la DLL no cambian.

## Resultado

Muestreo con el ejecutable nuevo (`host-sample-20261010-124020-199`):

| | Antes | Después |
|---|---:|---:|
| `RefreshRelSections` | 2,26% | 0,37% |
| `moderngekko-run.exe` (total) | 24,7% | 22,0% |
| DLL (código del juego) | 51,8% | 54,2% |

Velocidad en parejas ABBA de 120 s, misma DLL todo LLVM, ejecutable anterior conservado como `moderngekko-run-before-rel-window.exe`. Muestras: `boot-probe-20261010-163013-846` / `-163234-672` / `-163453-410` / `-163712-946`. Cocientes: **+4,36% y −0,23%**. La reducción de coste está confirmada por el muestreo. La ganancia de velocidad (~2% esperado) queda dentro de la variación entre sesiones, así que no se reclama una cifra.

## Costes restantes en el mismo muestreo

- **Espera de GPU, ~12%** (`ntdll`). Es `Vulkan::StreamBuffer::WaitForClearSpace` → `WaitForCommandBufferCompletion`, con IR 3x en el perfil de sondeo. El modo dual core solapa ese trabajo.
- **Helpers flotantes, 4,63%.** El backend LLVM emite todas las operaciones escalares (`fadds`, `fmuls`, `fsubs`, `fmadd`, `fctiw`…) como llamadas exactas a `cpu_interpreter_float.c`, sincronizando los slots implicados.
- **Consulta por despacho, ~3%.** `ChunkIndexOf` 1,95% y `ResolveNativeAddress` ~1,3%. Con disposición fija, la resolución antes y después de cada despacho es la identidad.

Las atribuciones de llamadas al sistema vienen del escaneo de pila sin desenrollado. Un retorno antiguo en la pila puede dar un llamador falso.
