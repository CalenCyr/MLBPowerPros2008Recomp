# SPDX-License-Identifier: GPL-3.0-or-later
"""Check real MEM2 snapshot code against leaking and repeated shadow writes."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

HARNESS = r'''
#include <cstdint>
#include <vector>
#include <cstring>
#include <algorithm>
using u8 = std::uint8_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;
#include "snapshot.inc"
int main() {
  for (u32 size : {1u, 7u, 32u, 257u, 65536u}) {
    std::vector<u8> bytes(size), original(size), native(size), other(size);
    for (u32 i = 0; i < size; ++i) original[i] = bytes[i] = static_cast<u8>(i*17);
    PowerProsExramSnapshot snapshot;
    snapshot.Capture(bytes.data(), size);
    if (snapshot.BeginShadow(other.data(), size)) return 1;
    if (snapshot.BeginShadow(bytes.data(), size+1)) return 2;
    for (u32 i = 0; i < size; i += 3) bytes[i] ^= 0x55;
    native = bytes;
    if (!snapshot.BeginShadow(bytes.data(), size) || bytes != original) return 3;
    // Replay exactly native's writes; matching memory must produce no reports.
    for (u32 i = 0; i < size; i += 3) bytes[i] ^= 0x55;
    if (snapshot.Differences([](u32,u8,u8){}) != 0) return 4;
    snapshot.RestoreNative();
    if (bytes != native) return 5;
    // New check captures the current canonical memory, not the previous pre-image.
    snapshot.Capture(bytes.data(), size);
    bytes[0] ^= 0x31;
    native = bytes;
    if (!snapshot.BeginShadow(bytes.data(), size)) return 6;
    std::fill(bytes.begin(), bytes.end(), 0xff);
    u64 expected = 0, reported = 0;
    for (u32 i=0; i<size; ++i) expected += bytes[i] != native[i];
    const auto count = snapshot.Differences([&](u32 off,u8 n,u8 s) {
      if (off >= size || n != native[off] || s != bytes[off]) std::abort();
      ++reported;
    });
    if (count != expected || reported != std::min<u64>(32, expected)) return 7;
    snapshot.RestoreNative();
    if (bytes != native) return 8;
    snapshot.Capture(nullptr, 0);
    if (!snapshot.BeginShadow(nullptr,0) || snapshot.Differences([](u32,u8,u8){}) != 0) return 9;
    snapshot.RestoreNative();
  }
}
'''


def main():
    root = Path(__file__).resolve().parents[1]
    header = root/'local/vendor/ModernGekko/vendor/dolphin/Source/Core/Core/PowerPC/StaticRecomp/StaticRecompLockstep.h'
    source = header.read_text()
    helper = source.split('// POWERPROS_LOCKSTEP_EXRAM_BEGIN', 1)[1].split('// POWERPROS_LOCKSTEP_EXRAM_END', 1)[0]
    folder = root/'local/analysis'/('lockstep-exram-check-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    (folder/'snapshot.inc').write_text(helper)
    (folder/'check.cpp').write_text(HARNESS)
    (folder/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(ExramCheck LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 17)\nadd_executable(exram_check check.cpp)\n')
    with (folder/'build.log').open('w') as log:
        subprocess.run(['cmake', '-S', str(folder), '-B', str(folder/'build'), '-G', 'Visual Studio 17 2022', '-A', 'x64'], check=True, stdout=log, stderr=log)
        subprocess.run(['cmake', '--build', str(folder/'build'), '--config', 'Release'], check=True, stdout=log, stderr=log)
    subprocess.run([str(folder/'build/Release/exram_check.exe')], check=True)
    (folder/'result.json').write_text(json.dumps({'helper_sha256': hashlib.sha256(helper.encode()).hexdigest(),
        'actual_helper_compiled': True, 'pre_native_image_replayed': True,
        'shadow_only_writes_restored': True, 'native_post_image_preserved': True,
        'repeated_checks_and_null_memory_validated': True, 'report_limit_and_total_checked': True}, indent=2)+'\n')
    print('PASS actual MEM2 snapshot: replay, restore, repeated checks, report bounds, pointer/size rejection;', folder)


if __name__ == '__main__':
    main()
