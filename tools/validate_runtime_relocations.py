# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare REL relocation fields with a paused snapshot at its observed addresses.

Uses the import stream from the original private REL, never the runtime-mutated
import stream. Relocation rules follow DolRecomp src/frontend/container/rel.c.
Matching fields do not validate generated C, CPU behavior, or native dispatch.
"""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path

REL_SHA256 = 'dcc37a1a4824702feff5bcaa6aae7cefdedfc3b5d832fbf3de92b982a59b4edc'


def be32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        raise ValueError('32-bit read outside source')
    return struct.unpack_from('>I', data, offset)[0]


def relocated_field(kind, target, address, original):
    target &= 0xFFFFFFFF
    if kind == 1:  # R_PPC_ADDR32
        return struct.pack('>I', target)
    if kind == 4:  # R_PPC_ADDR16_LO
        return struct.pack('>H', target & 0xFFFF)
    if kind == 6:  # R_PPC_ADDR16_HA
        return struct.pack('>H', ((target + 0x8000) >> 16) & 0xFFFF)
    if kind == 10:  # R_PPC_REL24: preserve opcode, AA and LK.
        delta = target - address
        if delta % 4 or not -0x2000000 <= delta <= 0x1FFFFFC:
            raise ValueError('REL24 displacement unaligned or out of range')
        return struct.pack('>I', (be32(original, 0) & 0xFC000003) | (delta & 0x03FFFFFC))
    raise ValueError(f'Unsupported relocation type: {kind}')


def validate(original, memory, candidate, *, linked_sections=None):
    table, count = be32(original, 0x10), be32(original, 0x0C)
    header = int(candidate['header_address'], 16) - 0x80000000
    if be32(memory, header + 0x10) != 0x80000000 + header + table:
        raise ValueError('Snapshot does not contain the expected linked table')
    if (be32(memory, header), be32(memory, header + 0x0C), be32(memory, header + 0x1C)) != (be32(original, 0), count, be32(original, 0x1C)):
        raise ValueError('Linked header identity differs from original REL')
    sections = {}
    for index in range(count):
        source_offset = be32(original, table + index * 8) & ~1
        size = be32(original, table + index * 8 + 4)
        if size != be32(memory, header + table + index * 8 + 4):
            raise ValueError('Section size differs from original')
        if not size:
            continue
        runtime = be32(memory, header + table + index * 8) & ~1
        if runtime < 0x80000000 or runtime + size > 0x80000000 + len(memory):
            raise ValueError('Linked section is outside MEM1')
        if source_offset and source_offset + size > len(original):
            raise ValueError('Source section is outside REL')
        payload = bytearray(original[source_offset:source_offset + size]) if source_offset else bytearray(size)
        sections[index] = {'base': runtime, 'size': size, 'bytes': payload,
                           'executable': bool(be32(original, table + index * 8) & 1)}
    import_offset, import_size = be32(original, 0x28), be32(original, 0x2C)
    if import_size % 8 or import_offset + import_size > len(original):
        raise ValueError('Invalid import table')
    counts, imports, records = collections.Counter(), [], []
    for entry in range(import_offset, import_offset + import_size, 8):
        imported, cursor = be32(original, entry), be32(original, entry + 4)
        if imported not in (0, be32(original, 0)):
            raise ValueError('Unresolved additional imported module')
        imports.append(imported)
        current, position = None, 0
        if cursor < be32(original, 0x24):
            raise ValueError('Import stream precedes relocation area')
        while True:
            if cursor + 8 > len(original):
                raise ValueError('Unterminated relocation stream')
            delta, kind, symbol_section, symbol_offset = struct.unpack_from('>HBBI', original, cursor)
            cursor += 8
            if kind == 203:  # R_DOLPHIN_END
                break
            if kind == 202:  # R_DOLPHIN_SECTION
                if symbol_section not in sections:
                    raise ValueError('Patch section has no payload')
                current, position = symbol_section, 0
                continue
            position += delta
            if kind in (0, 201):  # NONE / R_DOLPHIN_NOP
                continue
            if current not in sections:
                raise ValueError('Relocation without a patch section')
            section = sections[current]
            width = 2 if kind in (4, 6) else 4
            if position + width > section['size']:
                raise ValueError('Relocation write outside section')
            target = symbol_offset
            if imported:
                if symbol_section not in sections or symbol_offset > sections[symbol_section]['size']:
                    raise ValueError('Symbol outside its linked section')
                target += sections[symbol_section]['base']
            address = section['base'] + position
            value = relocated_field(kind, target, address, section['bytes'][position:position + width])
            section['bytes'][position:position + width] = value
            records.append((current, position, width, kind, imported))
            counts[kind] += 1
    mismatches, examples, matches = collections.Counter(), [], collections.Counter()
    for section_index, offset, width, kind, imported in records:
        section = sections[section_index]
        address = section['base'] + offset
        expected = section['bytes'][offset:offset + width]
        observed = memory[address - 0x80000000:address - 0x80000000 + width]
        category = 'code' if section['executable'] else 'data_or_bss'
        if observed == expected:
            matches[category] += 1
        else:
            mismatches[category] += 1
            if len(examples) < 25:
                examples.append({'section': section_index, 'address': f'0x{address:08X}',
                                 'type': kind, 'imported_module': imported,
                                 'expected': expected.hex(), 'observed': observed.hex()})
    code_sections = []
    for index, section in sections.items():
        if not section['executable']:
            continue
        start = section['base'] - 0x80000000
        actual = memory[start:start + section['size']]
        differences = sum(a != b for a, b in zip(section['bytes'], actual))
        code_sections.append({'index': index, 'runtime_start': f"0x{section['base']:08X}",
                              'bytes': section['size'], 'different_bytes': differences,
                              'expected_sha256': hashlib.sha256(section['bytes']).hexdigest(),
                              'observed_sha256': hashlib.sha256(actual).hexdigest()})
    if linked_sections is not None:
        linked_sections.update(sections)
    return {'imports': imports, 'relocation_records': len(records),
            'by_type': dict(counts), 'matching_fields': dict(matches),
            'mismatching_fields': dict(mismatches), 'mismatch_examples': examples,
            'code_sections': code_sections,
            'all_relocation_fields_match': not mismatches,
            'all_code_bytes_match': all(s['different_bytes'] == 0 for s in code_sections)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_directory', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    original = (root / 'local/disc/DATA/files/ovl_main.rel').read_bytes()
    if hashlib.sha256(original).hexdigest() != REL_SHA256:
        raise ValueError('Unexpected game REL revision')
    artifacts = args.probe_directory / 'control/artifacts'
    memory = (artifacts / 'mem1-low.bin').read_bytes() + (artifacts / 'mem1-high.bin').read_bytes()
    if len(memory) != 24 * 1024 * 1024:
        raise ValueError('Expected full MEM1 snapshot')
    candidates = json.loads((args.probe_directory / 'rel-memory-report.json').read_text())['candidates']
    linked = [c for c in candidates if c['state'] == 'absolute_section_addresses']
    if len(linked) != 1:
        raise ValueError('Expected exactly one linked REL')
    report = validate(original, memory, linked[0])
    report.update({'source_rel_sha256': REL_SHA256,
                   'snapshot_mem1_sha256': hashlib.sha256(memory).hexdigest(),
                   'note': 'Offline comparison at observed addresses. Mutable data may differ after linking. This does not validate generated C or native REL execution.'})
    (args.probe_directory / 'rel-relocation-validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'mismatch_examples'}, indent=2))
    if not report['all_code_bytes_match']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
