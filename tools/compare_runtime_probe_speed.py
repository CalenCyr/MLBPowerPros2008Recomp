# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare runtime revisions with unchanged module, saved state and probe options."""
import argparse
import datetime
import json
import re
from pathlib import Path
from compare_probe_speed import summarize


def compare(baseline, candidate, *, allow_empty_mod_hooks=False):
    before, base = summarize(baseline, allow_empty_mod_hooks=allow_empty_mod_hooks)
    after, test = summarize(candidate, allow_empty_mod_hooks=allow_empty_mod_hooks)
    if allow_empty_mod_hooks:
        for probe, result in ((baseline, before), (candidate, after)):
            hooks = result.get('empty_mod_hooks_counters') or {}
            if (result.get('skip_empty_mod_hooks_requested') is not True or
                    hooks.get('skipped_empty') is not True or hooks.get('loaded_mods') != 0):
                raise ValueError('Both revisions must prove active skipping with zero mods')
            proof = 'mod_hooks_skip_empty_requested=1 mod_hooks_skipped_empty=1 loaded_mods=0'
            if proof not in (probe/'stderr.log').read_text():
                raise ValueError('Missing empty-mod startup proof')
    for result in (before, after):
        for key in ('runner_sha256', 'module_sha256', 'load_state_sha256'):
            if not re.fullmatch('[0-9a-f]{64}', result.get(key) or ''):
                raise ValueError(f'Missing or invalid binary/state provenance: {key}')
        if result.get('fallback_profile_requested') is not False:
            raise ValueError('Disable fallback profiling in speed probes')
        if result.get('optimized_module') is not True:
            raise ValueError('Use the optimized module in both runtime probes')
        if result.get('finish_requested') is not False or result.get('executed_seconds', 0) < result['requested_seconds'] - 2:
            raise ValueError('Early-finished probes are not comparable')
        enabled = result.get('scheduler_idle_skip_requested')
        if type(enabled) is not bool:
            raise ValueError('Missing scheduler setting')
        counters = result.get('shutdown_counters') or {}
        if counters.get('failed_code_verifications') != 0:
            raise ValueError('Missing code verification counter or failed verification')
        skips = counters.get('scheduler_idle_skips')
        if type(skips) is not int or skips < 0 or (enabled and skips == 0) or (not enabled and skips != 0):
            raise ValueError('Scheduler setting was not exercised consistently')
    for key in ('module_sha256', 'load_state_sha256', 'graphics_backend', 'input_profile',
                'requested_seconds', 'capture_interval_seconds', 'scheduler_idle_skip_requested',
                'module_coverage', 'module_compiler', 'skip_empty_mod_hooks_requested'):
        if key not in before or key not in after or before[key] != after[key]:
            raise ValueError(f'Missing or different probe condition: {key}')
    if before['runner_sha256'] == after['runner_sha256']:
        raise ValueError('The runtime executables must differ')
    if 'runner_path' in before and 'runner_path' in after:
        if Path(before['runner_path']).resolve().parent != Path(after['runner_path']).resolve().parent:
            raise ValueError('Keep both runtime revisions in the same executable directory')
    base['runner_sha256'] = before['runner_sha256']
    test['runner_sha256'] = after['runner_sha256']
    return {'baseline': base, 'candidate': test,
            'guest_frame_speed_ratio': test['guest_frames_per_wall_second'] / base['guest_frames_per_wall_second'],
            'restored_state_sha256': before['load_state_sha256'],
            'scheduler_idle_skip_requested': before['scheduler_idle_skip_requested'],
            'empty_mod_hooks_enabled_in_both_revisions': allow_empty_mod_hooks,
            'scope': 'Short restored-state probes on this machine with different runtime executables. Guest frame progress, not render FPS, CPU-time attribution, full-match validation or native-only execution.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-empty-mod-hooks', action='store_true', help='Require identical active skipping with startup proof and zero mods in both revisions')
    args = parser.parse_args()
    report = compare(args.baseline, args.candidate, allow_empty_mod_hooks=args.allow_empty_mod_hooks)
    output = args.output or Path(__file__).resolve().parents[1] / 'local/analysis' / (
        'runtime-speed-comparison-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.json')
    if output.exists():
        raise ValueError('Refusing to overwrite a previous speed report')
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Evidence:', output)
