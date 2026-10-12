# SPDX-License-Identifier: GPL-3.0-or-later
"""Convert the dtk function inventories into a Wiicompiled MAP.txt ("hexaddr name").

REL rows are offsets into ovl_main.rel text (section 1); they are rebased to the
locked runtime placement read from the linked-REL layout.json. dtk's fn_* auto
names are written as unnamed entries so they only seed function starts; gap_*
rows are dtk's non-code holes (e.g. the MetroTRK string in .init) and are dropped.
Optional SDK_CSVs (identify_sdk_functions.py, align_sdk_by_anchors.py) name more
functions; an earlier CSV wins over a later one.
Usage: dtk_to_wiicompiled_map.py DOL_CSV REL_CSV LAYOUT_JSON OUT_MAP [SDK_CSV...]
"""
import csv
import json
import sys


def rows(path, base=0):
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            address = base + int(row['address'], 16)
            name = row['name']
            if name.startswith('gap_'):
                continue
            yield address, '' if name.startswith(('fn_', 'auto_')) else name


def build(dol_csv, rel_csv, layout_json, *sdk_csvs):
    with open(layout_json) as f:
        layout = json.load(f)
    text = next(s for s in layout['sections'] if s['index'] == 1 and s['executable'])
    entries = dict(rows(dol_csv))
    for address, name in rows(rel_csv, text['start']):
        assert text['start'] <= address < text['start'] + text['size'], hex(address)
        entries[address] = name
    for sdk_csv in reversed(sdk_csvs):
        with open(sdk_csv, newline='') as f:
            for row in csv.DictReader(f):
                address = int(row['address'], 16)
                assert address in entries, row  # these tools only name known starts
                entries[address] = row['name']
    return sorted(entries.items())


def main():
    dol_csv, rel_csv, layout_json, out = sys.argv[1:5]
    entries = build(dol_csv, rel_csv, layout_json, *sys.argv[5:])
    with open(out, 'w', newline='\n') as f:
        for address, name in entries:
            f.write(f'{address:08x} {name or f"0x{address:08x}"}\n')
    named = sum(1 for _, name in entries if name)
    print(f'{len(entries)} functions ({named} named) -> {out}')


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        # __start and the REL _prolog must land where the runtime puts them.
        mapped = dict(build('local/analysis/dol-functions.csv', 'local/analysis/rel-functions.csv',
                            'local/generated/dolrecomp/rel-linked/layout.json'))
        assert mapped[0x8000403C] == '__start'
        assert mapped[0x80AA0718] == '_prolog'
        assert 0x80004338 not in mapped  # gap_00_80004338_init is data
        print('self-test ok')
    else:
        main()
