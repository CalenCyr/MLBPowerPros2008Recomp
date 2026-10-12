# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare single-core and dual-core (separate GPU thread) probes with identical runner, module and state."""
import argparse
import datetime
import json
import re
from pathlib import Path
from compare_probe_speed import summarize


def compare(single, dual):
    before, base = summarize(single, allow_empty_mod_hooks=True, allow_dual_core=True)
    after, test = summarize(dual, allow_empty_mod_hooks=True, allow_dual_core=True)
    keys = ('runner_sha256', 'module_sha256', 'load_state_sha256', 'graphics_backend', 'input_profile',
            'requested_seconds', 'capture_interval_seconds', 'optimized_module',
            'scheduler_idle_skip_requested', 'skip_empty_mod_hooks_requested', 'cache_batch_requested',
            'module_coverage')
    for key in keys:
        if key not in before or key not in after or before[key] != after[key]:
            raise ValueError('Missing or different condition: ' + key)
    for probe, result, enabled in ((single, before, False), (dual, after, True)):
        if result.get('dual_core_requested') is not enabled or result.get('dual_core_confirmed') is not enabled:
            raise ValueError('Require a confirmed single-core probe first and a confirmed dual-core probe second')
        if f'CPU thread dual_core={int(enabled)}' not in (probe/'stderr.log').read_text(errors='replace'):
            raise ValueError('Missing runtime thread-mode proof')
        for key in ('runner_sha256', 'module_sha256', 'load_state_sha256'):
            if not re.fullmatch('[0-9a-f]{64}', result.get(key) or ''):
                raise ValueError('Invalid provenance: ' + key)
        if result.get('optimized_module') is not True or result.get('fallback_profile_requested') is not False:
            raise ValueError('Require optimized unprofiled module')
        if result.get('finish_requested') is not False or result.get('executed_seconds', 0) < result['requested_seconds'] - 2:
            raise ValueError('Incomplete interval')
        for key in ('mem1_snapshot_complete', 'mem2_snapshot_complete'):
            if result.get(key) is not True:
                raise ValueError('Missing final snapshot: ' + key)
        if (result.get('shutdown_counters') or {}).get('failed_code_verifications') != 0:
            raise ValueError('Missing or failed code verification')
    return {'single_core': base, 'dual_core': test,
            'guest_frame_speed_ratio': test['guest_frames_per_wall_second'] / base['guest_frames_per_wall_second'],
            'runner_sha256': before['runner_sha256'], 'module_sha256': before['module_sha256'],
            'restored_state_sha256': before['load_state_sha256'],
            'scope': 'Short restored-state probes on this PC. Guest frame progress, not render FPS, '
                     'determinism, full-game performance or native-only equivalence.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('single', type=Path)
    parser.add_argument('dual', type=Path)
    args = parser.parse_args()
    report = compare(args.single, args.dual)
    path = Path(__file__).resolve().parents[1]/'local/analysis'/('dual-core-speed-comparison-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.json')
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2)); print('Evidence:', path)
