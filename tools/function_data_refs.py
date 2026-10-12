# SPDX-License-Identifier: GPL-3.0-or-later
"""List the data addresses a guest function reads or writes, by name or address.

Used to locate SDK globals in MLB (e.g. the VI retrace counter read by
VIGetRetraceCount). Follows r13/r2 small-data accesses and lis+addi/ori/load
pairs inside the function; it does not follow calls or track registers across
branches. Function bounds come from a Wiicompiled MAP.txt (next start = end).
Usage: function_data_refs.py MAP_TXT MAIN_DOL LINKED_REL_DOL NAME_OR_ADDR...
"""
import struct
import sys

from identify_sdk_functions import dol_memory, reader

SDA1, SDA2 = 0x80322060, 0x80323940
LOADS = {32: 'lwz', 33: 'lwzu', 34: 'lbz', 35: 'lbzu', 40: 'lhz', 41: 'lhzu', 42: 'lha', 43: 'lhau',
         48: 'lfs', 49: 'lfsu', 50: 'lfd', 51: 'lfdu'}
STORES = {36: 'stw', 37: 'stwu', 38: 'stb', 39: 'stbu', 44: 'sth', 45: 'sthu', 52: 'stfs', 53: 'stfsu',
          54: 'stfd', 55: 'stfdu'}


def simm(word):
    return struct.unpack('>h', struct.pack('>H', word & 0xFFFF))[0]


def refs(words, start):
    """Yield (pc, kind, address) for each data access with a static address."""
    high = {}  # register -> value set by lis
    base = {}  # register -> address built by lis+addi (accesses through it are marked *)
    for k, word in enumerate(words):
        pc = start + 4 * k
        op, rd, ra = word >> 26, (word >> 21) & 31, (word >> 16) & 31
        if op == 15 and ra == 0:  # lis rD, hi
            high[rd] = (word & 0xFFFF) << 16
            base.pop(rd, None)
            continue
        built = None
        if op in LOADS or op in STORES or op == 14:  # loads, stores, addi
            kind = LOADS.get(op) or STORES.get(op) or 'addi'
            if ra == 13:
                built = (SDA1 + simm(word)) & 0xFFFFFFFF
            elif ra == 2:
                built = (SDA2 + simm(word)) & 0xFFFFFFFF
            elif ra in high:
                built = (high[ra] + simm(word)) & 0xFFFFFFFF
            elif ra in base:
                kind += '*'
                built = (base[ra] + simm(word)) & 0xFFFFFFFF
            if built is not None:
                yield pc, kind, built
        elif op == 24 and rd in high:  # ori rA, rS, lo
            yield pc, 'ori', high[rd] | (word & 0xFFFF)
        if op == 14 and built is not None:  # addi rD, base, d: rD now points into data
            base[rd] = built
            high.pop(rd, None)
        elif op in (14, 15, 24, 32, 34, 40, 42) and not (op == 15 and ra == 0):
            high.pop(rd, None)  # rD overwritten
            base.pop(rd, None)
        if op in (16, 18, 19) and word & 1:  # calls clobber volatile registers
            high = {r: v for r, v in high.items() if r >= 14}
            base = {r: v for r, v in base.items() if r >= 14}


def main():
    map_txt, dol, linked = sys.argv[1:4]
    starts, names = [], {}
    for line in open(map_txt):
        address, name = line.split(None, 1)
        starts.append(int(address, 16))
        names[name.strip()] = int(address, 16)
    starts.sort()
    words = reader(dol_memory(dol) + dol_memory(linked))
    for query in sys.argv[4:]:
        start = int(query, 16) if query.startswith('0x') else names[query]
        end = starts[starts.index(start) + 1]
        code = words(start, end - start)
        print(f'{query} @ 0x{start:08X} ({end - start} bytes)')
        for pc, kind, address in refs(code, start):
            print(f'  0x{pc:08X} {kind:6} 0x{address:08X}')


if __name__ == '__main__':
    # lwz r3, -0x7000(r13); lis r4, 0x8034; addi r4, r4, 0x1234
    got = list(refs([0x806D9000, 0x3C808034, 0x38841234], 0x80001000))
    assert got == [(0x80001000, 'lwz', SDA1 - 0x7000), (0x80001008, 'addi', 0x80341234)], got
    main()
