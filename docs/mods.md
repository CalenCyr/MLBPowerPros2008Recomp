# Mods

Los mods se activan en el launcher: **MODS** en el menú principal (con el arte MoonInning) o la pestaña **MODS** de Ajustes (con el estilo dibujado). Cada cambio se guarda en `Config.toml` (`[mods] enabled = [...]`) y se aplica al pulsar JUGAR, porque el juego relee los mods al arrancar.

## Dónde van

En la carpeta `mods` junto al ejecutable (`<instalación>\Game\mods`). La fila **ABRIR CARPETA DE MODS** la abre y deja un `LEEME.txt`. Cada mod es una carpeta:

```
mods\
  UniformesHD\
    mod.toml
    textures\      texturas de reemplazo
    disc\          archivos que reemplazan los del disco
    riivolution\   parches Riivolution (.xml)
    project\       paquetes de project.bin (.pack/.dat/.arc) con su nombre
    roster\        un roster de PowerUp / PowerUp+ (.dat)
```

`mod.toml` es opcional; sin él se usa el nombre de la carpeta:

```toml
name = "Uniformes HD"
author = "Tu nombre"
version = "1.0"
description = "Uniformes redibujados a 4x."
```

## Tipos de contenido

- **`textures/`**: reemplazo de texturas con los nombres de Dolphin, `tex1_<ancho>x<alto>_<hash>[_<hash de paleta>]_<formato>.png` o `.dds`. Pueden tener más resolución que la original.
  - Para obtener los nombres, pon en `UserData\Config.toml`, bajo `[video]`, `texture_replacements = true` y `texture_dumps = true`. Juega hasta la pantalla que quieras cambiar: las texturas del juego se exportan a `UserData\Cache\texture_dumps`.
  - Edita la que quieras y guárdala en el `textures/` de tu mod con el mismo nombre.
  - Muchas texturas son atlas, es decir, una imagen con varias piezas; solo se ven las zonas que el juego usa.
- **`disc/`**: archivos con la misma ruta que dentro de la carpeta `files` del disco. Por ejemplo, `disc/sound/SeData.bin` reemplaza `files/sound/SeData.bin` y `disc/project.bin` reemplaza el archivo de contenido (ver abajo).
- **`project/`**: entradas de `project.bin` con su nombre exacto, por ejemplo `project/PWM_mdl_uniform_MLB_BOS_00.pack`.
  - Al arrancar, el juego genera una copia de `project.bin` con esos archivos en `UserData\Cache\mods\disc\project.bin` y la usa en lugar de la del disco.
  - La copia se reutiliza mientras no cambien los mods ni el disco. Generarla tarda menos de un segundo en un SSD y ocupa 406 MB.
  - Si dos mods traen el mismo archivo, gana el primero en orden alfabético.
  - Es la forma correcta de repartir cambios de `project.bin`: el mod solo lleva sus `.pack`, nunca el archivo completo.
- **`roster/`**: un roster de [PowerUp / PowerUp+](https://github.com/ogura-connection/PowerUpPlus) (el `.dat` de MLB Power Pros 2007). El juego lo convierte al formato de 2008 al arrancar y vale para todos los modos, **MLB Life incluido**. Detalles en `docs/roster-2008.md`.
- **`riivolution/`**: XML de Riivolution (`<wiidisc>`) válidos para `RL8E54`. La carpeta del mod hace de raíz de la SD.
  - Los parches de archivos funcionan.
  - Los parches de **memoria** solo sirven para datos: el código del juego ya está traducido a nativo, así que cambiar instrucciones PowerPC en memoria no tiene efecto. Lo mismo pasa con los códigos Gecko/Action Replay que modifican código.

Si dos mods activos reemplazan la misma textura, gana la de `UserData\texture_replacements` y luego el primer mod en orden alfabético.

## `project.bin`

Casi todo el contenido de MLB (modelos, uniformes, menús, estadios, datos) está en `files/project.bin`, un archivo propio de 406 MB con 2.424 entradas (`.pack`, `.dat`, `.arc`). `tools/projectbin.py` lo lee y lo reconstruye:

```
python tools/projectbin.py list    <project.bin>                      # posición, tamaño y ruta de cada entrada
python tools/projectbin.py extract <project.bin> <carpeta> [filtro]   # p. ej. filtro "uniform_MLB_BOS"
python tools/projectbin.py build   <project.bin> <reemplazos> <salida>
```

`build` copia el original y sustituye las entradas cuyo nombre (p. ej. `PWM_mdl_uniform_MLB_CHC_00.pack`) esté en la carpeta de reemplazos, recalculando tamaños y posiciones. Sin reemplazos reproduce el archivo byte a byte. Para jugar no hace falta: basta con poner los `.pack` en `project/` del mod, y el juego hace lo mismo al arrancar (con resultado idéntico al de `build`). `extract` sirve para sacar el original y editarlo.

Para saber qué entrada usa cada pantalla, ejecuta el juego con `WIICOMPILED_DEBUG_DVD=1`: el registro muestra cada lectura de `project.bin` con su posición, que `projectbin.py list` traduce a nombre.

Formato (verificado en las 2.424 entradas): cabecera con versión 2 y sector 0x800; registros de 0x1C bytes en 0x6000 (nombre, sectores, alineación, tamaño); tabla de orden en 0x26000 (registro, sector de inicio); nombres en 0x2B000; datos desde 0x3D800. Los `.pack` empiezan por `PACKWII` (dos por `PACKPS2`) y por dentro son bloques con etiquetas (`SURF`, `SURG`...) y punteros relativos; ese formato interno todavía no está documentado.

Un mod no debe distribuir un `project.bin` completo (es contenido del juego): solo sus `.pack` en `project/`.

## Partidas por roster

Una carrera de MLB Life, una temporada o una liga empezadas con un roster modificado solo tienen sentido con ese roster. Por eso los mods que cambian el roster tienen partidas propias. Cuentan como tales los que traen `roster/` o un `game_data.pack` en `project/`.
- Con uno o más de ellos activos, la carpeta de partidas del juego (`title/00010000/524c3845/data` de la NAND) se lee y escribe en `<datos del usuario>\ModSaves\<mod+mod...>`. Cada combinación tiene la suya.
- Sin ellos, vuelven las partidas normales.
- Los mods de texturas, uniformes (`project/` sin `game_data.pack`), `disc/` o Riivolution usan las partidas normales.
- Si un mod Riivolution define su propio `<savegame>`, ese tiene prioridad.
- Una combinación nueva empieza sin partidas.
- Las partidas jugadas con un roster antes de este cambio quedaron en las normales.
- Parche `wiicompiled-mod-saves`. Usa el mismo redireccionador que el `<savegame>` de Riivolution, pero toma la carpeta de datos del título de disco que aparece en la ruta: el código de juego en memoria baja no dura una vez que el juego corre, y `CurrentNandDataDir` vuelve a `RMCP`.
- Verificado:
  - con Roster2025 activo, el juego busca `pm3usma.dat` en `ModSaves\Roster2025\`;
  - con solo uniformes y texturas, en la NAND normal.
  - La creación de una partida dentro de esa carpeta no se probó todavía.

## Reglas

Un mod solo debe traer sus propios archivos o diferencias, **nunca copias del juego** (ni texturas originales sin modificar, ni `project.bin`, ni el ejecutable).

## Estado

- **Verificado** (12 de octubre de 2026):
  - activar un mod en la pantalla MODS lo guarda y pide reinicio;
  - un mod con `textures/` reemplaza la pantalla de la correa del Wii Remote (`tex1_512x512_fdbf0c48ec7ed2b1_25db17d8ad4d988a_9`);
  - el registro muestra `mods: enabled ...` e `Indexed N texture replacements from 2 folder(s)`.
  - un pack de texturas de Dolphin real (logos y uniformes 2023, 206 texturas) funciona sin cambios como `textures/`;
  - un mod con solo `project/PWM_mdl_uniform_MLB_CHC_00.pack` (el de los Yankees, 6,9 KB) hace que los Cubs salgan con la gorra "NY" en la selección de equipo. El juego genera la copia en 656 ms, la reutiliza en el siguiente arranque y queda idéntica a la de `projectbin.py build` (mismo SHA-256).
- **Sin probar todavía:** `riivolution/` en MLB. Usa el mismo código de Wiicompiled que ya funciona con Mario Kart Wii.
- **Pendiente:**
  - formato interno de `PACKWII` (texturas y modelos);
  - opción en el launcher para volcar texturas sin editar `Config.toml`;
  - mods de código en C++ compilados por el Setup.
