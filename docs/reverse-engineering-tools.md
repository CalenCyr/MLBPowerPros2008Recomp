# Ghidra y REA preparados para este proyecto

9 de octubre de 2026. Instalación solicitada por el usuario en `D:\MLBPowerPros2008Recomp`. Se prepararon herramientas portables, se configuró REA y se comprobaron dos rutas de análisis estático. La evidencia consolidada está en `local/analysis/rea-ghidra-validation.json`.

## Herramientas y configuración

| Componente | Versión | Ubicación |
|---|---|---|
| Ghidra | 12.1.4, versión comprobada por el puente REA instalado | `local/tools/ghidra_12.1.4_PUBLIC/` |
| Java JDK x64, Eclipse Temurin | 21.0.12.1+1 | `local/tools/jdk-21.0.12.1+1/` |
| REA | 6.2.0, instalación existente | La ruta registrada en `config/rea-toolchain.json` |

Las descargas proceden de las publicaciones oficiales de [Ghidra 12.1.4](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build) y [Temurin 21.0.12.1+1](https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.12.1%2B1). Se comprobaron tamaño y SHA256 antes de extraerlas:

- Ghidra ZIP: `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`.
- JDK ZIP: `f9d6e191ab098c0d416e7d588a24420a8621cd2f4720dab2459b8b7b2d2d8b4e`.

Las respuestas de las API oficiales y el manifiesto están en `local/tools/ghidra-release.json`, `temurin-release.json` y `rea-engines-manifest.json`. Las descargas completas se conservaron. Las solicitudes de archivo completo se detenían; se descargaron rangos, se concatenaron en orden y después se verificó el hash completo. La limpieza opcional de los fragmentos fue rechazada por la revisión automática; siguen en `local/tools/rea-download-parts/`.

En `%USERPROFILE%\.codex\config.toml` se añadió únicamente el entorno del servidor REA: `GHIDRA_INSTALL_DIR`, `JAVA_HOME`, `TEMP` y `TMP`, con rutas del proyecto. Se compararon los TOML analizados antes/después: el resto de la configuración coincide. La copia previa está en `local/analysis/config-before-rea-ghidra-20261009-203425.toml`; el cambio exacto queda registrado en `rea-ghidra-configuration-plan.json`. No se modificó el Java del sistema ni su PATH.

`tools/rea.ps1` aplica esas rutas sólo al proceso invocado y restaura el entorno del proceso padre al terminar. Los temporales de REA usan `local/analysis/rea-temp/`. No se reinstaló REA ni se reemplazó la skill.

## Prueba real mediante MCP

Una conexión MCP nueva a REA reconoció Ghidra como disponible y ejecutó `open_binary`, `binary_overview`, `analyze_function` y `close_binary`. Se analizó el ejecutable real `binding_check.exe` que compila el gestor de mods y el fragmento de configuración del proyecto; no es un binario artificial escrito para esta instalación.

- Objetivo Windows x64: 97.792 bytes, SHA256 `76b9cc0c7610d95a83c02c87890defb32af502a5056ae3d3571da57b23590862`.
- Inventario: 376 procedimientos y 175 cadenas.
- Punto de entrada analizado: `0x14000f32c`, con pseudocódigo y desensamblado no vacíos.
- Proveedor observado: Ghidra 12.1.4; servidor: REA 6.2.0.
- Se guardó un snapshot y se cerró la sesión; el hash del ejecutable original no cambió. El ejecutable objetivo no se ejecutó.

Evidencia: `local/analysis/rea-ghidra-smoke-20261009-203449/`. Incluye las respuestas MCP completas, los IDs de evidencia, snapshot, stderr y `result.json`. Los IDs del análisis y del inventario son `ev_e503dd343a7e956ab8061047911c6241a0158cbcd455371a957ee277527468b9` y `ev_dbcd4e8f16d46c4df515b65dd0bb498a90fe32baec4f6f2a65bba167df42fe9d`.

La sesión anterior conservaba su entorno previo; su fotografía histórica está en `local/analysis/rea-codex-session-after-install.json`. Tras el reinicio del usuario, la conexión activa de Codex reconoce Ghidra 12.1.4 y Java 21 como disponibles. Evidencia de la conexión actual: `local/analysis/rea-reconnected-20261009.json`. No hace falta reinstalar las herramientas.

## Ruta comprobada para el PowerPC original de Wii

El puente REA 6.2.0 en Windows admite aplicaciones PE nativas x86/x64; no admite directamente DOL/REL PowerPC ni DLL. Esto es un límite del puente instalado, separado de las capacidades del motor Ghidra.

Se comprobó Ghidra directamente con los **668 bytes** de la función identificada por dtk como `memcpy`, a `0x8000626C` del DOL original extraído. Se conservaron su dirección, offset y hashes en `local/analysis/ghidra-ppc-memcpy/input.json`. La importación usó `PowerPC:BE:32:default` y comprobó que los bytes cargados coincidieran exactamente con los extraídos.

El script recuperó **167 instrucciones** y produjo `assembly.txt` y `pseudocode.c`. El hash del DOL original se volvió a comprobar y coincide. El proyecto temporal de Ghidra se eliminó mediante su propia opción de cierre; se conservaron las salidas y registros. No se ejecutó el código PowerPC.

El nombre y el tamaño de la función proceden del inventario inferido por dtk. Los tipos, firma y texto C recuperados son inferencias del decompilador, no el código fuente original ni una traducción lista para compilar. Esta prueba importa una sola región; no construye una base completa del DOL/REL, no resuelve todos sus contextos externos y no valida comportamiento del juego. Las comprobaciones diferenciales previas de memcpy/memset se conservan como evidencia independiente.

## Reutilizar

Desde la raíz del proyecto:

```powershell
# Consultar el proveedor con las rutas portables del proyecto.
./tools/rea.ps1 providers --format json

# Análisis mediante REA de una aplicación x64 admitida.
./tools/rea.ps1 function 'D:/MLBPowerPros2008Recomp/local/analysis/empty-mod-hooks-check-20261009-200300-632779/build/Release/binding_check.exe' 0x14000f32c --provider ghidra --format json

# Repetir la prueba directa de los bytes PowerPC originales ya extraídos.
./tools/probe-ghidra-ppc.ps1
```

El helper PowerPC está en `tools/ghidra/PowerProsFunctionProbe.java`. Sus artefactos privados están bajo `local/analysis/ghidra-ppc-memcpy/`; el C generado del proyecto recompilado permanece intacto. La instalación no cambia los 27 parches, los 552 bloques enlazados ni las mediciones de rendimiento anteriores.
