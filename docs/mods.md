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
- **`disc/`**: archivos con la misma ruta que dentro de la carpeta `files` del disco. Por ejemplo, `disc/sound/SeData.bin` reemplaza `files/sound/SeData.bin`.
  - Casi todo el contenido de MLB está en un solo archivo, `project.bin`, de 406 MB, con un formato propio todavía sin documentar.
  - Hasta que exista un extractor, este tipo sirve sobre todo para los archivos sueltos (sonido, videos).
- **`riivolution/`**: XML de Riivolution (`<wiidisc>`) válidos para `RL8E54`. La carpeta del mod hace de raíz de la SD.
  - Los parches de archivos funcionan.
  - Los parches de **memoria** solo sirven para datos: el código del juego ya está traducido a nativo, así que cambiar instrucciones PowerPC en memoria no tiene efecto. Lo mismo pasa con los códigos Gecko/Action Replay que modifican código.

Si dos mods activos reemplazan la misma textura, gana la de `UserData\texture_replacements` y luego el primer mod en orden alfabético.

## Reglas

Un mod solo debe traer sus propios archivos o diferencias, **nunca copias del juego** (ni texturas originales sin modificar, ni `project.bin`, ni el ejecutable).

## Estado

- **Verificado** (12 de octubre de 2026):
  - activar un mod en la pantalla MODS lo guarda y pide reinicio;
  - un mod con `textures/` reemplaza la pantalla de la correa del Wii Remote (`tex1_512x512_fdbf0c48ec7ed2b1_25db17d8ad4d988a_9`);
  - el registro muestra `mods: enabled ...` e `Indexed N texture replacements from 2 folder(s)`.
- **Sin probar todavía:** `disc/` y `riivolution/` en MLB. Usan el mismo código de Wiicompiled que ya funciona con Mario Kart Wii.
- **Pendiente:**
  - formato de `project.bin` (extractor y reemplazo por entrada);
  - opción en el launcher para volcar texturas sin editar `Config.toml`;
  - mods de código en C++ compilados por el Setup.
