# SPDX-License-Identifier: GPL-3.0-or-later
"""Check measurement arithmetic and reject unmatched probe conditions."""
import json
import os
import tempfile
from pathlib import Path
from compare_probe_speed import compare


def fixture(root, name, optimized, frames):
    path = root / name
    (path / 'control/processed').mkdir(parents=True)
    (path / 'control/commands').mkdir()
    result = {'exit_code': 0, 'forced_stop': False, 'failed_command_count': 0,
              'load_state_sha256': 'state', 'physical_input_mappings_disabled': True,
              'graphics_backend': 'Vulkan', 'input_profile': 'isolated',
              'requested_seconds': 120, 'optimized_module': optimized, 'module_sha256': name}
    (path / 'result.json').write_text(json.dumps(result))
    (path / 'control/processed/0000-load.ini').write_text('command=load_state\n')
    for filename, elapsed, count in [('status-progress-0001.txt', 0, 100), ('status-before-stop.txt', 60, 100 + frames)]:
        file = path / filename
        file.write_text(f'state=running\nframe_count={count}\nspeed=0.2\n')
        os.utime(file, (1700000000 + elapsed, 1700000000 + elapsed))
    return path


def rejects(callback):
    try:
        callback()
    except ValueError:
        return
    raise AssertionError('Unmatched probe accepted')


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    base = fixture(root, 'baseline', False, 300)
    opt = fixture(root, 'optimized', True, 600)
    report = compare(base, opt)
    assert report['guest_frame_speed_ratio'] == 2
    assert report['baseline']['guest_frames_per_wall_second'] == 5
    result = json.loads((opt / 'result.json').read_text())
    result['load_state_sha256'] = 'different-state'
    (opt / 'result.json').write_text(json.dumps(result))
    rejects(lambda: compare(base, opt))
    result['load_state_sha256'] = 'state'
    (opt / 'result.json').write_text(json.dumps(result))
    (opt / 'control/processed/0050-input.ini').write_text('command=pad_frames\nframes=60\nwii_a=1\n')
    rejects(lambda: compare(base, opt))
    (opt / 'control/processed/0050-input.ini').unlink()
    for key in ('runner_sha256', 'fallback_profile_requested', 'scheduler_idle_skip_requested'):
        changed = result | {key: 'different'}
        (opt / 'result.json').write_text(json.dumps(changed))
        rejects(lambda: compare(base, opt))
    (opt / 'result.json').write_text(json.dumps(result))
    os.utime(opt / 'status-before-stop.txt', (1700000010, 1700000010))
    rejects(lambda: compare(base, opt))
print('PASS frame-rate ratio, states, inputs, short samples and runtime/diagnostic/idle-option mismatch rejection')
