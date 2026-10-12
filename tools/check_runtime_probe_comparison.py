# SPDX-License-Identifier: GPL-3.0-or-later
"""Check arithmetic and reject mismatched runtime performance comparisons."""
import json
import tempfile
from pathlib import Path
from check_scheduler_probe_comparison import fixture
from compare_runtime_probe_speed import compare


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        base, original_base = fixture(root, 'old', True, 300)
        test, original_test = fixture(root, 'new', True, 600)
        common = {'module_sha256': 'c' * 64, 'load_state_sha256': 'd' * 64,
                  'finish_requested': False, 'executed_seconds': 120,
                  'module_compiler': 'clang-cl', 'skip_empty_mod_hooks_requested': False,
                  'module_coverage': 'DOL and placement-locked REL (experimental)'}
        before = original_base | common | {'runner_sha256': 'a' * 64}
        after = original_test | common | {'runner_sha256': 'b' * 64}
        (base / 'result.json').write_text(json.dumps(before))
        (test / 'result.json').write_text(json.dumps(after))
        assert compare(base, test)['guest_frame_speed_ratio'] == 2
        corrupt = [{'runner_sha256': before['runner_sha256']}, {'runner_sha256': None},
                   {'module_sha256': 'e' * 64}, {'load_state_sha256': 'e' * 64},
                   {'graphics_backend': 'Null'}, {'input_profile': 'different'},
                   {'capture_interval_seconds': 30}, {'requested_seconds': 90},
                   {'scheduler_idle_skip_requested': False}, {'fallback_profile_requested': True},
                   {'optimized_module': False}, {'module_coverage': 'DOL only'},
                   {'executed_seconds': 20}, {'finish_requested': True},
                   {'shutdown_counters': {'scheduler_idle_skips': 0, 'failed_code_verifications': 0}},
                   {'shutdown_counters': {'scheduler_idle_skips': 100, 'failed_code_verifications': 1}},
                   {'shutdown_counters': {}}, {'exit_code': 1}, {'forced_stop': True},
                   {'failed_command_count': 1}, {'physical_input_mappings_disabled': False},
                   {'dispatch_timing_requested': True}, {'cache_batch_requested': True}]
        for changed in corrupt:
            (test / 'result.json').write_text(json.dumps(after | changed))
            try:
                compare(base, test)
            except ValueError:
                continue
            raise AssertionError(f'Unmatched conditions accepted: {changed}')
        # OFF/OFF is valid too; inconsistent telemetry is not.
        for folder, result in ((base, before), (test, after)):
            result = result | {'scheduler_idle_skip_requested': False,
                              'shutdown_counters': {'scheduler_idle_skips': 0, 'failed_code_verifications': 0}}
            (folder / 'result.json').write_text(json.dumps(result))
        assert compare(base, test)['guest_frame_speed_ratio'] == 2
        after['scheduler_idle_skip_requested'] = False
        (test / 'result.json').write_text(json.dumps(after))
        try:
            compare(base, test)
        except ValueError:
            pass
        else:
            raise AssertionError('Scheduler OFF with nonzero skips accepted')
        # An explicit matching ON/ON configuration permits revision comparisons;
        # missing or inconsistent proof must still be rejected.
        before = before | {'skip_empty_mod_hooks_requested': True,
                           'empty_mod_hooks_counters': {'skipped_empty': True, 'loaded_mods': 0}}
        after = before | {'runner_sha256': 'b'*64}
        proof = 'mod_hooks_skip_empty_requested=1 mod_hooks_skipped_empty=1 loaded_mods=0'
        for folder, result in ((base, before), (test, after)):
            (folder/'result.json').write_text(json.dumps(result))
            (folder/'stderr.log').write_text(proof)
        assert compare(base, test, allow_empty_mod_hooks=True)['guest_frame_speed_ratio'] == 2
        def reject_explicit():
            try:
                compare(base, test, allow_empty_mod_hooks=True)
            except ValueError:
                return
            raise AssertionError('Unmatched hook-skipping revisions accepted')
        for changed in ({'skip_empty_mod_hooks_requested': False},
                        {'empty_mod_hooks_counters': {}},
                        {'empty_mod_hooks_counters': {'skipped_empty': False, 'loaded_mods': 0}},
                        {'empty_mod_hooks_counters': {'skipped_empty': True, 'loaded_mods': 1}},
                        {'host_sampling_requested': True}, {'module_compiler': 'MSVC'}):
            (test/'result.json').write_text(json.dumps(after | changed))
            reject_explicit()
        (test/'result.json').write_text(json.dumps(after))
        (test/'stderr.log').write_text('')
        reject_explicit()
        (test/'stderr.log').write_text(proof)
        (test/'host-sampling.json').write_text('{}')
        reject_explicit()
        (test/'host-sampling.json').unlink()
        for folder, result in ((base, before), (test, after)):
            result = result | {'runner_path': str(root/'same'/('old.exe' if folder==base else 'new.exe'))}
            (folder/'result.json').write_text(json.dumps(result))
        assert compare(base, test, allow_empty_mod_hooks=True)['guest_frame_speed_ratio'] == 2
        (test/'result.json').write_text(json.dumps(after | {'runner_path': str(root/'other/new.exe')}))
        reject_explicit()
        (test/'result.json').write_text(json.dumps(after))
        try:
            compare(base, test)
        except ValueError:
            pass
        else:
            raise AssertionError('Hook skipping accepted without explicit scope')
    print('PASS runtime speed ratio, scheduler ON/ON and OFF/OFF, 24 ordinary rejections, explicit empty-mod scope and 10 additional rejections')


if __name__ == '__main__':
    main()
