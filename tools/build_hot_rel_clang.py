# SPDX-License-Identifier: GPL-3.0-or-later
"""Recompile five sampled REL chunks; keep all other existing objects unchanged."""
import concurrent.futures
import datetime
import json
import subprocess
from pathlib import Path
from map_clang_module import sha

SELECTED = ['chunk_0085_text0_806C9654', 'chunk_0086_text0_806CD654',
            'chunk_0092_text0_806E5654', 'chunk_0093_text0_806E9654', 'chunk_0094_text0_806ED654']


def main():
    root=Path(__file__).resolve().parents[1]
    base=root/'local/build/runtime-module-rel-clang'
    manifest=json.loads((base/'module-build-manifest.json').read_text())
    if manifest['mode']!='clang_dol_msvc_rel' or sha(base/'gRL8E54_recomp.dll')!=manifest['binary_sha256']:
        raise ValueError('Require unchanged baseline hybrid DLL')
    compiler=Path(manifest['compiler']['path'])
    if sha(compiler)!=manifest['compiler']['sha256']:raise ValueError('Compiler changed')
    ninja=(base/'build.ninja').read_text()
    line=next(x for x in ninja.splitlines() if x.startswith('build gRL8E54_recomp.dll '))
    parts=line.split(' C_SHARED_LIBRARY_LINKER__gRL8E54_recomp_Release ',1)[1].split(' |',1)[0].split()
    objects=[(base/part.replace('$:',':')).resolve() for part in parts]
    if len(objects)!=560 or not all(x.is_file() for x in objects):raise ValueError('Unexpected baseline link inputs')
    for obj in objects:
        if obj.name in manifest['rel_objects'] and sha(obj)!=manifest['rel_objects'][obj.name]:
            raise ValueError('Preserved REL object changed: '+obj.name)
    for relative, expected in manifest['sources'].items():
        actual=base/'module_tables.inc' if relative=='module_tables.inc' else root/relative
        if sha(actual)!=expected:raise ValueError('Source input changed: '+relative)
    folder=root/'local/analysis'/('hot-rel-clang-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir();objdir=folder/'objects';objdir.mkdir()
    chassis=root/'local/vendor/ModernGekko/vendor/dolphin'
    rel=root/'local/generated/dolrecomp/rel-linked'
    flags=['/nologo','/DWIN32','/D_WINDOWS','/O2','/Ob2','/DNDEBUG','-MD','/bigobj','/fp:strict','/wd4102',
           '/DDOLRECOMP_CPU_HEADER="core/cpu.h"','/DPOWERPROS_ENABLE_REL=1','/DgRL8E54_recomp_EXPORTS']
    includes=[root/'local/generated/dolrecomp/dol',chassis/'GXRuntime/include',
              chassis/'Source/Core/Core/PowerPC/StaticRecomp',base,rel]
    def compile_chunk(name):
        source=rel/'runtime_rel_chunks'/(name+'.c');output=objdir/(name+'.obj')
        cmd=[str(compiler)]+flags+['/I'+str(x) for x in includes]+['/Fo'+str(output),'-c','--',str(source)]
        with (folder/(name+'.log')).open('w') as log:
            result=subprocess.run(cmd,stdout=log,stderr=log)
        if result.returncode:raise RuntimeError('Compilation failed: '+name)
        return name,{'source_sha256':sha(source),'object_sha256':sha(output),'object':str(output)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        compiled=dict(pool.map(compile_chunk,SELECTED))
    for i,obj in enumerate(objects):
        if obj.stem in SELECTED:objects[i]=objdir/(obj.stem+'.obj')
    rsp=folder/'objects.rsp';rsp.write_text('\n'.join('"'+x.as_posix()+'"' for x in objects)+'\n')
    binary=folder/'gRL8E54_recomp.dll';mapping=folder/'gRL8E54_recomp.map'
    libs=['kernel32.lib','user32.lib','gdi32.lib','winspool.lib','shell32.lib','ole32.lib',
          'oleaut32.lib','uuid.lib','comdlg32.lib','advapi32.lib']
    command=[str(root/'local/tools/llvm-22.1.8/bin/lld-link.exe'),'/nologo','@'+str(rsp),
             '/out:'+str(binary),'/implib:'+str(folder/'gRL8E54_recomp.lib'),'/dll','/version:0.0',
             '/machine:x64','/INCREMENTAL:NO','/map:'+str(mapping)]+libs
    with (folder/'link.log').open('w') as log:subprocess.run(command,stdout=log,stderr=log,check=True)
    # Keep the identical shared source-set hash; record the changed compiler
    # assignment and each object separately, including unchanged DOL objects.
    manifest.update({'baseline_binary_sha256':manifest['binary_sha256'],
                     'mode':'clang_dol_hot_rel_msvc_remaining_rel','binary':str(binary),
                     'binary_sha256':sha(binary),'binary_bytes':binary.stat().st_size,
                     'clang_rel_chunks':compiled,'selected_rel_chunks':SELECTED,
                     'compile_flags':flags,'map_sha256':sha(mapping),
                     'unchanged_dol_objects':{x.name:sha(x) for x in objects if '.c.obj' in x.name and 'main_chunks' in str(x)},
                     'scope':'Five unchanged REL sources compiled with clang-cl O2 and strict FP; preserved Clang DOL, CPU helpers and remaining MSVC REL. Input provenance, not CPU equivalence.'})
    for name in SELECTED:manifest['rel_objects'].pop(name+'.obj')
    if len(manifest['rel_objects'])!=473:raise ValueError('Expected 473 unchanged MSVC REL objects')
    (folder/'module-build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('mode','binary','binary_sha256','binary_bytes','selected_rel_chunks','source_set_sha256')},indent=2))
    print(folder)


if __name__=='__main__':main()
