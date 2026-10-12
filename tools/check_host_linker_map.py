# SPDX-License-Identifier: GPL-3.0-or-later
"""Check MSVC/LLD code symbols, aliases and PE identity rejection."""
import struct
import tempfile
from pathlib import Path
from analyze_host_samples import load_map


def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory); binary=root/'sample.dll'; mapping=root/'sample.map'
        head=bytearray(4096); pe=128; base=0x180000000
        struct.pack_into('<I',head,0x3c,pe);head[pe:pe+4]=b'PE\0\0'
        struct.pack_into('<HHI',head,pe+4,0x8664,2,0xabc)
        struct.pack_into('<H',head,pe+20,240);struct.pack_into('<Q',head,pe+48,base)
        for i,(size,rva,flags) in enumerate([(0x100,0x1000,0x60000020),(0x100,0x2000,0x40000040)]):
            at=pe+24+240+i*40;struct.pack_into('<II',head,at+8,size,rva);struct.pack_into('<I',head,at+36,flags)
        binary.write_bytes(head)
        text='Timestamp is abc\nPreferred load address is 0000000180000000\n'
        text+=' 0001:00000000 msvc_function 0000000180001000 f source.obj\n'
        text+=' 0001:00000010 lld_function 0000000180001010 source.obj\n'
        text+=' 0001:00000010 lld_alias 0000000180001010 other.obj\n'
        text+=' 0002:00000000 data_label 0000000180002000 data.obj\n'
        text+=' 0000:00000000 absolute_label 0000000000000000 absolute.obj\n'
        text+=' 0001:00000100 outside_code 0000000180001100 source.obj\n'
        mapping.write_text(text)
        addresses,symbols=load_map(mapping,binary)
        assert addresses==[0x1000,0x1010]
        assert symbols[0x1000]==[('msvc_function','source.obj')]
        assert set(symbols[0x1010])=={('lld_function','source.obj'),('lld_alias','other.obj')}
        for bad in (text.replace('Timestamp is abc','Timestamp is abd'),
                    text.replace('Preferred load address is 0000000180000000','Preferred load address is 0000000190000000'),
                    'Timestamp is abc\nPreferred load address is 0000000180000000\n 0002:0 data 0000000180002000 data.obj\n'):
            mapping.write_text(bad)
            try:load_map(mapping,binary)
            except ValueError:pass
            else:raise AssertionError('Invalid map admitted')
        mapping.write_text(text);struct.pack_into('<H',head,pe+4,0x14c);binary.write_bytes(head)
        try:load_map(mapping,binary)
        except ValueError:pass
        else:raise AssertionError('Non-x64 binary admitted')
    print('PASS MSVC/LLD code labels, aliases, code-end/data/absolute exclusion and four invalid-map rejections')


if __name__=='__main__':main()
