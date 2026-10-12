# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise locked patch preparation on private copies, including drift rejection."""
import datetime
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[1]
    fixture=root/'local/analysis'/('patch-preparation-check-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    fixture.mkdir(parents=True)
    subprocess.run(['git','init',str(fixture)],check=True,capture_output=True)
    lock=json.loads((root/'config/runtime.lock.json').read_text())
    (fixture/'config').mkdir()
    (fixture/'config/runtime.lock.json').write_text(json.dumps(lock))
    files=[]
    for relative, revision, patches in (
        ('local/vendor/ModernGekko',lock['commit'],lock['runtime_patches']),
        ('local/vendor/ModernGekko/vendor/dolphin',lock['recompcore_commit'],lock['patches'])):
        checkout=fixture/relative
        subprocess.run(['git','clone','--shared','--no-checkout',str(root/relative),str(checkout)],check=True,capture_output=True)
        affected=set()
        for patch in patches:
            dest=fixture/patch
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(root/patch,dest)
            affected.update(re.findall(r'^\+\+\+ b/([^\r\n\t]+)',dest.read_text(encoding='utf-8'),re.M))
        for path in affected:
            dest=checkout/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(subprocess.check_output(['git','-C',str(checkout),'show',revision+':'+path]))
            files.append((dest,root/relative/path))
    spec=importlib.util.spec_from_file_location('patch_checker',root/'tools/check_runtime_patches.py')
    checker=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    checker.__file__=str(fixture/'tools/check_runtime_patches.py')
    checker.main(prepare=True)
    assert all(a.read_text(encoding='utf-8')==b.read_text(encoding='utf-8') for a,b in files), 'Fresh checkout preparation differs from locked source'
    # An older, recognized series prefix must advance without duplicating patches.
    subject=fixture/'local/vendor/ModernGekko/vendor/dolphin/Source/Core/Core/Core.cpp'
    core_checkout=fixture/'local/vendor/ModernGekko/vendor/dolphin'
    core_path='Source/Core/Core/Core.cpp'
    subject.write_bytes(subprocess.check_output(['git','-C',str(core_checkout),'show',lock['recompcore_commit']+':'+core_path]))
    subprocess.run(['git','-C',str(core_checkout),'apply','--include='+core_path,str(fixture/lock['patches'][0])],check=True,capture_output=True)
    checker.main(prepare=True)
    assert all(a.read_text(encoding='utf-8')==b.read_text(encoding='utf-8') for a,b in files), 'Recognized prefix did not advance'
    # Unknown local edits must reject the whole preparation before changing another file.
    subject.write_text(subject.read_text(encoding='utf-8')+'\n// Unknown test-only edit\n',encoding='utf-8')
    another=fixture/'local/vendor/ModernGekko/src/runtime/dolphin_runtime.cpp'
    another.write_bytes(subprocess.check_output(['git','-C',str(fixture/'local/vendor/ModernGekko'),'show',lock['commit']+':src/runtime/dolphin_runtime.cpp']))
    previous={a:a.read_bytes() for a,_ in files}
    try:
        checker.main(prepare=True)
    except AssertionError as error:
        assert 'unrecognized source changes' in str(error)
    else:
        raise AssertionError('Unknown edits were accepted')
    assert all(a.read_bytes()==data for a,data in previous.items()), 'Rejected preparation changed source files'
    print(f'PASS fresh source, known prefix and drift preservation: {fixture}')


if __name__=='__main__':
    main()
