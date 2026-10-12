# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject speed comparisons that change binaries or fail to exercise idle skipping."""
import json
import os
import tempfile
from pathlib import Path
from compare_scheduler_probe_speed import compare


def fixture(root,name,enabled,frames):
    folder=root/name
    (folder/'control/processed').mkdir(parents=True)
    (folder/'control/commands').mkdir()
    result={'exit_code':0,'forced_stop':False,'failed_command_count':0,
            'physical_input_mappings_disabled':True,'load_state_sha256':'state',
            'graphics_backend':'Vulkan','input_profile':'isolated','requested_seconds':120,
            'capture_interval_seconds':10,'optimized_module':True,'runner_sha256':'runner',
            'module_sha256':'module','fallback_profile_requested':False,
            'scheduler_idle_skip_requested':enabled,
            'shutdown_counters':{'scheduler_idle_skips':100 if enabled else 0,'failed_code_verifications':0}}
    (folder/'result.json').write_text(json.dumps(result))
    for filename,elapsed,count in [('status-progress-0001.txt',0,100),('status-before-stop.txt',60,100+frames)]:
        path=folder/filename
        path.write_text(f'state=running\nframe_count={count}\nspeed=0.2\n')
        os.utime(path,(1700000000+elapsed,1700000000+elapsed))
    return folder,result


def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        base,_=fixture(root,'off',False,300)
        test,original=fixture(root,'on',True,600)
        assert compare(base,test)['guest_frame_speed_ratio']==2
        corrupt=[{'runner_sha256':'different'},{'module_sha256':'different'},
                 {'load_state_sha256':'different'},{'capture_interval_seconds':30},
                 {'fallback_profile_requested':True},{'scheduler_idle_skip_requested':False},
                 {'shutdown_counters':{'scheduler_idle_skips':0,'failed_code_verifications':0}},
                 {'shutdown_counters':{'scheduler_idle_skips':100,'failed_code_verifications':1}}]
        for changed in corrupt:
            (test/'result.json').write_text(json.dumps(original|changed))
            try:
                compare(base,test)
            except ValueError:
                continue
            raise AssertionError(f'Unmatched conditions accepted: {changed}')
    print('PASS speed ratio and 8 unmatched scheduler-probe rejections')


if __name__=='__main__':
    main()
