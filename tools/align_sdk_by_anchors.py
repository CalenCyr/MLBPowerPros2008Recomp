# SPDX-License-Identifier: GPL-3.0-or-later
"""Name more MLB SDK functions by aligning link order with Wiicompiled's MKW map.

Both games link the same RVL SDK libraries in the same object order. Between two
anchors (SDK names known in both maps, unique in each, kept in increasing order),
an equal number of functions on both sides is taken to be the same sequence; each
gap function is named when its size (distance to the next start) agrees.
No MKW binary is needed: only addresses and names from projects/mkwii/MAP.txt.
Usage: align_sdk_by_anchors.py MKW_MAP MLB_MAP OUT_CSV
"""
import csv
import re
import sys

SDK = {'GX', 'ES', 'ISFS', 'IOS', 'OS', 'VI', 'DVD', 'NAND', 'IOS', 'ISFS', 'IPC', 'SC', 'PAD', 'WPAD', 'KPAD', 'WUD',
       'AI', 'AX', 'AXFX', 'DSP', 'SI', 'EXI', 'DB', 'THP', 'MEM', 'MTX', 'PSMTX', 'NWC24', 'ESP',
       'CNT', 'ARC', 'TPL', 'FS', 'NET', 'SO', 'USB', 'WENC', 'ENC', 'HBM', 'RFL', 'DC', 'IC', 'PPC'}
MAX_GAP = 64
JUMP_LABEL = re.compile(r'_(switch|caseD_\w+)$')
SDK_NAME = re.compile(r'^(__)?(' + '|'.join(sorted(SDK, key=len, reverse=True)) + r')[A-Z_]')


def sdk_name(raw):
    """'GX::SetVtxDesc' -> 'GXSetVtxDesc', 'OS::__Foo' -> '__OSFoo'; None if not SDK."""
    if raw.startswith('RVL::'):  # MKW map spells some SDK names RVL::EXISelect, RVL::OS::ExitThread
        raw = raw[5:]
    if raw.startswith('__') and '::' in raw:  # __GX::SetDirtyState is __GXSetDirtyState
        inner = sdk_name(raw[2:])
        return '__' + inner if inner and not inner.startswith('__') else None
    if '::' in raw:
        space, _, rest = raw.partition('::')
        if space not in SDK or '::' in rest or '(' in rest:
            return None
        if space in ('IOS', 'ISFS', 'ES'):  # these libraries spell IOS_Open, ISFS_OpenLib
            return f'{space}_{rest}'
        return f'__{space}{rest[2:]}' if rest.startswith('__') else space + rest
    return raw if SDK_NAME.match(raw) else None


def load(path, convert):
    starts = []
    for line in open(path):
        address, name = line.split(None, 1)
        name = name.strip()
        if JUMP_LABEL.search(name):
            continue  # MKW map lists jump-table labels (VIInit_switch, _caseD_0) as entries
        starts.append((int(address, 16), None if name.startswith('0x') else convert(name)))
    starts.sort()
    return starts


def align(mkw, mlb):
    def unique(seq):
        seen = {}
        for i, (_, name) in enumerate(seq):
            if name:
                seen[name] = None if name in seen else i
        return {n: i for n, i in seen.items() if i is not None}
    a, b = unique(mkw), unique(mlb)
    anchors = sorted((a[n], b[n]) for n in a.keys() & b.keys())

    def size(seq, i):
        return seq[i + 1][0] - seq[i][0] if i + 1 < len(seq) else -1

    def similar(i, j):
        return abs(size(mkw, i) - size(mlb, j)) <= max(8, size(mkw, i) // 4)

    anchored = {i for i, _ in anchors}

    def run(i, j, step, limit):
        # Walk away from an anchor while sizes keep agreeing, stopping at the next anchor.
        for _ in range(limit):
            i, j = i + step, j + step
            if not (0 <= i < len(mkw) and 0 <= j < len(mlb)) or i in anchored or not similar(i, j):
                return
            yield i, j

    named = {}
    # Libraries are linked in a different order in each game, so anchors are
    # paired locally (consecutive in MKW and in the same order in MLB) instead
    # of through one global increasing chain.
    for (i1, j1), (i2, j2) in zip(anchors, anchors[1:]):
        local = 0 < j2 - j1 <= MAX_GAP and i2 - i1 <= MAX_GAP
        if local and i2 - i1 == j2 - j1:
            pairs = [(i1 + k, j1 + k) for k in range(1, i2 - i1) if similar(i1 + k, j1 + k)]
        else:
            # Differing SDK versions add or drop functions; across a library
            # boundary only the runs next to each anchor are trusted.
            pairs = list(run(i1, j1, 1, i2 - i1 - 1 if local else MAX_GAP))
            pairs += run(i2, j2, -1, i2 - i1 - 1 if local else MAX_GAP)
        for i, j in pairs:
            if mkw[i][1] and not mlb[j][1]:
                named.setdefault(j, (mlb[j][0], mkw[i][1], size(mlb, j), mkw[i][0]))
    chain = anchors
    uses = {}
    for entry in named.values():
        uses[entry[1]] = uses.get(entry[1], 0) + 1
    return chain, sorted(e for e in named.values() if uses[e[1]] == 1)  # drop ambiguous names


def main():
    mkw = load(sys.argv[1], sdk_name)
    mlb = load(sys.argv[2], lambda n: n)
    found, chain = [], []
    for _ in range(8):  # new names become anchors for the next round
        chain, more = align(mkw, mlb)
        if not more:
            break
        found += more
        new = {address: name for address, name, _, _ in more}
        mlb = [(a, n or new.get(a)) for a, n in mlb]
    found.sort()
    with open(sys.argv[3], 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['address', 'name', 'size', 'mkw_address'])
        for ba, name, size, ma in found:
            w.writerow([f'0x{ba:08X}', name, size, f'0x{ma:08X}'])
    print(f'{len(chain)} anchors, {len(found)} functions named -> {sys.argv[3]}')


if __name__ == '__main__':
    assert sdk_name('GX::SetVtxDesc') == 'GXSetVtxDesc'
    assert sdk_name('OS::__EnableBarnacle') == '__OSEnableBarnacle'
    assert sdk_name('nw4r::g3d::ResTev::GXSetTevColorIn') is None
    assert sdk_name('RVL::OS::ExitThread') == 'OSExitThread'
    assert sdk_name('ISFS::OpenLib') == 'ISFS_OpenLib'
    assert sdk_name('__GX::SetDirtyState') == '__GXSetDirtyState'
    m = [(0, 'GXA'), (8, 'GXB'), (16, 'GXC'), (24, 'GXD')]
    g = [(100, 'GXA'), (108, None), (116, None), (124, 'GXD')]
    assert [n for _, n, _, _ in align(m, g)[1]] == ['GXB', 'GXC']
    main()
