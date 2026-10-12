# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare the Clang C-backend DOL module with the LLVM-backend DOL module.

Same runner, saved state and probe options; both modules must link the same
preserved MSVC REL objects, so only the DOL translation differs.
"""
import argparse
import datetime
import json
import re
from pathlib import Path
from compare_probe_speed import summarize


def compare(baseline, candidate, baseline_mode='clang_dol_msvc_rel', candidate_mode='llvm_dol_msvc_rel'):
    before, base = summarize(baseline, allow_empty_mod_hooks=True)
    after, test = summarize(candidate, allow_empty_mod_hooks=True)
    keys = ('runner_sha256', 'load_state_sha256', 'graphics_backend', 'input_profile',
            'requested_seconds', 'capture_interval_seconds', 'optimized_module',
            'scheduler_idle_skip_requested', 'skip_empty_mod_hooks_requested',
            'cache_batch_requested', 'module_coverage')
    for key in keys:
        if key not in before or key not in after or before[key] != after[key]:
            raise ValueError('Missing or different condition: ' + key)
    manifests = []
    for probe, result, mode in ((baseline, before, baseline_mode), (candidate, after, candidate_mode)):
        for key in ('module_sha256', 'runner_sha256', 'load_state_sha256'):
            if not re.fullmatch('[0-9a-f]{64}', result.get(key) or ''):
                raise ValueError('Invalid provenance: ' + key)
        if result.get('optimized_module') is not True or result.get('fallback_profile_requested') is not False:
            raise ValueError('Require optimized unprofiled modules')
        if result.get('finish_requested') is not False or result.get('executed_seconds', 0) < result['requested_seconds'] - 2:
            raise ValueError('Incomplete interval')
        for key in ('mem1_snapshot_complete', 'mem2_snapshot_complete'):
            if result.get(key) is not True:
                raise ValueError('Missing final snapshot: ' + key)
        if (result.get('shutdown_counters') or {}).get('failed_code_verifications') != 0:
            raise ValueError('Missing or failed code verification')
        data = json.loads((probe / 'module-build-manifest.json').read_text())
        if data.get('binary_sha256') != result['module_sha256']:
            raise ValueError('Build manifest does not identify the probed module')
        if data.get('mode') != mode:
            raise ValueError(f'Expected module mode {mode}, found {data.get("mode")}')
        manifests.append(data)
    if candidate_mode == 'llvm_all':
        # vs llvm_dol_msvc_rel only the REL translation differs (same LLVM DOL objects);
        # vs clang_dol_msvc_rel both translations differ (whole-module comparison).
        if baseline_mode == 'llvm_dol_msvc_rel':
            if manifests[0].get('llvm_dol_dir') != manifests[1].get('llvm_dol_dir'):
                raise ValueError('llvm_all vs llvm_dol_msvc_rel requires the same LLVM DOL objects')
        elif baseline_mode == 'llvm_all':
            # Generator variants: both translations regenerated, so the object dirs must differ.
            if manifests[0].get('llvm_dol_dir') == manifests[1].get('llvm_dol_dir'):
                raise ValueError('llvm_all variants must come from different generated objects')
        elif baseline_mode != 'clang_dol_msvc_rel':
            raise ValueError('llvm_all baseline must be llvm_dol_msvc_rel, clang_dol_msvc_rel or llvm_all')
    elif not manifests[0].get('rel_objects') or manifests[0]['rel_objects'] != manifests[1].get('rel_objects'):
        raise ValueError('Modules must link identical preserved REL objects')
    return {'baseline': base, 'candidate': test,
            'guest_frame_speed_ratio': test['guest_frames_per_wall_second'] / base['guest_frames_per_wall_second'],
            'runner_sha256': before['runner_sha256'], 'restored_state_sha256': before['load_state_sha256'],
            'baseline_mode': baseline_mode, 'candidate_mode': candidate_mode,
            'candidate_llvm_dol_dir': manifests[1].get('llvm_dol_dir'),
            'candidate_llvm_rel_dir': manifests[1].get('llvm_rel_dir'),
            'scope': 'Short restored-state probes on this PC; only the named translation differs. Guest frame '
                     'progress, not render FPS, CPU equivalence or full-game performance.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--baseline-mode', default='clang_dol_msvc_rel')
    parser.add_argument('--candidate-mode', default='llvm_dol_msvc_rel', choices=('llvm_dol_msvc_rel', 'llvm_all'))
    args = parser.parse_args()
    report = compare(args.baseline, args.candidate, args.baseline_mode, args.candidate_mode)
    path = Path(__file__).resolve().parents[1] / 'local/analysis' / ('llvm-dol-speed-comparison-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.json')
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2)); print('Evidence:', path)
