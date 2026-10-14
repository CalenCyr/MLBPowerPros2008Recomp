# Estadios en Blender

El complemento **«Estadios de MLB Power Pros 2008»** abre en Blender cualquier estadio de tu juego: cada pieza en su sitio y con sus texturas, y la malla de colisión del campo.

También **exporta**: lo que cambies en las piezas del estadio vuelve al juego como un mod. Añadir piezas nuevas y mover las vallas de verdad (la colisión) son las fases siguientes. El formato está descrito en `docs/ingenieria-inversa.md`, sección 5, «Estadios».

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

## Exportar al juego

1. Edita lo que quieras de las piezas importadas:
   - mover, girar o escalar piezas;
   - editar su malla (también añadir o quitar caras dentro de una pieza);
   - pintar o cambiar sus imágenes;
   - asignarles otros materiales del mismo estadio;
   - borrar piezas.
2. **Archivo > Exportar > Mod de estadio de Power Pros 2008**, o el botón **Exportar mod de estadio** del panel Power Pros.
3. Rellena el diálogo:
   - **Nombre del mod**;
   - **Carpeta de mods**: si importaste desde la carpeta del juego, ya viene puesta (`<juego>\mods`);
   - **Reemplaza a**: el mismo estadio, u otro. Por ejemplo, puedes poner tu Coors Field editado en el hueco de Turner Field.
4. Activa el mod en **MODS** del launcher y juega un partido en ese estadio.

Qué hace al exportar:
- Escribe `mods\<nombre>\project\stadium_<código>.pack` y `stadium_<código>tbl.pack`, más un `mod.toml`.
- **Solo reescribe las piezas que cambiaste**; el resto queda idéntico al original. Lo nuevo se añade al final del pack.
- Una pieza borrada se queda sin geometría.
- Una imagen editada o nueva se guarda como textura RGB5A3. Si sus lados no son potencias de 2, se reescala a la más cercana (4 a 1024).
- Si mueves una pieza, actualiza su caja y su esfera en la tabla, para que el juego no la oculte cuando entra en cámara.
- **Límite de tamaño:** un pack de gráficos de 21 MB carga en un partido y uno de 31,5 MB no. El original pesa 1,1 MB. Si pasas de 20 MB, el exportador avisa.

Aún no:
- piezas nuevas (objetos que no vinieron del juego), que se ignoran al exportar;
- cambios en la colisión.

Un material nuevo con una imagen sí se exporta: se crea en la pieza con esa imagen como textura nueva.

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
- **Exportación de ida y vuelta** (`tools/blender/test_export.py`, mismos argumentos con la carpeta de mods al final):
  1. importa Coors Field y le hace cuatro cambios: sube `DP_stand_C` 15 m, sube la geometría de `DP_score` 10 m, borra una bandera y tiñe la imagen de `DP_ground`;
  2. exporta el mod `BlenderTest`;
  3. relee los packs y comprueba cada cambio.

  El mod resultante, cargado en un partido, muestra los cuatro cambios.
