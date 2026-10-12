# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the relocation verifier against the real snapshot and deliberate damage."""
import argparse
import json
import struct
from pathlib import Path
from validate_runtime_relocations import be32, validate


def first_site(original, candidate, wanted):
    sections = {s['index']: int(s['inferred_runtime_start'], 16) for s in candidate['sections']}
    begin, length = be32(original, 0x28), be32(original, 0x2C)
    for entry in range(begin, begin + length, 8):
        cursor, current, offset = be32(original, entry + 4), None, 0
        while True:
            delta, kind, section, _ = struct.unpack_from('>HBBI', original, cursor)
            cursor += 8
            if kind == 203:
                break
            if kind == 202:
                current, offset = section, 0
                continue
            offset += delta
            if kind == wanted:
                return sections[current] - 0x80000000 + offset
    raise ValueError('Requested test relocation absent')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_directory', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    original = (root / 'local/disc/DATA/files/ovl_main.rel').read_bytes()
    artifacts = args.probe_directory / 'control/artifacts'
    memory = (artifacts / 'mem1-low.bin').read_bytes() + (artifacts / 'mem1-high.bin').read_bytes()
    candidates = json.loads((args.probe_directory / 'rel-memory-report.json').read_text())['candidates']
    candidate = next(c for c in candidates if c['state'] == 'absolute_section_addresses')
    baseline = validate(original, memory, candidate)
    if not baseline['all_relocation_fields_match'] or not baseline['all_code_bytes_match']:
        raise AssertionError('Reference linked snapshot did not match')
    checks = ['Real snapshot: all 200212 relocation fields and full code match']
    damaged = bytearray(memory)
    damaged[first_site(original, candidate, 10) + 2] ^= 4
    result = validate(original, damaged, candidate)
    if result['all_code_bytes_match'] or result['mismatching_fields'].get('code') != 1:
        raise AssertionError('Verifier failed to detect a corrupt branch relocation')
    checks.append('Corrupt REL24 branch is detected')
    damaged = bytearray(memory)
    damaged[first_site(original, candidate, 1)] ^= 1
    result = validate(original, damaged, candidate)
    if not result['all_code_bytes_match'] or result['mismatching_fields'].get('data_or_bss') != 1:
        raise AssertionError('Verifier failed to distinguish a corrupt data pointer')
    checks.append('Corrupt ADDR32 data pointer is detected separately from code')
    damaged = bytearray(memory)
    struct.pack_into('>I', damaged, int(candidate['header_address'], 16) - 0x80000000 + 0x10, 0xFFFFFFFF)
    try:
        validate(original, damaged, candidate)
    except ValueError:
        checks.append('Invalid linked table is rejected')
    else:
        raise AssertionError('Verifier accepted an invalid table pointer')
    output = root / 'local/analysis/rel-relocation-checks.json'
    output.write_text(json.dumps({'checks': checks, 'passed': True}, indent=2)+'\n', encoding='utf-8')
    print('\n'.join('PASS ' + check for check in checks))


if __name__ == '__main__':
    main()
