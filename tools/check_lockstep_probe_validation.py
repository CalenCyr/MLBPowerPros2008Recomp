# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise audit rejection using independent boundary fixtures."""
import copy
import json
import tempfile
from pathlib import Path
from check_lockstep_probe import validate


def main():
    result = {
        'lockstep_requested': True, 'lockstep_trace_pc': 0xffffffff,
        'requested_seconds': 90, 'executed_seconds': 90, 'finish_requested': False,
        'physical_input_mappings_disabled': True, 'load_state_sha256': 'a'*64,
        'runner_sha256': 'b'*64, 'module_sha256': 'c'*64,
        'failed_command_count': 0, 'mem1_snapshot_complete': True, 'mem2_snapshot_complete': True,
        'reached_running_or_paused_state': True, 'forced_stop': False, 'exit_code': 0,
        'shutdown_counters': {'failed_code_verifications': 0, 'native_dispatches': 5000001},
        'lockstep_counters': {'checks': 5, 'distinct_pcs': 5, 'reports': 0,
                             'cap_hits': 0, 'filtered': 0, 'undercharges': 0, 'max_deficit': 0,
                             'skipped_fallback': 1, 'skipped_zero': 1},
    }
    for key in ('fallback_profile_requested', 'dispatch_timing_requested', 'cache_batch_requested',
                'scheduler_idle_skip_requested', 'host_sampling_requested'):
        result[key] = False
    rows = [f'[ls-boundary] entry=0x{pc:08X} end=0x80000110 steps=20 N_cyc=22 I_cyc=22 '
            'cycle_align=1 reached=1 cap_hit=0 matched=1\n'
            for pc in (0x80000100, 0x80000200, 0x80000300)]
    log = ''.join(rows)+'[powerpros-diagnostic] core state callback=0\n'
    required = (0x80000100,)
    cases = []
    for key, value in (('lockstep_requested', False), ('lockstep_trace_pc', 0),
                       ('executed_seconds', 20), ('finish_requested', True),
                       ('physical_input_mappings_disabled', False), ('load_state_sha256', None),
                       ('forced_stop', True), ('exit_code', 1), ('failed_command_count', 1),
                       ('mem1_snapshot_complete', False), ('mem2_snapshot_complete', False),
                       ('reached_running_or_paused_state', False)):
        changed = copy.deepcopy(result)
        changed[key] = value
        cases.append((key, changed, log, required))
    for key in ('fallback_profile_requested', 'dispatch_timing_requested', 'cache_batch_requested',
                'scheduler_idle_skip_requested', 'host_sampling_requested'):
        cases.append((key, result | {key: True}, log, required))
    for key in ('reports', 'cap_hits', 'filtered', 'undercharges', 'max_deficit'):
        changed = copy.deepcopy(result)
        changed['lockstep_counters'][key] = 1
        cases.append((key, changed, log, required))
    changed = copy.deepcopy(result)
    changed['lockstep_counters']['distinct_pcs'] = 4
    cases.append(('repeated checks', changed, log, required))
    changed = copy.deepcopy(result)
    changed['lockstep_counters']['checks'] = 2
    cases.append(('too few checks', changed, log, required))
    for label, text in (
        ('missing boundary', log.replace(rows[1], '')),
        ('duplicate boundary', log.replace(rows[1], rows[0])),
        ('unreached boundary', log.replace('reached=1', 'reached=0', 1)),
        ('step cap boundary', log.replace('cap_hit=0', 'cap_hit=1', 1)),
        ('mismatched boundary', log.replace('matched=1', 'matched=0', 1)),
        ('zero steps', log.replace('steps=20', 'steps=0', 1)),
        ('negative cycles', log.replace(rows[1], rows[1].replace('N_cyc=22', 'N_cyc=-1'))),
        ('aligned boundary undercharge', log.replace(rows[1], rows[1].replace('I_cyc=22', 'I_cyc=21'))),
        ('required cycles differ', log.replace('I_cyc=22', 'I_cyc=23', 1)),
        ('unaccounted divergence', log+'[lockstep] DIVERGE\n'),
        ('invalid memory', log+'[lockstep] MEM2 snapshot invalid\n'),
        ('missing shutdown', log.replace('[powerpros-diagnostic] core state callback=0', '')),
    ):
        cases.append((label, result, text, required))
    cases.append(('required entry absent', result, log, (0x80000400,)))
    cases.append(('empty-mod skipping needs explicit audit scope', result | {
        'skip_empty_mod_hooks_requested':True,
        'empty_mod_hooks_counters':{'skipped_empty':True,'loaded_mods':0}},log,required))
    with tempfile.TemporaryDirectory() as folder:
        probe = Path(folder)
        def run(data, text, entries, allow=False):
            (probe/'result.json').write_text(json.dumps(data))
            (probe/'stderr.log').write_text(text)
            return validate(probe, entries, min_checks=3,allow_empty_mod_hooks=allow)
        report = run(result, log, required)
        assert report['checks'] == 5 and report['completed_boundary_comparisons'] == 3
        assert report['required_entries'][0]['native_cycles'] == 22
        failures = []
        for label, data, text, entries in cases:
            try:
                run(data, text, entries)
            except (ValueError, AssertionError, KeyError):
                pass
            else:
                failures.append(label)
        if failures:
            raise AssertionError('Invalid audits accepted: '+', '.join(failures))
        mod_result=result | {'skip_empty_mod_hooks_requested':True,
            'empty_mod_hooks_counters':{'skipped_empty':True,'loaded_mods':0}}
        proof='mod_hooks_skip_empty_requested=1 mod_hooks_skipped_empty=1 loaded_mods=0\n'
        assert run(mod_result,log+proof,required,True)['empty_mod_hooks_skipping'] is True
        for data,text in ((result,log+proof),(mod_result,log),
                          (mod_result | {'empty_mod_hooks_counters':{'skipped_empty':True,'loaded_mods':1}},log+proof)):
            try:
                run(data,text,required,True)
            except ValueError:
                pass
            else:
                raise AssertionError('Unproven empty-mod audit accepted')
    print(f'PASS completed-versus-skipped accounting, explicit empty-mod scope and {len(cases)+3} invalid audit rejections')


if __name__ == '__main__':
    main()
