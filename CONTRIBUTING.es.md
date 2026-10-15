# Cómo colaborar

*English version: [CONTRIBUTING.md](CONTRIBUTING.md)*

Toda ayuda es bienvenida: reportes de errores, pruebas en otro hardware, código, ingeniería inversa, documentación y traducciones.

## Tres reglas

1. **Nada del juego entra en el repositorio.** Ni imágenes de disco, ni ejecutables, ni assets (texturas, modelos, audio, video, fuentes), ni código traducido o generado, ni partidas, ni `.dat` de rosters, ni volcados de bytes. Los mods hechos con datos del juego los comparten sus autores, no este repositorio. Instala la guardia una vez en tu clon:
   ```
   python tools/check_no_game_data.py --install-hook
   ```
2. **Los cambios al runtime son parches.** Wiicompiled está fijado (`config/tools.lock.json`); sus cambios viven en `tools/patches/wiicompiled-*.patch` y deben aplicarse limpios sobre los anteriores (`tools/wiicompiled-translate.ps1 -Fresh`).
3. **Di qué mediste.** Un arreglo o una función dice cómo se comprobó (una prueba, una medición, un paso en el juego) y qué no se comprobó.

## Reportar un error

Abre un issue con:
- qué hacías y qué pasó (una captura o un clip corto ayuda; recórtalo a la ventana del juego);
- tu GPU, driver y API gráfica (Direct3D 12 / Vulkan), y tu mando;
- el release o commit que usas;
- el registro, si el juego se cerró o el Setup falló (`setup.log` junto al juego instalado).

## Compilar

Ver «Compilar desde el código» en el [README](README.es.md). Todo lo que la compilación descarga o genera queda en `local/`, que git ignora.

## Documentación

Los textos para el usuario y la documentación existen en español e inglés: un cambio en `docs/<nombre>.md` va con su par en `docs/en/`, y los textos nuevos del launcher, el Setup o las herramientas pasan por `Tr("es", "en")`.

## Licencia

Al colaborar aceptas que tu aporte se publique bajo la GNU GPL v3, como el resto del proyecto.
