# Power Pros Wii 2008 Texture Studio

*English version: [en/texture-studio.md](en/texture-studio.md)*

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

**Idioma:** la píldora **ES | EN** de la banda superior cambia el idioma al momento y lo guarda en `Config.toml` (`[ui] language`), el mismo ajuste que el launcher. Sin elegir, usa el idioma de Windows.

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

## Escalar con IA (opcional, fuera del Studio)

El Studio no escala imágenes: se exporta, se escala con otro programa y se vuelve a importar la carpeta. Todo lo de abajo es gratuito, funciona sin conexión en tu tarjeta gráfica y no viene con el juego (cada uno lo descarga si quiere).

**Programas** (código abierto):

| Herramienta | Para qué | Licencia | Descarga aprox. |
|---|---|---|---|
| Real-ESRGAN ncnn-vulkan | motor de escalado en línea de comandos; Vulkan, funciona en AMD, NVIDIA e Intel | MIT (Real-ESRGAN: BSD-3) | ~45 MB |
| Upscayl | ventana sencilla sobre ese motor; admite modelos propios | AGPL-3.0 | ~150-200 MB |
| chaiNNer | editor por nodos para lotes; en AMD usa el motor NCNN, no PyTorch (solo NVIDIA) | GPL-3.0 | ~150 MB + motor (~0,5 GB con NCNN) |

**Modelos** (gratuitos, en OpenModelDB; revisa la licencia de cada uno antes de redistribuirlo):

- **4x-AnimeSharp**: menús, logos, letras, estadios y personajes; respeta el estilo de dibujo. CC BY-NC-SA 4.0 (sin uso comercial). ~65 MB (.pth) o ~35 MB (NCNN).
- **4x-UltraSharp** (misma licencia) o **RealESRGAN x4plus** (BSD): fotos reales, como las cartas de jugador.

**Pasos con chaiNNer:** Load Images (la carpeta exportada, incluidas subcarpetas) → Upscale Image con Load Model → Save Image en otra carpeta, **con el mismo nombre de archivo**. Luego **Importar carpeta...** en el Studio. Con Upscayl: carpeta de entrada, modelo y escala ×4, comprobando que conserve los nombres.

**Consejos:**

- A ×4 casi todo cabe en el máximo de 4096 px.
- Si ves halos en los bordes transparentes, escala el canal alfa aparte.
- Las texturas que se repiten (césped, gradas, muros) pueden mostrar costuras: revísalas en el juego y, si se notan, déjalas en el original o a ×2.
- No escales las que salen en gris (su paleta está en otro pack): se verían grises en el juego.
- Hazlo por partes: un ×4 multiplica por 16 los píxeles, así que el juego entero en ×4 son varios GB, y la memoria de vídeo crece con lo que haya en pantalla.

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
