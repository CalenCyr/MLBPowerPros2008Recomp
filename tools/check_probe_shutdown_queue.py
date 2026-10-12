# SPDX-License-Identifier: GPL-3.0-or-later
"""Accept only the evidenced redundant final stop; reject real pending work."""
import json
import tempfile
from pathlib import Path
from check_scheduler_probe_comparison import fixture
from compare_probe_speed import summarize


def main():
    with tempfile.TemporaryDirectory() as directory:
        folder, result = fixture(Path(directory), 'probe', True, 300)
        first = folder/'control/processed/0009-stop.ini'
        second = folder/'control/commands/0010-stop.ini'
        log = folder/'stderr.log'
        first.write_text('command=stop\n')
        second.write_text('command=stop\n')
        proof = '[powerpros-diagnostic] core state callback=0\n'
        log.write_text(proof)
        assert summarize(folder)[1]['accounted_redundant_shutdown_requests'] == 1
        rejections=0
        def rejects():
            nonlocal rejections
            try:
                summarize(folder)
            except ValueError:
                rejections += 1
                return
            raise AssertionError('Unaccounted pending work accepted')
        for command in ('screenshot', 'pad_frames', 'pause', 'read_memory', 'load_state'):
            second.write_text('command='+command+'\n')
            rejects()
        second.write_text('command=stop\nframes=100\n'); rejects()
        second.write_text('command=stop\n')
        for changed in ({'exit_code':1}, {'forced_stop':True}, {'failed_command_count':1}):
            (folder/'result.json').write_text(json.dumps(result | changed)); rejects()
        (folder/'result.json').write_text(json.dumps(result))
        log.write_text(''); rejects(); log.write_text(proof)
        first.write_text('command=pause\n'); rejects(); first.write_text('command=stop\n')
        first.unlink(); rejects(); first.write_text('command=stop\n')
        second.rename(second.with_name('0011-stop.ini')); rejects()
        second.with_name('0011-stop.ini').rename(second)
        extra=second.with_name('0020-extra.ini'); extra.write_text('command=stop\n'); rejects(); extra.unlink()
        second.unlink()
        assert summarize(folder)[1]['accounted_redundant_shutdown_requests'] == 0
        exclusion=folder/'benchmark-exclusion.json'; exclusion.write_text('{}'); rejects(); exclusion.unlink()
        print(f'PASS accounted redundant stop, empty queue, {rejections} unsafe/incomplete queue rejections')


if __name__=='__main__':
    main()
