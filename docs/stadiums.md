# Estadios en Blender

El complemento **«Estadios de MLB Power Pros 2008»** abre en Blender cualquier estadio de tu juego: cada pieza en su sitio y con sus texturas, y la malla de colisión del campo.

Por ahora solo importa. Volver a meter un estadio editado en el juego es la siguiente fase; el formato está descrito en `docs/ingenieria-inversa.md`, sección 5, «Estadios».

## Instalar

1. Necesitas **Blender 4.2 o más nuevo** ([blender.org](https://www.blender.org/download/)).
2. Consigue el complemento, un zip llamado `powerpros_stadium-<versión>.zip`. Para crearlo desde el repositorio: `python tools/blender/build_addon.py` (queda en `local/build/blender/`).
3. En Blender: **Editar > Preferencias > Obtener extensiones**. En el menú ⌄ de arriba a la derecha elige **Instalar desde disco…** y selecciona el zip.

## Importar un estadio

1. **Archivo > Importar > Estadio de Power Pros 2008**. También está en la barra lateral de la vista 3D (tecla N), pestaña **Power Pros**.
2. Elige la **carpeta del juego** instalado con el Setup (la que tiene `UserData`) o directamente el archivo `files/project.bin`.
3. En el panel de la derecha elige el **estadio**, deja marcada **Incluir colisión** si la quieres y pulsa **Importar estadio**.

Tarda unos segundos. No se extrae nada al disco: todo se lee del `project.bin` de tu juego.

## Qué obtienes

- **Una colección por estadio** (por ejemplo «Colorado Rockies — Coors Field») con **un objeto por pieza**, con el nombre que les dio el juego:
  - `DP_ground`: tierra;
  - `DP_MIP_turf`: césped;
  - `DP_stand_*`: gradas;
  - `DP_fence_*`: vallas;
  - `DP_score`: marcador;
  - `DP_auroravision`: pantalla;
  - `DP_Audience*`: público;
  - `DP_FLG_*`: banderas.
- **Escala real:** 1 unidad de Blender = 1 metro. Z hacia arriba, el plato en el origen y el center field hacia +Y.
- **Materiales como en el juego:** textura × color de vértice, sin iluminación. Las piezas con transparencia (`*_ALP_*`) se mezclan y las `*_ADD_*` suman luz. Para verlas así usa la vista **Material** (Z > Vista previa de material).
- **Texturas** empaquetadas dentro del `.blend`.
- **Colisión**, en la subcolección «… · Colisión», oculta al importar (actívala con el ojo):
  - es la malla con la que el juego decide por dónde rebota la pelota;
  - cada cara tiene un `surface_id` y un color por tipo (césped, tierra, montículo, vallas, gradas, postes de foul…; ver la tabla en `docs/ingenieria-inversa.md`).
- **Panel Power Pros (N):** la pieza seleccionada, su modelo original, el nodo de Maya y los flags de colocación. En la colisión, la superficie de la cara activa.

Las propiedades personalizadas `pp_*` de objetos y materiales guardan los datos originales que necesitará la exportación. No las borres si quieres volver a meter el estadio en el juego.

## Reglas

Los `.blend` con estadios importados contienen modelos y texturas del juego. Úsalos para tu mod, pero **no los compartas**. Un mod de estadio repartirá solo sus `.pack` modificados, igual que los uniformes (`docs/mods.md`).

## Para desarrolladores

- `python tools/blender/powerpros_stadium/selftest.py`: autotest de los lectores, sin datos del juego.
- `python tools/stadium_re.py check <project.bin>`: comprueba los 47 packs de estadio. `info` y `stats` dan resúmenes e histogramas de lo que falta por descifrar.
- **Prueba completa dentro de Blender** (Blender 4.2 LTS portátil en `local/tools/`):

  ```
  set BLENDER_USER_RESOURCES=<carpeta temporal>
  blender --background --factory-startup --python tools/blender/test_import.py -- <zip> <project.bin> col <carpeta de salida>
  ```

  Instala el zip, importa Coors Field, compara piezas, caras, texturas y colisión con lo que dicen los packs, y renderiza una vista cenital y otra desde el plato.
