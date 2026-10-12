# SPDX-License-Identifier: GPL-3.0-or-later
"""Report which Wiicompiled native hooks have a known MLB address by name.

Hooks are the PPC_NATIVE_OVERRIDE / REGISTER_NATIVE_FUNCTION sites in the
Wiicompiled runtime; their names (e.g. GX__SetVtxDesc_8016d3a4) are normalized
to SDK names (GXSetVtxDesc) and looked up in a Wiicompiled MAP.txt.
Usage: wiicompiled_native_coverage.py RUNTIME_SRC MAP_TXT [OUT_CSV]
"""
import collections
import csv
import pathlib
import re
import sys

HOOK = re.compile(r'(?:PPC_NATIVE_OVERRIDE(?:_VOID)?\(\s*([0-9a-fA-F]{8})|'
                  r'REGISTER_NATIVE_FUNCTION(?:_AS)?\(\s*0x([0-9a-fA-F]{8})u?)\s*,\s*&?(\w+)')


def normalize(name):
    """Candidate SDK spellings, most likely first."""
    name = re.sub(r'_[0-9a-fA-F]{8}(?=_|$)', '', re.sub(r'^Stub_', '', name))
    name = re.sub(r'_(HLE|hle|Cpu)$', '', name)
    private = re.match(r'^(?:__)?([A-Z]+)__(\w+)$', name)  # OS__InterruptInit, __GX__PEInit
    if private:
        space, rest = private.groups()
        if rest.startswith('__'):  # OS____PSInit is OS::__PSInit, i.e. __OSPSInit
            return ['__' + space + rest[2:]]
        return [space + rest, '__' + space + rest]
    return [name]


def hooks(runtime_src):
    for path in pathlib.Path(runtime_src).rglob('*.cpp'):
        for match in HOOK.finditer(path.read_text(encoding='utf-8', errors='replace')):
            yield (match.group(1) or match.group(2)).lower(), match.group(3), path.parent.name


def main():
    runtime_src, map_txt = sys.argv[1:3]
    names = {}
    for line in open(map_txt):
        address, name = line.split(None, 1)
        if not name.startswith('0x'):
            names[name.strip()] = address
    totals, found, rows = collections.Counter(), collections.Counter(), []
    for mkw, hook, group in sorted(set(hooks(runtime_src))):
        if hook.startswith('gx_stub_'):
            continue  # deliberate abort stubs, not implementations
        sdk = next((n for n in normalize(hook) if n in names), normalize(hook)[0])
        totals[group] += 1
        found[group] += sdk in names
        rows.append((group, hook, sdk, mkw, names.get(sdk, '')))
    for group in sorted(totals):
        print(f'{group:10} {found[group]:4}/{totals[group]:4}')
    print(f'{"total":10} {sum(found.values()):4}/{sum(totals.values()):4}')
    if len(sys.argv) > 3:
        with open(sys.argv[3], 'w', newline='') as f:
            w = csv.writer(f, lineterminator='\n')
            w.writerow(['group', 'hook', 'sdk_name', 'mkw_address', 'mlb_address'])
            w.writerows(rows)


if __name__ == '__main__':
    assert 'GXSetVtxDesc' in normalize('GX__SetVtxDesc_8016d3a4')
    assert normalize('WPADProbe_HLE') == ['WPADProbe']
    assert normalize('OS____PSInit_801a04a0') == ['__OSPSInit']
    assert '__OSUnmaskInterrupts' in normalize('__OSUnmaskInterrupts_801a69bc_hle')
    main()
