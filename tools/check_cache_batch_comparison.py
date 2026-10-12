# SPDX-License-Identifier: GPL-3.0-or-later
"""Check batching comparison arithmetic and reject mismatched probes."""
import json
from pathlib import Path
import tempfile
from check_scheduler_probe_comparison import fixture
from compare_cache_batch_speed import compare, MODULE_SHA, CHECKED_MODULES


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        base, original = fixture(root, 'off', True, 300)
        test, candidate = fixture(root, 'on', True, 600)
        common = {'runner_sha256': 'a' * 64, 'module_sha256': MODULE_SHA, 'load_state_sha256': 'b' * 64,
                  'executed_seconds': 120, 'finish_requested': False, 'module_coverage': 'DOL/REL',
                  'dispatch_timing_requested': False}
        before = original | common | {'cache_batch_requested': False,
                    'shutdown_counters': original['shutdown_counters'] | {'cache_batch_runs': 0, 'cache_batch_extra_lines': 0}}
        after = candidate | common | {'cache_batch_requested': True,
                    'shutdown_counters': candidate['shutdown_counters'] | {'cache_batch_runs': 10, 'cache_batch_extra_lines': 1270}}
        (base / 'result.json').write_text(json.dumps(before))
        (test / 'result.json').write_text(json.dumps(after))
        assert compare(base, test)['guest_frame_speed_ratio'] == 2
        corrupt = [{'cache_batch_requested': False}, {'runner_sha256': 'c' * 64}, {'module_sha256': 'c' * 64},
                   {'load_state_sha256': 'c' * 64}, {'scheduler_idle_skip_requested': False}, {'graphics_backend': 'Null'},
                   {'optimized_module': False}, {'input_profile': 'different'}, {'requested_seconds': 90},
                   {'capture_interval_seconds': 30}, {'module_coverage': 'DOL'}, {'dispatch_timing_requested': True},
                   {'fallback_profile_requested': True}, {'finish_requested': True}, {'executed_seconds': 20},
                   {'forced_stop': True}, {'exit_code': 1}, {'failed_command_count': 1}]
        for counter in ({'cache_batch_runs': 0}, {'cache_batch_extra_lines': 1271}, {'cache_batch_extra_lines': -1},
                        {'cache_batch_runs': True}, {'failed_code_verifications': 1}, {'scheduler_idle_skips': 0}):
            corrupt.append({'shutdown_counters': after['shutdown_counters'] | counter})
        for change in corrupt:
            (test / 'result.json').write_text(json.dumps(after | change))
            try:
                compare(base, test)
            except ValueError:
                continue
            raise AssertionError(change)
        for digest in CHECKED_MODULES:
            (base / 'result.json').write_text(json.dumps(before | {'module_sha256': digest}))
            (test / 'result.json').write_text(json.dumps(after | {'module_sha256': digest}))
            assert compare(base, test)['guest_frame_speed_ratio'] == 2
        # The Clang variant has not been validated for batching and must stay rejected.
        clang = '09296c1d72e4bb44080572964a1b664f148e2142cf691c04503258596f119357'
        for path, data in ((base, before), (test, after)):
            (path / 'result.json').write_text(json.dumps(data | {'module_sha256': clang}))
        try:
            compare(base, test)
        except ValueError:
            pass
        else:
            raise AssertionError('Unvalidated Clang batching accepted')
    print(f'PASS cache batching comparison ratio and {len(corrupt)} mismatched-probe rejections')


if __name__ == '__main__':
    main()
