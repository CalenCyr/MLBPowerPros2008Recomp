# SPDX-License-Identifier: GPL-3.0-or-later
"""Check site ranking and corrupt/missing aggregate rejection independently."""
import copy
from analyze_dispatch_sites import validate_sites


def main():
    rows = [
        dict(kind='dropped', context=context, pc='00000000', samples='0', total_ns='0', max_ns='0')
        for context in ('outside_rel_envelope', 'inside_rel_envelope')]
    rows += [dict(kind='site', context='outside_rel_envelope', pc='80000000', samples='2', total_ns='60', max_ns='40'),
             dict(kind='site', context='inside_rel_envelope', pc='80500000', samples='1', total_ns='50', max_ns='50')]
    report = {'contexts': {
        'outside_rel_envelope': {'phases': {'module_dispatch': {'samples': 2, 'total_ns': 60, 'max_ns': 40}}},
        'inside_rel_envelope': {'phases': {'module_dispatch': {'samples': 1, 'total_ns': 50, 'max_ns': 50}}}},
        'raw_sampled_time_by_phase_ns': {'module_dispatch': 110}}
    valid = validate_sites(rows, report)
    assert valid['recorded_sites'] == 2
    assert valid['sites_ranked_by_raw_sampled_time'][0]['mean_raw_elapsed_ns'] == 30
    assert valid['sites_ranked_by_raw_sampled_time'][0]['raw_share_of_sampled_module_time'] == 60 / 110
    overflow = copy.deepcopy(rows)
    overflow[0].update(samples='2', total_ns='60', max_ns='40')
    overflow.pop(2)
    assert validate_sites(overflow, report)['dropped_by_context']['outside_rel_envelope']['samples'] == 2
    bad = [rows[:-1], rows[1:], rows + [rows[2]]]
    for changed in ({'pc': '80000001'}, {'pc': 'bad'}, {'kind': 'unknown'}, {'context': 'wrong'},
                    {'samples': '0'}, {'samples': '-1'}, {'samples': str(1 << 64)},
                    {'total_ns': '61'}, {'max_ns': '61'}, {'max_ns': '39'}, {'max_ns': '0'}):
        copied = copy.deepcopy(rows)
        copied[2].update(changed)
        bad.append(copied)
    dropped = copy.deepcopy(rows)
    dropped[0]['pc'] = '80000000'
    bad.append(dropped)
    cap = copy.deepcopy(rows[:2]) + [rows[2] | {'pc': f'{0x80000000+4*i:08X}'} for i in range(4097)]
    bad.append(cap)
    for corrupt in bad:
        try:
            validate_sites(corrupt, report)
        except ValueError:
            continue
        raise AssertionError('Corrupt sites accepted')
    print(f'PASS module site arithmetic/ranking, overflow accounting and {len(bad)} corrupt-profile rejections')


if __name__ == '__main__':
    main()
