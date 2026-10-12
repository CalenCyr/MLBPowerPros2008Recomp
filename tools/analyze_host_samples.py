# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve Windows x64 RIP samples to nearest code labels in MSVC/LLD maps.

Labels do not establish exclusive function time or bounds, especially with inlining
and aliases. A relinked map requires independently checked identical code sections.
"""
import argparse
import bisect
import collections
import csv
import ctypes
import hashlib
import json
import re
import struct
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def load_map(path, binary):
    data = path.read_text(encoding='utf-8')
    base = int(re.search(r'Preferred load address is ([0-9a-fA-F]+)', data)[1], 16)
    stamp = int(re.search(r'Timestamp is ([0-9a-fA-F]+)', data)[1], 16)
    with binary.open('rb') as f:
        head = f.read(4096)
    pe = struct.unpack_from('<I', head, 0x3c)[0]
    if head[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', head, pe+4)[0] != 0x8664:
        raise ValueError('Require x64 PE')
    if stamp != struct.unpack_from('<I', head, pe+8)[0]:
        raise ValueError('Linker map timestamp does not match binary')
    if base != struct.unpack_from('<Q', head, pe+48)[0]:
        raise ValueError('Linker map base does not match binary')
    count = struct.unpack_from('<H', head, pe+6)[0]
    optional_size = struct.unpack_from('<H', head, pe+20)[0]
    executable = []
    for i in range(count):
        at = pe+24+optional_size+i*40
        size, rva = struct.unpack_from('<II', head, at+8)
        if struct.unpack_from('<I', head, at+36)[0] & 0x20000000:
            executable.append((rva, rva+size))
    symbols = collections.defaultdict(list)
    for line in data.splitlines():
        # MSVC marks functions with "f"; LLD omits this marker. Admit only
        # symbols inside executable PE sections in either format, never data
        # or absolute symbols merely because they are adjacent in the map.
        m = re.match(r'\s+[0-9a-fA-F]{4}:[0-9a-fA-F]+\s+(\S+)\s+([0-9a-fA-F]{16})\s+(?:f\s+)?(.*)', line)
        if m and any(start <= int(m[2],16)-base < end for start,end in executable):
            symbols[int(m[2], 16) - base].append((m[1], m[3].removeprefix('i ').strip()))
    if not symbols:
        raise ValueError('No function symbols')
    return sorted(symbols), symbols


def undecorate(name):
    if not name.startswith('?'):
        return name
    buffer = ctypes.create_string_buffer(8192)
    dbghelp = ctypes.WinDLL('dbghelp')
    fn = dbghelp.UnDecorateSymbolName
    fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32]
    fn.restype = ctypes.c_uint32
    if fn(name.encode(), buffer, len(buffer), 0x1000):
        return buffer.value.decode('utf-8', errors='replace')
    return name


def analyze(folder, maps):
    summary = dict(line.split('=', 1) for line in (folder/'summary.txt').read_text().splitlines())
    selected = int(summary['selected_tid'])
    modules = list(csv.DictReader((folder/'modules.csv').open(newline='')))
    resolved = {}
    provenance = []
    for mapping in maps:
        binary_name, path = mapping.split('=', 1)
        matches = [m for m in modules if Path(m['path']).name.lower() == binary_name.lower()]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous mapped module')
        module = matches[0]
        binary, path = Path(module['path']), Path(path)
        resolved[binary_name.lower()] = load_map(path, binary)
        provenance.append({'binary': str(binary), 'binary_sha256': sha(binary),
                           'map': str(path), 'map_sha256': sha(path)})
    counts = collections.Counter()
    by_module = collections.Counter()
    total = 0
    last_time = -1
    for row in csv.DictReader((folder/'samples.csv').open(newline='')):
        when, tid, rip, cycles, suspended = (int(row[k]) for k in
            ('elapsed_ns', 'tid', 'rip', 'cycles_since_last', 'suspend_ns'))
        if tid != selected or when <= last_time or not cycles or suspended < 0 or when > int(summary['elapsed_ns']):
            raise ValueError('Invalid sample chronology or thread')
        last_time = when
        matches = [m for m in modules if int(m['base']) <= rip < int(m['base']) + int(m['size'])]
        if len(matches) > 1:
            raise ValueError('Overlapping loaded modules')
        module = matches[0] if matches else None
        name = Path(module['path']).name if module else '<unmapped/JIT>'
        by_module[name] += 1
        label, obj = '<no map>', ''
        if name.lower() in resolved:
            addresses, symbols = resolved[name.lower()]
            rva = rip - int(module['base'])
            index = bisect.bisect_right(addresses, rva) - 1
            if index >= 0:
                entries = symbols[addresses[index]]
                label = ' | '.join(sorted(set(undecorate(s[0]) for s in entries)))
                obj = ' | '.join(sorted(set(s[1] for s in entries)))
        counts[(name, label, obj)] += 1
        total += 1
    if not total or total != int(summary['samples']):
        raise ValueError('Sample accounting mismatch')
    threads = []
    for row in csv.DictReader((folder/'threads.csv').open(newline='')):
        threads.append({'tid': int(row['tid']), 'name': row['name'], 'cycles': int(row['cycles']),
                        'user_seconds': int(row['user_100ns']) / 1e7,
                        'kernel_seconds': int(row['kernel_100ns']) / 1e7})
    if sum(t['tid'] == selected for t in threads) != 1:
        raise ValueError('Selected thread missing CPU accounting')
    return {'summary': summary, 'provenance': provenance,
            'scope': 'Point samples of one selected Windows thread with positive cycle deltas. Nearest linker function labels may include gaps, aliases and inlined work. Fractions are sample shares, not full CPU/GPU time, FPS or validated game behavior. Brief suspensions perturb execution; do not use this probe for speed comparisons.',
            'threads': sorted(threads, key=lambda t: t['cycles'], reverse=True),
            'modules': [{'name': n, 'samples': c, 'sample_share': c/total}
                        for n, c in by_module.most_common()],
            'top_functions': [{'module': n, 'nearest_function': f, 'object': o,
                               'samples': c, 'sample_share': c/total}
                              for (n, f, o), c in counts.most_common(60)]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--map', action='append', required=True)
    args = parser.parse_args()
    report = analyze(args.folder, args.map)
    (args.folder/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('summary', 'modules')}, indent=2))
    for row in report['top_functions'][:20]:
        print(f"{row['sample_share']:.1%}: {row['nearest_function']} ({row['module']})")
