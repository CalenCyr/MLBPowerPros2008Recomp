# Power Pros Wii 2008 Texture Studio — diseño

*English version: [../../en/superpowers/specs/2026-10-14-texture-studio-design.md](../../en/superpowers/specs/2026-10-14-texture-studio-design.md)*

Fecha: 14 de octubre de 2026. Estado: aprobado en conversación, pendiente de revisión escrita.

## Objetivo

Una app de escritorio para crear **mods de texturas** de MLB Power Pros 2008 (Wii) sin tocar el juego original:

- ver cada textura del juego con su contexto (menú, estadio, uniforme, carta…);
- exportarla a PNG para editarla fuera (Photoshop, GIMP, escalado con IA en chaiNNer);
- volver a importarla, a su tamaño o más grande (HD), convertida a lo que el juego necesita;
- guardar todo como un mod que se activa o desactiva en el launcher y se puede compartir.

La inspiración son los packs HD de otros juegos (por ejemplo, texturas escaladas con AnimeSharp + chaiNNer conservando el estilo).

**No es** un editor de imagen: no se dibuja ni se retoca dentro de la app.

## Quién lo usa

Jugadores sin conocimientos técnicos, con el juego instalado por el Setup. No pueden necesitar Python ni línea de comandos. También el autor del proyecto para hacer packs completos.

## Base técnica comprobada

- El runtime ya carga reemplazos al estilo Dolphin: archivos `tex1_<ancho>x<alto>_<hash>[_<hash de paleta>]_<formato>.png|.dds` dentro de `mods/<mod>/textures/` (y `UserData/texture_replacements/`), a cualquier resolución. Un mod activado con `textures/` activa los reemplazos sin más ajustes (`mods.cpp`).
- `<hash>` es XXH64 (semilla 0) de los bytes del nivel base de la textura; `<hash de paleta>` es XXH64 del tramo de la paleta entre el índice mínimo y el máximo que usa la textura (`texture_replacement.cpp`). `$` es comodín para cualquiera de los dos.
- Comprobado el 14 de octubre de 2026 con el volcado del runtime hasta el menú principal (`docs/ingenieria-inversa.md`, sección 5): el hash calculado desde el `.pack` coincide con el del juego en las 39 texturas de packs vistas, y la paleta en 36 de 38. El juego usa los bytes del pack tal cual.
- Lo que no viene de packs: vídeos THP (I8 de 512×448 y 256×224, se ignoran) y unas pocas texturas de tamaño no potencia de dos generadas en ejecución (se cubren con la captura).

Consecuencia: el Studio nunca reescribe `.pack` ni `project.bin`. Solo escribe PNG con el nombre correcto en la carpeta del mod.

## Arquitectura

App C++20 independiente con Dear ImGui + SDL3 (renderizador SDL), con el mismo estilo que el Setup y el launcher (`power_pros_ui.h`). Dependencias ya fijadas en el proyecto: SDL3, ImGui, libpng + zlib, xxhash. Sin librerías nuevas.

```
tools/texture-studio/
  CMakeLists.txt        compilación estática, como tools/setup
  studio.cpp            ventana, estado de la interfaz, acciones
  catalog.{h,cpp}       lee project.bin → packs → texturas; índice en caché
  gx.{h,cpp}            decodificadores GX (RGBA8, RGB5A3, I4, I8, C4, C8) y bloques
  names.{h,cpp}         nombres tex1_… (hash de textura y de paleta)
  categories.{h,cpp}    pack → categoría y nombre legible (tabla escrita a mano)
  pngio.{h,cpp}         leer cualquier PNG → RGBA 8 bits; escribir PNG RGBA; leer los DDS
                        sin comprimir que vuelca el runtime (formato a confirmar en el plan)
  modfolder.{h,cpp}     crear/elegir mod, escribir/quitar reemplazos, empaquetar .zip
  capture.{h,cpp}       lanzar el juego con volcado y leer la sesión
  selftest.cpp          autotest con datos sintéticos (sin datos del juego)
```

Cada unidad tiene una sola responsabilidad y se prueba por separado. `catalog`, `gx` y `names` no dependen de la interfaz.

`tools/packwii.py` queda como implementación de referencia y para pruebas locales; los decodificadores C++ deben dar los mismos píxeles.

### Datos de entrada

- `UserData/Config.toml` junto al ejecutable del juego: `[paths] dvd_root` → `<dvd_root>/files/project.bin`.
- `project.bin`: formato documentado (`tools/projectbin.py`, `docs/ingenieria-inversa.md` sección 5).
- Dentro de cada `PACKWII`: cabeceras de textura de modelo y de interfaz, paletas, conjuntos de texturas; emparejado de paleta por puntero o, si no, por los colores que siguen a los píxeles (como `packwii.py`).

### Índice

- Al abrir: recorre los 2.356 packs (unos 392 MB) en un hilo, con barra de progreso, y guarda en memoria por textura: pack, posición, ancho, alto, formato, posición de paleta, hash de textura y hash de paleta. Medido: 9.657 texturas distintas en 1,1 s, así que no se guarda en disco (decisión de implementación del 14 de octubre de 2026).
- Texturas idénticas en varios packs se agrupan por nombre `tex1_…`; la ficha muestra «usada en N packs».
- Miniaturas: se decodifican al aparecer en pantalla y se guardan en caché en memoria (con límite).

## Reglas de nombres

| Caso | Nombre del reemplazo |
|---|---|
| Sin paleta (RGBA8, RGB5A3, I4, I8) | `tex1_WxH_<hash>_<fmt>` |
| Paleta conocida | `tex1_WxH_<hash>_<hash paleta>_<fmt>` |
| Paleta en otro pack (~430) | `tex1_WxH_<hash>_$_<fmt>`; se ve en gris |
| Variantes de paleta vistas en una captura | además, un archivo por cada `<hash paleta>` capturado |
| «Aplicar a todas las paletas» (opción en la ficha) | `…_$_<fmt>` |

Por defecto, nombre exacto: los uniformes podrían compartir píxeles y cambiar solo la paleta por equipo, y un comodín los igualaría.

## Importar

- PNG de cualquier tipo (paleta, gris, 16 bits, con o sin alfa) → RGBA 8 bits. DDS se copia tal cual.
- Tamaño: misma proporción que el original, hasta 4096 px de lado. Múltiplo exacto (×2, ×4, ×8) recomendado; otro tamaño con la misma proporción se acepta con aviso; otra proporción se rechaza.
- Importar carpeta: recorrido recursivo, casa por nombre de archivo `tex1_…` (lo que deja chaiNNer al conservar nombres). Informe final: importadas, rechazadas (motivo), sin casar.
- El reemplazo se escribe en `mods/<mod>/textures/<categoría>/<subgrupo>/tex1_….png` (carpetas legibles; el runtime busca de forma recursiva).

## Exportar

- Una textura, una categoría o todo, como PNG RGBA al tamaño original, en `export/<categoría>/<subgrupo>/tex1_….png` dentro de la carpeta que elija el jugador.
- Las de paleta desconocida se exportan en gris, marcadas en el informe.

## Mods

- Elegir o crear el mod activo: `mods/<nombre>/mod.toml` (`name`, `version`) + `textures/`.
- Barra superior: si el mod está activado en `Config.toml [mods] enabled`; botón «Activar».
- «Quitar reemplazo» borra el archivo del mod.
- «Empaquetar .zip»: solo `mod.toml` y `textures/` del mod. Nunca packs ni texturas sin modificar.

## Captura en juego

- «Capturar en juego» lanza el juego con el launcher saltado (`WIICOMPILED_SKIP_LAUNCHER=1`) y el volcado activado sin tocar la configuración del jugador (variable de entorno nueva en el parche del runtime, ver abajo).
- Al cerrarse el juego, los volcados pasan a `UserData/Cache/texture_studio/captures/<n>/` y el Studio crea la sesión «Sesión n».
- Los nombres capturados marcan con 👁 las texturas del catálogo vistas y añaden variantes de paleta. Las que no están en ningún pack forman la categoría «Solo vistas en juego» y se muestran desde el volcado; se pueden reemplazar igual. Los fotogramas de vídeo se descartan.

## Interfaz

Estilo **B** de la maqueta (`.superpowers/brainstorm/.../studio-layout-v2.html`): paneles oscuros neutros, franja superior azul con el título «POWER PROS WII 2008 / TEXTURE STUDIO» con contorno, botones píldora, **sin franja roja**. Ratón y teclado, en español.

- Barra superior: título, mod activo (desplegable), estado de activación, «+ Nuevo mod».
- Izquierda: categorías con contador y subgrupos (Menús, Estadios › <estadio>, Uniformes › <equipo>, Cartas de jugador, Logos, Solo vistas en juego, Capturas › Sesión n).
- Centro: búsqueda (nombre legible, pack o hash), filtros «Solo reemplazadas» y «Vistas en captura», rejilla de miniaturas con insignias ✓ (reemplazada) y 👁 (vista en captura) y el tamaño.
- Ficha: original y reemplazo lado a lado sobre fondo a cuadros, ampliables; pack(s), formato, nombre del archivo, estado; acciones Exportar PNG, Importar PNG…, Quitar reemplazo, Abrir carpeta, Aplicar a todas las paletas.
- Abajo: Exportar categoría, Importar carpeta…, Capturar en juego, Empaquetar .zip, estado del índice.

## Integración

- **Make-Payload**: compila el Studio como el Setup y lo incluye en el paquete. No lleva nada del juego; la revisión de contenido del paquete sigue aplicando.
- **LocalBuild (Setup)**: lo instala junto al juego (`Game/TextureStudio.exe`) y crea su acceso directo si se pidió.
- **Parche del runtime** `wiicompiled-texture-studio`:
  - botón «TEXTURAS» en el launcher que abre el Studio;
  - `WIICOMPILED_TEXTURE_DUMPS=1` activa reemplazos y volcado solo en esa ejecución.

## Errores

Se muestran en la ventana, sin cerrarla:

- falta `Config.toml`, `dvd_root` o `project.bin` → «Instala el juego con el Setup»;
- PNG ilegible o corrupto;
- proporción incorrecta o tamaño mayor de 4096;
- carpeta del mod sin permiso de escritura;
- el mod no está activado (botón para activarlo);
- el juego no se pudo lanzar para capturar.

## Pruebas

- **Autotest** (`TextureStudio.exe --selftest`, en el repo): decodificadores sobre texturas sintéticas con resultado conocido, normalización de PNG, nombres y hash de paleta sobre datos sintéticos, reglas de tamaño.
- **Comprobación local** (no se sube, usa los datos del jugador): píxeles idénticos a `packwii.py` en todas las texturas; nombres calculados iguales a un volcado real del juego.
- **Prueba en el juego**: reemplazo ×4 de la etiqueta «Exhibition» del menú y de una textura de estadio, mod activado, captura de pantalla.
- **Setup**: paquete regenerado e instalación de prueba con el Studio.

## Fuera de alcance (primera versión)

Dibujar o editar dentro de la app; escalado con IA integrado; vídeos THP; modelos 3D; cambiar estadios; escribir texturas dentro de los `.pack` (eso sigue en `tools/packwii.py`).

## Reglas del proyecto que aplican

- Nada del juego en el repositorio, el paquete ni la app: la app lee el `project.bin` del jugador en tiempo de ejecución.
- Todo documento de ingeniería inversa nuevo va a `docs/ingenieria-inversa.md` (y el PDF).
- El cambio del runtime es un parche reproducible en `tools/patches/`, registrado en `tools/wiicompiled-translate.ps1`.
