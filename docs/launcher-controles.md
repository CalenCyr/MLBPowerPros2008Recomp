# Launcher y controles

La build local conserva el fondo, los colores y los botones brillantes del launcher original. Vídeo, Audio, Controles e Interfaz se abren mediante sus pestañas; Mods y Herramientas conservan su entrada desde el menú principal.

## Diseño adaptable

El panel de ajustes usa el marco dibujado del fondo solo cuando la ventana tiene una proporción cercana a 16:9. Con otras proporciones (ventanas estrechas, altas o 4:3) el panel ocupa la ventana sobre el fondo desenfocado, en lugar de quedar encajonado. Las listas largas se desplazan y la paginación se recalcula al cambiar el tamaño. Las ventanas emergentes se centran al abrirse.

## Uso con mando

- **Menú principal:** cruceta o stick para elegir, Cruz/A para entrar.
- **Listas de ajustes (Vídeo, Audio, Interfaz, Mods):** arriba/abajo eligen la fila (resaltada en naranja); izquierda/derecha o Cruz cambian su valor; L1/R1 cambian de pestaña; L2/R2 pasan de página; Círculo/B vuelve. En ventanas estrechas, Triángulo/Y abre la explicación del ajuste. La barra inferior muestra estas teclas.
- **Controles:** la cruceta mueve el foco por la cuadrícula; Cruz asigna; L1/R1 y Círculo igual que arriba.
- Aceptar y Volver no se repiten al mantenerlos, así que entrar en una pantalla con Cruz no cambia también el primer ajuste.
- El launcher escucha todos los mandos conectados, no solo el primero que lista SDL (DS4Windows expone el mando físico y su gemelo Xbox virtual).
- Con teclado: flechas o WASD, Enter para cambiar, Q/E para pestañas, Esc para volver.

## Controles (estilo Dolphin)

`Ajustes > Controles` es una sola pantalla con grupos, como el diálogo de mando de GameCube de Dolphin:

- **Cabecera:** Jugador (1–4), Dispositivo (mandos conectados o Teclado y ratón), Nombres de botones (automático, PlayStation o Xbox) y Predeterminado. Se reparte en 4, 2 o 1 columnas según el ancho.
- **Grupos:** Botones (A, B, X, Y, Z, START), Cruceta, Stick principal, Stick C, Gatillos (L, R, L analógico, R analógico) y Opciones. Se reparten en 4, 3, 2 o 1 columnas según el ancho; si no caben, la zona se desplaza.
- **Asignar:** clic (o Cruz/A/Enter) en una asignación. El botón se vuelve naranja y espera a que se suelte la entrada anterior; después acepta la nueva. Esc, otro clic en el mismo botón o 8 segundos sin entrada cancelan sin cambiar nada. Clic derecho quita la asignación de un botón o tecla.
- Los botones del juego aceptan botones, gatillos o direcciones de stick del mando. Las direcciones de los sticks y los gatillos analógicos aceptan un eje o un botón. Con Teclado y ratón, también teclas y botones del ratón. Los duplicados entre botones principales se intercambian.
- **Sticks:** cada grupo muestra una puerta octogonal con la zona muerta y la señal que recibe MLB, usando `PADRead` y la misma conversión a los rangos de GameCube del port (87/74, normalizados por MLB entre 88/64). Debajo, zona muerta y sensibilidad. Una sensibilidad menor de 1 suaviza la respuesta cerca del centro; una mayor de 1 la acelera. Ambas conservan el recorrido completo.
- **Probar sticks** (en Opciones) evita que los sticks muevan el menú mientras se prueban; Esc u OPTIONS termina.

## Volver y cierres

Volver (Esc, Retroceso, K o Círculo/B) solo cuenta en el fotograma en que se pulsa y nunca se repite. Así, la pulsación que cierra un desplegable o cancela una captura no cierra también la página de ajustes. Antes, mantenerla un instante provocaba esos cierres en cadena.

## Guardado

Se mantienen los archivos de mapeo existentes y la sección `[controller]` de `Config.toml`. Los ajustes adicionales se guardan bajo `UserData` en instalaciones portátiles:

- `stick_response.txt`: sensibilidad de ambos sticks por jugador; archivo versionado, con valores predeterminados de 1 si falta o no es válido.
- `launcher_prompts.txt`: familia de nombres de botones elegida.

No se cambia el formato binario de los mapeos existentes. Una dirección de stick asignada a un botón usa el campo `nativeButton` que ya existía en el mapeo de ejes. El parche reproducible es `tools/patches/wiicompiled-launcher-controls.patch`, aplicado después de los parches existentes por `tools/wiicompiled-translate.ps1`.

## Verificación

`tools/test-launcher.ps1` crea una copia portátil privada bajo `local/analysis/launcher-tests/` y ejecuta una prueba breve con un mando virtual SDL. Comprueba:

- cambios de nombres de botones y rechazo del ruido pequeño del stick;
- sensibilidad aplicada por `PADRead` con el recorrido completo;
- captura en el propio botón e intercambio de duplicados;
- dirección de stick asignada a un botón;
- cancelación con Esc;
- desconexión del mando;
- lectura de los ajustes en un proceso nuevo;
- en una tercera pasada, la lista de ajustes con el mando: una fila por pulsación, cambiar con derecha, Cruz mantenida que cambia una sola vez y R1 para la siguiente pestaña.

No inicia una partida ni modifica los ajustes de la instalación del usuario.

El target `mkw_stick_response_tests` comprueba centro, borde de zona muerta, diagonales, respuesta monótona, sensibilidad y extremos. La interfaz se revisó a 640×480, 800×1061, 1280×720 y 1920×1061. Esto no sustituye una comprobación física con el mando del usuario.
