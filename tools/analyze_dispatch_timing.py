# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate sampled dispatch phase timings; raw elapsed time, not exclusive CPU time."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

CONTEXTS = ('outside_rel_envelope', 'inside_rel_envelope')
PHASES = ('address_resolution', 'module_dispatch', 'return_translation')


def validate(rows, native_dispatches):
    fields = {'context', 'phase', 'observed_dispatches', 'stride', 'samples', 'total_ns', 'max_ns'}
    entries = {}
    for raw in rows:
        if set(raw) != fields:
            raise ValueError('Unexpected timing CSV columns')
        key = (raw['context'], raw['phase'])
        if key in entries:
            raise ValueError('Duplicate timing row')
        entry = {k: int(raw[k]) for k in fields - {'context', 'phase'}}
        if any(value < 0 for value in entry.values()) or entry['max_ns'] > entry['total_ns']:
            raise ValueError('Invalid aggregate')
        if entry['samples'] == 0 and (entry['total_ns'] or entry['max_ns']):
            raise ValueError('Time recorded without samples')
        if entry['total_ns'] > entry['samples'] * entry['max_ns']:
            raise ValueError('Total exceeds the sample maximum')
        entries[key] = entry
    expected = {(context, phase) for context in CONTEXTS for phase in PHASES} | {('calibration', 'clock_pair')}
    if set(entries) != expected:
        raise ValueError('Missing or unexpected timing rows')
    calibration = entries[('calibration', 'clock_pair')]
    if calibration['observed_dispatches'] or calibration['stride'] or calibration['samples'] != 10000:
        raise ValueError('Invalid clock-pair calibration')
    clock_mean = calibration['total_ns'] / calibration['samples']
    observed_total = 0
    contexts = {}
    for context in CONTEXTS:
        observed = entries[(context, PHASES[0])]['observed_dispatches']
        observed_total += observed
        phases = {}
        for phase in PHASES:
            entry = entries[(context, phase)]
            if entry['stride'] != 4096 or entry['observed_dispatches'] != observed or entry['samples'] != observed // 4096:
                raise ValueError('Dispatch count or phase sampling mismatch')
            mean = entry['total_ns'] / entry['samples'] if entry['samples'] else None
            phases[phase] = entry | {'mean_raw_elapsed_ns': mean,
                                    'near_clock_pair_cost': mean is not None and mean <= clock_mean * 2}
        contexts[context] = {'observed_dispatches': observed, 'phases': phases}
    if observed_total != native_dispatches:
        raise ValueError('Timing dispatch total differs from shutdown counter')
    totals = {phase: sum(entries[(context, phase)]['total_ns'] for context in CONTEXTS) for phase in PHASES}
    timed_total = sum(totals.values())
    if not timed_total:
        raise ValueError('No elapsed time sampled')
    return {'contexts': contexts, 'clock_pair_mean_raw_ns': clock_mean,
            'raw_sampled_time_by_phase_ns': totals,
            'raw_share_of_three_sampled_phases': {phase: total / timed_total for phase, total in totals.items()}}


def analyze(probe):
    result = json.loads((probe / 'result.json').read_text(encoding='utf-8-sig'))
    if result.get('dispatch_timing_requested') is not True or result.get('dispatch_timing_saved') is not True:
        raise ValueError('Probe did not request and save dispatch timings')
    if result['exit_code'] != 0 or result['forced_stop'] or result['failed_command_count']:
        raise ValueError('Timing probe did not finish cleanly')
    counters = result.get('shutdown_counters') or {}
    if counters.get('failed_code_verifications') != 0:
        raise ValueError('Missing or failed code verification counter')
    csv_path = probe / 'dispatch-timing.csv'
    with csv_path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    report = validate(rows, counters['native_dispatches'])
    report.update({'probe': str(probe.resolve()), 'runner_sha256': result['runner_sha256'],
                   'module_sha256': result['module_sha256'], 'load_state_sha256': result['load_state_sha256'],
                   'csv_sha256': hashlib.sha256(csv_path.read_bytes()).hexdigest(),
                   'scope': 'Periodic samples of elapsed intervals on the guest execution thread, including startup/restore/shutdown. Module time includes instruction callbacks. Three phases exclude block guards, scheduling, JIT, graphics thread and other work. Clock overhead is reported without automatic subtraction. Sampling can be biased and includes preemption; these shares are not whole-frame CPU percentages, render FPS or recomp coverage.'})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_directory', type=Path)
    args = parser.parse_args()
    report = analyze(args.probe_directory)
    output = args.probe_directory / 'dispatch-timing-report.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
