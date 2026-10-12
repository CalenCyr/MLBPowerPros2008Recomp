# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare the real cache batch helper/call site with unchanged generated loop C."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

HARNESS = r'''
#include <array>
#include <cstdint>
#include <string>
#include <vector>
using u8=std::uint8_t; using u32=std::uint32_t; using u64=std::uint64_t; using s64=std::int64_t; using s32=std::int32_t;
struct CPUState { u32 gpr[32]{},pc=0x8009C4A4,ctr=0,exception=0; s64 downcount=0; u8* ram=nullptr; u32 ram_size=0; };
#include "helper.inc"
static std::vector<u32> trace;
struct Jit { void InvalidateICacheLine(u32 a) { trace.push_back(a); } };
struct System { Jit jit; Jit& GetJitInterface() { return jit; } };
struct Verifier { bool enabled=false; bool IsEnabled() { return enabled; } };
struct Module { char game_id[8]="RL8E54"; };
struct Core { bool m_cache_batch_enabled=false; Module module; Module* m_module=&module; Verifier verifier; Verifier* m_lockstep_verifier=&verifier; u64 m_cache_batch_runs=0,m_cache_batch_extra_lines=0; };
struct PPC { int downcount=1000000; u32 Exceptions=0; bool m_enable_dcache=false; };
static Core storage; static Core* core=&storage;
static PPC ppc; static System test_system;
struct Profile { std::string path; } g_powerpros_fallback_profile;
static u64 hooks=0;
void ppc_fallback_instruction(CPUState* cpu,u32 raw,u32 cia) {
  ++hooks;
  auto& system=test_system;
  const u32 ea=cpu->gpr[3],xo=86;
#include "call.inc"
}
void ppc_system_call_exception(CPUState* cpu,u32) { cpu->exception=1; cpu->pc=0xC00; }
#define DOLRECOMP_C_LOOP_CYCLE_BUDGET 256
void Generated(CPUState* ctx) {
#include "loop.inc"
}
struct Result { CPUState cpu; PPC cycles; std::vector<u32> invalidations; u64 callbacks,runs,extra; };
Result Run(CPUState cpu,bool enabled) {
  core->m_cache_batch_enabled=enabled; core->m_cache_batch_runs=core->m_cache_batch_extra_lines=hooks=0;
  ppc={}; trace.clear(); Generated(&cpu);
  return {cpu,ppc,trace,hooks,core->m_cache_batch_runs,core->m_cache_batch_extra_lines};
}
int main() {
  std::vector<u8> ram(0x9C4B4);
  auto write=[&](u32 a,u32 v){ for(u32 i=0;i<4;++i) ram[a+i]=u8(v>>(24-8*i)); };
  write(0x9C4A4,0x7C0018AC);write(0x9C4A8,0x38630020);write(0x9C4AC,0x4200FFF8);write(0x9C4B0,0x44000002);
  CPUState cpu; cpu.ram=ram.data();cpu.ram_size=u32(ram.size());cpu.ctr=256;cpu.downcount=-2;
  auto count=[&](){return PowerProsCacheBatchCount(&cpu,0x7C0018AC,0x8009C4A4,true,0,false,false);};
  if(count()!=127) return 1;
  for(u32 a : {0x9C4A4u,0x9C4A8u,0x9C4ACu,0x9C4B0u}) { ram[a]^=1; if(count()!=1) return 2;ram[a]^=1; }
  for(int guard=0;guard<10;++guard) {
    CPUState c=cpu;u32 raw=0x7C0018AC,cia=0x8009C4A4,pending=0;bool allowed=true,dcache=false,ls=false;
    switch(guard) {case 0:allowed=false;break;case 1:raw^=1;break;case 2:cia+=4;break;case 3:c.pc+=4;break;
      case 4:c.exception=1;break;case 5:pending=1;break;case 6:dcache=true;break;case 7:ls=true;break;
      case 8:c.ram=nullptr;break;case 9:--c.ram_size;break;}
    if(PowerProsCacheBatchCount(&c,raw,cia,allowed,pending,dcache,ls)!=1) return 3;
  }
  u64 cases=0,batches=0;
  for(s64 dc=-270;dc<=0;++dc) for(u32 ctr : {0u,1u,2u,3u,127u,128u,129u,255u,256u,0xFFFFFFFFu})
    for(u32 address : {0u,0x80000001u,0xFFFFFFF0u}) {
      cpu.downcount=dc;cpu.ctr=ctr;cpu.gpr[3]=address;cpu.pc=0x8009C4A4;
      auto before=Run(cpu,false),after=Run(cpu,true);
      if(before.cpu.pc!=after.cpu.pc || before.cpu.ctr!=after.cpu.ctr || before.cpu.gpr[3]!=after.cpu.gpr[3] ||
         before.cpu.downcount!=after.cpu.downcount || before.cpu.exception!=after.cpu.exception ||
         before.cycles.downcount!=after.cycles.downcount || before.invalidations!=after.invalidations) return 4;
      if(after.callbacks+after.extra!=before.callbacks) return 5;
      ++cases;batches+=after.runs;
    }
  // Real call-site guards also leave callback execution unchanged.
  for(int guard=0;guard<4;++guard) {
    cpu.downcount=-2;cpu.ctr=128;
    core->verifier.enabled=guard==0;
    g_powerpros_fallback_profile.path=guard==1?"enabled":"";
    core->m_module=guard==2?nullptr:&core->module;
    core->module.game_id[0]=guard==3?'X':'R';
    auto before=Run(cpu,false),after=Run(cpu,true);
    if(after.runs || after.callbacks!=before.callbacks || after.invalidations!=before.invalidations) return 6;
  }
  if(cases!=8130 || batches==0) return 7;
  return 0;
}
'''


def main():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'local/vendor/ModernGekko/vendor/dolphin/Source/Core/Core/PowerPC/StaticRecomp/StaticRecompCore_Hooks.cpp').read_text(encoding='utf-8')
    helper = source.split('// POWERPROS_CACHE_BATCH_BEGIN', 1)[1].split('// POWERPROS_CACHE_BATCH_END', 1)[0]
    call = source.split('        u32 batch = 1;', 1)[1].split('      // These bypass SingleStepInner', 1)[0]
    call = 'u32 batch = 1;' + call
    # The extracted region includes the outer else closing brace; drop just that brace.
    call = call.rsplit('}', 1)[0]
    suffix = source.split('      // These bypass SingleStepInner', 1)[1].split('    }\n  }', 1)[0]
    call += suffix[suffix.index('      ppc.downcount -='):]
    generated = (root / 'local/generated/dolrecomp/dol/main_chunks/chunk_0038_text1_8009B360.c').read_text(encoding='utf-8')
    loop = 'label_8009C4A4:' + generated.split('label_8009C4A4:', 1)[1].split('label_8009C4B4:', 1)[0]
    folder = root / 'local/analysis' / ('cache-batch-check-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    for name, text in (('helper.inc', helper), ('call.inc', call), ('loop.inc', loop), ('check.cpp', HARNESS)):
        (folder / name).write_text(text, encoding='utf-8')
    (folder / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(CacheBatchCheck LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 17)\nadd_executable(cache_batch_check check.cpp)\n')
    with (folder / 'build.log').open('w') as log:
        subprocess.run(['cmake', '-S', str(folder), '-B', str(folder / 'build'), '-G', 'Visual Studio 17 2022', '-A', 'x64'], check=True, stdout=log, stderr=log)
        subprocess.run(['cmake', '--build', str(folder / 'build'), '--config', 'Release'], check=True, stdout=log, stderr=log)
    subprocess.run([str(folder / 'build/Release/cache_batch_check.exe')], check=True)
    result = {'helper_sha256': hashlib.sha256(helper.encode()).hexdigest(), 'call_site_sha256': hashlib.sha256(call.encode()).hexdigest(),
              'generated_loop_sha256': hashlib.sha256(loop.encode()).hexdigest(), 'differential_cases': 8130,
              'same_cache_line_sequence_cycles_registers_yield_and_sc': True, 'guards_and_instruction_changes_rejected': True,
              'scope': 'Real helper, call-site code and unchanged generated loop with synthetic invalidator and system-call exception; not complete JIT/cache or hardware testing.'}
    (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS cache batch guards and 8130 differential loop cases:', folder)


if __name__ == '__main__':
    main()
