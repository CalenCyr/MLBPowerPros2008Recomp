# SPDX-License-Identifier: GPL-3.0-or-later
"""Check a complete, unfiltered lockstep audit with per-entry boundary accounting."""
import argparse
import json
import re
from pathlib import Path
from check_probe_shutdown import check as check_shutdown

PATTERN = re.compile(r'\[ls-boundary\] entry=0x([0-9A-F]+) end=0x([0-9A-F]+) steps=(\d+) N_cyc=(-?\d+) I_cyc=(-?\d+) cycle_align=(\d+) reached=(\d+) cap_hit=(\d+) matched=(\d+)')


def validate(probe, required_entries=(), min_checks=1000, *, allow_empty_mod_hooks=False):
    result = json.loads((probe/'result.json').read_text(encoding='utf-8-sig'))
    if result.get('lockstep_requested') is not True or result.get('lockstep_trace_pc') != 0xffffffff:
        raise ValueError('Require lockstep with all boundary records')
    if result.get('executed_seconds', 0) < result['requested_seconds']-2 or result.get('finish_requested'):
        raise ValueError('Incomplete audit interval')
    for key in ('fallback_profile_requested', 'dispatch_timing_requested', 'cache_batch_requested',
                'scheduler_idle_skip_requested', 'host_sampling_requested'):
        if result.get(key) is not False:
            raise ValueError('Other diagnostics or performance option enabled: '+key)
    if result.get('physical_input_mappings_disabled') is not True or not result.get('load_state_sha256'):
        raise ValueError('Require restored state and isolated inputs')
    if result.get('failed_command_count') != 0:
        raise ValueError('Failed or missing command accounting')
    for key in ('mem1_snapshot_complete', 'mem2_snapshot_complete'):
        if result.get(key) is not True:
            raise ValueError('Missing final memory snapshot: '+key)
    mod_hooks = result.get('empty_mod_hooks_counters') or {}
    mod_skipping = result.get('skip_empty_mod_hooks_requested', False) or mod_hooks.get('skipped_empty', False)
    if mod_skipping or allow_empty_mod_hooks:
        if (not allow_empty_mod_hooks or result.get('skip_empty_mod_hooks_requested') is not True or
                mod_hooks.get('skipped_empty') is not True or mod_hooks.get('loaded_mods') != 0):
            raise ValueError('Require explicit empty-mod audit scope and startup accounting')
    counters = result.get('lockstep_counters') or {}
    for key in ('reports', 'cap_hits', 'filtered', 'undercharges', 'max_deficit'):
        if counters.get(key) != 0:
            raise ValueError('Audit not exact/unfiltered: '+key)
    # Hardware-side MEM2 writes (synchronous HLE) are replayed from native; each must be re-applied.
    if 'hw_mem2_writes' in counters and counters.get('hw_mem2_replayed') != counters['hw_mem2_writes']:
        raise ValueError('Recorded hardware MEM2 write not replayed')
    checks = counters.get('checks', 0)
    if checks < min_checks or counters.get('distinct_pcs') != checks:
        raise ValueError('Insufficient or repeated entry checks')
    text = (probe/'stderr.log').read_text()
    if allow_empty_mod_hooks and 'mod_hooks_skip_empty_requested=1 mod_hooks_skipped_empty=1 loaded_mods=0' not in text:
        raise ValueError('Missing startup proof for empty-mod audit')
    if '[lockstep] MEM2 snapshot invalid' in text or '[lockstep] DIVERGE' in text:
        raise ValueError('Unaccounted memory snapshot failure or divergence')
    rows = []
    for match in PATTERN.finditer(text):
        row = dict(zip(('entry','end','steps','native_cycles','shadow_cycles','cycle_align','reached','cap_hit','matched'),
                       [int(match[1],16),int(match[2],16)]+[int(x) for x in match.groups()[2:]]))
        if row['reached'] != 1 or row['cap_hit'] != 0 or row['matched'] != 1 or row['steps'] <= 0:
            raise ValueError('Incomplete or divergent boundary record')
        if row['native_cycles'] <= 0 or row['shadow_cycles'] <= 0:
            raise ValueError('Nonpositive completed boundary cycles')
        if row['cycle_align'] not in (0, 1) or (row['cycle_align'] and row['shadow_cycles'] < row['native_cycles']):
            raise ValueError('Invalid or undercharged cycle alignment')
        rows.append(row)
    completed = checks-counters['skipped_fallback']-counters['skipped_zero']
    if len(rows) != completed or len({r['entry'] for r in rows}) != completed:
        raise ValueError('Missing or duplicate boundary accounting')
    required = []
    for pc in required_entries:
        found = [r for r in rows if r['entry'] == pc]
        if len(found) != 1 or found[0]['native_cycles'] != found[0]['shadow_cycles']:
            raise ValueError('Required entry absent or cycle alignment inexact: '+hex(pc))
        required.append(found[0])
    check_shutdown(probe)
    return {'probe':probe.name,'checks':checks,'completed_boundary_comparisons':completed,
            'skipped_fallback':counters['skipped_fallback'],'skipped_zero':counters['skipped_zero'],
            'empty_mod_hooks_skipping':allow_empty_mod_hooks,
            'hw_mem2_writes_replayed':counters.get('hw_mem2_writes'),
            'hw_mem2_bytes_replayed':counters.get('hw_mem2_bytes'),
            'required_entries':required,'runner_sha256':result['runner_sha256'],
            'module_sha256':result['module_sha256'],'state_sha256':result['load_state_sha256'],
            'scope':'Reached unique entries in a bounded audit. Skipped entries and unvisited paths are not validated; not full-game or native-only equivalence.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe',type=Path)
    parser.add_argument('--require-entry',action='append',type=lambda s:int(s,0),default=[])
    parser.add_argument('--min-checks',type=int,default=1000)
    parser.add_argument('--allow-empty-mod-hooks',action='store_true')
    args = parser.parse_args()
    report = validate(args.probe,args.require_entry,args.min_checks,allow_empty_mod_hooks=args.allow_empty_mod_hooks)
    (args.probe/'lockstep-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS lockstep entries, exact required boundaries and complete accounting:',json.dumps(report,indent=2))
