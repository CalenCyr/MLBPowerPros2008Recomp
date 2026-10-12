# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject compiler comparisons contaminated by diagnostics or changed game inputs."""
import hashlib
import json
import tempfile
from pathlib import Path
from check_scheduler_probe_comparison import fixture
from compare_compiler_probe_speed import compare


def main():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        baseline, before = fixture(root, 'msvc', True, 300)
        candidate, after = fixture(root, 'clang', True, 600)
        common = {'runner_sha256': 'a'*64, 'load_state_sha256': 'b'*64,
                  'executed_seconds': 120, 'finish_requested': False,
                  'module_coverage': 'DOL and placement-locked REL (experimental)'}
        before |= common | {'module_sha256': 'c'*64}
        after |= common | {'module_sha256': 'd'*64}
        sources = {f'chunk{i}.c': 'e'*64 for i in range(552)}
        objects = {f'rel{i}.obj': 'f'*64 for i in range(478)}
        manifests = []
        for probe, result, mode, compiler in ((baseline, before, 'msvc_all', 'MSVC'),
                                            (candidate, after, 'clang_dol_msvc_rel', 'Clang')):
            data = {'binary_sha256': result['module_sha256'], 'chunk_count': 552,
                    'sources': sources, 'rel_objects': objects, 'mode': mode,
                    'source_set_sha256': hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
                    'compiler': {'id': compiler}}
            (probe/'result.json').write_text(json.dumps(result))
            (probe/'module-build-manifest.json').write_text(json.dumps(data))
            manifests.append(data)
        assert compare(baseline, candidate)['guest_frame_speed_ratio'] == 2
        changes = [{'runner_sha256': '9'*64}, {'load_state_sha256': '9'*64},
                   {'graphics_backend': 'Null'}, {'input_profile': 'other'},
                   {'requested_seconds': 90}, {'capture_interval_seconds': 20},
                   {'optimized_module': False}, {'scheduler_idle_skip_requested': False},
                   {'module_coverage': 'DOL only'}, {'executed_seconds': 20},
                   {'finish_requested': True}, {'fallback_profile_requested': True},
                   {'dispatch_timing_requested': True}, {'cache_batch_requested': True},
                   {'lockstep_requested': True}, {'host_sampling_requested': True},
                   {'forced_stop': True}, {'exit_code': 1}, {'failed_command_count': 1},
                   {'module_sha256': '8'*64}, {'runner_sha256': None},
                   {'shutdown_counters': {}}, {'physical_input_mappings_disabled': False},
                   {'shutdown_counters': {'failed_code_verifications': 1, 'scheduler_idle_skips': 100}}]
        rejected = 0
        for change in changes:
            (candidate/'result.json').write_text(json.dumps(after | change))
            try:
                compare(baseline, candidate)
            except ValueError:
                rejected += 1
            else:
                raise AssertionError(change)
        (candidate/'result.json').write_text(json.dumps(after))
        changes = [{'mode': 'clang_all'}, {'compiler': {'id': 'MSVC'}},
                   {'chunk_count': 551}, {'source_set_sha256': '0'*64},
                   {'sources': {}}, {'rel_objects': {}}]
        for change in changes:
            (candidate/'module-build-manifest.json').write_text(json.dumps(manifests[1] | change))
            try:
                compare(baseline, candidate)
            except ValueError:
                rejected += 1
            else:
                raise AssertionError(change)
        changed = manifests[1] | {'rel_objects': objects | {'rel0.obj': '0'*64}}
        (candidate/'module-build-manifest.json').write_text(json.dumps(changed))
        try:
            compare(baseline, candidate)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('Changed REL object accepted')
        (candidate/'module-build-manifest.json').write_text(json.dumps(manifests[1]))
        (candidate/'host-sampling.json').write_text('{}')
        try:
            compare(baseline, candidate)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('External sampling marker accepted')
    print(f'PASS compiler ratio and {rejected} contaminated/mismatched comparison rejections')


if __name__ == '__main__':
    main()
