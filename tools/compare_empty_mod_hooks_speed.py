# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare empty-mod hook skipping OFF/ON with identical runner, module and state."""
import argparse
import datetime
import json
import re
from pathlib import Path
from compare_probe_speed import summarize


def compare(baseline, candidate):
    before, base=summarize(baseline,allow_empty_mod_hooks=True)
    after, test=summarize(candidate,allow_empty_mod_hooks=True)
    keys=('runner_sha256','module_sha256','load_state_sha256','graphics_backend','input_profile',
          'requested_seconds','capture_interval_seconds','optimized_module',
          'scheduler_idle_skip_requested','module_coverage')
    for key in keys:
        if key not in before or key not in after or before[key] != after[key]:
            raise ValueError('Missing or different condition: '+key)
    for probe,result,enabled in ((baseline,before,False),(candidate,after,True)):
        if result.get('skip_empty_mod_hooks_requested') is not enabled:
            raise ValueError('Require OFF first and ON second')
        counters=result.get('empty_mod_hooks_counters') or {}
        if counters.get('loaded_mods') != 0 or counters.get('skipped_empty') is not enabled:
            raise ValueError('No proof of empty manager and requested callback configuration')
        proof=f'mod_hooks_skip_empty_requested={int(enabled)} mod_hooks_skipped_empty={int(enabled)} loaded_mods=0'
        if proof not in (probe/'stderr.log').read_text():
            raise ValueError('Missing runtime startup proof')
        for key in ('runner_sha256','module_sha256','load_state_sha256'):
            if not re.fullmatch('[0-9a-f]{64}',result.get(key) or ''):
                raise ValueError('Invalid provenance: '+key)
        if result.get('optimized_module') is not True or result.get('fallback_profile_requested') is not False:
            raise ValueError('Require optimized unprofiled module')
        if result.get('finish_requested') is not False or result.get('executed_seconds',0) < result['requested_seconds']-2:
            raise ValueError('Incomplete interval')
        for key in ('mem1_snapshot_complete','mem2_snapshot_complete'):
            if result.get(key) is not True:
                raise ValueError('Missing final snapshot: '+key)
        shutdown=result.get('shutdown_counters') or {}
        if shutdown.get('failed_code_verifications') != 0:
            raise ValueError('Missing or failed code verification')
        scheduler=result['scheduler_idle_skip_requested']
        skips=shutdown.get('scheduler_idle_skips')
        if type(scheduler) is not bool or type(skips) is not int or skips < 0 or bool(skips) != scheduler:
            raise ValueError('Scheduler option not exercised consistently')
    return {'baseline':base,'candidate':test,
            'guest_frame_speed_ratio':test['guest_frames_per_wall_second']/base['guest_frames_per_wall_second'],
            'runner_sha256':before['runner_sha256'],'module_sha256':before['module_sha256'],
            'restored_state_sha256':before['load_state_sha256'],
            'scope':'Short consecutive restored-state OFF/ON probes on this PC with no loaded mods. Guest frame progress, not render FPS, full-game performance or native-only equivalence.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path)
    parser.add_argument('candidate',type=Path)
    args=parser.parse_args()
    report=compare(args.baseline,args.candidate)
    path=Path(__file__).resolve().parents[1]/'local/analysis'/('empty-mod-hooks-speed-comparison-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.json')
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2)); print('Evidence:',path)
