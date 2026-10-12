# SPDX-License-Identifier: GPL-3.0-or-later
"""Locate this game's REL in paused, private MEM1/MEM2 snapshots."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def u32(data, offset):
    return struct.unpack_from('>I', data, offset)[0]


def inspect(memory, original, base=0x80000000):
    module_id = u32(original, 0)
    count = u32(original, 0x0C)
    table = u32(original, 0x10)
    version = u32(original, 0x1C)
    matches = []
    position = 0
    signature = original[:4]
    while True:
        position = memory.find(signature, position)
        if position < 0:
            break
        candidate = position
        position += 4
        if candidate % 4 or candidate + max(0x4C, table + count * 8) > len(memory):
            continue
        raw_table = u32(memory, candidate + 0x10)
        # OSLink replaces the table's file offset with an absolute pointer.
        if (u32(memory, candidate + 0x0C), u32(memory, candidate + 0x1C)) != (count, version):
            continue
        if raw_table not in (table, base + candidate + table):
            continue
        sections = []
        valid = True
        absolute = True
        for index in range(count):
            source_entry = table + index * 8
            raw = u32(memory, candidate + source_entry)
            size = u32(memory, candidate + source_entry + 4)
            if size != u32(original, source_entry + 4):
                valid = False
                break
            if not size:
                continue
            address = raw & ~1
            if address < 0x80000000:
                absolute = False
                if address:
                    address += base + candidate
            in_snapshot = base <= address and address + size <= base + len(memory)
            sections.append({'index': index, 'raw_entry': f'0x{raw:08X}',
                             'inferred_runtime_start': f'0x{address:08X}',
                             'size': size, 'executable': bool(raw & 1),
                             'within_header_memory_region': in_snapshot})
        if valid:
            match = {'module_id': module_id, 'header_address': f'0x{base + candidate:08X}',
                     'section_count': count, 'version': version,
                     'raw_section_table': f'0x{raw_table:08X}',
                     'raw_prolog': f'0x{u32(memory, candidate + 0x34):08X}',
                     'state': 'absolute_section_addresses' if absolute else 'file_offsets_or_partial_link',
                     'sections': sections}
            if not absolute and candidate + len(original) <= len(memory):
                payload = memory[candidate:candidate + len(original)]
                first_difference = next((index for index, (left, right) in
                                         enumerate(zip(original, payload)) if left != right), len(original))
                match['contiguous_file_comparison'] = {
                    'compared_bytes': len(payload),
                    'matches_original': payload == original,
                    'matching_prefix_bytes': first_difference,
                    'snapshot_payload_sha256': hashlib.sha256(payload).hexdigest(),
                    'note': 'Differences may reflect incomplete loading or runtime edits; this comparison alone does not identify their cause.'}
            matches.append(match)
    return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_directory', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts = args.probe_directory / 'control/artifacts'
    low = (artifacts / 'mem1-low.bin').read_bytes()
    high = (artifacts / 'mem1-high.bin').read_bytes()
    if len(low) != 16 * 1024 * 1024 or len(high) != 8 * 1024 * 1024:
        raise ValueError('MEM1 snapshot must contain the full, contiguous 24 MiB')
    original = (root / 'local/disc/DATA/files/ovl_main.rel').read_bytes()
    source_hash = hashlib.sha256(original).hexdigest()
    if source_hash != 'dcc37a1a4824702feff5bcaa6aae7cefdedfc3b5d832fbf3de92b982a59b4edc':
        raise ValueError('REL source does not match this game revision')
    memory = low + high
    regions = [{'name': 'MEM1', 'base': '0x80000000', 'size': len(memory),
                'sha256': hashlib.sha256(memory).hexdigest()}]
    candidates = inspect(memory, original)
    mem2_parts = [artifacts / f'mem2-{part}.bin' for part in range(4)]
    if all(path.exists() for path in mem2_parts):
        parts = [path.read_bytes() for path in mem2_parts]
        if any(len(part) != 16 * 1024 * 1024 for part in parts):
            raise ValueError('Each MEM2 part must contain 16 MiB')
        mem2 = b''.join(parts)
        regions.append({'name': 'MEM2', 'base': '0x90000000', 'size': len(mem2),
                        'sha256': hashlib.sha256(mem2).hexdigest()})
        candidates.extend(inspect(mem2, original, 0x90000000))
    report = {'source_rel_sha256': source_hash, 'searched_regions': regions,
              'candidates': candidates,
              'note': 'Header/section matches locate candidates; they do not validate execution or relocations. Absence is limited to this paused snapshot and the listed regions.'}
    output = args.probe_directory / 'rel-memory-report.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
