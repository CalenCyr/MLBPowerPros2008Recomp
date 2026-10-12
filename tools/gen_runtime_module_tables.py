# SPDX-License-Identifier: GPL-3.0-or-later
"""Merge DOL and fixed-layout REL metadata without editing generated C."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def coalesce(lines):
    """Merge touching code ranges: the LLVM backend emits one per function, while the
    REL validator requires each executable section inside a single range."""
    ranges = sorted((int(a,16),int(b,16)) for line in lines
                    for a,b in re.findall(r'0x([0-9A-Fa-f]+)u, 0x([0-9A-Fa-f]+)u',line))
    if len(ranges) != len(lines):
        raise ValueError('Unexpected code range format')
    merged = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [f'    {{0x{a:08X}u, 0x{b:08X}u}},' for a,b in merged]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--dol-dir', type=Path, help='Generated DOL directory (default: C backend output)')
    parser.add_argument('--rel-dir', type=Path, help='Generated linked-REL header/SMC directory (default: C backend output)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    generator = root / 'local/vendor/ModernGekko/vendor/dolphin/module-template/gen_module_tables.py'
    dol = args.dol_dir or root / 'local/generated/dolrecomp/dol'
    rel = root / 'local/generated/dolrecomp/rel-linked'  # linked image and layout
    rel_generated = args.rel_dir or rel
    arrays = {name: [] for name in ('s_code_ranges','s_smc_ranges','s_chunk_ranges','s_chunk_hashes')}
    counts = {name: 0 for name in ('CODE_RANGE','SMC_RANGE','CHUNK_RANGE')}
    for stem, directory, image in [('main',dol,root/'local/disc/DATA/sys/main.dol'),('runtime_rel',rel_generated,rel/'linked-analysis.dol')]:
        temporary = args.output.with_name(stem+'_tables.inc')
        smc = directory/(stem+'_smc.txt')
        if not smc.exists():
            smc = args.output.with_name(stem+'_no_reported_smc.txt')
            smc.write_text('# No SMC candidate report emitted; chunk hashes remain mandatory.\n')
        subprocess.run([sys.executable,str(generator),str(directory/(stem+'.h')),
                        str(smc),str(image),str(temporary)],check=True)
        text = temporary.read_text()
        for name in arrays:
            match = re.search(r'static const \w+ '+name+r'\[\] = \{\n(.*?)\n\};',text,re.S)
            if not match:
                raise ValueError('Unexpected metadata format: '+name)
            values = [line for line in match[1].splitlines() if 'zero-sized' not in line]
            if name == 's_code_ranges':
                values = coalesce(values)
            arrays[name].extend(values)
        counts['CODE_RANGE'] = len(arrays['s_code_ranges'])
        for name in ('SMC_RANGE','CHUNK_RANGE'):
            counts[name] += int(re.search(r'#define MODULE_'+name+r'_COUNT (\d+)u',text)[1])
    lines = ['// Generated combined module metadata; no game code edits.']
    for name, values in arrays.items():
        kind = 'u64' if name == 's_chunk_hashes' else 'StaticRecompRange'
        lines += [f'static const {kind} {name}[] = {{'] + values + ['};']
    for name, count in counts.items():
        lines.append(f'#define MODULE_{name}_COUNT {count}u')
    layout = json.loads((rel/'layout.json').read_text())
    lines.append('static const StaticRecompRelSection s_rel_sections[] = {')
    for section in layout['sections']:
        lines.append(f'    {{{layout["module_id"]}u, {section["index"]}u, 0x{section["start"]:08X}u, {section["size"]}u}},')
    lines += ['};','static const StaticRecompRelModule s_rel_modules[] = {',
              f'    {{{layout["module_id"]}u, {layout["version"]}u, {layout["section_count"]}u, {layout["section_info_offset"]}u, {layout["file_size"]}u, s_rel_sections, {len(layout["sections"])}u}},','};',
              '#define MODULE_REL_MODULE_COUNT 1u',
              f'#define MODULE_REL_HEADER {layout["header_address"]}u',
              f'#define MODULE_REL_CODE_START 0x{layout["sections"][0]["start"]:08X}u',
              f'#define MODULE_REL_CODE_END 0x{layout["sections"][0]["start"]+layout["sections"][0]["size"]:08X}u']
    args.output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Merged DOL/REL metadata:',counts)


if __name__ == '__main__':
    main()
