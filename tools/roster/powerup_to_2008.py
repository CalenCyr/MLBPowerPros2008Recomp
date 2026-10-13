"""Convert a PowerUp / PowerUp+ roster (MLB Power Pros 2007 Wii save, pm2maus.dat) into an MLB Power
Pros 2008 roster mod.

2008 keeps the 2007 save's roster block inside project.bin's game_data.pack, at 0x20: 1500 player
records of 0xB0 bytes, then lineups, free agents and 32 teams of 0x140, 0x43E80 bytes in all (the
2007 save holds the same block at 0x68C74). Player records are rebuilt field by field, because 2008
moved part of the record (see tools/roster/align_2007_2008.py and docs/roster-2008.md):
  - up to 0x5C and 0x60..0x6F (names, number, appearance, fielding capabilities, hot zones,
    batting side, ratings) are unchanged, except the face: 2008 inserted faces, so 2007's ids move
    by 0 to 12 (face_2008), and skin/eyes, where 2008 added a complexion (skin_2008);
  - batting and pitching forms grew to 9 bits, which moves position and the P/C capabilities by
    2 bits;
  - the second "hitting versus lefty" field is gone, so 0x70..0x77.6 moves back 3 bits; 2008 adds
    a bit at 0x77.4, so from 0x77.7 (pivot man, pull hitter, pitching block) it is back 2 bits;
  - birth date moves back 12 bits; years in the majors and season stats are at 0x85.2 (years),
    0x85.7 (AVG), 0x88.0 (RBI), 0x89.2 (HR); ERA stays at 0x8C.0;
  - 0x8C..0x93 and the pitch arsenal (0x94..) are unchanged; the voice id keeps its place but
    2008 renumbered the voices, so a 2007 voice id is dropped.
Bits PowerUp has no name for travel with their zone, so nothing the game stores is dropped.

A player who is also in the original 2008 roster (same name and birthday; when those repeat, as with
2008's two "Great Harris", the same id decides) starts from his 2008 record: what only 2008 has (his
voice, the bits 2008 added) survives, and so do his 2008 values for the bits PowerUp has no name for
(PowerUp cannot edit them and fills them from whatever player had that slot in its base save) and
the bytes after a long name's special id (u16 >= 0xF00 at 0x02). Everyone else starts from zeros;
unused slots get 2008's empty record. Lineups, free agents and teams come from the save, with 2008's
empty entries and the entry bits PowerUp does not model (convert_rest).

A mod whose mod.toml says roster_ids = "2008" (PowerUp+'s 2008 export) has 2008 voice, face and
skin/eyes values in its .dat already, so they are copied as they are.

The output is a mod folder: <out>/mod.toml and <out>/project/game_data.pack, built on the player's
own game_data.pack (extract it with tools/projectbin.py), so nothing from the game ships.

usage: powerup_to_2008.py <powerup save .dat> <original 2008 game_data.pack> <out mod dir> [name]
"""
import re
import sys
from pathlib import Path

PLAYER = 0xB0
SLOTS = 1500
BLOCK = 0x43E80
SAVE_BLOCK_2007 = 0x68C74
PACK_BLOCK_2008 = 0x20
NAMES = slice(0x16, 0x4E)                # last and first name
# The rest of the block, after the players: 32 lineups of 0x48 (18 entries of 4 bytes: id, position),
# 200 free agents of 8 bytes, 32 teams of 0x140 (40 entries of 8 bytes).
LINEUPS, FREE_AGENTS, TEAMS = 0x40740, 0x41040, 0x41680
# Bits of a team entry that PowerUp's GSTeamPlayerEntry has no field for.
TEAM_ENTRY_UNMODELED = (0x00, 0x00, 0x38, 0x3F, 0xFF, 0xF0, 0xE3, 0x00)

# PowerUp GSPlayer fields: name -> (bit position in 2007, bits). Parsed from the PowerUp sources at
# runtime when available; this table only lists the fields whose 2008 position differs.
MOVED = {
    # name: (2008 bit position, 2008 width) or None when 2008 dropped the field
    "BattingForm": (0x2E4, 9),
    "PitchingForm": (0x2ED, 9),
    "PrimaryPosition": (0x2F6, 4),
    "PitcherCapability": (0x2FA, 3),
    "CatcherCapability": (0x2FD, 3),
    "HittingVersusLefty2": None,
    "BirthYear": (0x414, 11),
    "BirthMonth": (0x420, 4),
    "BirthDay": (0x424, 5),
    "YearsInMajors": (0x42A, 5),
    "BattingAveragePoints": (0x42F, 10),
    "RunsBattedIn": (0x440, 10),
    "HomeRuns": (0x44A, 10),
    "VoiceId": None,
}


def target(name, bit, bits):
    """2008 (bit, bits) for a 2007 field, or None to drop it."""
    if name in MOVED:
        return MOVED[name]
    if bit < 0x37D:
        return bit, bits                 # unchanged through HittingVersusLefty1
    if 0x380 <= bit < 0x3BF:
        return bit - 3, bits             # 0x70.0 .. 0x77.6
    if 0x3BF <= bit < 0x41B:
        return bit - 2, bits             # 0x77.7 .. PowerOrBreakingBallPitcher
    if bit >= 0x460:
        return bit, bits                 # ERA and the pitch arsenal
    return None


def load_fields(powerup_repo):
    src = (powerup_repo / "PowerUp/PowerUp/GameSave/Objects/Players/GSPlayer.cs").read_text(encoding="utf-8-sig")
    fields = []
    for m in re.finditer(r"\[GS(UInt|SInt|Boolean)\((0x[0-9a-fA-F]+)(?:, bits: (\d+))?(?:, bitOffset: (\d+))?"
                         r"[^\]]*\)\]\s*public [\w?<>]+ (\w+)", src):
        _, off, bits, bit_offset, name = m.groups()
        fields.append((name, int(off, 16) * 8 + int(bit_offset or 0), int(bits or 1)))
    # Unnamed bits in the zones that move as a whole (hidden abilities, flags) go as 1-bit fields.
    # 0x5C..0x5F (the 2008 forms grew over it) and the padding after the pitching block are left out.
    named = {b for _, bit, count in fields for b in range(bit, bit + count)}
    zones = [*range(0x6F * 8, 0x40B), *range(0x460, 0x94 * 8)]
    fields += [(f"Bit_{b // 8:X}_{b % 8}", b, 1) for b in zones if b not in named]
    return fields


def get_bits(record, bit, count):
    value = int.from_bytes(record, "big")
    return (value >> (len(record) * 8 - bit - count)) & ((1 << count) - 1)


def set_bits(record, bit, count, field):
    value = int.from_bytes(record, "big")
    shift = len(record) * 8 - bit - count
    mask = ((1 << count) - 1) << shift
    value = (value & ~mask) | ((field << shift) & mask)
    record[:] = value.to_bytes(len(record), "big")


def person_2008(record):
    return bytes(record[NAMES]), get_bits(record, 0x420, 4), get_bits(record, 0x424, 5)


def person_2007(record):
    return bytes(record[NAMES]), get_bits(record, 0x42B, 4), get_bits(record, 0x42F, 5)


def originals_by_name(block):
    """Player records of a 2008 roster block by name and birthday (a list: they can repeat)."""
    found = {}
    for i in range(SLOTS):
        record = block[i * PLAYER:(i + 1) * PLAYER]
        if record[0] or record[1]:
            found.setdefault(person_2008(record), []).append(bytes(record))
    return found


def convert_rest(old, original):
    """Lineups, free agents and teams of a PowerUp save (`old`, from 0x40740 of the block) over the
    original 2008 ones. Entries PowerUp leaves blank get 2008's empty entry, used free agents 2008's
    filler bytes; a team entry for the same member keeps the original's bits PowerUp does not model,
    and a lineup entry with the same player and position keeps the original's flags."""
    rest = bytearray(old)
    def entries(start, count, size):
        return [start - LINEUPS + i * size for i in range(count)]
    fa = entries(FREE_AGENTS, 200, 8)
    teams = entries(TEAMS, 32 * 40, 8)
    empty = next((original[o:o + 8] for o in fa + teams if original[o:o + 2] == b"\0\0"), None)
    used_fa = next((original[o:o + 8] for o in fa if original[o:o + 2] != b"\0\0"), None)
    for o in fa + teams:
        if rest[o:o + 2] == b"\0\0" and empty:
            rest[o:o + 8] = empty
        elif o < TEAMS - LINEUPS and used_fa:
            rest[o + 2:o + 8] = used_fa[2:]
        elif o >= TEAMS - LINEUPS and rest[o:o + 2] == original[o:o + 2]:
            for k, mask in enumerate(TEAM_ENTRY_UNMODELED):
                rest[o + k] = rest[o + k] & ~mask | original[o + k] & mask
    for o in entries(LINEUPS, 32 * 18, 4):
        if rest[o:o + 2] == original[o:o + 2] and rest[o + 2] >> 4 == original[o + 2] >> 4:
            rest[o:o + 4] = original[o:o + 4]
    return bytes(rest)


def unnamed_2008(fields):
    """2008 bit positions that hold bits PowerUp has no name for."""
    named = {b for name, bit, count in fields if not name.startswith("Bit_") for b in range(bit, bit + count)}
    # 0x4E..0x5B: after the names (0x02..0x4D, strings PowerUp's regex above does not list).
    copied = [b for b in [*range(0x4E * 8, 0x5C * 8), *range(0x60 * 8, 0x6F * 8)] if b not in named]
    return copied + [target(name, bit, 1)[0] for name, bit, _ in fields if name.startswith("Bit_")]


VOICE = (0x492, 14)                      # VoiceId, same place in both games
FACE = (0x2A4, 8)


def face_2008(face):
    """2007 face id -> 2008's. 2008 inserted faces after 27, 105, 160 and 176 (707 of the 729 players
    in both games match with this; the rest got another face)."""
    return face + (0 if face < 28 else 1 if face < 106 else 2 if face < 161 else 7 if face < 177 else 12)


SKIN = (0x2AC, 4)                        # SkinAndEyes: complexion, + offset for brown eyes


def skin_2008(value):
    """2007 SkinAndEyes -> 2008's. 2007 has 5 complexions and adds 5 for brown eyes; 2008 inserted a
    complexion at 2 and adds 6 (695 of the 729 common players match; 272 without it)."""
    return value + (0 if value < 2 else 1 if value < 7 else 2)


def skin_2007(value):
    """2008 SkinAndEyes -> 2007's; 2008's new complexion becomes the one before it."""
    return max(v for v in range(16) if skin_2008(v) <= value)


def face_2007(face):
    """2008 face id -> 2007's; a face 2008 added becomes the 2007 one before it."""
    return max(f for f in range(256) if face_2008(f) <= face)


def empty_record(block):
    """2008 fills unused slots with a fixed record (zeros plus "no value" stats), not zeros."""
    for i in range(SLOTS):
        record = block[i * PLAYER:(i + 1) * PLAYER]
        if record[0] == 0 and record[1] == 0:
            return bytes(record)
    return bytes(PLAYER)


def convert_player(old, fields, originals=None, ids_2008=False, empty=bytes(PLAYER), typical=None):
    if old[0] == 0 and old[1] == 0:
        return empty
    same = (originals or {}).get(person_2007(old), [])
    # Repeated name and birthday (2008 has two "Great Harris"): the one with the same id.
    base = next((o for o in same if o[:2] == old[:2]), same[0] if same else None)
    new = bytearray(base or bytes(PLAYER))
    new[:0x5C] = old[:0x5C]              # id, names, flags, team, number, appearance
    new[0x60:0x6F] = old[0x60:0x6F]      # capabilities, hot zones, side, ratings
    for name, bit, count in fields:
        if bit < 0x5C * 8 or 0x60 * 8 <= bit < 0x6F * 8:
            continue
        place = target(name, bit, count)
        if place is None:
            continue
        value = get_bits(old, bit, count)
        if name == "BirthYear" and value:
            # PowerUp stores "opening day 2007 minus age"; 2008's calendar is a year later.
            value += 1
        set_bits(new, place[0], place[1], value)
    if ids_2008:
        set_bits(new, *VOICE, get_bits(old, *VOICE))
    else:
        set_bits(new, *FACE, face_2008(get_bits(old, *FACE)))
        set_bits(new, *SKIN, skin_2008(get_bits(old, *SKIN)))
    if base:
        for b in unnamed_2008(fields):
            set_bits(new, b, 1, get_bits(base, b, 1))
        if new[2:4] == base[2:4] and int.from_bytes(base[2:4], "big") >= 0xF00:
            new[4:0x16] = base[4:0x16]
    elif ids_2008 and typical:
        # PowerUp+'s 2008 export starts from a zeroed block: its new players take 2008's usual value
        # of each bit PowerUp cannot name (0x4E-0x4F and 0x92.0 hold the lineup screen's names).
        for b, value in typical.items():
            set_bits(new, b, 1, value)
    # game_data.pack is the base roster: nobody is edited (Unedited 0x50.3, IsEdited 0x50.4), and
    # the game keeps edited players out of MLB Life. PowerUp+ marks every imported player edited.
    set_bits(new, 0x283, 2, 0b10)
    return bytes(new)


def typical_unnamed(block, fields):
    """For each unnamed bit, the value most of 2008's players have."""
    records = [block[i * PLAYER:(i + 1) * PLAYER] for i in range(SLOTS)]
    records = [r for r in records if r[0] or r[1]]
    return {b: int(sum(get_bits(r, b, 1) for r in records) * 2 > len(records)) for b in unnamed_2008(fields)}


def revert_player(new, fields, base=None):
    """2008 record back to the 2007 layout (PowerUp+ imports the 2008 roster this way). The face goes
    back to 2007's numbering, which PowerUp's editor shows; the voice keeps 2008's id (same place,
    2008 numbering); the second "versus lefty", which 2008 dropped, comes from `base`, the 2007
    record of the same player."""
    if new[0] == 0 and new[1] == 0:
        return bytes(PLAYER)
    old = bytearray(base or bytes(PLAYER))
    old[:0x5C] = new[:0x5C]
    old[0x60:0x6F] = new[0x60:0x6F]
    for name, bit, count in fields:
        if bit < 0x5C * 8 or 0x60 * 8 <= bit < 0x6F * 8:
            continue
        place = target(name, bit, count)
        if place is None:
            continue
        value = get_bits(new, place[0], place[1])
        if name == "BirthYear" and value:
            value -= 1
        set_bits(old, bit, count, value)
    set_bits(old, *VOICE, get_bits(new, *VOICE))
    set_bits(old, *FACE, face_2007(get_bits(new, *FACE)))
    set_bits(old, *SKIN, skin_2007(get_bits(new, *SKIN)))
    return bytes(old)


def emit_cpp(repo):
    """The field table runtime/src/mods.cpp uses to convert PowerUp saves when a roster mod loads."""
    lines = ["// Generated by tools/roster/powerup_to_2008.py --emit-cpp from PowerUp's GSPlayer.cs:",
             "// 2007 (bit, width) -> 2008 (bit, width) for every player field outside the byte ranges",
             "// copied as they are (0x00..0x5B, 0x60..0x6E). birthYear marks the year to move by +1.",
             "struct RosterField { uint16_t from, bits, to, toBits; bool birthYear; };",
             "constexpr RosterField kRosterFields[] = {"]
    for name, bit, count in load_fields(repo):
        if bit < 0x5C * 8 or 0x60 * 8 <= bit < 0x6F * 8:
            continue
        place = target(name, bit, count)
        if place is not None:
            year = "true" if name == "BirthYear" else "false"
            lines.append(f"    {{0x{bit:03X}, {count}, 0x{place[0]:03X}, {place[1]}, {year}}},  // {name}")
    lines.append("};")
    lines.append("// 2008 bits PowerUp has no name for; a player found in the original 2008 roster keeps his.")
    lines.append("constexpr uint16_t kRosterUnnamed[] = {")
    unnamed = unnamed_2008(load_fields(repo))
    for i in range(0, len(unnamed), 12):
        lines.append("    " + " ".join(f"0x{b:03X}," for b in unnamed[i:i + 12]))
    lines.append("};")
    print("\n".join(lines))


def emit_cs(repo):
    """The same table for PowerUp+ (PowerUp/GameSave/PowerPros2008/PowerPros2008Fields.cs)."""
    lines = ["// Generated by tools/roster/powerup_to_2008.py --emit-cs (MLB Power Pros 2008 recomp project)",
             "// from GSPlayer.cs: 2007 (bit, width) -> 2008 (bit, width) for every player field outside the",
             "// byte ranges copied as they are (0x00..0x5B, 0x60..0x6E). BirthYear moves by one year.",
             "namespace PowerUp.GameSave.PowerPros2008",
             "{",
             "  public static class PowerPros2008Fields",
             "  {",
             "    public static readonly (int From, int Bits, int To, int ToBits, bool BirthYear)[] All =",
             "    ["]
    for name, bit, count in load_fields(repo):
        if bit < 0x5C * 8 or 0x60 * 8 <= bit < 0x6F * 8:
            continue
        place = target(name, bit, count)
        if place is not None:
            year = "true" if name == "BirthYear" else "false"
            lines.append(f"      (0x{bit:03X}, {count}, 0x{place[0]:03X}, {place[1]}, {year}), // {name}")
    lines += ["    ];", "  }", "}"]
    print("\n".join(lines))


def main(argv):
    if argv and argv[0] in ("--emit-cpp", "--emit-cs"):
        repo = Path(__file__).resolve().parents[2] / "local" / "vendor" / "PowerUpPlus"
        (emit_cpp if argv[0] == "--emit-cpp" else emit_cs)(repo)
        return
    save, original, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    name = argv[3] if len(argv) > 3 else save.stem
    repo = Path(__file__).resolve().parents[2] / "local" / "vendor" / "PowerUpPlus"
    fields = load_fields(repo)
    old_block = save.read_bytes()[SAVE_BLOCK_2007:SAVE_BLOCK_2007 + BLOCK]
    pack = bytearray(original.read_bytes())
    if pack[:8] != b"PACKWII " or len(pack) != PACK_BLOCK_2008 + BLOCK:
        sys.exit("not MLB Power Pros 2008's game_data.pack")
    originals = originals_by_name(pack[PACK_BLOCK_2008:])
    empty = empty_record(pack[PACK_BLOCK_2008:])
    manifest = save.parent.parent / "mod.toml"
    ids_2008 = manifest.is_file() and re.search(r'(?m)^roster_ids\s*=\s*"2008"', manifest.read_text("utf-8")) is not None
    typical = typical_unnamed(pack[PACK_BLOCK_2008:], fields)
    players = b"".join(convert_player(old_block[i * PLAYER:(i + 1) * PLAYER], fields, originals, ids_2008, empty, typical)
                       for i in range(SLOTS))
    pack[PACK_BLOCK_2008:PACK_BLOCK_2008 + SLOTS * PLAYER] = players
    rest = SLOTS * PLAYER
    pack[PACK_BLOCK_2008 + rest:PACK_BLOCK_2008 + BLOCK] = convert_rest(old_block[rest:], pack[PACK_BLOCK_2008 + rest:PACK_BLOCK_2008 + BLOCK])
    (out / "project").mkdir(parents=True, exist_ok=True)
    (out / "project" / "game_data.pack").write_bytes(pack)
    (out / "mod.toml").write_text(
        f'name = "{name}"\nauthor = "PowerUp+ (convertido a 2008)"\nversion = "1"\n'
        f'description = "Roster convertido desde {save.name} (MLB Power Pros 2007) al formato de 2008. '
        'Afecta a todos los modos, incluido MLB Life."\n', encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
