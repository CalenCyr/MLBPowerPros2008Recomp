# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate sampled hook accounting and report frequencies, never CPU time."""
import argparse
import csv
import json
import re
from pathlib import Path


def read_profile(path, expected_hooks=None):
    metadata = {}
    sites = {'slow': [], 'cache_fast': []}
    seen = set()
    required = {'stride', 'total_slow', 'dropped_slow',
                'total_cache_fast', 'dropped_cache_fast'}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['kind', 'pc', 'raw', 'count']:
            raise ValueError('Unexpected profile columns')
        for row in reader:
            if set(row) != {'kind', 'pc', 'raw', 'count'} or None in row.values():
                raise ValueError('Incomplete profile row')
            kind = row['kind']
            if not re.fullmatch(r'[0-9A-Fa-f]{8}', row['pc']) or not re.fullmatch(r'[0-9A-Fa-f]{8}', row['raw']):
                raise ValueError('Invalid PC or raw instruction')
            pc, raw, count = int(row['pc'], 16), int(row['raw'], 16), int(row['count'])
            if count < 0 or count > (1 << 64) - 1:
                raise ValueError('Count outside uint64 range')
            if kind in required:
                if kind in metadata or pc or raw:
                    raise ValueError('Duplicate or malformed metadata')
                metadata[kind] = count
            elif kind in sites:
                key = kind, pc, raw
                if key in seen or pc % 4 or not count:
                    raise ValueError('Duplicate, unaligned or empty sample site')
                seen.add(key)
                sites[kind].append({'pc': f'0x{pc:08X}', 'raw': f'0x{raw:08X}', 'samples': count})
            else:
                raise ValueError(f'Unknown row kind: {kind}')
    if set(metadata) != required or metadata['stride'] != 1024:
        raise ValueError('Missing metadata or unsupported stride')
    total = metadata['total_slow'] + metadata['total_cache_fast']
    if expected_hooks is not None and total != expected_hooks:
        raise ValueError('Profile totals disagree with runtime hook counter')
    groups = {}
    for kind, entries in sites.items():
        observed = metadata['total_' + kind]
        dropped = metadata['dropped_' + kind]
        collected = sum(entry['samples'] for entry in entries)
        if len(entries) > 4096 or collected + dropped != observed // metadata['stride']:
            raise ValueError(f'Invalid sampled accounting for {kind}')
        groups[kind] = {'observed_calls': observed,
                        'percent_of_hook_calls': 100 * observed / total if total else None,
                        'collected_samples': collected, 'dropped_samples': dropped,
                        'sites': sorted(entries, key=lambda entry: (-entry['samples'], entry['pc'], entry['raw']))}
    return {'stride_per_kind': metadata['stride'], 'total_hook_calls': total, 'groups': groups}


def annotate(root, entries):
    """Copy only instruction comments for sampled PCs from read-only generated C."""
    wanted = {int(entry['pc'], 16) for entry in entries}
    found = {}
    pattern = re.compile(r'// ([0-9A-Fa-f]{8}):\s*(.+)')
    directories = ['local/generated/dolrecomp/dol/main_chunks',
                   'local/generated/dolrecomp/rel-linked/runtime_rel_chunks']
    for directory in directories:
        for path in (root / directory).glob('chunk_*.c'):
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                match = pattern.search(line)
                if match and int(match[1], 16) in wanted:
                    found.setdefault(int(match[1], 16), {
                        'generated_instruction_comment': match[2],
                        'generated_source': path.relative_to(root).as_posix(), 'source_line': number})
    for entry in entries:
        entry.update(found.get(int(entry['pc'], 16), {}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = json.loads((args.probe / 'result.json').read_text(encoding='utf-8-sig'))
    if not result.get('fallback_profile_requested') or not result.get('fallback_profile_saved'):
        raise ValueError('Probe did not request and save a fallback profile')
    if result['exit_code'] != 0 or result['forced_stop'] or result['shutdown_counters']['failed_code_verifications']:
        raise ValueError('Probe did not finish cleanly with verified code')
    report = read_profile(args.probe / 'fallback-profile.csv', result['shutdown_counters']['instruction_hook_fallbacks'])
    report['provenance'] = {key: result[key] for key in (
        'runner_sha256', 'module_sha256', 'load_state_sha256', 'executed_seconds', 'graphics_backend')}
    log = (args.probe / 'stderr.log').read_text(encoding='utf-8', errors='replace')
    report['native_dispatch_sampled_top16'] = [
        {'pc': '0x' + pc.upper(), 'samples': int(count)} for pc, count in
        re.findall(r'\[staticrecomp\] dispatch-site pc=([0-9a-fA-F]{8}) samples=(\d+)', log)]
    hook_sites = [entry for group in report['groups'].values() for entry in group['sites']]
    annotate(root, hook_sites + report['native_dispatch_sampled_top16'])
    paths = [args.probe / 'control/artifacts' / ('mem1-' + part + '.bin') for part in ('low', 'high')]
    report['hook_instructions_checked_against_final_mem1'] = False
    if all(path.exists() for path in paths):
        parts = [path.read_bytes() for path in paths]
        if [len(part) for part in parts] != [16 * 1024 * 1024, 8 * 1024 * 1024]:
            raise ValueError('Incomplete MEM1 snapshot')
        memory = b''.join(parts)
        for entry in hook_sites:
            offset = int(entry['pc'], 16) - 0x80000000
            if not 0 <= offset <= len(memory) - 4:
                raise ValueError('Sample instruction outside final MEM1')
            if int.from_bytes(memory[offset:offset + 4], 'big') != int(entry['raw'], 16):
                raise ValueError(f"Instruction changed at {entry['pc']}")
        report['hook_instructions_checked_against_final_mem1'] = True
    report['limits'] = [
        'Counts include startup, state restore and shutdown, not only the requested running interval.',
        'Each category samples every 1024th call; periodic sampling can be biased.',
        'Frequencies are not CPU time, native execution coverage or speed measurements.',
        'Native dispatch samples list only the top 16 sites, not the complete distribution.',
        'Final snapshot equality does not prove instructions stayed unchanged throughout execution.']
    output = args.probe / 'fallback-profile-report.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'PASS profile accounting: {report["total_hook_calls"]} hook calls; '
          f'cache fast {report["groups"]["cache_fast"]["percent_of_hook_calls"]:.4f}%; {output}')


if __name__ == '__main__':
    main()
