# SPDX-License-Identifier: GPL-3.0-or-later
"""Check empty-mod OFF/ON comparisons and prevent unrelated benchmark contamination."""
import json
import tempfile
from pathlib import Path
from check_scheduler_probe_comparison import fixture
from compare_probe_speed import summarize


def main():
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder)
        baseline, before=fixture(root,'off',True,300)
        candidate, after=fixture(root,'on',True,600)
        common={'runner_sha256':'a'*64,'module_sha256':'b'*64,'load_state_sha256':'c'*64,
                'executed_seconds':120,'finish_requested':False,'module_coverage':'DOL/REL',
                'mem1_snapshot_complete':True,'mem2_snapshot_complete':True,
                'cache_batch_requested':False,'lockstep_requested':False,
                'host_sampling_requested':False,'dispatch_timing_requested':False}
        before |= common | {'skip_empty_mod_hooks_requested':False,
                            'empty_mod_hooks_counters':{'skipped_empty':False,'loaded_mods':0}}
        after |= common | {'skip_empty_mod_hooks_requested':True,
                           'empty_mod_hooks_counters':{'skipped_empty':True,'loaded_mods':0}}
        for probe, data, flag in ((baseline,before,0),(candidate,after,1)):
            (probe/'result.json').write_text(json.dumps(data))
            (probe/'stderr.log').write_text(f'[powerpros-diagnostic] mod_hooks_skip_empty_requested={flag} mod_hooks_skipped_empty={flag} loaded_mods=0\n')
        try:
            summarize(candidate)
        except ValueError:
            pass
        else:
            raise AssertionError('Generic comparison accepted active empty-mod skipping')
        from compare_empty_mod_hooks_speed import compare
        assert compare(baseline,candidate)['guest_frame_speed_ratio']==2
        changes=[{'skip_empty_mod_hooks_requested':False},
                 {'empty_mod_hooks_counters':None},
                 {'empty_mod_hooks_counters':{'skipped_empty':False,'loaded_mods':0}},
                 {'empty_mod_hooks_counters':{'skipped_empty':True,'loaded_mods':1}},
                 {'runner_sha256':'d'*64},{'module_sha256':'d'*64},{'load_state_sha256':'d'*64},
                 {'runner_sha256':None},{'graphics_backend':'Null'},{'input_profile':'other'},
                 {'requested_seconds':90},{'executed_seconds':20},{'capture_interval_seconds':30},
                 {'optimized_module':False},{'module_coverage':'DOL'},
                 {'scheduler_idle_skip_requested':False},{'fallback_profile_requested':True},
                 {'cache_batch_requested':True},{'lockstep_requested':True},{'host_sampling_requested':True},
                 {'dispatch_timing_requested':True},{'finish_requested':True},
                 {'forced_stop':True},{'exit_code':1},{'failed_command_count':1},
                 {'physical_input_mappings_disabled':False},
                 {'mem1_snapshot_complete':False},{'mem2_snapshot_complete':False},
                 {'shutdown_counters':after['shutdown_counters']|{'failed_code_verifications':1}},
                 {'shutdown_counters':after['shutdown_counters']|{'scheduler_idle_skips':0}}]
        for change in changes:
            (candidate/'result.json').write_text(json.dumps(after|change))
            try:
                compare(baseline,candidate)
            except ValueError:
                continue
            raise AssertionError('Invalid comparison accepted: '+str(change))
        (candidate/'result.json').write_text(json.dumps(after))
        (candidate/'stderr.log').write_text('')
        try:
            compare(baseline,candidate)
        except ValueError:
            pass
        else:
            raise AssertionError('Missing startup proof accepted')
    print(f'PASS ratio, generic comparison guard and {len(changes)+1} dedicated rejections')


if __name__=='__main__':
    main()
