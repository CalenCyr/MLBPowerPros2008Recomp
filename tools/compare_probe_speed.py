# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare idle probes restored from the same private state; not a gameplay FPS test."""
import argparse
import datetime
import json
import statistics
from pathlib import Path


def summarize(probe, *, allow_cache_batch=False, allow_empty_mod_hooks=False, allow_dual_core=False):
    if (probe/'benchmark-exclusion.json').exists():
        raise ValueError('Probe excluded by recorded validation evidence')
    result = json.loads((probe / 'result.json').read_text(encoding='utf-8-sig'))
    if result.get('lockstep_requested', False) or result.get('host_sampling_requested', False) or (probe/'host-sampling.json').exists():
        raise ValueError('Disable lockstep and external thread sampling in speed probes')
    if result.get('dispatch_timing_requested', False):
        raise ValueError('Disable dispatch timing in speed-comparison probes')
    if not allow_empty_mod_hooks and (result.get('skip_empty_mod_hooks_requested', False) or
            (result.get('empty_mod_hooks_counters') or {}).get('skipped_empty', False)):
        raise ValueError('Use the dedicated empty-mod comparison for active hook skipping')
    if not allow_cache_batch and (result.get('cache_batch_requested', False) or
            (result.get('shutdown_counters') or {}).get('cache_batch_extra_lines', 0) or
            (result.get('shutdown_counters') or {}).get('cache_batch_runs', 0)):
        raise ValueError('Use the dedicated cache batch comparison for active batching')
    if not allow_dual_core and (result.get('dual_core_requested', False) or result.get('dual_core_confirmed', False)):
        raise ValueError('Use the dedicated dual-core comparison for separate CPU/GPU threads')
    if result['exit_code'] != 0 or result['forced_stop'] or result['failed_command_count']:
        raise ValueError('Both probes must finish cleanly without failed commands')
    if not result['load_state_sha256'] or not result['physical_input_mappings_disabled']:
        raise ValueError('A restored state and isolated inputs are required')
    allowed = {'load_state', 'screenshot', 'pause', 'resume', 'read_memory', 'stop'}
    for command in (probe / 'control/processed').glob('*.ini'):
        fields = dict(line.split('=', 1) for line in command.read_text().splitlines() if '=' in line)
        if fields.get('command', '').strip() not in allowed:
            raise ValueError('Input or other state changes make this an unmatched idle probe')
    pending = list((probe / 'control/commands').glob('*.ini'))
    # The fallback shutdown request can arrive after the first stop has already
    # completed. Account for that exact redundant command without altering logs
    # or permitting unprocessed capture/input/state commands.
    redundant_stop = 0
    if pending:
        first_stop = probe/'control/processed/0009-stop.ini'
        log = probe/'stderr.log'
        if (len(pending) == 1 and pending[0].name == '0010-stop.ini' and
                pending[0].read_text().strip() == 'command=stop' and
                first_stop.is_file() and first_stop.read_text().strip() == 'command=stop' and
                log.is_file() and '[powerpros-diagnostic] core state callback=0' in log.read_text()):
            redundant_stop = 1
        else:
            raise ValueError('Pending commands remain in the probe')
    paths = list(probe.glob('status-progress-*.txt')) + [probe / 'status-before-stop.txt']
    samples = []
    for path in sorted(paths, key=lambda path: path.stat().st_mtime_ns):
        fields = dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)
        if fields.get('state') == 'running':
            samples.append((path.stat().st_mtime_ns / 1e9, int(fields['frame_count']), float(fields['speed'])))
    if len(samples) < 2:
        raise ValueError('At least two running status samples are required')
    duration = samples[-1][0] - samples[0][0]
    if duration < 30 or any(b[1] < a[1] for a, b in zip(samples, samples[1:])):
        raise ValueError('Need at least 30 seconds of monotonically advancing guest frames')
    frames = samples[-1][1] - samples[0][1]
    if frames <= 0:
        raise ValueError('No guest frames advanced')
    return result, {'probe': probe.name, 'sample_seconds': duration, 'guest_frames': frames,
                    'guest_frames_per_wall_second': frames / duration,
                    'median_reported_speed': statistics.median(s[2] for s in samples),
                    'accounted_redundant_shutdown_requests': redundant_stop,
                    'module_sha256': result['module_sha256']}


def compare(baseline, optimized):
    base_result, base = summarize(baseline)
    opt_result, opt = summarize(optimized)
    for key in ('load_state_sha256', 'graphics_backend', 'input_profile', 'requested_seconds'):
        if base_result[key] != opt_result[key]:
            raise ValueError(f'Probe conditions differ: {key}')
    for key in ('runner_sha256', 'fallback_profile_requested', 'scheduler_idle_skip_requested'):
        if base_result.get(key) != opt_result.get(key):
            raise ValueError(f'Probe conditions differ: {key}')
    if base_result['optimized_module'] or not opt_result['optimized_module']:
        raise ValueError('Expected baseline first, optimized module second')
    if base['module_sha256'] == opt['module_sha256']:
        raise ValueError('The module binaries must differ')
    ratio = opt['guest_frames_per_wall_second'] / base['guest_frames_per_wall_second']
    return {'baseline': base, 'optimized': opt, 'guest_frame_speed_ratio': ratio,
            'restored_state_sha256': base_result['load_state_sha256'],
            'scope': 'Two consecutive idle restored-state probes on this machine. Guest frame progress, not render FPS, full-match performance, or native-only execution.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('optimized', type=Path)
    args = parser.parse_args()
    report = compare(args.baseline, args.optimized)
    output = Path(__file__).resolve().parents[1] / 'local/analysis' / (
        'module-speed-comparison-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.json')
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Evidence:', output)
