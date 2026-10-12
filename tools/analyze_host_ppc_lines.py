# SPDX-License-Identifier: GPL-3.0-or-later
"""Attribute host RIP samples in the recomp DLL to guest PPC instructions and functions.

Requires a line-table build of the module whose executable sections are byte-identical to
the sampled DLL, so its PDB can stand in for it. Each RIP resolves to a generated C line; the
nearest preceding '// XXXXXXXX:' comment names the guest instruction. Inlined and merged code
can blur instruction boundaries: shares are sample fractions, not exclusive function costs.
"""
import argparse
import bisect
import collections
import csv
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import re
import struct
from pathlib import Path

PPC_COMMENT = re.compile(r'^\s*// ([0-9A-F]{8}):')


def text_sections(path):
    data = path.read_bytes()
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    count = struct.unpack_from('<H', data, pe + 6)[0]
    optional = struct.unpack_from('<H', data, pe + 20)[0]
    base = struct.unpack_from('<Q', data, pe + 48)[0]
    sections = []
    for i in range(count):
        at = pe + 24 + optional + i * 40
        vsize, rva, rsize, raw = struct.unpack_from('<IIII', data, at + 8)
        if struct.unpack_from('<I', data, at + 36)[0] & 0x20000000:
            sections.append((rva, data[raw:raw + min(vsize, rsize)]))
    return base, sections


def differing_bytes(left, right):
    if [(rva, len(body)) for rva, body in left] != [(rva, len(body)) for rva, body in right]:
        return None
    block = 1 << 20
    count = 0
    for (_, a), (_, b) in zip(left, right):
        for at in range(0, len(a), block):
            x, y = a[at:at + block], b[at:at + block]
            if x != y:
                count += sum(1 for i, j in zip(x, y) if i != j)
    return count


class Lines:
    def __init__(self, dll, base):
        self.dbg = ctypes.WinDLL('dbghelp')
        self.process = wt.HANDLE(0x5A5A)
        self.dbg.SymSetOptions(0x10 | 0x2)  # SYMOPT_LOAD_LINES | SYMOPT_UNDNAME
        if not self.dbg.SymInitialize(self.process, None, False):
            raise OSError('SymInitialize failed')
        load = self.dbg.SymLoadModuleEx
        load.restype = ctypes.c_uint64
        load.argtypes = [wt.HANDLE, wt.HANDLE, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint64,
                         wt.DWORD, ctypes.c_void_p, wt.DWORD]
        if not load(self.process, None, str(dll).encode(), None, base, dll.stat().st_size, None, 0):
            raise OSError('SymLoadModuleEx failed')
        self.base = base

    class LINE(ctypes.Structure):
        _fields_ = [('SizeOfStruct', wt.DWORD), ('Key', ctypes.c_void_p), ('LineNumber', wt.DWORD),
                    ('FileName', ctypes.c_char_p), ('Address', ctypes.c_uint64)]

    def lookup(self, rva):
        line = self.LINE(); line.SizeOfStruct = ctypes.sizeof(self.LINE)
        displacement = wt.DWORD()
        if not self.dbg.SymGetLineFromAddr64(self.process, ctypes.c_uint64(self.base + rva),
                                             ctypes.byref(displacement), ctypes.byref(line)):
            return None
        return line.FileName.decode(errors='replace'), line.LineNumber


def guest_address(path, number, cache={}):
    if path not in cache:
        lines = Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
        marks = [(i + 1, int(m[1], 16)) for i, text in enumerate(lines) if (m := PPC_COMMENT.match(text))]
        cache[path] = ([n for n, _ in marks], [a for _, a in marks])
    numbers, addresses = cache[path]
    i = bisect.bisect_right(numbers, number) - 1
    return addresses[i] if i >= 0 else None


def functions(*paths):
    entries = []
    for path in paths:
        for row in csv.DictReader(open(path, newline='')):
            entries.append((int(row['address'], 16), int(row['size']), row['name']))
    entries.sort()
    return [e[0] for e in entries], entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='host-sample folder')
    parser.add_argument('sampled_dll', type=Path)
    parser.add_argument('line_dll', type=Path, help='same-code DLL with PDB line tables')
    parser.add_argument('--functions', type=Path, nargs='+',
                        default=[Path('local/analysis/dol-functions.csv')])
    parser.add_argument('--top', type=int, default=30)
    parser.add_argument('--allow-differing-bytes', type=int, default=0,
                        help='Tolerate this many differing code bytes (e.g. RIP-relative .rdata displacements '
                             'shifted by the debug directory); layout and section sizes must still match')
    args = parser.parse_args()
    base, sampled = text_sections(args.sampled_dll)
    line_base, lined = text_sections(args.line_dll)
    differing = differing_bytes(sampled, lined)
    if base != line_base or differing is None or differing > args.allow_differing_bytes:
        raise SystemExit(f'Executable sections differ ({differing} bytes): line tables cannot stand in for the sampled DLL')
    name = args.sampled_dll.name.lower()
    module = next(r for r in csv.DictReader(open(args.folder / 'modules.csv'))
                  if Path(r['path']).name.lower() == name)
    start, size = int(module['base']), int(module['size'])
    resolver = Lines(args.line_dll, base)
    starts, entries = functions(*args.functions)
    total = 0
    by_function, by_instruction, unresolved = collections.Counter(), collections.Counter(), 0
    for row in csv.DictReader(open(args.folder / 'samples.csv')):
        if int(row['cycles_since_last']) <= 0:
            continue
        total += 1
        rip = int(row['rip'])
        if not start <= rip < start + size:
            continue
        found = resolver.lookup(rip - start)
        address = guest_address(*found) if found else None
        if address is None:
            unresolved += 1
            continue
        by_instruction[address] += 1
        i = bisect.bisect_right(starts, address) - 1
        if i >= 0 and address < entries[i][0] + entries[i][1]:
            by_function[f'{entries[i][2]}@{entries[i][0]:08X}+{entries[i][1]}'] += 1
        else:
            by_function['<outside inventory>'] += 1
    dll_samples = sum(by_instruction.values()) + unresolved
    report = {
        'sampled_dll_text_sha256': [hashlib.sha256(body).hexdigest() for _, body in sampled],
        'differing_code_bytes': differing,
        'samples': total, 'dll_samples': dll_samples, 'unresolved_dll_samples': unresolved,
        'functions': [{'function': k, 'samples': v, 'share': v / total} for k, v in by_function.most_common(args.top)],
        'instructions': [{'address': f'{k:08X}', 'samples': v, 'share': v / total} for k, v in by_instruction.most_common(args.top)],
        'scope': 'Point samples of one host thread mapped through line tables of a byte-identical build. '
                 'Sample fractions, not exclusive CPU time, FPS or validated behavior.',
    }
    (args.folder / 'ppc-lines.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'total={total} dll={dll_samples} unresolved={unresolved}')
    for item in report['functions']:
        print(f"{item['samples']:5d} {item['share']:6.2%} {item['function']}")


if __name__ == '__main__':
    main()
