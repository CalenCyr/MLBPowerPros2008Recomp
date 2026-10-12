# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare scheduler-idle off/on with identical executable, module and saved state."""
import argparse
import datetime
import json
from pathlib import Path
from compare_probe_speed import summarize


def compare(baseline, candidate):
    before, base = summarize(baseline)
    after, test = summarize(candidate)
    for key in ('runner_sha256', 'module_sha256', 'load_state_sha256', 'graphics_backend',
                'input_profile', 'requested_seconds', 'capture_interval_seconds', 'optimized_module'):
        if not before.get(key) or before[key] != after.get(key):
            raise ValueError(f'Missing or different probe condition: {key}')
    if before.get('scheduler_idle_skip_requested') is not False or after.get('scheduler_idle_skip_requested') is not True:
        raise ValueError('Require scheduler idle OFF first and ON second')
    if before.get('fallback_profile_requested') is not False or after.get('fallback_profile_requested') is not False:
        raise ValueError('Disable fallback profiling in both speed probes')
    base_skips=before['shutdown_counters'].get('scheduler_idle_skips')
    test_skips=after['shutdown_counters'].get('scheduler_idle_skips')
    if base_skips != 0 or not isinstance(test_skips, int) or test_skips <= 0:
        raise ValueError('Missing counters or scheduler optimization was not exercised')
    if before['shutdown_counters']['failed_code_verifications'] or after['shutdown_counters']['failed_code_verifications']:
        raise ValueError('Code verification failed')
    ratio=test['guest_frames_per_wall_second']/base['guest_frames_per_wall_second']
    return {'baseline':base,'scheduler_idle':test,'guest_frame_speed_ratio':ratio,
            'scheduler_idle_skips':test_skips,'runner_sha256':before['runner_sha256'],
            'restored_state_sha256':before['load_state_sha256'],
            'scope':'Consecutive short restored-state probes on this machine. Guest frame progress, not render FPS, CPU-time attribution, full-match validation or native-only execution.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path)
    parser.add_argument('candidate',type=Path)
    parser.add_argument('--output',type=Path,help='Save to a new report path for a benchmark batch')
    args=parser.parse_args()
    report=compare(args.baseline,args.candidate)
    output=args.output or Path(__file__).resolve().parents[1]/'local/analysis'/('scheduler-speed-comparison-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.json')
    if output.exists():
        raise ValueError('Refusing to overwrite a previous speed report')
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    print('Evidence:',output)
