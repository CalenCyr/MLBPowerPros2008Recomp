# Rosters de MLB Power Pros 2008 y PowerUp / PowerUp+

## Qué es PowerUp+

[PowerUp+](https://github.com/ogura-connection/PowerUpPlus) es un fork, con licencia GPLv3, de [PowerUp](https://github.com/CSho27/PowerUp), el editor de partidas guardadas de **MLB Power Pros 2007** para Wii.
- Lee y escribe `pm2maus.dat`, la partida de 2007, y genera rosters reales a partir de la MLB Stats API.
- Trae dos rosters ya generados: 2025/2026 y "All-Time Franchise".
- Todo el formato del guardado de 2007 lo descifró Christopher Shorter (PowerUp).

## Dónde vive el roster en 2008

En 2008 el roster base **no** está en la partida guardada, sino en `project.bin` → `/game_data.pack` (278.176 bytes).
- Ese paquete es `PACKWII` + 0x20 bytes de cabecera + el **mismo bloque de roster** que el guardado de 2007 tiene en 0x68C74. Son 0x43E80 bytes:
  - 1.500 jugadores de 0xB0 bytes (1.007 ocupados en 2008);
  - alineaciones, agentes libres y 32 equipos de 0x140 bytes (30 franquicias + All-Stars AL y NL).
- Los nombres usan la misma tabla de caracteres de 16 bits que 2007 (`Character_Library.csv` de PowerUp).
- `game_data.pack` lo leen todos los modos al arrancar. Por eso un roster cambiado ahí aparece en Exhibition, en la demo y en **MLB Life** (verificado: MLB Life → From Beginning → MLB Career Mode → la selección de jugador muestra los Red Sox 2025 con Crochet, ERA 2.59, 98 mph, abridor zurdo).
- Lo que el modo Edit guarda en la partida no llega a MLB Life porque MLB Life parte de `game_data.pack`. Cambiar el paquete resuelve ese problema.

## Diferencias del registro de jugador 2007 → 2008

Se obtuvieron comparando los 729 jugadores que están en el roster base de ambos juegos (`tools/roster/align_2007_2008.py`): para cada campo de PowerUp se busca el desplazamiento que más coincide, contando solo los jugadores cuyo valor no es el más común.

| Zona (bits de 2007) | En 2008 |
|---|---|
| 0x00–0x5B (id, nombres, número, equipo, apariencia) | igual |
| forma de bateo y de lanzamiento | pasan de 8 a 9 bits (0x5C.4 y 0x5D.5) |
| posición principal y capacidades de P y C | +2 bits |
| 0x60–0x6E (capacidades de defensa, zonas calientes, lado de bateo, ratings) | igual |
| segundo "contra zurdos" (0x6F.5) | ya no existe |
| 0x70.0–0x78.1 (habilidades de bateo y defensa) | −3 bits |
| 0x78.2–0x81 (bloque de pitcher) | −2 bits |
| fecha de nacimiento | −12 bits; el año se suma +1 porque PowerUp calcula desde el día inaugural de 2007 |
| estadísticas | AVG en 0x85.7, RBI en 0x88.0, HR en 0x89.2; ERA sigue en 0x8C.0 |
| repertorio (0x94–) | igual |

**Sin confirmar todavía**, se escriben donde estaban en 2007: banderas de relevista y cerrador, "table setter", "push", "free swinger" y "pull hitter", y piel/ojos.

## Usarlo

**Como mod (lo normal):** una carpeta `mods\<nombre>\roster\` con el `.dat` de PowerUp / PowerUp+ (por ejemplo `2025_MLB_Rosters.dat`) y un `mod.toml` opcional.
- Al activarlo en MODS y pulsar JUGAR, el juego extrae el `game_data.pack` de **tu** disco, lo convierte con el roster del `.dat` y lo sirve dentro de un `project.bin` modificado.
- La conversión se guarda en `UserData\Cache\mods\roster\<mod>\` y se rehace si cambia el `.dat`.
- El mod nunca lleva archivos del juego.

**A mano:** `python tools/roster/powerup_to_2008.py <roster.dat> <game_data.pack original> <carpeta del mod>` genera el mod con `project/game_data.pack`. El resultado es byte a byte igual al del runtime. `tools/projectbin.py extract` saca el `game_data.pack` original.

La tabla de campos del runtime (`runtime/src/roster_fields.inc`, parche `wiicompiled-mods`) sale de `powerup_to_2008.py --emit-cpp`, que lee `GSPlayer.cs` de PowerUp.

## Pendiente

- Confirmar los campos marcados arriba, usando el modo Edit de 2008 sobre un jugador conocido.
- Escribir rosters de 2008 directamente desde PowerUp+ (generador con la MLB Stats API), sin pasar por el formato de 2007.
- Los jugadores de 2025 usan las caras y formas de 2007 que eligió PowerUp+. Las caras o uniformes nuevos de 2008 no se aprovechan todavía.
