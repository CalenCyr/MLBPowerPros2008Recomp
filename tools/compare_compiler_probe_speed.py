# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare compiler variants with preserved sources, REL objects and runtime."""
import argparse
import datetime
import hashlib
import json
import re
from pathlib import Path
from compare_probe_speed import summarize


def compare(baseline, candidate):
    before, base = summarize(baseline)
    after, test = summarize(candidate)
    for key in ('runner_sha256', 'load_state_sha256', 'graphics_backend', 'input_profile',
                'requested_seconds', 'capture_interval_seconds', 'optimized_module',
                'scheduler_idle_skip_requested', 'module_coverage'):
        if key not in before or key not in after or before[key] != after[key]:
            raise ValueError('Missing or different condition: '+key)
    manifests = []
    for probe, result, mode, compiler in ((baseline, before, 'msvc_all', 'MSVC'),
                                        (candidate, after, 'clang_dol_msvc_rel', 'Clang')):
        if result.get('optimized_module') is not True:
            raise ValueError('Both compiler builds must be optimized')
        if result.get('fallback_profile_requested') is not False or result.get('finish_requested') is not False:
            raise ValueError('Require unprofiled complete intervals')
        if result.get('executed_seconds', 0) < result['requested_seconds'] - 2:
            raise ValueError('Incomplete interval')
        for key in ('module_sha256', 'runner_sha256', 'load_state_sha256'):
            if not re.fullmatch('[0-9a-f]{64}', result.get(key) or ''):
                raise ValueError('Invalid provenance: '+key)
        counts = result.get('shutdown_counters') or {}
        if counts.get('failed_code_verifications') != 0:
            raise ValueError('Missing or failed code verification')
        skips = counts.get('scheduler_idle_skips')
        enabled = result.get('scheduler_idle_skip_requested')
        if type(enabled) is not bool or type(skips) is not int or skips < 0 or bool(skips) != enabled:
            raise ValueError('Scheduler state not exercised consistently')
        data = json.loads((probe/'module-build-manifest.json').read_text())
        if data.get('binary_sha256') != result['module_sha256'] or data.get('chunk_count') != 552:
            raise ValueError('Build manifest does not identify the probed module')
        if data.get('mode') != mode or data.get('compiler', {}).get('id') != compiler:
            raise ValueError('Unexpected compiler experiment')
        sources, objects = data.get('sources', {}), data.get('rel_objects', {})
        if len(sources) < 552 or len(objects) != 478:
            raise ValueError('Missing preserved inputs or REL objects')
        for digest in list(sources.values())+list(objects.values()):
            if not re.fullmatch('[0-9a-f]{64}', digest):
                raise ValueError('Invalid input digest')
        fingerprint = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
        if data.get('source_set_sha256') != fingerprint:
            raise ValueError('Invalid shared-input fingerprint')
        manifests.append(data)
    for key in ('sources', 'source_set_sha256', 'rel_objects'):
        if manifests[0][key] != manifests[1][key]:
            raise ValueError('Compiler variants differ in preserved inputs: '+key)
    if base['module_sha256'] == test['module_sha256']:
        raise ValueError('Expected different compiler binaries')
    return {'baseline': base, 'candidate': test,
            'guest_frame_speed_ratio': test['guest_frames_per_wall_second']/base['guest_frames_per_wall_second'],
            'runner_sha256': before['runner_sha256'],
            'restored_state_sha256': before['load_state_sha256'],
            'source_set_sha256': manifests[0]['source_set_sha256'],
            'baseline_compiler': manifests[0]['compiler'], 'candidate_compiler': manifests[1]['compiler'],
            'preserved_rel_objects': 478,
            'scope': 'Short consecutive restored-state probes on this PC. Clang DOL/helpers with unchanged MSVC REL objects. Guest frame progress, not render FPS, native-only execution or full-game equivalence.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    report = compare(args.baseline, args.candidate)
    path = Path(__file__).resolve().parents[1]/'local/analysis'/('compiler-speed-comparison-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.json')
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    print('Evidence:', path)
