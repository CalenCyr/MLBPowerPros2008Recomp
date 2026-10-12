# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile the real timing helper and dispatch call site with a synthetic module."""
import csv
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

HARNESS = r'''
#include <chrono>
#include <cstdio>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <unordered_map>
using u32 = std::uint32_t;
using u64 = std::uint64_t;
#include "helper.inc"
struct Guest { u32 pc=0; };
static u64 calls=0;
static u32 expected=0;
static void Dispatch(Guest* guest,u32 pc) {
  if (pc!=expected || guest->pc!=pc) throw std::runtime_error("module entry changed");
  ++calls; guest->pc=pc+4;
}
struct Module { void (*dispatch)(Guest*,u32)=Dispatch; };
struct Core {
  Guest m_guest;
  Module module;
  Module* m_module=&module;
  bool m_dispatch_timing_enabled=false, m_has_rel_modules=true;
  u32 m_rel_runtime_begin=0x80500000;
  u64 m_rel_runtime_end=0x80501000;
  u64 resolves=0,translations=0;
  bool ResolveNativeAddress(u32 pc,u32* linked,u32*) {
    ++resolves; *linked=pc>=m_rel_runtime_begin ? pc-0x500000 : pc; return true;
  }
  u32 TranslateRelAddress(u32 pc) {
    ++translations; return pc>=0x80000000 && pc<0x80001000 ? pc+0x500000 : pc;
  }
  void One() {
#include "call.inc"
  }
  void Check(u32 pc) {
    m_guest.pc=pc;
    expected=m_has_rel_modules && pc>=m_rel_runtime_begin ? pc-0x500000 : pc;
    const u64 before=calls;
    One();
    if (calls!=before+1 || m_guest.pc!=pc+4) throw std::runtime_error("dispatch result changed");
  }
};
int main(int argc,char**argv) {
  if(argc!=4) return 1;
  auto& p=g_powerpros_dispatch_timing;
  Core core;
  p.Reset(nullptr);
  core.Check(0x80500004);
  core.m_dispatch_timing_enabled=true;
  core.Check(0x80500004);
  if(p.observed[0] || p.observed[1] || p.clock_pair.samples || !p.Write()) return 2;
  p.Reset(argv[1]);
  if(p.clock_pair.samples!=10000) return 3;
  core.m_dispatch_timing_enabled=false;
  core.Check(0x80500004);
  if(p.observed[1]) return 4;
  core.m_dispatch_timing_enabled=true;
  for(u32 i=0;i<8192;++i) core.Check(0x80500004);
  for(u32 i=0;i<4099;++i) core.Check(0x8000403C);
  if(p.observed[0]!=4099 || p.observed[1]!=8192) return 5;
  for(u32 phase=0;phase<3;++phase)
    if(p.phases[0][phase].samples!=1 || p.phases[1][phase].samples!=2) return 6;
  p.Add(2,0,100); p.Add(0,3,100);
  if(p.phases[0][0].samples!=1 || !p.Write()) return 7;
  if(p.module_sites.size()!=2) return 11;
  const auto outside=p.module_sites.at(0x8000403Cu);
  const auto inside=p.module_sites.at((u64(1)<<32)|0x80500004u);
  if(outside.samples!=1 || inside.samples!=2) return 12;
  if(outside.total_ns!=p.phases[0][1].total_ns || inside.total_ns!=p.phases[1][1].total_ns) return 13;
  p.Reset(nullptr);
  p.AddModuleSample(0,0x80000000,100);
  if(!p.module_sites.empty() || p.dropped_sites[0].samples) return 14;
  core.m_has_rel_modules=false;
  const u64 before_resolves=core.resolves,before_translations=core.translations;
  core.Check(0x8000403C);
  if(core.resolves!=before_resolves || core.translations!=before_translations) return 8;
  if(p.observed[0] || p.observed[1] || p.phases[0][0].samples || p.clock_pair.samples) return 9;
  p.Reset(argv[2]);
  if(p.Write()) return 10;
  for(u32 i=0;i<4096;++i) p.AddModuleSample(0,0x80000000+4*i,10);
  p.AddModuleSample(0,0x80010000,20);
  p.AddModuleSample(1,0x80500000,30);
  p.AddModuleSample(0,0x80000000,40);
  p.AddModuleSample(2,0x80000000,50);
  if(p.module_sites.size()!=4096 || p.dropped_sites[0].samples!=1 || p.dropped_sites[1].samples!=1) return 15;
  if(p.module_sites.at(0x80000000).samples!=2 || p.module_sites.at(0x80000000).total_ns!=50) return 16;
  if(p.phases[0][1].samples!=4098 || p.phases[1][1].samples!=1) return 17;
  p.Reset(argv[3]);
  if(p.Write()) return 18;
  return 0;
}
'''


def main():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'local/vendor/ModernGekko/vendor/dolphin/Source/Core/Core/PowerPC/StaticRecomp/StaticRecompCore_Run.cpp').read_text(encoding='utf-8')
    helper = source.split('// POWERPROS_DISPATCH_TIMING_BEGIN', 1)[1].split('// POWERPROS_DISPATCH_TIMING_END', 1)[0]
    call = source.split('// POWERPROS_DISPATCH_TIMING_CALL_BEGIN', 1)[1].split('// POWERPROS_DISPATCH_TIMING_CALL_END', 1)[0]
    folder = root / 'local/analysis' / ('dispatch-timing-check-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    (folder / 'helper.inc').write_text(helper)
    (folder / 'call.inc').write_text(call)
    (folder / 'check.cpp').write_text(HARNESS)
    (folder / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(DispatchTimingCheck LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 17)\nadd_executable(dispatch_timing_check check.cpp)\n')
    with (folder / 'build.log').open('w') as log:
        subprocess.run(['cmake', '-S', str(folder), '-B', str(folder / 'build'), '-G', 'Visual Studio 17 2022', '-A', 'x64'], check=True, stdout=log, stderr=log)
        subprocess.run(['cmake', '--build', str(folder / 'build'), '--config', 'Release'], check=True, stdout=log, stderr=log)
    (folder / 'blocked.csv.sites.csv').mkdir()
    subprocess.run([str(folder / 'build/Release/dispatch_timing_check.exe'), str(folder / 'timing.csv'), str(folder / 'absent/timing.csv'), str(folder / 'blocked.csv')], check=True)
    assert (folder / 'blocked.csv').is_file()
    with (folder / 'timing.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 7
    assert sum(int(r['samples']) for r in rows if r['phase'] != 'clock_pair') == 9
    assert all(int(r['max_ns']) <= int(r['total_ns']) for r in rows)
    with (folder / 'timing.csv.sites.csv').open(newline='') as stream:
        sites = list(csv.DictReader(stream))
    assert len(sites) == 4
    assert sum(int(r['samples']) for r in sites) == 3
    assert sum(int(r['total_ns']) for r in sites) == sum(int(r['total_ns']) for r in rows if r['phase'] == 'module_dispatch')
    evidence = {'helper_sha256': hashlib.sha256(helper.encode()).hexdigest(),
                'call_site_sha256': hashlib.sha256(call.encode()).hexdigest(),
                'disabled_and_reset': True, 'separate_context_sampling': True,
                'actual_call_site_preserves_module_entry_and_result': True,
                'no_rel_call_site': True, 'invalid_indices_rejected': True,
                'output_failure_detected': True,
                'module_site_accounting_and_runtime_pc': True,
                'bounded_sites_overflow_and_existing_site_update': True,
                'companion_output_failure_detected': True,
                'scope': 'Actual helper and dispatch call-site code with synthetic conversion methods and module; not game execution, real REL resolution or full runtime testing.'}
    (folder / 'result.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print('PASS timing helper and dispatch call site, disabled/reset, contexts, calibration, write failure:', folder)


if __name__ == '__main__':
    main()
