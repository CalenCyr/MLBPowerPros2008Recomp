# SPDX-License-Identifier: GPL-3.0-or-later
"""Create a private analysis DOL containing the REL linked at verified addresses.

The game continues loading its original REL. This DOL is only a container for
static translation and hashing; its contents come from the original REL plus
the original relocation lists, rather than copying patched runtime code.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from validate_runtime_relocations import REL_SHA256, be32, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_directory', type=Path)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    original = (root / 'local/disc/DATA/files/ovl_main.rel').read_bytes()
    if hashlib.sha256(original).hexdigest() != REL_SHA256:
        raise ValueError('Unexpected original REL')
    artifacts = args.probe_directory / 'control/artifacts'
    memory = (artifacts / 'mem1-low.bin').read_bytes() + (artifacts / 'mem1-high.bin').read_bytes()
    if len(memory) != 24*1024*1024:
        raise ValueError('Expected complete MEM1')
    candidates = json.loads((args.probe_directory / 'rel-memory-report.json').read_text())['candidates']
    linked = [c for c in candidates if c['state'] == 'absolute_section_addresses']
    if len(linked) != 1:
        raise ValueError('Expected exactly one linked module')
    sections = {}
    result = validate(original, memory, linked[0], linked_sections=sections)
    if not result['all_relocation_fields_match'] or not result['all_code_bytes_match']:
        raise ValueError('Cannot translate an unverified linked image')
    output = root / 'local/generated/dolrecomp/rel-linked'
    output.mkdir(parents=True, exist_ok=True)
    image = bytearray(256)
    text_index, data_index, bss = 0, 7, []
    for index, section in sections.items():
        original_offset = be32(original, be32(original, 0x10)+index*8) & ~1
        if not original_offset:
            bss.append(section)
            continue
        slot = text_index if section['executable'] else data_index
        if section['executable']:
            text_index += 1
        else:
            data_index += 1
        if text_index > 7 or data_index > 18:
            raise ValueError('Too many sections for analysis DOL')
        while len(image) % 4:
            image.append(0)
        struct.pack_into('>I', image, slot*4, len(image))
        struct.pack_into('>I', image, 0x48+slot*4, section['base'])
        struct.pack_into('>I', image, 0x90+slot*4, section['size'])
        image.extend(section['bytes'])
    if len(bss) != 1:
        raise ValueError('Expected one independent BSS range')
    struct.pack_into('>II', image, 0xD8, bss[0]['base'], bss[0]['size'])
    prolog = sections[original[0x30]]['base'] + be32(original, 0x34)
    struct.pack_into('>I', image, 0xE0, prolog)
    image_path = output / 'linked-analysis.dol'
    image_path.write_bytes(image)
    layout = {'source_rel_sha256': REL_SHA256, 'probe': str(args.probe_directory),
              'header_address': linked[0]['header_address'],
              'section_info_offset': be32(original,0x10), 'section_count': be32(original,0x0C),
              'module_id': be32(original,0), 'version': be32(original,0x1C),
              'file_size': len(original), 'entry_point': f'0x{prolog:08X}',
              'analysis_dol_sha256': hashlib.sha256(image).hexdigest(),
              'sections': [{'index': index, 'start': section['base'], 'size': section['size'],
                            'executable': section['executable'],
                            'sha256': hashlib.sha256(section['bytes']).hexdigest()}
                           for index, section in sections.items()],
              'fixed_layout_required': True,
              'note': 'Private translation input, not a replacement game asset or boot image.'}
    (output / 'layout.json').write_text(json.dumps(layout,indent=2)+'\n',encoding='utf-8')
    lock = json.loads((root / 'config/recompiler.lock.json').read_text())
    revision = subprocess.check_output(['git','-C',str(root/'local/vendor/DolRecomp'),'rev-parse','HEAD'],text=True).strip()
    if revision != lock['commit']:
        raise ValueError('Translator revision differs from lock')
    with (root / 'local/analysis/dolrecomp-rel-linked.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(root/'local/build/dolrecomp/Release/dolrecomp.exe'),
                        '--cpu','broadway',f'-j{args.jobs}',str(image_path),'RL8E54',
                        str(output/'runtime_rel.c')],stdout=log,stderr=subprocess.STDOUT,check=True)
    print(f'Linked REL translated; entry=0x{prolog:08X}; BSS=0x{bss[0]["base"]:08X}')


if __name__ == '__main__':
    main()
