# SPDX-License-Identifier: GPL-3.0-or-later
"""Rebind Wiicompiled's Mario Kart Wii native hooks and guest addresses to MLB.

Rewrites a freshly patched Wiicompiled working copy (runtime/src, runtime/include):
- Hook macros (PPC_NATIVE_OVERRIDE, REGISTER_*_FUNCTION, MKW_KNOWN_*) in enabled
  groups get the MLB address of the same function (matched by name between
  Wiicompiled's MKW MAP.txt and MLB's MAP.txt); every other hook is renamed to
  its *_UNBOUND form, which binds nothing and is invisible to the translator.
- Other 0x80xxxxxx literals in enabled groups are mapped: code addresses by
  function name, data addresses through the verified ranges of DATA_CSV.
  Unmapped literals are reported and fail the run.
Groups are runtime/src/hle/<group>; a file directly in hle/ is the group named by its stem.
Usage: wiicompiled_rebind.py RUNTIME_DIR MKW_MAP MLB_MAP DATA_CSV GROUP...
"""
import csv
import pathlib
import re
import sys

from align_sdk_by_anchors import JUMP_LABEL, sdk_name

HOOKS = [  # (regex, address group, bound name prefix, unbound replacement)
    (r'PPC_NATIVE_OVERRIDE(_VOID)?(\s*\(\s*)([0-9A-Fa-f]{8})(\s*,\s*)(\w+)', 'PPC_NATIVE_UNBOUND'),
    (r'REGISTER_NATIVE_FUNCTION(_AS)?(\s*\(\s*0x)([0-9A-Fa-f]{8})(u?\s*,\s*&?)(\w+)', 'REGISTER_NATIVE_UNBOUND'),
    (r'REGISTER_TRANSLATED_FUNCTION()(\s*\(\s*0x)([0-9A-Fa-f]{8})(u?\s*,\s*)(\w+)', 'REGISTER_TRANSLATED_UNBOUND'),
    (r'MKW_KNOWN_TYPED_NATIVE()(\s*\(\s*0x)([0-9A-Fa-f]{8})(u?\s*,\s*)(\w+)', 'MKW_KNOWN_TYPED_UNBOUND'),
    (r'MKW_KNOWN_NATIVE_CPU_CALL()(\s*\(\s*0x)([0-9A-Fa-f]{8})(u?\s*,\s*)(\w+)', 'MKW_KNOWN_NATIVE_CPU_UNBOUND'),
]
FILE_GROUPS = {'fiber_manager.cpp': 'os', 'gx_egg.cpp': 'gx_egg'}  # gx_egg: MKW's EGG renderer  # core runtime files that act on one SDK group's globals
LITERAL = re.compile(r'0x(80[0-9A-Fa-f]{6})(u?)\b')
BOUND = '@@BOUND@@'  # sentinel, removed before writing
LOW_MEMORY_END = 0x80004000  # OS globals at fixed addresses, identical on every game


def load_map(path, convert=lambda n: n):
    by_addr, by_name = {}, {}
    for line in open(path):
        address, name = line.split(None, 1)
        name = name.strip()
        if name.startswith('0x') or JUMP_LABEL.search(name):
            continue
        address = int(address, 16)
        by_addr[address] = name
        for candidate in {name, convert(name) or name}:
            by_name.setdefault(candidate, address)
    return by_addr, by_name


class Mapper:
    def __init__(self, mkw_map, mlb_map, data_csv):
        self.mkw, _ = load_map(mkw_map)
        self.mkw_names = list(self.mkw.values())
        _, self.mlb = load_map(mlb_map)
        self.ranges, self.texts, self.codes, self.ignored, self.unbind = [], [], {}, set(), set()
        self.coderanges = []
        with open(data_csv, newline='') as f:
            for row in csv.DictReader(f):
                if row['kind'] == 'range':
                    self.ranges.append((int(row['mkw_start'], 16), int(row['mkw_end'], 16),
                                        int(row['mlb_start'], 16)))
                elif row['kind'] == 'coderange':  # whole object linked identically in both games
                    self.coderanges.append((int(row['mkw_start'], 16), int(row['mkw_end'], 16),
                                            int(row['mlb_start'], 16)))
                elif row['kind'] == 'code':
                    self.codes[int(row['mkw_start'], 16)] = int(row['mlb_start'], 16)
                elif row['kind'] == 'ignore':
                    self.ignored.add(int(row['mkw_start'], 16))
                elif row['kind'] == 'unbind':  # MKW hook whose MLB function must stay translated
                    self.unbind.add(int(row['mkw_start'], 16))
                else:
                    self.texts.append((row['mkw_start'], row['mkw_end'], row['mlb_start']))

    def code(self, mkw):
        if mkw in self.codes:
            return self.codes[mkw]
        for start, end, mlb in self.coderanges:
            if start <= mkw < end:
                return mlb + (mkw - start)
        name = self.mkw.get(mkw)
        if name is None or self.mkw_names.count(name) > 1:
            return None  # an MKW name used at several addresses cannot pick one MLB function
        for candidate in (name, sdk_name(name)):
            if candidate and candidate in self.mlb:
                return self.mlb[candidate]
        return None

    def data(self, mkw):
        for start, end, mlb in self.ranges:
            if start <= mkw < end:
                return mlb + (mkw - start)
        return None


def spell(old, value):
    """Format value like the literal it replaces (case of hex digits)."""
    text = f'{value:08x}'
    return text.upper() if old.isupper() else text


def rewrite(text, group_enabled, mapper, path, problems, counts):
    def hook(match, unbound):
        macro_suffix, open_, addr, sep, symbol = match.groups()
        if symbol.startswith('MLB_'):  # MLB-only natives (runtime/src/hle/mlb) already carry MLB addresses
            counts['bound'] += 1
            return match.group(0)
        # gx_stub_* hooks abort on purpose (MKW never reaches them); for another game the
        # translated original is the better fallback, so they are never bound.
        if group_enabled and not symbol.startswith('gx_stub_') and int(addr, 16) not in mapper.unbind:
            mlb = mapper.code(int(addr, 16))
            if mlb is not None:
                counts['bound'] += 1
                # BOUND keeps the literal pass below from re-mapping an MLB address.
                return match.group(0).replace(open_ + addr, open_ + BOUND + spell(addr, mlb), 1)
        counts['unbound'] += 1
        head = match.group(0)[:match.start(2) - match.start(0)]
        rest = match.group(0)[len(head):].replace(open_ + addr, open_ + BOUND + addr, 1)
        return unbound + (macro_suffix or '') + rest

    for pattern, unbound in HOOKS:
        text = re.sub(pattern, lambda m, u=unbound: hook(m, u), text)
    if not group_enabled:
        return text.replace(BOUND, '')

    def literal(match):
        value = int(match.group(1), 16)
        if value < LOW_MEMORY_END or value in mapper.ignored:
            return match.group(0)
        mlb = mapper.code(value)
        if mlb is None:
            mlb = mapper.data(value)
        if mlb is None:
            problems.append(f'{path}: unmapped 0x{match.group(1)}')
            return match.group(0)
        counts['literals'] += 1
        return '0x' + spell(match.group(1), mlb) + match.group(2)

    lines = []
    for line in text.splitlines(keepends=True):
        code, sep, comment = line.partition('//')  # addresses in comments are documentation
        lines.append(LITERAL.sub(literal, code) + sep + comment)
    return ''.join(lines).replace(BOUND, '')


def main():
    runtime, mkw_map, mlb_map, data_csv, *groups = sys.argv[1:]
    runtime = pathlib.Path(runtime)
    mapper = Mapper(mkw_map, mlb_map, data_csv)
    problems, counts = [], {'bound': 0, 'unbound': 0, 'literals': 0}
    for path in sorted((runtime / 'src').rglob('*.cpp')) + sorted((runtime / 'src').rglob('*.h')) + \
            sorted((runtime / 'include').glob('*.inc')):
        rel = path.relative_to(runtime / 'src') if (runtime / 'src') in path.parents else path.name
        parts = pathlib.PurePath(rel).parts
        # hle/<group>/...; files directly in hle/ (vi.cpp, sc.cpp...) are their own group.
        group = (parts[1] if len(parts) > 2 else pathlib.PurePath(parts[1]).stem) if parts[0] == 'hle' else None
        group = FILE_GROUPS.get(path.name, group)
        if path.suffix == '.inc':
            group = 'gx'  # native_cpu_calls.inc holds the typed GX fast paths
        raw = path.read_bytes()
        text = raw.decode('utf-8-sig')
        source = text
        for file, old, replacement in mapper.texts:  # before the literal pass sees them
            if pathlib.PurePath(rel).as_posix() == file and group in groups:
                assert old in source, (file, old)
                source = source.replace(old, replacement.replace('0x', '0x' + BOUND))
        new = rewrite(source, group in groups, mapper, rel, problems, counts).replace(BOUND, '')
        if new != text:
            path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + new.encode('utf-8'))
    (runtime / 'include' / 'game_natives_rebound.h').write_text(
        '#pragma once\n// Written by tools/wiicompiled_rebind.py: hook addresses are this game\'s.\n'
        f'// Enabled groups: {" ".join(groups) or "(none)"}\n#define WIICOMPILED_NATIVES_REBOUND 1\n')
    print(f"hooks bound {counts['bound']}, unbound {counts['unbound']}, literals mapped {counts['literals']}")
    for problem in problems:
        print('UNMAPPED', problem)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    assert spell('8016D3A4', 0x800a09b4) == '800A09B4' and spell('8016d3a4', 0x800a09b4) == '800a09b4'
    main()
