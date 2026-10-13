"""Align PowerUp's 2007 player-record fields to MLB Power Pros 2008's game_data.pack.

2008 keeps the 2007 save's roster block (0xB0-byte players, lineups, free agents, 32 teams of
0x140) but some player fields moved by a few bits. For every field PowerUp defines (GSPlayer.cs),
this pairs players present in both games by first+last name and tries bit shifts from -16 to +16,
keeping the shift where the 2008 values most often equal the 2007 ones. Ratings drift between
seasons, so the match rate is a vote, not proof; fields with a weak winner are flagged.

--bits prints, for every 2008 bit from 0x6F to 0x82, the phi correlation with the 2007 bit 0..4
positions later. Phi only counts players whose bit differs from the rest, so sparse flags and bits
PowerUp has no name for show where they went (that is how the -3/-2 boundary at 0x77.7 was found).

usage: align_2007_2008.py <PowerUp repo> <game_data.pack> [out.csv | --bits]
  <PowerUp repo>/PowerUp/PowerUp.ElectronUI/Data/data/BASE.pm2maus.dat is the 2007 base roster.
"""
import csv
import re
import struct
import sys
from pathlib import Path

PLAYER = 0xB0
SAVE_PLAYERS_2007 = 0x68C74
PACK_PLAYERS_2008 = 0x20


def load_fields(repo):
    src = (repo / "PowerUp/PowerUp/GameSave/Objects/Players/GSPlayer.cs").read_text(encoding="utf-8-sig")
    fields = []
    for m in re.finditer(r"\[GS(UInt|SInt|Boolean)\((0x[0-9a-fA-F]+)(?:, bits: (\d+))?(?:, bitOffset: (\d+))?"
                         r"[^\]]*\)\]\s*public [\w?<>]+ (\w+)", src):
        kind, off, bits, bit_offset, name = m.groups()
        fields.append((name, int(off, 16) * 8 + int(bit_offset or 0), int(bits or 1)))
    return fields


def load_charmap(repo):
    charmap = {}
    for line in (repo / "PowerUp/PowerUp.ElectronUI/Data/data/Character_Library.csv").read_text(encoding="utf-8").splitlines():
        if "," in line:
            key, value = line.split(",", 1)
            charmap.setdefault(int(key), value)
    return charmap


def bits_at(record, bit, count):
    value = int.from_bytes(record, "big")
    return (value >> (len(record) * 8 - bit - count)) & ((1 << count) - 1)


def players(block, count, charmap):
    def text(record, offset):
        return "".join(charmap.get(struct.unpack_from(">H", record, offset + 2 * i)[0], "*") for i in range(14)).strip()
    result = {}
    for i in range(count):
        record = block[i * PLAYER:(i + 1) * PLAYER]
        if struct.unpack_from(">H", record, 0)[0] == 0:
            continue
        result.setdefault((text(record, 0x32), text(record, 0x16)), record)
    return result


def phi(xs, ys):
    n, both, x, y = len(xs), sum(a and b for a, b in zip(xs, ys)), sum(xs), sum(ys)
    d = (x * (n - x) * y * (n - y)) ** 0.5
    return (n * both - x * y) / d if d else 0.0


def main(argv):
    repo, pack = Path(argv[0]), Path(argv[1])
    charmap = load_charmap(repo)
    save = (repo / "PowerUp/PowerUp.ElectronUI/Data/data/BASE.pm2maus.dat").read_bytes()
    old = players(save[SAVE_PLAYERS_2007:], 1500, charmap)
    new = players(pack.read_bytes()[PACK_PLAYERS_2008:], 1500, charmap)
    common = [k for k in old if k in new and all(k)]
    print(f"{len(old)} players in 2007, {len(new)} in 2008, {len(common)} in both")
    if argv[2:] == ["--bits"]:
        owner = {b: name for name, bit, count in load_fields(repo) for b in range(bit, bit + count)}
        for b in range(0x6F * 8, 0x83 * 8):
            ys = [bits_at(new[k], b, 1) == 1 for k in common]
            row = (f"+{s}:{phi([bits_at(old[k], b + s, 1) == 1 for k in common], ys):+.2f}"
                   f"({owner.get(b + s, '?')[:12]})" for s in range(5))
            print(f"{b // 8:X}.{b % 8}", " ".join(row) if any(ys) else "always 0")
        return
    rows = []
    for name, bit, count in load_fields(repo):
        votes = {}
        for shift in range(-16, 17):
            start = bit + shift
            if start < 0 or start + count > PLAYER * 8:
                continue
            votes[shift] = sum(bits_at(old[k], bit, count) == bits_at(new[k], start, count) for k in common)
        best = max(votes, key=lambda s: (votes[s], -abs(s)))
        rate = votes[best] / len(common)
        runner = sorted(votes.values())[-2] / len(common)
        rows.append((name, hex(bit // 8), bit % 8, count, best, round(rate, 3), round(runner, 3)))
    width = max(len(r[0]) for r in rows)
    for r in rows:
        flag = "" if r[5] >= 0.6 and r[5] - r[6] >= 0.15 else "   <- weak"
        print(f"{r[0]:{width}}  {r[1]}.{r[2]} x{r[3]:2}  shift {r[4]:+3}  match {r[5]:.2f} (next {r[6]:.2f}){flag}")
    if len(argv) > 2:
        with open(argv[2], "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["field", "byte_2007", "bit_2007", "bits", "shift_2008", "match", "next_best"])
            w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
