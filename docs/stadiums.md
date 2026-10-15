# Estadios en Blender

El complemento **«Estadios de MLB Power Pros 2008»** abre en Blender cualquier estadio de tu juego: cada pieza en su sitio y con sus texturas, y la malla de colisión del campo.

También **exporta**: lo que cambies en las piezas y en la colisión vuelve al juego como un mod. Y puede meter en el juego **un estadio tuyo** hecho en SketchUp, Blender u otro programa (ver «Tu propio modelo»). El formato está descrito en `docs/ingenieria-inversa.md`, sección 5, «Estadios».

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
   - **Tipo**:
     - **Estadio nuevo** (predeterminado): se **añade** a la elección de estadio de Exhibición y no quita ninguno. Pide un **código** corto (letras minúsculas, números o _, por ejemplo `truist`) y un **nombre**. Usa los datos de juego del estadio importado: medidas, menú y partidas;
     - **Reemplazar un estadio**: sustituye al mismo estadio o a otro. Por ejemplo, puedes poner tu Coors Field editado en el hueco de Turner Field.
4. Activa el mod en **MODS** del launcher. Un estadio nuevo aparece en Exhibición al elegir estadio, después de los del juego (con la izquierda desde el primero llegas antes).

Qué hace al exportar:
- Escribe `mods\<nombre>\project\stadium_<código>.pack` y `stadium_<código>tbl.pack`, más un `mod.toml`.
- **Solo reescribe las piezas que cambiaste**; el resto queda idéntico al original. Lo nuevo se añade al final del pack.
- Una pieza borrada se queda sin geometría.
- Una imagen editada o nueva se guarda como textura RGB5A3. Si sus lados no son potencias de 2, se reescala a la más cercana (4 a 1024).
- Si mueves una pieza, actualiza su caja y su esfera en la tabla, para que el juego no la oculte cuando entra en cámara, y rehace el árbol con el que el juego reparte las piezas.
- **Colisión:** si cambiaste la malla «Colisión» (moverla, editar sus caras o cambiar su superficie), la escribe entera y rehace el árbol de colisión del juego.
  - La **superficie** de cada cara sale del número final del nombre de su material: «Superficie 9» es valla. Para cambiar una cara de tipo, asígnale otro material «Superficie N».
  - La normal de cada cara apunta al lado que golpea la pelota: arriba en el suelo y hacia el campo en las vallas.
- **Límite de tamaño:** un pack de gráficos de 21 MB carga en un partido y uno de 31,5 MB no. El original pesa 1,1 MB. Si pasas de 20 MB, el exportador avisa.

Aún no: objetos sueltos que no vinieron del juego. El exportador los ignora: pásalos antes por **Convertir objetos en piezas** (abajo).

Un material nuevo con una imagen sí se exporta: se crea en la pieza con esa imagen como textura nueva.

## Tu propio modelo (SketchUp, glTF, OBJ…)

Puedes llevar al juego un estadio que no existe en él.

1. **Importa un estadio del juego** como base. Pon el que quieras que aporte sus datos de juego (medidas, menú, partidas); por ejemplo, AT&T Park para un estadio de los Giants.
2. **Importa tu modelo** en la misma escena: Archivo > Importar > glTF, OBJ, FBX…
   - **SketchUp** (`.skp`): conviértelo antes a `.glb`. Por ejemplo, con [OpenSKP](https://github.com/iamahsanmehmood/openskp) (código abierto, MIT): `pip install openskp pillow` y luego `python -c "from openskp import SkpFile; from openskp.export import glb; s = SkpFile.open('estadio.skp'); s.parse(); glb.export(s, 'estadio.glb', textures=True)"`. Sale en milímetros: escálalo a 0,001.
   - Borra lo que no sea el estadio, como fotos aéreas, terreno lejano o personas.
3. **Colócalo como el estadio del juego:**
   - en metros;
   - con el plato en el origen, el suelo a la altura 0 y la segunda base hacia +Y.
   - Compruébalo con las bases de tu modelo: del plato a primera y a tercera hay 27,43 m (90 pies), y a la goma 18,44 m. Muchos modelos no están a escala: si tus bases están más lejos, escala todo el modelo hasta que cuadren.
4. Selecciona los objetos de tu modelo y pulsa **Convertir objetos en piezas** (panel Power Pros, tecla N):
   - Cada cara va a la pieza del estadio más cercana (gradas, vallas o suelo), porque el juego solo dibuja las piezas que ya tiene el estadio.
   - El color de cada material y un sol suave se guardan en el color de los vértices, porque el juego dibuja los estadios sin luz.
   - Las caras de materiales de dos caras se duplican por detrás, porque el juego no dibuja la parte de atrás de las caras.
   - Con **Quitar el estadio original** (activado por defecto), las piezas del estadio base desaparecen y solo queda tu modelo.
5. Pulsa **Generar colisión**. Crea la malla «Colisión» de tu estadio:
   - el suelo (césped si es verde, tierra si no) y el montículo;
   - las vallas, siguiendo la pared más cercana al campo en todas direcciones;
   - las paredes invisibles sobre las vallas, como las del juego: en territorio fair (1, el home run) y en foul (0);
   - los postes de foul donde las líneas cortan las vallas;
   - las gradas, simplificadas a unos 5.000 triángulos, y un límite exterior detrás del outfield.

   Revísala: está oculta, actívala con el ojo. Si algo no cuadra, puedes editarla a mano.
6. **Exporta** como estadio nuevo.

Límites:
- La colisión puede tener hasta 65.535 triángulos.
- Las texturas pasan a RGB5A3 y potencias de 2 de hasta 1024. Muchas texturas grandes suben el tamaño del pack.
- El generador de colisión supone un campo de béisbol normal: suelo a la altura 0, el centro del campo unos 45 m por delante del plato y paredes alrededor.

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
  4. vuelve a importar Coors Field con colisión, sube sus vallas (superficie 9) 3 m, cambia una cara a poste de foul y comprueba la tabla escrita: superficies, sentido de las caras y los dos árboles.
- **Modelo propio** (`tools/blender/test_convert.py`, mismos argumentos que la exportación): construye un estadio de prueba con formas simples (césped, tierra, una valla circular y gradas), lo convierte en piezas de Coors Field, genera su colisión, lo exporta como estadio nuevo y comprueba lo escrito.
