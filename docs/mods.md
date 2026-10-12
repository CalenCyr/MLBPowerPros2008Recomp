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

`build` copia el original y sustituye las entradas cuyo nombre (p. ej. `PWM_mdl_uniform_MLB_CHC_00.pack`) esté en la carpeta de reemplazos, recalculando tamaños y posiciones. Sin reemplazos reproduce el archivo byte a byte. El resultado va en `mods/<mod>/disc/project.bin`.

Para saber qué entrada usa cada pantalla, ejecuta el juego con `WIICOMPILED_DEBUG_DVD=1`: el registro muestra cada lectura de `project.bin` con su posición, que `projectbin.py list` traduce a nombre.

Formato (verificado en las 2.424 entradas): cabecera con versión 2 y sector 0x800; registros de 0x1C bytes en 0x6000 (nombre, sectores, alineación, tamaño); tabla de orden en 0x26000 (registro, sector de inicio); nombres en 0x2B000; datos desde 0x3D800. Los `.pack` empiezan por `PACKWII` (dos por `PACKPS2`) y por dentro son bloques con etiquetas (`SURF`, `SURG`...) y punteros relativos; ese formato interno todavía no está documentado.

Un mod no debe distribuir un `project.bin` completo (es contenido del juego). Lo correcto es repartir solo los `.pack` propios y que cada jugador genere su `project.bin` con `build` a partir de su disco; el siguiente paso es que el runtime lo haga solo al activar el mod.

## Reglas

Un mod solo debe traer sus propios archivos o diferencias, **nunca copias del juego** (ni texturas originales sin modificar, ni `project.bin`, ni el ejecutable).

## Estado

- **Verificado** (12 de octubre de 2026):
  - activar un mod en la pantalla MODS lo guarda y pide reinicio;
  - un mod con `textures/` reemplaza la pantalla de la correa del Wii Remote (`tex1_512x512_fdbf0c48ec7ed2b1_25db17d8ad4d988a_9`);
  - el registro muestra `mods: enabled ...` e `Indexed N texture replacements from 2 folder(s)`.
  - un pack de texturas de Dolphin real (logos y uniformes 2023, 206 texturas) funciona sin cambios como `textures/`;
  - `disc/project.bin` reconstruido con el uniforme de los Yankees en el lugar de los Cubs: en la selección de equipo los Cubs salen con la gorra "NY".
- **Sin probar todavía:** `riivolution/` en MLB. Usa el mismo código de Wiicompiled que ya funciona con Mario Kart Wii.
- **Pendiente:**
  - que el runtime genere el `project.bin` con los `.pack` de los mods (hoy hay que hacerlo con `projectbin.py build`);
  - formato interno de `PACKWII` (texturas y modelos);
  - opción en el launcher para volcar texturas sin editar `Config.toml`;
  - mods de código en C++ compilados por el Setup.
