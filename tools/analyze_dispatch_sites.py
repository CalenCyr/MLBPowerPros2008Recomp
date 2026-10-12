# SPDX-License-Identifier: GPL-3.0-or-later
"""Rank sampled module entry PCs by raw elapsed time, including callbacks."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
from analyze_dispatch_timing import analyze, CONTEXTS
from analyze_fallback_profile import annotate


def validate_sites(rows, phase_report):
    fields = {'kind', 'context', 'pc', 'samples', 'total_ns', 'max_ns'}
    sites, dropped, seen = [], {}, set()
    for raw in rows:
        if set(raw) != fields or raw['context'] not in CONTEXTS:
            raise ValueError('Invalid site columns or context')
        if raw['kind'] not in ('site', 'dropped') or not re.fullmatch('[0-9A-Fa-f]{8}', raw['pc'] or ''):
            raise ValueError('Invalid site kind or PC')
        pc = int(raw['pc'], 16)
        numbers = {key: int(raw[key]) for key in ('samples', 'total_ns', 'max_ns')}
        samples, total, maximum = (numbers[k] for k in ('samples', 'total_ns', 'max_ns'))
        if any(value < 0 or value > (1 << 64) - 1 for value in numbers.values()):
            raise ValueError('Site aggregate outside uint64')
        if maximum > total or total > samples * maximum or (samples == 0 and (total or maximum)):
            raise ValueError('Invalid site time aggregate')
        context = raw['context']
        key = raw['kind'], context, pc
        if key in seen:
            raise ValueError('Duplicate site row')
        seen.add(key)
        entry = {'context': context, 'pc': f'0x{pc:08X}', **numbers}
        if raw['kind'] == 'dropped':
            if pc or context in dropped:
                raise ValueError('Invalid dropped row')
            dropped[context] = entry
        else:
            if pc % 4 or samples == 0:
                raise ValueError('Unaligned or empty site')
            sites.append(entry)
    if len(sites) > 4096 or set(dropped) != set(CONTEXTS):
        raise ValueError('Site cap exceeded or dropped accounting missing')
    for context in CONTEXTS:
        group = [s for s in sites if s['context'] == context] + [dropped[context]]
        expected = phase_report['contexts'][context]['phases']['module_dispatch']
        if any(sum(s[k] for s in group) != expected[k] for k in ('samples', 'total_ns')):
            raise ValueError('Site accounting differs from module phase')
        if max(s['max_ns'] for s in group) != expected['max_ns']:
            raise ValueError('Site maximum differs from module phase')
    total = phase_report['raw_sampled_time_by_phase_ns']['module_dispatch']
    for entry in sites:
        entry['mean_raw_elapsed_ns'] = entry['total_ns'] / entry['samples']
        entry['raw_share_of_sampled_module_time'] = entry['total_ns'] / total if total else None
    sites.sort(key=lambda s: (-s['total_ns'], s['context'], s['pc']))
    return {'recorded_sites': len(sites), 'sampled_module_time_ns': total,
            'dropped_by_context': dropped, 'sites_ranked_by_raw_sampled_time': sites}


def analyze_sites(probe):
    result = json.loads((probe / 'result.json').read_text(encoding='utf-8-sig'))
    if result.get('dispatch_timing_sites_saved') is not True:
        raise ValueError('Probe did not save dispatch timing sites')
    phase_report = analyze(probe)
    path = probe / 'dispatch-timing.csv.sites.csv'
    with path.open(newline='') as stream:
        report = validate_sites(list(csv.DictReader(stream)), phase_report)
    top = [entry.copy() for entry in report['sites_ranked_by_raw_sampled_time'][:25]]
    annotate(Path(__file__).resolve().parents[1], top)
    report.update({'top25_with_generated_comments': top, 'phase_report': phase_report,
                   'sites_csv_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'scope': 'Periodic runtime entry-PC samples of module elapsed time including callbacks and system preemption, across startup/restore/shutdown. Entry PCs are not necessarily function starts. Ranking is biased by periodic sampling and clock overhead. No exclusive function costs, whole-game CPU percentages or speed-gain claim. Capped sites retain overflow accounting.'})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_directory', type=Path)
    args = parser.parse_args()
    report = analyze_sites(args.probe_directory)
    output = args.probe_directory / 'dispatch-sites-report.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'recorded_sites': report['recorded_sites'],
                      'dropped_by_context': report['dropped_by_context'],
                      'top10': report['top25_with_generated_comments'][:10],
                      'report': str(output)}, indent=2))
