# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent sample fractions/CPU units and rejection of invalid provenance."""
import struct
import tempfile
from pathlib import Path
from analyze_host_samples import analyze


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        binary, symbols = root/'fixture.dll', root/'fixture.map'
        image = bytearray(4096)
        struct.pack_into('<I', image, 0x3c, 128)
        image[128:132] = b'PE\0\0'
        struct.pack_into('<H', image, 132, 0x8664)
        struct.pack_into('<I', image, 136, 123)
        struct.pack_into('<Q', image, 176, 0x180000000)
        binary.write_bytes(image)
        maptext = 'Preferred load address is 0000000180000000\nTimestamp is 0000007b\n 0001:00000000 first 0000000180000010 f first.obj\n 0001:00000010 second 0000000180000020 f second.obj\n'
        symbols.write_text(maptext)
        (root/'summary.txt').write_text('selected_tid=10\nsamples=3\nelapsed_ns=40\n')
        (root/'modules.csv').write_text(f'base,size,path\n4096,100,"{binary}"\n')
        samples = 'elapsed_ns,tid,rip,cycles_since_last,suspend_ns\n10,10,4112,100,1\n20,10,4128,100,1\n30,10,9000,100,1\n'
        (root/'samples.csv').write_text(samples)
        threads = 'tid,name,cycles,user_100ns,kernel_100ns\n10,CPU,1000,25000000,5000000\n'
        (root/'threads.csv').write_text(threads)
        mapping = ['fixture.dll='+str(symbols)]
        report = analyze(root, mapping)
        assert report['modules'][0]['sample_share'] == 2/3
        assert report['modules'][1]['sample_share'] == 1/3
        assert {x['nearest_function'] for x in report['top_functions']} == {'first', 'second', '<no map>'}
        assert report['threads'][0]['user_seconds'] == 2.5
        assert report['threads'][0]['kernel_seconds'] == 0.5
        changes = [(root/'samples.csv', samples.replace('20,10', '20,11')),
                   (root/'samples.csv', samples.replace('20,10', '5,10')),
                   (root/'samples.csv', samples.replace('30,10', '50,10')),
                   (root/'samples.csv', samples.replace(',100,1', ',0,1')),
                   (root/'samples.csv', samples.replace('30,10,9000,100,1\n', '')),
                   (root/'threads.csv', threads.replace('10,CPU', '11,CPU')),
                   (symbols, maptext.replace('0000007b', '0000007c')),
                   (symbols, maptext.replace('0000000180000000', '0000000180001000'))]
        for path, changed in changes:
            original = path.read_text()
            path.write_text(changed)
            try:
                analyze(root, mapping)
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid sample/provenance accepted: '+str(path))
            finally:
                path.write_text(original)
    print('PASS independent sample fractions/CPU units and 8 chronology/provenance rejections')


if __name__ == '__main__':
    main()
