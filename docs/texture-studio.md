# Power Pros Wii 2008 Texture Studio

Programa para crear **mods de texturas** de MLB Power Pros 2008. Con él puedes:

- ver todas las texturas del juego, ordenadas por lo que son;
- exportarlas a PNG para editarlas en otro programa (Photoshop, GIMP, Krita) o escalarlas con IA (chaiNNer, Upscayl);
- volver a meterlas, del mismo tamaño o más grandes (HD).

El juego nunca se modifica: todo va a un mod que activas o desactivas en el launcher.

## Abrirlo

- Desde el juego: launcher → AJUSTES → **HERRAMIENTAS** → **EDITOR DE TEXTURAS** → Abrir.
- O con el acceso directo **Power Pros Wii 2008 Texture Studio** del escritorio, si lo creaste al instalar.

La primera vez tarda un segundo en leer las texturas de tu copia del juego (unas 9.700 distintas).

## La ventana

- **Arriba:** el mod en el que trabajas, si está activado en el juego (botón **Activar**) y **+ Nuevo mod**.
- **Izquierda:** categorías.
  - Menús, Estadios (por equipo, más cielos y estadios originales), Uniformes, Cartas de jugador, Logos, Caras, MLB Life, Temporada, Success…
  - Al final, las **capturas** que hayas hecho.
- **Centro:**
  - un buscador por nombre, pack o hash;
  - los filtros **Solo reemplazadas** y **Vistas en captura**;
  - las miniaturas, con un ✓ verde en las que ya reemplazaste y un ojo naranja en las que viste al capturar. Doble clic exporta una textura.
- **Ficha:** la textura original junto a tu reemplazo.
  - Haz clic en cualquiera de las dos para verla grande.
  - Debajo verás el pack de donde sale, su formato, el nombre del archivo y los botones **Exportar PNG**, **Importar PNG...**, **Quitar reemplazo** y **Abrir carpeta**.
- **Abajo:** **Exportar esta vista**, **Importar carpeta...**, **Capturar en juego** y **Empaquetar .zip**.

## Crear un pack HD paso a paso

1. **+ Nuevo mod**: ponle un nombre (será la carpeta `mods\<nombre>`).
2. Elige una categoría (por ejemplo, Menús › Menú principal) y pulsa **Exportar esta vista**. Elige una carpeta: se crean subcarpetas con los PNG originales.
3. Edita esos PNG o pásalos por chaiNNer o Upscayl. **No cambies los nombres de archivo**: el nombre `tex1_…` es lo que el juego busca.
4. **Importar carpeta...** y elige la carpeta con tus PNG. Busca en todas las subcarpetas y te enseña un informe: qué se importó y qué no, y por qué.
5. **Activar** (arriba) y abre el juego.

Para una sola textura: selecciónala, **Exportar PNG**, edítala e **Importar PNG...**.

## Tamaños

- Puedes usar la textura más grande, pero con la **misma proporción** (una de 256×128 puede ser 512×256, 1024×512…).
- Lo ideal es multiplicar por 2, 4 u 8. Otro tamaño con la misma proporción se acepta con un aviso.
- Máximo: 4096 píxeles de lado.
- Se aceptan PNG de cualquier tipo (con paleta, en gris, de 16 bits) y los DDS que vuelca el juego. Desde Photoshop, guarda como PNG.

## Paletas

Muchas texturas del juego usan paleta (16 o 256 colores). No tienes que preocuparte: el reemplazo es una imagen a todo color.

- Unas 300 texturas tienen la paleta en otro pack. El Studio las muestra **en gris**, pero se pueden exportar y reemplazar igual.
- Si el juego pinta una misma textura con varias paletas, cada variante es un reemplazo distinto. **Aplicar a todas las paletas** (en la ficha) hace que tu imagen sirva para todas.

## Capturar en juego

Sirve para encontrar la textura de algo que ves en pantalla.

1. Pulsa **Capturar en juego**: se abre el juego sin el launcher.
2. Ve a la pantalla que te interesa y cierra el juego.
3. El Studio crea **Capturas › Sesión N** con las texturas que aparecieron y las marca con el ojo.

Algunas texturas solo existen mientras se juega (no están en ningún pack). Salen en **Solo vistas en juego** y también se pueden reemplazar. Los vídeos no se pueden reemplazar.

## Compartir tu mod

**Empaquetar .zip** crea un zip con tu `mod.toml` y tus imágenes, nada más. Quien lo reciba lo descomprime en su carpeta `mods` y lo activa en el launcher (MODS).

No compartas texturas originales sin modificar: son contenido del juego. Comparte solo lo que tú hiciste.

## Para usuarios avanzados

`TextureStudio.exe` también funciona desde la línea de comandos:

```
TextureStudio.exe --new-mod <carpeta mods> <nombre>
TextureStudio.exe --export <project.bin> "<grupo>[/<subgrupo>]" <carpeta>
TextureStudio.exe --import-folder <project.bin> <carpeta del mod> <carpeta con PNG>
TextureStudio.exe --selftest
```

La ventana se puede abrir en una vista concreta con `--view "Estadios/Yankees (NYY)"`, `--search <texto>`, `--select <nombre tex1_>` y `--mod <nombre>`.

Para meter texturas dentro de los `.pack` en lugar de usar un mod de texturas, está `tools/packwii.py` (ver `docs/mods.md`).
