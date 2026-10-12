# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile the frontend binding fragment with the actual static mod loader."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

HARNESS = r'''
#include "moderngekko/mod_loader.hpp"
#include <cstdint>
using u32=std::uint32_t;
using u8=std::uint8_t;
using u64=std::uint64_t;
#include "Core/PowerPC/StaticRecomp/StaticRecompModuleSource.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#define main upstream_static_mod_test
#include "upstream-static-tests.inc"
#undef main
using moderngekko::ModManager;
StaticRecompModuleSource Configure(ModManager* manager, const char* setting) {
  _putenv_s("STATICRECOMP_POWERPROS_SKIP_EMPTY_MOD_HOOKS", setting);
  struct Reference {
    ModManager* ptr;
    ModManager* get() const { return ptr; }
    ModManager* operator->() const { return ptr; }
  };
  struct Impl { Reference mods; } object{{manager}};
  auto* impl = &object;
  StaticRecompModuleSource recomp_source;
  #include "binding.inc"
  return recomp_source;
}
unsigned cases=0, failures=0;
void expect(bool ok, const char* label) {
  ++cases;
  std::printf("%s %s\n",ok?"PASS":"FAIL",label);
  failures += !ok;
}
bool Bound(const StaticRecompModuleSource& source, ModManager* manager) {
  return source.host_call == &ModManager::HostCall &&
    source.host_call_contains == &ModManager::HostCallContains &&
    source.host_call_range_contains == &ModManager::HostCallRangeContains &&
    source.host_call_user == manager;
}
bool Unbound(const StaticRecompModuleSource& source) {
  return !source.host_call && !source.host_call_contains &&
    !source.host_call_range_contains && !source.host_call_user;
}
int main() {
  expect(upstream_static_mod_test()==0,"actual upstream static patches/hooks/events/dependencies/ABI/unload");
  ModManager manager;
  expect(Bound(Configure(&manager,""),&manager),"empty manager keeps default bindings");
  expect(Unbound(Configure(&manager,"1")),"opt-in empty manager has no guest callbacks");
  expect(Bound(Configure(&manager,"true"),&manager),"unknown setting keeps default bindings");
  expect(Bound(Configure(&manager,"0"),&manager),"disabled setting keeps default bindings");
  auto report=manager.Load({moderngekko::ModSource::AttachedDescriptor(&base_descriptor,"base")},"TEST01");
  expect(bool(report)&&!manager.Empty(),"actual patch/hook mod loaded");
  auto source=Configure(&manager,"1");
  expect(Bound(source,&manager),"opt-in loaded mod keeps every binding");
  CPUState state{}; state.lr=0x80004000; state.gpr[3]=5;
  expect(source.host_call && source.host_call(&state,0x80002000,source.host_call_user) &&
    state.gpr[3]==77 && state.pc==state.lr,"patch callback still executes through bound source");
  expect(source.host_call_contains && source.host_call_contains(0x80003000,source.host_call_user),
    "entry and return hook interception retained");
  manager.Unload();
  expect(Unbound(Configure(&manager,"1")),"new configuration after unload omits empty callbacks");
  auto events=dependent_descriptor;
  events.id="event_only"; events.dependencies=nullptr; events.num_dependencies=0;
  events.imports=nullptr; events.num_imports=0;
  events.callbacks=&dependent_callbacks[1]; events.num_callbacks=1;
  report=manager.Load({moderngekko::ModSource::AttachedDescriptor(&events,"events")},"TEST01");
  expect(bool(report)&&!manager.Empty()&&!manager.HasGuestInterception(),"actual event-only mod loaded");
  source=Configure(&manager,"1");
  expect(Bound(source,&manager),"event-only mod retains runtime-start callback bindings");
  int previous=runtime_callbacks;
  state.gpr[3]=123;
  expect(source.host_call && !source.host_call(&state,0x80005000,source.host_call_user) &&
    runtime_callbacks==previous+1 && state.gpr[3]==123,"runtime-start event executes and preserves guest state");
  report=manager.Load({moderngekko::ModSource::AttachedDescriptor(&missing_descriptor,"rejected")},"TEST01");
  expect(!report&&manager.Empty()&&Unbound(Configure(&manager,"1")),"rejected mods leave safe empty binding");
  _putenv_s("STATICRECOMP_POWERPROS_SKIP_EMPTY_MOD_HOOKS", "");
  std::printf("%s %u binding/integration cases; %u failures\n",failures?"FAIL":"PASS",cases,failures);
  return failures?1:0;
}
'''


def main():
    root=Path(__file__).resolve().parents[1]
    vendor=root/'local/vendor/ModernGekko'
    source=(vendor/'src/runtime/dolphin_runtime.cpp').read_text(encoding='utf-8')
    marker='// POWERPROS_EMPTY_MOD_HOOKS_BEGIN'
    start=source.index(marker) if marker in source else source.index('  recomp_source.host_call = &ModManager::HostCall;')
    binding=source[start:source.index('  jit.SetStaticRecompModuleSource',start)]
    tests=(vendor/'tests/mod_loader_test.cpp').read_text(encoding='utf-8')
    # The attached-descriptor path does not require hardware or a shared-library fixture.
    tests=tests[:tests.index('  const auto dynamic =')]+'  return 0;\n}\n'
    folder=root/'local/analysis'/('empty-mod-hooks-check-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    (folder/'binding.inc').write_text(binding,encoding='utf-8')
    (folder/'upstream-static-tests.inc').write_text(tests,encoding='utf-8')
    (folder/'check.cpp').write_text(HARNESS,encoding='utf-8')
    cmake=f'''cmake_minimum_required(VERSION 3.20)
project(EmptyModHooksCheck LANGUAGES CXX)
add_executable(binding_check check.cpp "{vendor.as_posix()}/src/runtime/mod_loader.cpp")
target_include_directories(binding_check PRIVATE "{vendor.as_posix()}/include" "{vendor.as_posix()}/vendor/dolphin/Source/Core" "{vendor.as_posix()}/vendor/dolphin/GXRuntime/include")
target_compile_features(binding_check PRIVATE cxx_std_23)
enable_testing()
add_test(NAME empty_mod_bindings_and_static_mod_behavior COMMAND binding_check)
'''
    (folder/'CMakeLists.txt').write_text(cmake,encoding='utf-8')
    with (folder/'build.log').open('w') as log:
        subprocess.run(['cmake','-S',str(folder),'-B',str(folder/'build'),'-G','Visual Studio 17 2022','-A','x64'],check=True,stdout=log,stderr=log)
        subprocess.run(['cmake','--build',str(folder/'build'),'--config','Release'],check=True,stdout=log,stderr=log)
    result=subprocess.run(['ctest','--test-dir',str(folder/'build'),'-C','Release','--output-on-failure'],text=True,capture_output=True)
    (folder/'result.json').write_text(json.dumps({'binding_sha256':hashlib.sha256(binding.encode()).hexdigest(),
        'actual_mod_loader_compiled':True,'exit_code':result.returncode,'output':result.stdout,
        'scope':'Actual frontend source binding fragment and actual static mod loader. Hardware startup and dynamic shared-library loading not exercised.'},indent=2)+'\n')
    print(result.stdout,folder)
    raise SystemExit(result.returncode)


if __name__=='__main__':
    main()
