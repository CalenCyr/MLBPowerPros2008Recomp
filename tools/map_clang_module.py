# SPDX-License-Identifier: GPL-3.0-or-later
"""Link existing hybrid objects privately and admit the map only for identical code.

No compilation or replacement of the active DLL. The original timestamp is
preserved and executable section addresses, sizes and bytes must all match.
"""
import datetime
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def pe_sections(path):
    with path.open('rb') as f:
        head=f.read(16384)
        pe=struct.unpack_from('<I',head,0x3c)[0]
        if head[pe:pe+4]!=b'PE\0\0' or struct.unpack_from('<H',head,pe+4)[0]!=0x8664:
            raise ValueError('Require x64 PE')
        count=struct.unpack_from('<H',head,pe+6)[0]
        optional=struct.unpack_from('<H',head,pe+20)[0]
        sections=[]
        for i in range(count):
            at=pe+24+optional+i*40
            name=head[at:at+8].rstrip(b'\0').decode('ascii')
            size,rva,raw_size,offset=struct.unpack_from('<IIII',head,at+8)
            flags=struct.unpack_from('<I',head,at+36)[0]
            if flags&0x20000000:
                f.seek(offset);data=f.read(raw_size)
                if len(data)!=raw_size:raise ValueError('Truncated executable section')
                sections.append({'name':name,'rva':rva,'virtual_size':size,'raw_size':raw_size,
                                 'sha256':hashlib.sha256(data).hexdigest()})
        return {'timestamp':struct.unpack_from('<I',head,pe+8)[0],
                'image_base':struct.unpack_from('<Q',head,pe+48)[0],
                'executable_sections':sections}


def main():
    root=Path(__file__).resolve().parents[1]
    build=root/(sys.argv[1] if len(sys.argv)>1 else 'local/build/runtime-module-rel-clang')
    original=build/'gRL8E54_recomp.dll'
    manifest=json.loads((build/'module-build-manifest.json').read_text())
    before=sha(original)
    if before!=manifest['binary_sha256']:raise ValueError('DLL differs from manifest')
    layout=pe_sections(original)
    ninja=(build/'build.ninja').read_text()
    line=next(x for x in ninja.splitlines() if x.startswith('build gRL8E54_recomp.dll '))
    parts=line.split(' C_SHARED_LIBRARY_LINKER__gRL8E54_recomp_Release ',1)[1].split(' |',1)[0].split()
    objects=[(build/part.replace('$:',':')).resolve() for part in parts]
    if not all(x.is_file() and x.suffix.lower() in ('.obj','.o') for x in objects):
        raise ValueError('Unexpected object input or Ninja escaping')
    folder=root/'local/analysis'/('clang-module-map-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    rsp=folder/'objects.rsp';rsp.write_text('\n'.join('"'+x.as_posix()+'"' for x in objects)+'\n')
    output=folder/'gRL8E54_recomp.dll';mapping=folder/'gRL8E54_recomp.map'
    libs=['kernel32.lib','user32.lib','gdi32.lib','winspool.lib','shell32.lib','ole32.lib',
          'oleaut32.lib','uuid.lib','comdlg32.lib','advapi32.lib']
    command=[str(root/'local/tools/llvm-22.1.8/bin/lld-link.exe'),'/nologo','@'+str(rsp),
             '/out:'+str(output),'/implib:'+str(folder/'gRL8E54_recomp.lib'),'/dll','/version:0.0',
             '/machine:x64','/INCREMENTAL:NO','/timestamp:'+str(layout['timestamp']),'/map:'+str(mapping)]+libs
    with (folder/'link.log').open('w') as log:
        result=subprocess.run(command,cwd=build,stdout=log,stderr=log)
    report={'original_binary':str(original),'original_sha256':before,'object_count':len(objects),
            'exit_code':result.returncode,'map':str(mapping),'scope':'Private link from existing objects. Admit symbols only after executable section identity; no target execution or active DLL replacement.'}
    if result.returncode==0:
        relinked=pe_sections(output)
        report.update({'original_layout':layout,'relinked_layout':relinked,
                       'executable_code_identical':layout==relinked,'relinked_sha256':sha(output),
                       'map_sha256':sha(mapping)})
    report['active_dll_unchanged']=sha(original)==before
    (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    print(folder)
    if result.returncode or not report.get('executable_code_identical') or not report['active_dll_unchanged']:
        raise SystemExit(1)


if __name__=='__main__':main()
