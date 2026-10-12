# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare the five-chunk Clang REL experiment with its unchanged hybrid baseline."""
import argparse
import datetime
import hashlib
import json
import re
from pathlib import Path
from compare_probe_speed import summarize
from build_hot_rel_clang import SELECTED


def compare(baseline,candidate):
    before,base=summarize(baseline,allow_empty_mod_hooks=True)
    after,test=summarize(candidate,allow_empty_mod_hooks=True)
    for key in ('runner_sha256','load_state_sha256','graphics_backend','input_profile',
                'requested_seconds','capture_interval_seconds','optimized_module',
                'scheduler_idle_skip_requested','module_coverage','module_compiler'):
        if key not in before or before[key]!=after.get(key):raise ValueError('Different condition: '+key)
    manifests=[]
    for folder,result,mode in ((baseline,before,'clang_dol_msvc_rel'),(candidate,after,'clang_dol_hot_rel_msvc_remaining_rel')):
        if result.get('optimized_module') is not True or result.get('module_compiler')!='clang-cl':raise ValueError('Require optimized Clang modules')
        if result.get('fallback_profile_requested') is not False or result.get('finish_requested') is not False:
            raise ValueError('Require unprofiled complete interval')
        if result.get('executed_seconds',0)<result['requested_seconds']-2:raise ValueError('Incomplete interval')
        for key in ('runner_sha256','load_state_sha256','module_sha256'):
            if not re.fullmatch('[0-9a-f]{64}',result.get(key) or ''):raise ValueError('Invalid digest: '+key)
        hooks=result.get('empty_mod_hooks_counters') or {}
        if result.get('skip_empty_mod_hooks_requested') is not True or hooks!={'skipped_empty':True,'loaded_mods':0}:
            raise ValueError('Require identical empty-mod configuration')
        if 'mod_hooks_skip_empty_requested=1 mod_hooks_skipped_empty=1 loaded_mods=0' not in (folder/'stderr.log').read_text():
            raise ValueError('Missing empty-mod startup proof')
        counts=result.get('shutdown_counters') or {}; enabled=result.get('scheduler_idle_skip_requested')
        if counts.get('failed_code_verifications')!=0 or type(enabled) is not bool or type(counts.get('scheduler_idle_skips')) is not int or bool(counts['scheduler_idle_skips'])!=enabled:
            raise ValueError('Missing code/scheduler accounting')
        if result.get('mem1_snapshot_complete') is not True or result.get('mem2_snapshot_complete') is not True:
            raise ValueError('Missing final memory snapshots')
        m=json.loads((folder/'module-build-manifest.json').read_text())
        if m.get('mode')!=mode or m.get('binary_sha256')!=result['module_sha256'] or m.get('chunk_count')!=552 or m.get('compiler',{}).get('id')!='Clang':
            raise ValueError('Wrong module manifest')
        sources=m.get('sources',{}); objects=m.get('rel_objects',{})
        if len(sources)<552 or not objects:raise ValueError('Missing source/object provenance')
        for digest in list(sources.values())+list(objects.values()):
            if not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Invalid input digest')
        if m.get('source_set_sha256')!=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest():
            raise ValueError('Invalid source fingerprint')
        manifests.append(m)
    b,c=manifests
    for key in ('sources','source_set_sha256','compiler'):
        if b[key]!=c[key]:raise ValueError('Changed shared input: '+key)
    if len(b['rel_objects'])!=478 or len(c['rel_objects'])!=473:raise ValueError('Wrong REL object counts')
    if c.get('baseline_binary_sha256')!=before['module_sha256'] or before['module_sha256']==after['module_sha256']:
        raise ValueError('Candidate not bound to baseline')
    if c.get('selected_rel_chunks')!=SELECTED or set(c.get('clang_rel_chunks',{}))!=set(SELECTED):
        raise ValueError('Unexpected compiled chunks')
    expected={k:v for k,v in b['rel_objects'].items() if k not in {x+'.obj' for x in SELECTED}}
    if c['rel_objects']!=expected:raise ValueError('Other REL objects changed')
    flags=c.get('compile_flags',[])
    if '/O2' not in flags or '/fp:strict' not in flags or any('fast' in x.lower() or 'fp:precise' in x.lower() for x in flags):
        raise ValueError('Missing strict compilation or relaxed FP flag')
    for name,obj in c['clang_rel_chunks'].items():
        key='local/generated/dolrecomp/rel-linked/runtime_rel_chunks/'+name+'.c'
        if obj.get('source_sha256')!=b['sources'].get(key) or not re.fullmatch('[0-9a-f]{64}',obj.get('object_sha256') or ''):
            raise ValueError('Compiled chunk differs from original source')
    if 'runner_path' in before and 'runner_path' in after and Path(before['runner_path']).parent!=Path(after['runner_path']).parent:
        raise ValueError('Different runner directories')
    return {'baseline':base,'candidate':test,'guest_frame_speed_ratio':test['guest_frames_per_wall_second']/base['guest_frames_per_wall_second'],
            'runner_sha256':before['runner_sha256'],'state_sha256':before['load_state_sha256'],
            'source_set_sha256':b['source_set_sha256'],'compiled_rel_chunks':SELECTED,'preserved_rel_objects':473,
            'scope':'Short restored first-out probes on this PC; five unchanged REL chunks compiled with Clang strict FP, same runtime and options. Guest frames, not render FPS, full game performance or equivalence.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path);args=p.parse_args()
    report=compare(args.baseline,args.candidate)
    target=Path(__file__).resolve().parents[1]/'local/analysis'/('hot-rel-speed-comparison-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.json')
    target.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));print(target)
