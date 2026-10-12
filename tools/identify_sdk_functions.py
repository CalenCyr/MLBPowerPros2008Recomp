# SPDX-License-Identifier: GPL-3.0-or-later
"""Name MLB functions by matching Dolphin's signature database (Data/Sys/totaldb.dsy).

The hash is Dolphin's HashSignatureDB::ComputeCodeChecksum: opcode bits only, so
relocated operands do not matter. Function boundaries come from the dtk inventory;
REL code is read from the linked analysis DOL at its locked runtime addresses.
A name is accepted only when its hash occurs once in the game and the database
gives that hash one name. Untagged C++ names (no library) are other games' classes
whose tiny bodies collide with generic code, and a real dtk name always wins. Output CSV: address,name,size,library,source.
Usage: identify_sdk_functions.py DSY MAIN_DOL LINKED_REL_DOL DOL_CSV REL_CSV LAYOUT_JSON OUT_CSV
"""
import collections
import csv
import json
import struct
import sys


def checksum(words):
    total = 0
    for opcode in words:
        op = opcode & 0xFC000000
        op2 = op3 = 0
        aux = op >> 26
        if aux == 4:
            op2 = opcode & 0x3F
            if op2 in (0, 8, 16, 21, 22):
                op3 = opcode & 0x7C0
        elif aux in (7, 8, 10, 11, 12, 13, 14, 15) or 32 <= aux < 56:
            op2 = opcode & 0x03FF0000
        elif aux in (19, 31, 63):
            op2 = opcode & 0x7FF
        elif aux == 59:
            op2 = opcode & 0x3F
            if op2 < 16:
                op3 = opcode & 0x7C0
        total = ((total << 17) & 0xFFFE0000) | ((total >> 15) & 0x1FFFF)
        total ^= op | op2 | op3
    return total


def load_dsy(path):
    data = open(path, 'rb').read()
    count = struct.unpack_from('<I', data)[0]
    names = collections.defaultdict(set)
    for i in range(count):
        base = 4 + i * 136
        hash_, size = struct.unpack_from('<II', data, base)
        raw = data[base + 8:base + 136].split(b'\0')[0].decode('latin1')
        name, _, library = raw.partition('\t')
        names[hash_].add((name.strip(), size, library.strip()))
    return names


def dol_memory(path):
    data = open(path, 'rb').read()
    offsets = struct.unpack_from('>18I', data, 0)
    addresses = struct.unpack_from('>18I', data, 0x48)
    sizes = struct.unpack_from('>18I', data, 0x90)
    return [(a, data[o:o + s]) for o, a, s in zip(offsets, addresses, sizes) if s]


def reader(sections):
    def words(address, size):
        for start, blob in sections:
            if start <= address and address + size <= start + len(blob):
                o = address - start
                return struct.unpack_from(f'>{size // 4}I', blob, o)
        return None
    return words


def functions(dol_csv, rel_csv, rel_text):
    for path, base in ((dol_csv, 0), (rel_csv, rel_text)):
        with open(path, newline='') as f:
            for row in csv.DictReader(f):
                if not row['name'].startswith('gap_') and int(row['size']):
                    yield base + int(row['address'], 16), int(row['size']), row['name']


def identify(dsy, dol, linked, dol_csv, rel_csv, layout_json):
    with open(layout_json) as f:
        rel_text = next(s['start'] for s in json.load(f)['sections'] if s['index'] == 1)
    words = reader(dol_memory(dol) + dol_memory(linked))
    db = load_dsy(dsy)
    by_hash = collections.defaultdict(list)
    for address, size, dtk_name in functions(dol_csv, rel_csv, rel_text):
        code = words(address, size) if size % 4 == 0 else None
        if code:
            by_hash[checksum(code)].append((address, size, dtk_name))
    found = []
    for hash_, hits in by_hash.items():
        candidates = {name for name, _, _ in db.get(hash_, ())}
        if len(hits) == 1 and len(candidates) == 1:
            address, size, dtk_name = hits[0]
            name, _, library = next(iter(db[hash_]))
            if not library and ('::' in name or '(' in name):
                continue
            if not dtk_name.startswith(('fn_', 'auto_')) and dtk_name.split('_8')[0] != name:
                continue
            found.append((address, name, size, library, dtk_name))
    return sorted(found)


def main():
    *inputs, out = sys.argv[1:8]
    found = identify(*inputs)
    with open(out, 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['address', 'name', 'size', 'library', 'dtk_name'])
        for address, name, size, library, dtk_name in found:
            w.writerow([f'0x{address:08X}', name, size, library, dtk_name])
    print(f'{len(found)} functions named -> {out}')


if __name__ == '__main__':
    # Self-check: immediates are ignored (li r3,1 == li r3,0x123), registers are not.
    assert checksum([0x38600001, 0x4E800020]) == checksum([0x38600123, 0x4E800020])
    assert checksum([0x38600001, 0x4E800020]) != checksum([0x38800001, 0x4E800020])
    main()
