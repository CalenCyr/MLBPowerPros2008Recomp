# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise comparison arithmetic and reject changed conditions/compiler inputs."""
import copy
import json
import tempfile
from pathlib import Path
from check_scheduler_probe_comparison import fixture
from compare_hot_rel_probe_speed import compare
from build_hot_rel_clang import SELECTED


def main():
    project=Path(__file__).resolve().parents[1]
    baseline=json.loads((project/'local/build/runtime-module-rel-clang/module-build-manifest.json').read_text())
    candidates=sorted((project/'local/analysis').glob('hot-rel-clang-*/module-build-manifest.json'))
    candidate=json.loads(candidates[-1].read_text())
    with tempfile.TemporaryDirectory() as directory:
        base,rb=fixture(Path(directory),'baseline',True,300)
        test,rt=fixture(Path(directory),'candidate',True,600)
        shared={'runner_sha256':'a'*64,'load_state_sha256':'b'*64,'module_compiler':'clang-cl',
                'module_coverage':'DOL and placement-locked REL (experimental)',
                'finish_requested':False,'executed_seconds':120,'mem1_snapshot_complete':True,
                'mem2_snapshot_complete':True,'skip_empty_mod_hooks_requested':True,
                'empty_mod_hooks_counters':{'skipped_empty':True,'loaded_mods':0}}
        rb=rb|shared|{'module_sha256':baseline['binary_sha256']}
        rt=rt|shared|{'module_sha256':candidate['binary_sha256']}
        for folder,result,manifest in ((base,rb,baseline),(test,rt,candidate)):
            (folder/'result.json').write_text(json.dumps(result))
            (folder/'module-build-manifest.json').write_text(json.dumps(manifest))
            (folder/'stderr.log').write_text('mod_hooks_skip_empty_requested=1 mod_hooks_skipped_empty=1 loaded_mods=0')
        assert compare(base,test)['guest_frame_speed_ratio']==2
        rejected=0
        def rejects():
            nonlocal rejected
            try:compare(base,test)
            except ValueError:rejected+=1;return
            raise AssertionError('Changed condition or provenance admitted')
        for change in ({'runner_sha256':'c'*64},{'load_state_sha256':'c'*64},{'graphics_backend':'Null'},
                       {'module_sha256':'c'*64},{'scheduler_idle_skip_requested':False},
                       {'host_sampling_requested':True},{'lockstep_requested':True},
                       {'dispatch_timing_requested':True},{'cache_batch_requested':True},
                       {'fallback_profile_requested':True},{'finish_requested':True},{'executed_seconds':20},
                       {'requested_seconds':60},{'capture_interval_seconds':20},{'optimized_module':False},
                       {'skip_empty_mod_hooks_requested':False},{'empty_mod_hooks_counters':{}},
                       {'mem1_snapshot_complete':False},{'mem2_snapshot_complete':False},
                       {'forced_stop':True},{'exit_code':1},{'failed_command_count':1},
                       {'module_compiler':'MSVC'},{'shutdown_counters':{}},
                       {'shutdown_counters':{'scheduler_idle_skips':1,'failed_code_verifications':1}}):
            (test/'result.json').write_text(json.dumps(rt|change));rejects()
        (test/'result.json').write_text(json.dumps(rt))
        for key,value in [('mode','clang_all'),('chunk_count',551),('baseline_binary_sha256','c'*64),
                          ('compiler',{}),('sources',{}),('source_set_sha256','c'*64),
                          ('selected_rel_chunks',SELECTED[:-1]),('clang_rel_chunks',{}),
                          ('rel_objects',{}),('compile_flags',['/O2','/fp:fast'])]:
            changed=copy.deepcopy(candidate);changed[key]=value
            (test/'module-build-manifest.json').write_text(json.dumps(changed));rejects()
        changed=copy.deepcopy(candidate);changed['clang_rel_chunks'][SELECTED[0]]['source_sha256']='c'*64
        (test/'module-build-manifest.json').write_text(json.dumps(changed));rejects()
        changed=copy.deepcopy(candidate);changed['rel_objects'][next(iter(changed['rel_objects']))]='c'*64
        (test/'module-build-manifest.json').write_text(json.dumps(changed));rejects()
        (test/'module-build-manifest.json').write_text(json.dumps(candidate))
        (test/'stderr.log').write_text('');rejects()
        (test/'stderr.log').write_text('mod_hooks_skip_empty_requested=1 mod_hooks_skipped_empty=1 loaded_mods=0')
        (test/'benchmark-exclusion.json').write_text('{}');rejects()
        assert rejected==39,rejected
        print('PASS hot REL speed ratio and 39 contaminated condition/provenance rejections')


if __name__=='__main__':main()
