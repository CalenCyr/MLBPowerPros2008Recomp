# SPDX-License-Identifier: GPL-3.0-or-later
"""Record shared input hashes and compiler provenance for a module experiment."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1048576), b''):
            h.update(data)
    return h.hexdigest()


def manifest(build):
    root = Path(__file__).resolve().parents[1]
    compiler_files = list((build/'CMakeFiles').glob('*/CMakeCCompiler.cmake'))
    if len(compiler_files) != 1:
        raise ValueError('Missing or ambiguous compiler record')
    text = compiler_files[0].read_text()
    compiler = {k: re.search(r'set\(CMAKE_C_COMPILER'+suffix+r' "([^"]+)"\)', text)[1]
                for k, suffix in (('path', ''), ('id', '_ID'), ('version', '_VERSION'))}
    compiler['sha256'] = sha(Path(compiler['path']))
    cache = (build/'CMakeCache.txt').read_text()
    for option in ('POWERPROS_ENABLE_REL', 'POWERPROS_OPTIMIZE_MODULE'):
        if not re.search(r'^'+option+r':BOOL=ON$', cache, re.M):
            raise ValueError('Require combined optimized module: '+option)
    chassis = root/'local/vendor/ModernGekko/vendor/dolphin'
    llvm_dol = re.search(r'^POWERPROS_LLVM_DOL_DIR:PATH=(.+)$', cache, re.M)
    llvm_dol = Path(llvm_dol[1].strip()) if llvm_dol and llvm_dol[1].strip() else None
    dol = llvm_dol or root/'local/generated/dolrecomp/dol'
    llvm_rel = re.search(r'^POWERPROS_LLVM_REL_DIR:PATH=(.+)$', cache, re.M)
    llvm_rel = Path(llvm_rel[1].strip()) if llvm_rel and llvm_rel[1].strip() else None
    rel = llvm_rel or root/'local/generated/dolrecomp/rel-linked'
    dol_chunks = sorted(dol.glob('main_chunks/*.o' if llvm_dol else 'main_chunks/*.c'))
    chunks = dol_chunks + sorted(rel.glob('runtime_rel_chunks/*.o' if llvm_rel else 'runtime_rel_chunks/*.c'))
    if not llvm_dol and len(chunks) != 552:
        raise ValueError('Expected 552 preserved chunks')
    extra = ([root/'runtime/module/llvm_module_export.c', root/'runtime/module/llvm_support.c',
              dol/'main_fallbacks.csv', dol/'main_smc.txt'] if llvm_dol else [])
    extra += ([root/'runtime/module/llvm_rel_dispatch.c', root/'runtime/module/llvm_lookup.h',
               rel/'runtime_rel_fallbacks.csv'] if llvm_rel else [])
    files = chunks + extra + [dol/'main.h', rel/'runtime_rel.h',
        root/'runtime/module/module_export.c', root/'runtime/module/rel_dispatch.c',
        root/'local/disc/DATA/sys/main.dol', root/'local/disc/DATA/files/ovl_main.rel']
    files += sorted((chassis/'GXRuntime/include/core').glob('*.h'))
    for name in ('cpu', 'cpu_exception', 'cpu_interpreter', 'cpu_interpreter_table',
                 'cpu_interpreter_float', 'cpu_interpreter_integer'):
        files.append(chassis/'GXRuntime/src/core'/(name+'.c'))
    files.append(chassis/'Source/Core/Core/PowerPC/StaticRecomp/StaticRecompABI.h')
    sources = {p.relative_to(root).as_posix(): sha(p) for p in files}
    sources['module_tables.inc'] = sha(build/'module_tables.inc')
    binary = build/'gRL8E54_recomp.dll'
    if not binary.exists():
        binary = build/'Release/gRL8E54_recomp.dll'
    reuse = bool(re.search(r'^POWERPROS_REUSE_MSVC_REL_OBJECTS:BOOL=ON$', cache, re.M))
    rel_objects = {}
    if compiler['id'] == 'MSVC' or reuse:
        objdir = root/'local/build/runtime-module-rel-optimized/gRL8E54_recomp.dir/Release'
        rel_objects = {p.stem+'.obj': sha(objdir/(p.stem+'.obj')) for p in rel.glob('runtime_rel_chunks/*.c')}
    return {'compiler': compiler, 'binary': str(binary.resolve()),
            'mode': 'llvm_all' if llvm_rel else 'llvm_dol_msvc_rel' if llvm_dol else 'clang_dol_msvc_rel' if reuse else compiler['id'].lower()+'_all',
            'llvm_dol_dir': str(llvm_dol) if llvm_dol else None,
            'llvm_rel_dir': str(llvm_rel) if llvm_rel else None,
            'rel_objects': rel_objects,
            'binary_sha256': sha(binary), 'binary_bytes': binary.stat().st_size,
            'chunk_count': len(chunks), 'sources': sources,
            'source_set_sha256': hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
            'cache_sha256': sha(build/'CMakeCache.txt'),
            'scope': 'Input identity and compiler provenance only; does not prove CPU equivalence or gameplay correctness.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--check-rel-objects', action='store_true')
    args = parser.parse_args()
    result = manifest(args.build)
    if args.check_rel_objects:
        original = json.loads((args.build/'module-build-manifest.json').read_text())
        for key in ('source_set_sha256', 'binary_sha256', 'rel_objects'):
            if original.get(key) != result[key]:
                raise ValueError('Preserved MSVC build no longer matches: '+key)
        print('PASS preserved MSVC sources, DLL and 478 REL objects')
        raise SystemExit(0)
    (args.build/'module-build-manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('sources', 'rel_objects')}, indent=2))
