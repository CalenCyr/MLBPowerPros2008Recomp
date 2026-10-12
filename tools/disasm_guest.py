# SPDX-License-Identifier: GPL-3.0-or-later
"""Print guest disassembly for MLB addresses from the DolRecomp C output comments.

The C backend writes "// 800A9F7C: lwz r3, ..." before every instruction it
translates, so local/generated/dolrecomp doubles as a disassembly listing.
Usage: disasm_guest.py MAP_TXT NAME_OR_ADDR [COUNT]   (COUNT defaults to the function size)
"""
import bisect
import pathlib
import re
import sys

ROOTS = ['local/generated/dolrecomp/dol/main_chunks', 'local/generated/dolrecomp/rel-linked']
LINE = re.compile(r'^\s*// ([0-9A-F]{8}): (.*)$')


def listing():
    found = {}
    for root in ROOTS:
        for path in pathlib.Path(root).rglob('*.c'):
            for line in path.read_text(errors='replace').splitlines():
                match = LINE.match(line)
                if match:
                    found.setdefault(int(match.group(1), 16), match.group(2).strip())
    return found


def main():
    starts, names = [], {}
    for line in open(sys.argv[1]):
        address, name = line.split(None, 1)
        starts.append(int(address, 16))
        names[int(address, 16)] = name.strip()
    starts.sort()
    by_name = {n: a for a, n in names.items()}
    query = sys.argv[2]
    start = int(query, 16) if query.startswith('0x') else by_name[query]
    end = starts[bisect.bisect_right(starts, start)]
    count = int(sys.argv[3]) if len(sys.argv) > 3 else (end - start) // 4
    code = listing()
    for k in range(count):
        pc = start + 4 * k
        label = f'  <{names[pc]}>' if pc in names else ''
        print(f'{pc:08X}: {code.get(pc, "?")}{label}')


if __name__ == '__main__':
    main()
