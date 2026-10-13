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
| 0x70.0–0x77.6 (habilidades de bateo y defensa) | −3 bits |
| 0x77.7–0x81 (pivot man, pull hitter, bloque de pitcher) | −2 bits; 2008 agrega un bit nuevo en 0x77.4 |
| fecha de nacimiento | −12 bits; el año se suma +1 porque PowerUp calcula desde el día inaugural de 2007 |
| años en las mayores y estadísticas | años en 0x85.2, AVG en 0x85.7, RBI en 0x88.0, HR en 0x89.2; ERA sigue en 0x8C.0 |
| 0x8C–0x93 | igual, salvo la voz (2008 renumeró las voces; queda en 0) |
| repertorio (0x94–) | igual |

Los bits que PowerUp no nombra viajan con su zona; el conversor los copia como campos de un bit. Por ejemplo, 0x76.0 y 0x76.1, 0x77.7, 0x80.7, 0x8D.6–0x8E.3 y 0x92.0: 2008 los conserva en la posición esperada, con φ ≈ 1.

**Cómo se confirmó:** `align_2007_2008.py --bits` calcula, para cada bit de 2008, la correlación φ con los bits de 2007 desplazados de 0 a 4 posiciones. Así salen claras las banderas raras que el voto por coincidencias no distingue:
- abridor, relevista y cerrador son campos de 3 bits (0x62.5, 0x63.0 y 0x63.3) y siguen en su sitio (φ 0,82, 0,83 y 0,70);
- el límite entre −3 y −2 está en 0x77.7, no en 0x78.2 como se creía antes. Con el límite viejo, "pull hitter" caía en 0x77.6, donde 2008 tiene un solo jugador marcado; en 0x77.7 hay 42 (φ 0,37);
- frente al conversor anterior, los bits que coinciden con el roster real de 2008 suben de 88,9 % a 89,3 %, y los 1 reproducidos, de 61,7 % a 64,5 %.

**Todavía dudosos:**
- "table setter": en 2008 ese bit vale 0 para los 1.004 jugadores.
- "push hitter" (φ 0,20) y "free swinger" (φ 0,07): están en medio de la zona −3, así que la posición es coherente, pero 2008 los asignó a otros jugadores.
- La voz.

## Usarlo

**Como mod (lo normal):** una carpeta `mods\<nombre>\roster\` con el `.dat` de PowerUp / PowerUp+ (por ejemplo `2025_MLB_Rosters.dat`) y un `mod.toml` opcional.
- Al activarlo en MODS y pulsar JUGAR, el juego extrae el `game_data.pack` de **tu** disco, lo convierte con el roster del `.dat` y lo sirve dentro de un `project.bin` modificado.
- La conversión se guarda en `UserData\Cache\mods\roster\<mod>\`. Se rehace si cambia el `.dat` o la tabla de campos del conversor, porque el nombre del archivo lleva un hash de esa tabla.
- El mod nunca lleva archivos del juego.
- Si un jugador del `.dat` también está en el roster original de 2008 (mismo nombre y apellido), parte de su registro de 2008. Así conserva lo que solo existe en 2008 (su voz, los bits nuevos) y sus valores de 2008 en los bits que PowerUp no nombra. PowerUp no puede editar esos bits y los rellena con lo que tuviera ese hueco en su partida base. Los demás jugadores parten de ceros.

**Con PowerUp+ (editar el roster de 2008):** el parche `tools/patches/powerupplus-2008.patch` le agrega a PowerUp+ soporte para 2008.
- **Abrir:** en *Import Roster → Game Save* se puede elegir el `project.bin` del juego (`<instalación>\Data\files\project.bin`) o un `game_data.pack`.
  - PowerUp+ lo convierte al formato de 2007 y lo abre como un roster más.
  - Para los nombres largos que añadió 2008 (Saltalamacchia, Chamberlain…), el parche agrega sus códigos a `SpecialSavedName_Library.csv`.
  - El `game_data.pack` queda guardado en su carpeta de datos, junto a la partida base. Solo vive en la PC del jugador.
- **Exportar:** *Export Roster → MLB Power Pros 2008 Mod* descarga un zip con `<nombre>\mod.toml` y `<nombre>\roster\<nombre>.dat`. Se descomprime en `mods\` y se activa en MODS.
  - El modelo de PowerUp no conserva todos los valores exactos: piel y ojos según la cara, color de un pelo que no existe, movimiento de la recta, banderas de "editado".
  - Por eso, en cada campo que vale lo mismo que daría un viaje de ida y vuelta sin tocar el jugador original, la exportación escribe el valor original de 2008.
- **Línea de comandos:** `tools/powerupplus.ps1` compila y ejecuta PowerUp+ con todo dentro de `local\` (necesita el SDK de .NET 10 en `local\tools\dotnet10`). Ejemplos:
  - `read-game-save --in-file <project.bin> --name "MLB 2008"`
  - `write-game-save --roster-id N --mlb2008-mod --out-dir <carpeta mods>`
- **Verificado:**
  - Abrir el roster de 2008 y exportarlo sin cambios lo devuelve igual. Solo cambian los id de jugador, que PowerUp reasigna. También cambian los bytes que sobran tras el código de los nombres largos, que el juego no lee.
  - En el juego, MLB Life muestra a los Red Sox de 2008 (Beckett, ERA 3.27, 97 mph).
  - Un cambio hecho en PowerUp+ (el ERA de Beckett, de 3.27 a 1.23) llega al juego.
  - La exportación desde la interfaz y desde la línea de comandos dan el mismo archivo.
- **Límites:**
  - PowerUp exporta solo jugadores con equipo o en la lista de agentes libres. Los 10 jugadores sueltos del roster de 2008 (Matt Morris, Tomas Perez…) se pierden.
  - Las caras de 2008 no coinciden con la lista de caras de 2007 que muestra PowerUp+.

**A mano:** `python tools/roster/powerup_to_2008.py <roster.dat> <game_data.pack original> <carpeta del mod>` genera el mod con `project/game_data.pack`. El resultado es byte a byte igual al del runtime. `tools/projectbin.py extract` saca el `game_data.pack` original.

La tabla de campos del runtime (`runtime/src/roster_fields.inc`, parche `wiicompiled-mods`) sale de `powerup_to_2008.py --emit-cpp`, que lee `GSPlayer.cs` de PowerUp.

## Pendiente

- Confirmar "table setter", "push hitter", "free swinger" y la tabla de voces, usando el modo Edit de 2008 sobre un jugador conocido.
- Los jugadores de 2025 usan las caras y formas de 2007 que eligió PowerUp+. Las caras nuevas de 2008 no se aprovechan todavía: hace falta una tabla de caras de 2008 para el editor.
- Conservar los id de jugador de 2008 en los jugadores importados, en lugar de dejar que PowerUp los reasigne según el salario.
