# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile the actual guard and reject unsafe scheduler-idle conditions."""
import datetime
import json
import subprocess
from pathlib import Path

HARNESS = r'''
#include <cstdint>
#include <vector>
using u32 = std::uint32_t;
using u8 = std::uint8_t;
#include "guard.inc"
int main() {
  std::vector<u8> ram(0x0031B274);
  auto write = [&](u32 offset, u32 value) {
    for (int i=0; i<4; ++i) ram[offset+i] = static_cast<u8>(value >> (24-8*i));
  };
  write(0xA4318, 0x800D9210); write(0xA431C, 0x2C000000); write(0xA4320, 0x4182FFF8);
  auto safe = [&]() {return PowerProsCanIdleScheduler(0x800A4318,0x8000,0x80322060,0,0,ram.data(),ram.size());};
  if (!safe()) return 1;
  if (PowerProsCanIdleScheduler(0x800A431C,0x8000,0x80322060,0,0,ram.data(),ram.size())) return 2;
  if (PowerProsCanIdleScheduler(0x800A4318,0,0x80322060,0,0,ram.data(),ram.size())) return 3;
  if (PowerProsCanIdleScheduler(0x800A4318,0x8000,0x80322064,0,0,ram.data(),ram.size())) return 4;
  if (PowerProsCanIdleScheduler(0x800A4318,0x8000,0x80322060,1,0,ram.data(),ram.size())) return 5;
  if (PowerProsCanIdleScheduler(0x800A4318,0x8000,0x80322060,0,1,ram.data(),ram.size())) return 6;
  if (PowerProsCanIdleScheduler(0x800A4318,0x8000,0x80322060,0,0,nullptr,ram.size())) return 7;
  if (PowerProsCanIdleScheduler(0x800A4318,0x8000,0x80322060,0,0,ram.data(),ram.size()-1)) return 8;
  for (u32 offset : {0xA4318u,0xA431Cu,0xA4320u}) {
    ram[offset+3] ^= 1;
    if (safe()) return 9;
    ram[offset+3] ^= 1;
  }
  for (u32 priority=0; priority<32; ++priority) {
    write(0x31B270, 1u<<priority);
    if (safe()) return 10;
  }
  write(0x31B270,0);
  if (!safe()) return 11;
}
'''


def main():
    root=Path(__file__).resolve().parents[1]
    source=(root/'local/vendor/ModernGekko/vendor/dolphin/Source/Core/Core/PowerPC/StaticRecomp/StaticRecompCore_Run.cpp').read_text(encoding='utf-8')
    helper=source.split('// POWERPROS_SCHEDULER_IDLE_BEGIN',1)[1].split('// POWERPROS_SCHEDULER_IDLE_END',1)[0]
    folder=root/'local/analysis'/('scheduler-idle-check-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    (folder/'guard.inc').write_text(helper,encoding='utf-8')
    (folder/'check.cpp').write_text(HARNESS,encoding='utf-8')
    (folder/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(IdleGuard LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 17)\nadd_executable(guard_check check.cpp)\n')
    with (folder/'build.log').open('w') as log:
        subprocess.run(['cmake','-S',str(folder),'-B',str(folder/'build'),'-G','Visual Studio 17 2022','-A','x64'],check=True,stdout=log,stderr=log)
        subprocess.run(['cmake','--build',str(folder/'build'),'--config','Release'],check=True,stdout=log,stderr=log)
    subprocess.run([str(folder/'build/Release/guard_check.exe')],check=True)
    (folder/'result.json').write_text(json.dumps({'actual_guard_compiled':True,'empty_queue_allowed':True,'unsafe_conditions_rejected':True,'every_ready_priority_rejected':True},indent=2)+'\n')
    print('PASS scheduler-idle guard: PC, EE, SDA, exceptions, RAM bounds, opcodes, all 32 ready priorities;',folder)


if __name__=='__main__':
    main()
