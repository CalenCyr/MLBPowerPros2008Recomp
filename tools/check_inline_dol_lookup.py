# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare actual old/new Run lambdas with the real REL detector methods.

The reference is the preserved source from the sampled 27-patch executable.
Both fixed and dynamic REL builds use the linked MEM1 fixture. This is a
state-only check; game dispatch and hardware are checked separately.
"""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from check_rel_detector import HARNESS, method


CHECK = r'''
unsigned lookup_cases=0;
static void compare_lookup(const StaticRecompCore& seed) {
  auto before=seed, after=seed;
  std::vector<u32> addresses={0u,0xffffffffu,0x8000403Cu,0x8000403Du,
    0x80004040u,0x90000000u,0x9000000Fu,0x90000010u,0x81800000u};
  for (const auto& section:seed.m_active_rel_sections) {
    for (u32 pc:{section.runtime_start-1,section.runtime_start,
      section.runtime_start+1,section.runtime_start+section.size-1,
      section.runtime_start+section.size}) addresses.push_back(pc);
  }
  for (const auto& section:fixture_sections) {
    addresses.push_back(section.linked_start);
    addresses.push_back(section.linked_start+section.size);
  }
  u32 random=0x42389au;
  for (unsigned i=0;i<16;++i) {
    random=random*1664525u+1013904223u;
    addresses.push_back(random);
    addresses.push_back(0x80000000u+(random%0x1800000u));
  }
  for (bool has_rel:{false,true}) {
    before.m_has_rel_modules=after.m_has_rel_modules=has_rel;
    for (const auto address:addresses) {
      if (before.BeforeLookup(address)!=after.AfterLookup(address))
        throw std::runtime_error("old/new Run dispatch eligibility differs");
      if (before.m_chunk_state!=after.m_chunk_state ||
          before.m_effective_chunk_hashes!=after.m_effective_chunk_hashes ||
          before.m_failed_chunks!=after.m_failed_chunks ||
          before.m_rel_mapping_generation!=after.m_rel_mapping_generation ||
          before.m_rel_runtime_begin!=after.m_rel_runtime_begin ||
          before.m_rel_runtime_end!=after.m_rel_runtime_end ||
          before.m_active_rel_sections.size()!=after.m_active_rel_sections.size())
        throw std::runtime_error("lookup changed REL refresh or invalidation state");
      for (size_t i=0;i<before.m_active_rel_sections.size();++i) {
        const auto& a=before.m_active_rel_sections[i];
        const auto& b=after.m_active_rel_sections[i];
        if (a.module_id!=b.module_id || a.section_index!=b.section_index ||
            a.linked_start!=b.linked_start || a.runtime_start!=b.runtime_start || a.size!=b.size)
          throw std::runtime_error("lookup changed REL section mapping");
      }
      ++lookup_cases;
    }
  }
}
'''


def lambda_method(source, name):
    start = source.index('  const auto fast_dispatchable_at = [this](u32 address)')
    end = source.index('\n  };', start) + len('\n  };')
    fragment = source[start:end]
    body = fragment[fragment.index('{'):].removesuffix(';')
    return f'bool StaticRecompCore::{name}(u32 address) {body}\n'


def main():
    root = Path(__file__).resolve().parents[1]
    source = root/'local/vendor/ModernGekko/vendor/dolphin/Source/Core/Core/PowerPC/StaticRecomp'
    old = (root/'local/analysis/host-sample-20261009-164527-499/preserved/StaticRecompCore_Run-before.cpp').read_text(encoding='utf-8')
    if hashlib.sha256(old.encode()).hexdigest() != 'ad17d069aeb1804b53ef59e2f6411e662ce7cb7a196333ef7f50e2bb117efe87':
        raise ValueError('Unexpected reference Run source; require the preserved 27-patch revision')
    # The measured candidate was withdrawn from the active runtime because its
    # speed results were inconsistent; test its frozen source without reapplying it.
    new = (root/'local/analysis/inline-dol-lookup-candidate/StaticRecompCore_Run.cpp').read_text(encoding='utf-8')
    smc = (source/'StaticRecompCore_SMC.cpp').read_text(encoding='utf-8')
    extracted = method((source/'StaticRecompCore.cpp').read_text(encoding='utf-8'), 'bool RelModulesValid(')
    for signature in ('void StaticRecompCore::RefreshRelSections()', 'bool StaticRecompCore::ResolveNativeAddress(',
                      'int StaticRecompCore::GetAddressLookupIndex(', 'int StaticRecompCore::ChunkIndexOf(',
                      'bool StaticRecompCore::FastDispatchableAt(', 'bool StaticRecompCore::IsForcedFallbackAddress(',
                      'bool StaticRecompCore::ResolveRuntimeAddress(', 'u32 StaticRecompCore::TranslateRelAddress('):
        extracted += '\n'+method(smc, signature)
    extracted += lambda_method(old, 'BeforeLookup')+lambda_method(new, 'AfterLookup')
    harness = HARNESS.replace('  bool m_module_active = true;', '  bool m_module_active = true;\n  bool m_has_rel_modules = true;\n  bool BeforeLookup(u32);\n  bool AfterLookup(u32);')
    harness = harness.replace('int main(int argc, char** argv)', CHECK+'\nint main(int argc, char** argv)')
    # Insert the differential check after state changes already covered by the
    # detector fixture, including cold maps, SMC demotion, forced ranges,
    # inactive modules, overlapping DOL tags, unload/reload and empty tables.
    anchors = ['    require(native.ChunkIndexOf(0x8000403Cu)==0',
               '    native.m_chunk_state[1]=StaticRecompCore::CHUNK_VERIFIED;',
               '      require(!native.FastDispatchableAt(0x8000403Cu)',
               '    require(!native.FastDispatchableAt(0x8000403Cu) && native.FastDispatchableAt(0x80004040u)',
               '    require(native.ChunkIndexOf(0x8000403Cu)==-1 && !native.FastDispatchableAt(expected.front())',
               '#ifdef STATICRECOMP_REQUIRE_FIXED_REL_LAYOUT\n    require(native.ChunkIndexOf(expected.front())==0',
               '    require(native.ChunkIndexOf(expected.front())==1 && !native.FastDispatchableAt(expected.front())',
               '    require(native.ChunkIndexOf(0x8000403Cu)==-1, "empty chunk lookup accepted");']
    for anchor in anchors:
        assert anchor in harness, anchor
        harness = harness.replace(anchor, '    compare_lookup(native);\n'+anchor)
    harness = harness.replace('  std::cout << "ALL CHECKS PASSED\\n";', '  std::cout << "PASS " << lookup_cases << " old/new Run lambda eligibility and REL state comparisons\\n";\n  std::cout << "ALL CHECKS PASSED\\n";')
    folder = root/'local/analysis'/('inline-dol-lookup-check-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    reports=[]
    for fixed in (False, True):
        fixture = root/('local/build/rel-detector-checks'+('-fixed' if fixed else ''))
        build = folder/('fixed' if fixed else 'dynamic'); build.mkdir()
        (build/'check.cpp').write_text(harness,encoding='utf-8')
        (build/'detector_methods.inc').write_text(extracted,encoding='utf-8')
        (build/'detector_fixture.inc').write_bytes((fixture/'detector_fixture.inc').read_bytes())
        cmake = 'cmake_minimum_required(VERSION 3.20)\nproject(InlineDolLookupCheck LANGUAGES CXX)\nadd_executable(lookup_check check.cpp)\ntarget_compile_features(lookup_check PRIVATE cxx_std_17)\n'
        if fixed:
            cmake += 'target_compile_definitions(lookup_check PRIVATE STATICRECOMP_REQUIRE_FIXED_REL_LAYOUT=1 STATICRECOMP_FIXED_REL_HEADER=0x80575580u)\n'
        (build/'CMakeLists.txt').write_text(cmake)
        with (build/'build.log').open('w',encoding='utf-8') as log:
            subprocess.run(['cmake','-S',str(build),'-B',str(build/'build'),'-G','Visual Studio 17 2022','-A','x64'],check=True,stdout=log,stderr=log)
            subprocess.run(['cmake','--build',str(build/'build'),'--config','Release'],check=True,stdout=log,stderr=log)
        result=subprocess.run([str(build/'build/Release/lookup_check.exe'),str(fixture/'mem1.bin')],text=True,capture_output=True)
        (build/'checks.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        reports.append({'fixed_layout':fixed,'exit_code':result.returncode,'checks':result.stdout.splitlines(),'errors':result.stderr})
        print(result.stdout[-600:],result.stderr)
    evidence={'old_run_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_run_sha256':hashlib.sha256(new.encode()).hexdigest(),
              'extracted_methods_sha256':hashlib.sha256(extracted.encode()).hexdigest(),'checks':reports,
              'scope':'Actual old/new Run lambdas and current SMC/REL methods; state-only fixture, separate from full runtime/game validation.'}
    (folder/'result.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(folder)
    raise SystemExit(int(any(r['exit_code'] for r in reports)))


if __name__=='__main__':
    main()
