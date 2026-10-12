# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject a boot probe that needed forced termination or lost final counters."""
import argparse
import json
from pathlib import Path


def check(probe: Path, require_inflight_wc24=False):
    result = json.loads((probe / 'result.json').read_text(encoding='utf-8-sig'))
    assert result['reached_running_or_paused_state'], 'The guest never reached execution'
    assert not result['forced_stop'], 'Runtime remained alive after both shutdown requests'
    assert result['exit_code'] == 0, f"Runtime exit code: {result['exit_code']}"
    counters = result['shutdown_counters']
    assert counters is not None, 'Missing final shutdown counters'
    assert counters['failed_code_verifications'] == 0, 'Code verification failed'
    log = (probe / 'stderr.log').read_text(encoding='utf-8', errors='replace')
    assert '[powerpros-diagnostic] core state callback=0' in log, 'Core did not finish shutdown'
    if require_inflight_wc24:
        start = log.rfind('IOS KD: entering download request')
        stopping = log.find('IOS KD: cleaning sockets', start)
        returned = log.find('IOS KD: download request returned', start)
        joined = log.find('IOS KD: stopped', stopping)
        assert start >= 0 and stopping > start, 'No WC24 transfer available for this regression'
        assert returned > stopping, 'WC24 transfer finished before shutdown; retry the regression'
        assert joined > returned, 'Worker was not joined after its transfer returned'
    print(f'PASS clean shutdown: {probe.name}; native={counters["native_dispatches"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('--require-inflight-wc24', action='store_true')
    args = parser.parse_args()
    check(args.probe, args.require_inflight_wc24)
