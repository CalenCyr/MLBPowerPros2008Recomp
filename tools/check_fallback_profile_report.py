# SPDX-License-Identifier: GPL-3.0-or-later
"""Check corrupt, truncated and overflowing diagnostic profile accounting."""
import tempfile
from pathlib import Path
from analyze_fallback_profile import read_profile


VALID = '''kind,pc,raw,count
stride,00000000,00000000,1024
total_slow,00000000,00000000,2050
dropped_slow,00000000,00000000,1
slow,80000000,12345678,1
total_cache_fast,00000000,00000000,1024
dropped_cache_fast,00000000,00000000,0
cache_fast,80000004,7C0000AC,1
'''


def main():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'profile.csv'
        path.write_text(VALID, encoding='utf-8')
        report = read_profile(path, 3074)
        assert report['groups']['slow']['dropped_samples'] == 1
        invalid = [
            (VALID, 3073),
            (VALID.replace('total_slow,00000000,00000000,2050\n', ''), None),
            (VALID.replace('dropped_slow,00000000,00000000,1', 'dropped_slow,00000000,00000000,0'), None),
            (VALID + 'slow,80000000,12345678,1\n', None),
            (VALID.replace('80000004', '80000005'), None),
            (VALID.replace(',2050', ',-1'), None),
            (VALID.replace(',2050', ',18446744073709551616'), None),
            (VALID.replace('cache_fast,80000004,7C0000AC,1', 'cache_fast,80000004,7C0000AC'), None),
            (VALID.replace('stride,00000000,00000000,1024', 'stride,00000000,00000000,0'), None)]
        for index, (content, hooks) in enumerate(invalid):
            path.write_text(content, encoding='utf-8')
            try:
                read_profile(path, hooks)
            except ValueError:
                continue
            raise AssertionError(f'Corrupt case {index} was accepted')
    print(f'PASS valid dropped-sample accounting and {len(invalid)} corrupt-profile rejections')


if __name__ == '__main__':
    main()
