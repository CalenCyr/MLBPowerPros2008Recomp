"""Inventory a user's extracted Wii disc; keep every generated file in local/."""

import argparse
import collections
import hashlib
import json
import re
import struct
from pathlib import Path


def be32(data, offset):
    return struct.unpack_from('>I', data, offset)[0]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inspect_dol(path):
    data = path.read_bytes()
    if len(data) < 0x100:
        raise ValueError('DOL header is truncated')
    sections = []
    for kind, count, offset_base, address_base, size_base in (
        ('text', 7, 0, 0x48, 0x90),
        ('data', 11, 0x1C, 0x64, 0xAC),
    ):
        for index in range(count):
            offset = be32(data, offset_base + index * 4)
            address = be32(data, address_base + index * 4)
            size = be32(data, size_base + index * 4)
            if not size:
                continue
            if offset < 0x100 or offset + size > len(data):
                raise ValueError(f'DOL {kind}[{index}] lies outside file')
            sections.append(dict(kind=kind, index=index, file_offset=offset,
                                 address=f'0x{address:08X}', size=size))
    return dict(size=len(data), sha256=sha256(path),
                entry_point=f'0x{be32(data, 0xE0):08X}', sections=sections,
                text_bytes=sum(s['size'] for s in sections if s['kind'] == 'text'),
                data_bytes=sum(s['size'] for s in sections if s['kind'] == 'data'),
                bss_address=f'0x{be32(data, 0xD8):08X}', bss_bytes=be32(data, 0xDC))


def inspect_rel(path):
    data = path.read_bytes()
    if len(data) < 0x40:
        raise ValueError('REL header is truncated')
    count, table = be32(data, 0xC), be32(data, 0x10)
    if count > 1024 or table + count * 8 > len(data):
        raise ValueError('Invalid REL section table')
    sections = []
    for index in range(count):
        flags, size = struct.unpack_from('>II', data, table + index * 8)
        offset = flags & ~3
        if offset and offset + size > len(data):
            raise ValueError(f'REL section {index} lies outside file')
        kind = 'text' if flags & 1 else ('bss' if size and not offset else 'data')
        sections.append(dict(index=index, kind=kind, file_offset=offset, size=size))
    imports = []
    table, size = be32(data, 0x28), be32(data, 0x2C)
    if size % 8 or table + size > len(data):
        raise ValueError('Invalid REL import table')
    for position in range(table, table + size, 8):
        module, relocation_offset = struct.unpack_from('>II', data, position)
        imports.append(dict(module_id=module, relocation_offset=relocation_offset))
    return dict(path=path.name, size=len(data), sha256=sha256(path),
                module_id=be32(data, 0), version=be32(data, 0x1C),
                bss_bytes=be32(data, 0x20), sections=sections, imports=imports,
                text_bytes=sum(s['size'] for s in sections if s['kind'] == 'text'),
                data_bytes=sum(s['size'] for s in sections if s['kind'] == 'data'))


def inspect_fst(path, files_root):
    data = path.read_bytes()
    if len(data) < 12 or data[0] != 1:
        raise ValueError('Invalid FST root')
    count = be32(data, 8)
    strings_offset = count * 12
    if strings_offset > len(data):
        raise ValueError('FST entry table is truncated')
    entries, stack = [], [('', count)]
    for index in range(1, count):
        while stack and index >= stack[-1][1]:
            stack.pop()
        if not stack:
            raise ValueError('FST directory ranges are inconsistent')
        name_field, offset, size = struct.unpack_from('>III', data, index * 12)
        name_offset = strings_offset + (name_field & 0xFFFFFF)
        end = data.find(b'\0', name_offset)
        if name_offset >= len(data) or end < 0:
            raise ValueError('FST name is out of bounds')
        name = data[name_offset:end].decode('utf-8', errors='replace')
        if name in ('.', '..') or '/' in name or '\\' in name:
            raise ValueError('Unsafe FST filename')
        relative = f'{stack[-1][0]}/{name}'.lstrip('/')
        if name_field >> 24:
            if not index < size <= stack[-1][1]:
                raise ValueError('FST directory range is invalid')
            entries.append(dict(path=relative, kind='directory'))
            stack.append((relative, size))
        else:
            extracted = files_root / relative
            if not extracted.is_file() or extracted.stat().st_size != size:
                raise ValueError(f'Extracted file does not match FST size: {relative}')
            with extracted.open('rb') as stream:
                header = stream.read(32)
            entries.append(dict(path=relative, kind='file', size=size,
                                partition_byte_offset=offset * 4,
                                header_hex=header.hex(),
                                header_ascii=''.join(chr(b) if 32 <= b < 127 else '.' for b in header)))
    return entries


STRING_PATTERNS = {
    'sdk_versions': r'(?:<<\s*RVL|Revolution SDK|RVL_SDK|SDKVersion|build:|\b(?:OS|GX|AX|WPAD|PAD|DVD|VI|AI|DSP|EXI|SI|NAND|SC|KPAD|ARC):)',
    'toolchain': r'(?:Metrowerks|CodeWarrior|MWCC|mwcceppc|MW C/C\+\+|MSL C|MetroTRK)',
    'online_candidates': r'(?:DWC_|GameSpy|gamespy|Nintendo WFC|nwfc|nhttp|SOStartup|SOConnect|SOInit)',
    'middleware': r'(?:\b(?:THP|AX|DSP|NW4R|CriWare|CRI|ADX|NintendoWare|MusyX|Yaz0|Yay0)\b)',
    'asset_candidates': r'(?:project\.bin|\.rel\b|\.brres\b|\.tpl\b|\.bmd\b|\.bti\b|roster|\.thp\b|strbgm|WaveData|SeData)',
}


def inspect_strings(path):
    data = path.read_bytes()
    patterns = {key: re.compile(pattern, re.IGNORECASE) for key, pattern in STRING_PATTERNS.items()}
    results = {key: [] for key in patterns}
    for match in re.finditer(rb'[\x20-\x7E]{5,}', data):
        value = match.group().decode('ascii')
        if len(value) > 2048:
            continue
        for category, pattern in patterns.items():
            if pattern.search(value):
                results[category].append(dict(file_offset=f'0x{match.start():X}', value=value))
    return results


def inspect_dtk_log(path):
    if not path.exists():
        return None
    text = path.read_text(encoding='utf-8-sig', errors='replace')
    candidates = []
    for line in text.splitlines():
        match = re.match(r'\s*(\.text|\.init)\s*\|\s*(0x[0-9A-Fa-f]+)\s*\|\s*(?:0x[0-9A-Fa-f]+|\?)\s*\|\s*(.+)', line)
        if match:
            candidates.append(dict(section=match[1], address=match[2], name=match[3].strip()))
    exception = re.search(r'(\d+) discovered functions from exception table', text)
    return dict(named_code_symbols=candidates,
                unique_named_code_addresses=len({s['address'] for s in candidates}),
                exception_table_functions=int(exception[1]) if exception else None,
                note='Named symbols and exception-table entries are not the total function count.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--extracted', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not output.is_relative_to(root / 'local'):
        parser.error('--output must be inside this project\'s local/ directory')
    output.mkdir(parents=True, exist_ok=True)
    with args.image.open('rb') as stream:
        header = stream.read(0x400)
    if len(header) < 0x400 or be32(header, 0x18) != 0x5D1C9EA3:
        parser.error('Expected a raw Wii ISO/NKit ISO header')
    project = json.loads((root / 'config/project.json').read_text(encoding='utf-8'))
    game_id = header[:6].decode('ascii')
    if game_id != project['game_id']:
        parser.error(f'Expected {project["game_id"]}, got {game_id}')
    dol_path = args.extracted / 'sys/main.dol'
    files_root = args.extracted / 'files'
    fst = inspect_fst(args.extracted / 'sys/fst.bin', files_root)
    rel_paths = sorted(files_root.rglob('*.rel'))
    code_paths = [dol_path, *rel_paths]
    strings = {p.name: inspect_strings(p) for p in code_paths}
    inventory = dict(
        source=dict(path=str(args.image.resolve()), size=args.image.stat().st_size,
                    sha256=sha256(args.image), game_id=game_id,
                    internal_title=header[0x20:0x80].split(b'\0')[0].decode('ascii'),
                    revision=header[7], nkit_marker=header[0x200:0x208].hex()),
        dol=inspect_dol(dol_path), rels=[inspect_rel(p) for p in rel_paths],
        fst=fst, file_count=sum(e['kind'] == 'file' for e in fst),
        file_bytes=sum(e.get('size', 0) for e in fst),
        extension_counts=dict(collections.Counter(Path(e['path']).suffix.lower() for e in fst if e['kind'] == 'file')),
        symbol_files=[e['path'] for e in fst if Path(e['path']).suffix.lower() in ('.map', '.sym', '.elf', '.sel')],
        dtk_dol=inspect_dtk_log(output / 'dol-info.txt'),
        strings_counts={p: {k: len(v) for k, v in groups.items()} for p, groups in strings.items()},
    )
    (output / 'inventory.json').write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (output / 'strings-candidates.json').write_text(json.dumps(strings, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(game_id=game_id, dol_bytes=inventory['dol']['size'],
                         rel_count=len(rel_paths), fst_files=inventory['file_count'],
                         output=str(output)), ensure_ascii=False))


if __name__ == '__main__':
    main()
