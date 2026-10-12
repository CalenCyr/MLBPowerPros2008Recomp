# Perfil por instrucción PPC del código traducido

Fecha: 9 de octubre de 2026.

## Método

`tools/analyze_host_ppc_lines.py` atribuye muestras del hilo CPU-GPU a direcciones PPC. Usa una variante de la DLL Clang compilada con `-gline-tables-only` y enlazada con `/DEBUG /OPT:REF /OPT:ICF` (`local/build/runtime-module-rel-clang-lines/`). Resuelve RIP → línea C con `dbghelp` y toma el comentario `// XXXXXXXX:` anterior como instrucción invitada. Las funciones salen de `local/analysis/dol-functions.csv`.

La variante conserva la disposición y el tamaño de las secciones ejecutables. Difiere en **184 bytes** de código, en dos zonas de GXRuntime: desplazamientos RIP-relativos hacia `.rdata`, que creció 0x88 bytes con el directorio de depuración. El analizador rechaza cualquier diferencia que supere el umbral declarado (`--allow-differing-bytes 184`) y la registra en `ppc-lines.json`.

Se usó el muestreo `host-sample-20261009-193251-398` (3.251 posiciones, DLL `09296c1d…`). De sus 1.708 muestras en la DLL, 709 quedan sin línea: objetos REL de MSVC reutilizados sin tablas y helpers.

## Resultado

El coste está repartido. Las funciones DOL con más muestras:

| Función | Muestras |
|---|---:|
| `fn_80126AE8` (584 bytes) | 2,37% |
| `__fill_mem` | 1,57% |
| `fn_800BFB24` | 1,17% |
| `fn_800BC3AC` | 0,98% |
| `SelectThread` (espera del planificador del SO invitado) | 0,77% |

Ninguna función domina, así que reemplazar funciones sueltas por código nativo daría ganancias pequeñas.

## Causa sistémica

En el desensamblado del bucle caliente de `fn_80126AE8` (`0x80126BEC–0x80126C1C`), cada lectura y escritura de `ctx->gpr[]`, `ctx->cr` y `ctx->downcount` es un acceso a memoria. No se mantiene ningún registro PPC en registros x64; por ejemplo, aparece `shl dword ptr [rsi],1`.

El origen está en el generador C de DolRecomp:

- Cada bloque empieza con `switch (ctx->pc)` y **un `case` por instrucción**: 4.180 en `chunk_0072`. Todas las etiquetas son entradas posibles, así que los bucles tienen varias entradas (CFG irreducible) y LLVM no puede promover el estado a registros.
- `clang-cl` desactiva el strict aliasing y las escrituras a RAM invitada usan `u8*`, por lo que cualquier store puede afectar al estado de la CPU.
- El generador extrae a `static void loop_XXXX(CPUState*)` solo los bucles de un único bloque básico (`c_cfg.c`, `straight_line`). Esos tampoco guardan registros en variables locales.

El backend LLVM de DolRecomp (`src/backend/llvm/register_state.cpp`) promueve el estado de la arquitectura a SSA. Requiere librerías de desarrollo de LLVM 19/20, y su salida `--runtime moderngekko` usa otra ABI de entrada que el módulo actual de `StaticRecompCore`. Existe también `--runtime recompcore`, sin evaluar.

## Alcance

Son fracciones de muestras de un hilo, sin atribución exclusiva de CPU. No se cambió código del juego ni del generador en esta tanda.
