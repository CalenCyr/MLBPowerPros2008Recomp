# Pruebas manuales

Sesiones jugadas por una persona con `tools/play.ps1`. Complementan las sondas automáticas desde estados guardados, sin sustituirlas. Cada sesión deja su log en `local/analysis/play-*.err.log`.

## 10 de octubre de 2026

### Sesión 1: módulo todo LLVM, arranque en frío

`play-20261010-144240.err.log`, mando de PS5 vía DS4Windows (`-Pad`), perfil nuevo `local/play-user`.

Falló durante el arranque con el aviso `Oversized range in GetPointerForRange. fffffffd bytes at 0x101321c3`, seguido de una violación de acceso.

Causa: un error del backend LLVM en `sthbrx`/`lhbrx`. Invertía los 32 bits del registro en lugar de la media palabra, así que la longitud de un mensaje de control USB para el Bluetooth emulado llegaba a 0, y `BTEmuHCI` calculaba `0 − 3`.
- La auditoría lockstep desde el arranque en frío lo localizó en la entrada `0x8010676C` (`mem2[0x935E2B80]`: N=0x00, I=0x03).
- Corrección: `tools/patches/dolrecomp-llvm-halfword-reverse.patch`, con una prueba de regresión que falla sin ella.
- La DLL Clang/C no tiene el error y arrancó 150 s sin fallo.
- Las auditorías anteriores no lo veían porque partían de estados guardados, con el Bluetooth ya inicializado.

### Sesión 2: DLL Clang/C, arranque en frío

`play-20261010-151503.err.log`, mando de PS5 vía DS4Windows (`-Pad`). Cierre manual de la ventana.

| Probado por el usuario | Resultado |
|---|---|
| Arranque en frío hasta el menú | Funciona |
| Entrar a un partido | Funciona |
| Lanzar | Funciona |
| Defender (fildeo) | Funciona |
| Menú de ajustes | Funciona |
| Menú de edición de jugador | Funciona |
| Mando de PS5 con el mapeo `-Pad` | Funciona |

- **Rendimiento:** ~30 FPS durante el partido y 60 FPS en algunas pantallas. Coincide con la velocidad medida de la DLL Clang (~55% de la velocidad real), con la regeneración LLVM ocupando 4 núcleos en segundo plano.
- **Log:** sin avisos ni errores. Tras el apagado limpio, el proceso terminó con `0xC000041D` (fallo al salir); está pendiente de revisar.

Siguen sin probar a mano: batear, un partido completo, la temporada, el modo Success, el guardado y la calidad del audio.
