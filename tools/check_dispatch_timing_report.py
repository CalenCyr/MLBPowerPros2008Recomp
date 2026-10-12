# SPDX-License-Identifier: GPL-3.0-or-later
"""Check timing-report arithmetic and reject truncated or inconsistent profiles."""
import copy
from analyze_dispatch_timing import CONTEXTS, PHASES, validate


def fixture():
    rows = []
    for context in CONTEXTS:
        for phase in PHASES:
            rows.append({'context': context, 'phase': phase, 'observed_dispatches': '8192',
                         'stride': '4096', 'samples': '2',
                         'total_ns': '200' if phase == 'module_dispatch' else '40',
                         'max_ns': '100' if phase == 'module_dispatch' else '20'})
    rows.append({'context': 'calibration', 'phase': 'clock_pair', 'observed_dispatches': '0',
                 'stride': '0', 'samples': '10000', 'total_ns': '100000', 'max_ns': '20'})
    return rows


def main():
    rows = fixture()
    report = validate(rows, 16384)
    assert abs(report['raw_share_of_three_sampled_phases']['module_dispatch'] - 5 / 7) < 1e-12
    assert report['clock_pair_mean_raw_ns'] == 10
    bad = [rows[:-1], rows + [rows[0]], rows[1:]]
    for changed in ({'samples': '1'}, {'observed_dispatches': '4096'}, {'stride': '1024'},
                    {'total_ns': '-1'}, {'max_ns': '201'}, {'total_ns': '1000'},
                    {'phase': 'unknown'}, {'samples': '0', 'total_ns': '40'}):
        copy_rows = copy.deepcopy(rows)
        copy_rows[0].update(changed)
        bad.append(copy_rows)
    calibration = copy.deepcopy(rows)
    calibration[-1]['samples'] = '9999'
    bad.append(calibration)
    for corrupt in bad:
        try:
            validate(corrupt, 16384)
        except ValueError:
            continue
        raise AssertionError('Corrupt timing rows accepted')
    try:
        validate(rows, 16383)
    except ValueError:
        pass
    else:
        raise AssertionError('Shutdown mismatch accepted')
    print('PASS phase arithmetic, calibration and 13 corrupt timing-profile rejections')


if __name__ == '__main__':
    main()
