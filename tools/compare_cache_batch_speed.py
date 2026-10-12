# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare cache batching OFF/ON with identical runtime, module and saved state."""
import argparse
import datetime
import json
from pathlib import Path
import re
from compare_probe_speed import summarize

MODULE_SHA = '393d5affad5cec418798745878cd5c75fe65f67c6540b51d6203bd9dab487cc6'
CHECKED_MODULES = {MODULE_SHA, '60a0611c6e528583f67b985cc31d290973cf96666685523eec8c1ab316702865'}


def compare(baseline, candidate):
    before, base = summarize(baseline, allow_cache_batch=True)
    after, test = summarize(candidate, allow_cache_batch=True)
    for key in ('runner_sha256', 'module_sha256', 'load_state_sha256', 'graphics_backend',
                'input_profile', 'requested_seconds', 'capture_interval_seconds',
                'optimized_module', 'scheduler_idle_skip_requested', 'module_coverage'):
        if key not in before or key not in after or before[key] != after[key]:
            raise ValueError(f'Missing or different probe condition: {key}')
    if before.get('cache_batch_requested') is not False or after.get('cache_batch_requested') is not True:
        raise ValueError('Require cache batching OFF first and ON second')
    for result, enabled in ((before, False), (after, True)):
        if result['module_sha256'] not in CHECKED_MODULES or result['optimized_module'] is not True:
            raise ValueError('Require the checked optimized module with loop budget 256')
        for key in ('runner_sha256', 'load_state_sha256'):
            if not re.fullmatch('[0-9a-f]{64}', result.get(key) or ''):
                raise ValueError('Invalid runner or state provenance')
        if result.get('fallback_profile_requested') is not False or result.get('finish_requested') is not False:
            raise ValueError('Require unprofiled probes that finish their interval')
        if result.get('executed_seconds', 0) < result['requested_seconds'] - 2:
            raise ValueError('Probe interval incomplete')
        counters = result.get('shutdown_counters') or {}
        if counters.get('failed_code_verifications') != 0:
            raise ValueError('Missing or failed code verification counter')
        runs, extra = (counters.get(k) for k in ('cache_batch_runs', 'cache_batch_extra_lines'))
        if type(runs) is not int or type(extra) is not int or runs < 0 or extra < 0:
            raise ValueError('Invalid cache batch counters')
        if (enabled and not (0 < runs <= extra <= runs * 127)) or (not enabled and (runs or extra)):
            raise ValueError('Cache batching not exercised consistently')
        scheduler = result['scheduler_idle_skip_requested']
        skips = counters.get('scheduler_idle_skips')
        if type(scheduler) is not bool or type(skips) is not int or skips < 0 or (scheduler and skips == 0) or (not scheduler and skips):
            raise ValueError('Scheduler state not exercised consistently')
    return {'baseline': base, 'candidate': test,
            'guest_frame_speed_ratio': test['guest_frames_per_wall_second'] / base['guest_frames_per_wall_second'],
            'candidate_batch_runs': after['shutdown_counters']['cache_batch_runs'],
            'candidate_extra_lines': after['shutdown_counters']['cache_batch_extra_lines'],
            'runner_sha256': before['runner_sha256'], 'module_sha256': before['module_sha256'],
            'restored_state_sha256': before['load_state_sha256'],
            'scope': 'Consecutive short idle restored-state OFF/ON probes on this machine. Guest frame progress, not render FPS, CPU-time attribution, full-match validation or native-only execution.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = compare(args.baseline, args.candidate)
    output = args.output or Path(__file__).resolve().parents[1] / 'local/analysis' / ('cache-batch-speed-comparison-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.json')
    if output.exists():
        raise ValueError('Refusing to overwrite a previous speed report')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
