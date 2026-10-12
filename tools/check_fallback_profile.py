# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile the actual bounded sampling helper; check disabled mode and accounting."""
import csv
import datetime
import json
import subprocess
from pathlib import Path

HARNESS = r'''
#include <cstdio>
#include <string>
#include <unordered_map>
#include <cstdint>
using u32 = std::uint32_t;
using u64 = std::uint64_t;
#include "profile.inc"
int main(int argc, char** argv) {
  PowerProsFallbackProfile p;
  p.Reset(nullptr);
  for (int n=0; n<2048; ++n) p.Observe(0x80000000, 0x12345678, false);
  if (p.observed[0] || !p.sites[0].empty() || !p.Write()) return 1;
  p.Reset(argv[1]);
  for (int n=0; n<2050; ++n) p.Observe(0x80000000, 0x12345678, false);
  for (int n=0; n<1024; ++n) p.Observe(0x80000000, 0x7C0000AC, true);
  if (!p.Write()) return 2;
  p.Reset(argv[2]);
  for (u32 site=0; site<PowerProsFallbackProfile::max_sites+1; ++site)
    for (u64 n=0; n<PowerProsFallbackProfile::stride; ++n)
      p.Observe(0x80000000 + 4*site, 0x12345678, false);
  // Existing entries must still accumulate after the map reaches its limit.
  for (u64 n=0; n<PowerProsFallbackProfile::stride; ++n)
    p.Observe(0x80000000, 0x12345678, false);
  if (p.sites[0].size()!=PowerProsFallbackProfile::max_sites || p.dropped[0]!=1) return 3;
  if (!p.Write()) return 4;
  p.Reset(nullptr);
  if (p.observed[0] || p.dropped[0] || !p.sites[0].empty()) return 5;
}
'''


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'local/vendor/ModernGekko/vendor/dolphin/Source/Core/Core/PowerPC/StaticRecomp/StaticRecompCore_Hooks.cpp').read_text(encoding='utf-8')
    helper = source.split('// POWERPROS_FALLBACK_PROFILE_BEGIN', 1)[1].split('// POWERPROS_FALLBACK_PROFILE_END', 1)[0]
    folder = root / 'local/analysis' / ('fallback-profile-check-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    (folder / 'profile.inc').write_text(helper, encoding='utf-8')
    (folder / 'check.cpp').write_text(HARNESS, encoding='utf-8')
    (folder / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(ProfileCheck LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 17)\nadd_executable(profile_check check.cpp)\n')
    with (folder / 'build.log').open('w') as log:
        subprocess.run(['cmake', '-S', str(folder), '-B', str(folder / 'build'), '-G', 'Visual Studio 17 2022', '-A', 'x64'], check=True, stdout=log, stderr=log)
        subprocess.run(['cmake', '--build', str(folder / 'build'), '--config', 'Release'], check=True, stdout=log, stderr=log)
    subprocess.run([str(folder / 'build/Release/profile_check.exe'), str(folder / 'small.csv'), str(folder / 'bounded.csv')], check=True)
    small = read(folder / 'small.csv')
    totals = {r['kind']: int(r['count']) for r in small if r['kind'].startswith('total_')}
    assert totals == {'total_slow': 2050, 'total_cache_fast': 1024}
    samples = {r['kind']: int(r['count']) for r in small if r['kind'] in ('slow', 'cache_fast')}
    assert samples == {'slow': 2, 'cache_fast': 1}
    bounded = read(folder / 'bounded.csv')
    sites = [r for r in bounded if r['kind'] == 'slow']
    assert len(sites) == 4096
    assert sum(int(r['count']) for r in sites) == 4097
    assert next(int(r['count']) for r in bounded if r['kind'] == 'dropped_slow') == 1
    assert next(int(r['count']) for r in bounded if r['kind'] == 'total_slow') == 4098 * 1024
    (folder / 'result.json').write_text(json.dumps({'disabled_and_reset': True, 'separate_fast_and_slow_accounting': True, 'bounded_sites_and_existing_entry_accumulation': True}, indent=2) + '\n')
    print('PASS disabled/reset, sampling accounting, bounded overflow: ' + str(folder))


if __name__ == '__main__':
    main()
