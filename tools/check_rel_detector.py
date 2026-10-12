# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile the actual upstream REL detector with a small state-only test fixture.

No detector algorithm is reimplemented here. The method and address conversion
are extracted from the pinned source; this isolated check does not dispatch game
code and is separate from compiling the full runtime.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path


def method(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


HARNESS = r'''
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>
using u8 = uint8_t;
using u32 = uint32_t;
using u64 = uint64_t;
struct StaticRecompRelSection { u32 module_id, section_index, linked_start, size; };
struct StaticRecompRelModule {
  u32 module_id, version, section_count, section_info_offset, file_size;
  const StaticRecompRelSection* sections;
  u32 num_sections;
};
struct Module {
  const StaticRecompRelModule* rel_modules;
  u32 num_rel_modules;
  const u64* chunk_hashes;
  const struct StaticRecompRange* code_ranges = nullptr;
  u32 num_code_ranges = 0;
};
struct StaticRecompRange { u32 start, end; };
using StaticRecompModuleDesc = Module;
class StaticRecompCore {
public:
  struct ActiveRelSection { u32 module_id, section_index, linked_start, runtime_start, size; };
  struct Guest { u8* ram; u32 ram_size; } m_guest{};
  const Module* m_module = nullptr;
  std::vector<ActiveRelSection> m_active_rel_sections;
  std::vector<ActiveRelSection> m_rel_discovered_scratch;
  std::vector<ActiveRelSection> m_rel_candidate_scratch;
  std::vector<u8> m_rel_window_scratch;
  std::vector<u8> m_rel_window_last;
  bool m_rel_window_valid = false;
  u32 m_rel_runtime_begin = 0;
  u64 m_rel_runtime_end = 0;
  u32 m_lookup_ram_size = 0;
  u32 m_lookup_exram_size = 0;
  std::vector<int> m_chunk_lookup_table;
  bool m_module_active = true;
  std::vector<StaticRecompRange> m_forced_fallback_ranges;
  std::vector<int> m_chunk_rel_sections;
  std::vector<u8> m_chunk_state;
  std::vector<u64> m_effective_chunk_hashes;
  u64 m_rel_mapping_generation = 0;
  u32 m_failed_chunks = 0;
  enum { CHUNK_UNVERIFIED, CHUNK_VERIFIED, CHUNK_FAILED };
  void RefreshRelSections();
  bool ResolveNativeAddress(u32, u32*, u32*);
  int GetAddressLookupIndex(u32) const;
  int ChunkIndexOf(u32);
  bool FastDispatchableAt(u32);
  bool IsForcedFallbackAddress(u32) const;
  bool ResolveRuntimeAddress(u32, u32*) const;
  u32 TranslateRelAddress(u32);
};
static u32 ReadGuestBE32(const u8* bytes) {
  return (u32(bytes[0]) << 24) | (u32(bytes[1]) << 16) | (u32(bytes[2]) << 8) | bytes[3];
}
#include "detector_methods.inc"
#include "detector_fixture.inc"
static void put(std::vector<u8>& ram, size_t at, u32 value) {
  if (at + 4 > ram.size()) throw std::runtime_error("fixture write outside RAM");
  for (int i=0;i<4;++i) ram[at+i] = u8(value >> (24-i*8));
}
static void require(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}
static StaticRecompCore inspect(std::vector<u8>& ram, const Module& module) {
  StaticRecompCore core;
  core.m_guest = {ram.data(), u32(ram.size())}; core.m_module = &module;
  core.RefreshRelSections();
  return core;
}
int main(int argc, char** argv) {
 try {
  require(argc == 2, "MEM1 path required");
  std::ifstream file(argv[1], std::ios::binary);
  require(bool(file), "MEM1 could not be read");
  std::vector<u8> actual((std::istreambuf_iterator<char>(file)), {});
  require(actual.size() == 24*1024*1024, "MEM1 size mismatch");
  const u64 hashes[] = {0x123456789u, 0x23456789au};
  StaticRecompRelModule rel = fixture_module;
  Module module{&rel,1,hashes};
  const StaticRecompRange code_range[] = {{rel.sections[0].linked_start,rel.sections[0].linked_start+rel.sections[0].size}};
  module.code_ranges=code_range;module.num_code_ranges=1;
  require(RelModulesValid(module),"complete code/data/BSS metadata rejected");
  {
    std::vector<StaticRecompRelSection> altered(rel.sections,rel.sections+rel.num_sections);
    rel.sections=altered.data();altered.back().section_index=altered.front().section_index;
    require(!RelModulesValid(module),"duplicate section metadata accepted");
    altered.back()=fixture_sections[rel.num_sections-1];
    altered.back().linked_start=altered.front().linked_start+4;
    require(!RelModulesValid(module),"overlapping section metadata accepted");
    rel=fixture_module;module.num_code_ranges=0;
    require(!RelModulesValid(module),"REL metadata with no executable section accepted");
    module.num_code_ranges=1;
  }
  std::cout << "PASS code/data/BSS metadata; duplicate, overlapping and non-executable maps rejected\n";
  auto core = inspect(actual,module);
  require(core.m_active_rel_sections.size() == expected.size(), "linked snapshot not detected");
  for (size_t i=0;i<expected.size();++i) {
    const auto& section = core.m_active_rel_sections[i];
    require(section.runtime_start == expected[i], "snapshot section address mismatch");
    u32 address=0;
    require(core.ResolveRuntimeAddress(section.linked_start,&address) && address == expected[i], "section-start mapping failed");
    require(core.ResolveRuntimeAddress(section.linked_start+section.size-1,&address) && address == expected[i]+section.size-1, "section-end mapping failed");
    require(core.TranslateRelAddress(section.linked_start) == expected[i], "translation wrapper failed");
  }
  // Check gaps and both sides of each section against the fixture mapping.
  std::vector<u32> boundaries = {0u, 0x8000403Cu, 0x90000000u, 0xffffffffu};
  for (const auto& section : core.m_active_rel_sections) {
    boundaries.push_back(section.linked_start-1);
    boundaries.push_back(section.linked_start);
    boundaries.push_back(section.linked_start+section.size-1);
    boundaries.push_back(section.linked_start+section.size);
  }
  for (const u32 linked : boundaries) {
    u32 reference=linked;
    for (const auto& section : core.m_active_rel_sections) {
      if (linked >= section.linked_start && u64(linked) < u64(section.linked_start)+section.size) {
        reference=section.runtime_start+(linked-section.linked_start);
        break;
      }
    }
    require(core.TranslateRelAddress(linked)==reference, "boundary or gap mapping changed");
  }
  std::cout << "PASS translation wrapper, section boundaries, gaps, DOL/MEM2 and integer extremes\n";
  std::cout << "PASS real linked MEM1: " << expected.size() << " sections, including BSS\n";
  {
    auto native=core;
    native.m_lookup_ram_size=u32(actual.size());
    native.m_lookup_exram_size=16;
    native.m_chunk_lookup_table.assign((native.m_lookup_ram_size+native.m_lookup_exram_size)/4,-1);
    native.m_chunk_rel_sections={-1,0};
    native.m_chunk_state={1,1};
    native.m_effective_chunk_hashes={hashes[0],hashes[1]};
    native.m_chunk_lookup_table[native.GetAddressLookupIndex(0x8000403Cu)]=0;
    native.m_chunk_lookup_table[native.GetAddressLookupIndex(0x90000000u)]=0;
    native.m_chunk_lookup_table[native.GetAddressLookupIndex(rel.sections[0].linked_start)]=1;
    u32 linked=0, index=0;
    require(native.ResolveNativeAddress(0x8000403Cu,&linked,&index) && linked==0x8000403Cu && index==0xffffffffu, "DOL direct mapping changed");
    require(native.ResolveNativeAddress(0x90000000u,&linked,nullptr) && linked==0x90000000u, "MEM2 direct mapping changed");
    for (u32 i=0;i<native.m_active_rel_sections.size();++i) {
      const auto& section=native.m_active_rel_sections[i];
      for (const u32 runtime : {section.runtime_start,section.runtime_start+section.size-1}) {
        require(native.ResolveNativeAddress(runtime,&linked,&index) && index==i &&
                linked==section.linked_start+(runtime-section.runtime_start), "REL native mapping or section index changed");
        require(native.ResolveNativeAddress(runtime,&linked,nullptr), "optional section index changed");
      }
    }
    // Check rejection outside the envelope and in every actual gap.
    std::vector<u32> misses={0u,0x80000000u,0xffffffffu,0x90000010u};
    for (const auto& section:native.m_active_rel_sections) {
      for (const u32 candidate : {section.runtime_start-1,section.runtime_start+section.size}) {
        bool inside=false;
        for (const auto& other:native.m_active_rel_sections)
          inside |= candidate>=other.runtime_start && u64(candidate)<u64(other.runtime_start)+other.size;
        if (!inside) misses.push_back(candidate);
      }
    }
    for (const u32 runtime:misses) {
      linked=0x12345678u; index=0x87654321u;
      require(!native.ResolveNativeAddress(runtime,&linked,&index) && linked==0x12345678u && index==0x87654321u, "unmapped native address accepted or outputs changed");
    }
    // No active map: rediscover before accepting a REL address; a lookup entry
    // for REL code must never suffice on its own.
    native.m_active_rel_sections.clear(); native.m_rel_runtime_begin=0; native.m_rel_runtime_end=0;
    require(native.ResolveNativeAddress(expected.front(),&linked,&index) && index==0 && native.m_active_rel_sections.size()==expected.size(), "cold-map refresh did not resolve REL");
    std::cout << "PASS native lookup: DOL/MEM2, REL boundaries and indices, gaps, rejected outputs and cold refresh\n";
    require(native.ChunkIndexOf(0x8000403Cu)==0 && native.ChunkIndexOf(0x90000000u)==0 &&
            native.ChunkIndexOf(expected.front())==1 && native.ChunkIndexOf(expected.front()+1)==1,
            "DOL/MEM2/REL chunk index or existing unaligned lookup changed");
    require(!native.FastDispatchableAt(expected.front()), "unverified REL chunk dispatched after refresh");
    native.m_chunk_state[1]=StaticRecompCore::CHUNK_VERIFIED;
    require(native.FastDispatchableAt(expected.front()), "verified REL chunk rejected");
    for (const u8 state:{u8(StaticRecompCore::CHUNK_UNVERIFIED),u8(StaticRecompCore::CHUNK_FAILED)}) {
      native.m_chunk_state[0]=state; native.m_chunk_state[1]=state;
      require(!native.FastDispatchableAt(0x8000403Cu) && !native.FastDispatchableAt(expected.front()),
              "unverified or failed chunk bypassed guard");
    }
    native.m_chunk_state={StaticRecompCore::CHUNK_VERIFIED,StaticRecompCore::CHUNK_VERIFIED};
    native.m_chunk_lookup_table[native.GetAddressLookupIndex(0x80004040u)]=0;
    native.m_forced_fallback_ranges={{0x8000403Cu,0x80004040u}};
    require(!native.FastDispatchableAt(0x8000403Cu) && native.FastDispatchableAt(0x80004040u),
            "forced fallback range or exclusive end changed");
    native.m_forced_fallback_ranges.clear();
    native.m_module_active=false;
    require(native.ChunkIndexOf(0x8000403Cu)==-1 && !native.FastDispatchableAt(expected.front()),
            "inactive module dispatched");
    native.m_module_active=true;
    // A DOL-tagged lookup overlapping an active REL still resolves through
    // the REL in dynamic mode. Fixed mode keeps the same identity address.
    const int runtime_idx=native.GetAddressLookupIndex(expected.front());
    const int previous=native.m_chunk_lookup_table[runtime_idx];
    native.m_chunk_lookup_table[runtime_idx]=0;
#ifdef STATICRECOMP_REQUIRE_FIXED_REL_LAYOUT
    require(native.ChunkIndexOf(expected.front())==0, "fixed overlap chunk changed");
#else
    require(native.ChunkIndexOf(expected.front())==1, "dynamic REL precedence bypassed by DOL tag");
#endif
    native.m_chunk_lookup_table[runtime_idx]=previous;
    put(actual,fixture_header+0x10,0xDEADBEEF);
    native.RefreshRelSections();
    native.m_chunk_state[1]=StaticRecompCore::CHUNK_VERIFIED;
    require(native.ChunkIndexOf(expected.front())==-1 && !native.FastDispatchableAt(expected.front()),
            "REL lookup entry alone allowed unloaded code");
    require(native.FastDispatchableAt(0x8000403Cu), "DOL depends on REL being loaded");
    put(actual,fixture_header+0x10,0x80000000u+fixture_header+rel.section_info_offset);
    require(native.ChunkIndexOf(expected.front())==1 && !native.FastDispatchableAt(expected.front()),
            "REL reload failed to demote verification state");
    for (const u32 runtime:misses)
      require(native.ChunkIndexOf(runtime)==-1, "unmapped chunk accepted");
    native.m_chunk_lookup_table.clear();
    require(native.ChunkIndexOf(0x8000403Cu)==-1, "empty chunk lookup accepted");
    std::cout << "PASS chunk lookup and dispatch guards: inactive, empty, unverified, failed, forced fallback, dynamic precedence, REL unload/reload\n";
  }
  const auto generation = core.m_rel_mapping_generation;
  core.RefreshRelSections();
  require(core.m_rel_mapping_generation == generation, "stable map unnecessarily invalidated");
  core.m_chunk_rel_sections={0,-1}; core.m_chunk_state={2,1};
  core.m_effective_chunk_hashes={0,0}; core.m_failed_chunks=1;
  put(actual,fixture_header+0x10,0xDEADBEEF);
  core.RefreshRelSections();
  require(core.m_active_rel_sections.empty(), "invalidated map remained active");
  u32 unloaded=0, unloaded_index=0;
  require(!core.ResolveNativeAddress(expected.front(),&unloaded,&unloaded_index), "unloaded REL address accepted");
  for (const u32 linked : boundaries)
    require(core.TranslateRelAddress(linked)==linked, "unloaded mapping is not identity");
  require(core.m_rel_mapping_generation == generation+1, "map removal generation missing");
  require(core.m_failed_chunks == 0 && core.m_chunk_state[0] == 0 && core.m_chunk_state[1] == 1 && core.m_effective_chunk_hashes[0] == hashes[0], "REL demotion reset damaged state");
  std::cout << "PASS stable mapping and REL-only cache invalidation\n";
  put(actual,fixture_header+0x10,0x80000000u+fixture_header+rel.section_info_offset);
  require(core.ResolveNativeAddress(expected.front(),&unloaded,&unloaded_index) &&
          unloaded==rel.sections[0].linked_start && unloaded_index==0 &&
          core.m_rel_mapping_generation==generation+2, "REL reload did not rebuild native mapping");
  std::cout << "PASS unload rejection and reload discovery\n";
  std::vector<u8> blank(actual.size(),0);
  auto synthetic = [&]() {
    auto ram=blank;
    put(ram,fixture_header,rel.module_id);
    put(ram,fixture_header+0x0C,rel.section_count);
    put(ram,fixture_header+0x10,0x80000000u+fixture_header+rel.section_info_offset);
    put(ram,fixture_header+0x1C,rel.version);
    for (u32 i=0;i<rel.num_sections;++i) {
      size_t entry=fixture_header+rel.section_info_offset+rel.sections[i].section_index*8;
      put(ram,entry,expected[i]); put(ram,entry+4,rel.sections[i].size);
    }
    return ram;
  };
  auto rejected = [&](std::vector<u8>& ram, const char* name) {
    require(inspect(ram,module).m_active_rel_sections.empty(),name);
    std::cout << "PASS rejection: " << name << '\n';
  };
  const size_t first=fixture_header+rel.section_info_offset+rel.sections[0].section_index*8;
  const size_t bss=fixture_header+rel.section_info_offset+rel.sections[rel.num_sections-1].section_index*8;
  auto ram=synthetic();
  put(ram,fixture_header+0x10,0x80000004u+fixture_header+rel.section_info_offset);
  rejected(ram,"foreign section-table pointer");
  ram=synthetic(); put(ram,first+4,rel.sections[0].size+4);
  rejected(ram,"wrong section size");
  ram=synthetic(); put(ram,bss,0);
  rejected(ram,"unallocated BSS");
  ram=synthetic(); put(ram,first,0xD5);
  rejected(ram,"file offset in linked table");
  ram=synthetic(); put(ram,first,0x817FFFFD);
  rejected(ram,"section outside MEM1");
  ram=synthetic(); put(ram,fixture_header+0x1C,rel.version+1);
  rejected(ram,"wrong REL version");
  ram=synthetic(); put(ram,fixture_header+0x0C,rel.section_count+1);
  rejected(ram,"wrong section count");
  // Original table offsets remain supported before OSLink updates the header.
  ram=synthetic(); put(ram,fixture_header+0x10,rel.section_info_offset);
  put(ram,first,0xD5);
  auto relative=inspect(ram,module);
#ifdef STATICRECOMP_REQUIRE_FIXED_REL_LAYOUT
  require(relative.m_active_rel_sections.empty(), "unlinked table accepted by fixed layout");
  std::cout << "PASS fixed-layout rejection of unlinked table\n";
  ram=synthetic(); put(ram,bss,expected.back()+4);
  rejected(ram,"moved BSS with fixed layout");
  ram=synthetic(); put(ram,first,expected.front()+4);
  rejected(ram,"moved code with fixed layout");
#else
  require(relative.m_active_rel_sections.size() == expected.size() && relative.m_active_rel_sections[0].runtime_start == 0x80000000u+fixture_header+0xD4, "relative table no longer supported");
  std::cout << "PASS relative table and executable flag\n";
  // Refresh an existing map, moving both ends beyond the previous envelope.
  ram=synthetic();
  auto moved=inspect(ram,module);
  put(ram,first,expected.front()-0x1000u);
  put(ram,bss,expected.back()+0x10000u);
  moved.RefreshRelSections();
  u32 moved_linked=0, moved_index=0;
  require(moved.ResolveNativeAddress(expected.front()-0x1000u,&moved_linked,&moved_index) &&
          moved_linked==rel.sections[0].linked_start && moved_index==0, "moved lower bound was stale");
  const auto& last=rel.sections[rel.num_sections-1];
  require(moved.ResolveNativeAddress(expected.back()+0x10000u+last.size-1,&moved_linked,&moved_index) &&
          moved_linked==last.linked_start+last.size-1 && moved_index==rel.num_sections-1, "moved upper bound was stale");
  // Preserve the existing first-section precedence for overlapping runtime maps.
  ram=synthetic(); put(ram,first,expected[1]);
  auto overlap=inspect(ram,module);
  require(overlap.ResolveNativeAddress(expected[1],&moved_linked,&moved_index) &&
          moved_linked==rel.sections[0].linked_start && moved_index==0, "runtime overlap precedence changed");
  std::cout << "PASS moved lower/upper bounds and overlapping-runtime precedence\n";
#endif
  // Validate metadata bounds before indexing a table, even for a matching header.
  std::vector<StaticRecompRelSection> bad(fixture_sections,fixture_sections+rel.num_sections);
  bad[0].section_index=rel.section_count; rel.sections=bad.data();
  ram=synthetic(); rejected(ram,"out-of-range section metadata");
  rel=fixture_module; rel.num_sections=0;
  ram=synthetic(); rejected(ram,"empty section metadata");
  rel=fixture_module;
  std::vector<u8> short_ram(0x40,0);
  rejected(short_ram,"truncated section table");
  std::cout << "ALL CHECKS PASSED\n";
  return 0;
 } catch (const std::exception& error) {
  std::cerr << "FAIL: " << error.what() << '\n';
  return 1;
 }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_directory', type=Path)
    parser.add_argument('--cmake', default='cmake')
    parser.add_argument('--baseline', action='store_true', help='Run the same fixture against the pinned, unpatched method; failure is expected')
    parser.add_argument('--fixed-layout', action='store_true', help='Require the observed six section addresses and fixed header')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.baseline and args.fixed_layout:
        parser.error('baseline and fixed-layout are separate checks')
    suffix = '-baseline' if args.baseline else ('-fixed' if args.fixed_layout else '')
    build = root / ('local/build/rel-detector-checks' + suffix)
    build.mkdir(parents=True, exist_ok=True)
    source = root / 'local/vendor/ModernGekko/vendor/dolphin/Source/Core/Core/PowerPC/StaticRecomp/StaticRecompCore_SMC.cpp'
    text = source.read_text(encoding='utf-8')
    if args.baseline:
        vendor = root / 'local/vendor/ModernGekko/vendor/dolphin'
        text = subprocess.check_output(['git', '-C', str(vendor), 'show', 'HEAD:Source/Core/Core/PowerPC/StaticRecomp/StaticRecompCore_SMC.cpp'], text=True)
    extracted = '\n\n'.join(method(text, signature) for signature in (
        'void StaticRecompCore::RefreshRelSections()',
        'bool StaticRecompCore::ResolveNativeAddress(',
        'int StaticRecompCore::GetAddressLookupIndex(',
        'int StaticRecompCore::ChunkIndexOf(',
        'bool StaticRecompCore::FastDispatchableAt(',
        'bool StaticRecompCore::IsForcedFallbackAddress(',
        'bool StaticRecompCore::ResolveRuntimeAddress(',
        'u32 StaticRecompCore::TranslateRelAddress('))
    validation_source = source.with_name('StaticRecompCore.cpp').read_text(encoding='utf-8')
    extracted = method(validation_source,'bool RelModulesValid(') + '\n\n' + extracted
    (build / 'detector_methods.inc').write_text(extracted, encoding='utf-8')
    original = (root / 'local/disc/DATA/files/ovl_main.rel').read_bytes()
    if hashlib.sha256(original).hexdigest() != 'dcc37a1a4824702feff5bcaa6aae7cefdedfc3b5d832fbf3de92b982a59b4edc':
        raise ValueError('Unexpected game REL revision')
    be = lambda offset: struct.unpack_from('>I', original, offset)[0]
    report = json.loads((args.probe_directory / 'rel-memory-report.json').read_text())
    matches = [c for c in report['candidates'] if c['state'] == 'absolute_section_addresses']
    if len(matches) != 1:
        raise ValueError('Expected one linked REL candidate')
    candidate = matches[0]
    fixture = ['static const StaticRecompRelSection fixture_sections[] = {']
    # The linked test layout preserves file offsets; BSS gets a distinct range.
    for section in candidate['sections']:
        offset = be(be(0x10) + section['index'] * 8) & ~1
        linked = 0x80500000 + (offset if offset else (len(original)+31) & ~31)
        if args.fixed_layout:
            linked = int(section['inferred_runtime_start'],16)
        fixture.append(f"  {{1u,{section['index']}u,0x{linked:08X}u,{section['size']}u}},")
    fixture.append('};')
    fixture.append('static const StaticRecompRelModule fixture_module = {' +
                   f'{be(0)}u,{be(0x1C)}u,{be(0x0C)}u,{be(0x10)}u,{len(original)}u,fixture_sections,{len(candidate["sections"])}u' + '};')
    fixture.append(f'static const u32 fixture_header = {int(candidate["header_address"],16)-0x80000000}u;')
    fixture.append('static const std::vector<u32> expected = {' + ','.join(s['inferred_runtime_start']+'u' for s in candidate['sections']) + '};')
    (build / 'detector_fixture.inc').write_text('\n'.join(fixture)+'\n', encoding='utf-8')
    (build / 'check.cpp').write_text(HARNESS, encoding='utf-8')
    cmake_text = 'cmake_minimum_required(VERSION 3.20)\nproject(RelDetectorChecks LANGUAGES CXX)\nadd_executable(rel_detector_check check.cpp)\ntarget_compile_features(rel_detector_check PRIVATE cxx_std_17)\n'
    if args.fixed_layout:
        cmake_text += 'target_compile_definitions(rel_detector_check PRIVATE STATICRECOMP_REQUIRE_FIXED_REL_LAYOUT=1 STATICRECOMP_FIXED_REL_HEADER='+candidate['header_address']+'u)\n'
    (build / 'CMakeLists.txt').write_text(cmake_text, encoding='utf-8')
    artifacts = args.probe_directory / 'control/artifacts'
    memory = (artifacts / 'mem1-low.bin').read_bytes() + (artifacts / 'mem1-high.bin').read_bytes()
    if len(memory) != 24*1024*1024:
        raise ValueError('Snapshot must cover all MEM1')
    memory_path = build / 'mem1.bin'
    memory_path.write_bytes(memory)
    log = root / ('local/analysis/rel-detector-checks' + suffix + '.log')
    with log.open('w', encoding='utf-8') as output:
        subprocess.run([args.cmake, '-S', str(build), '-B', str(build / 'cmake'), '-G', 'Visual Studio 17 2022', '-A', 'x64'], stdout=output, stderr=subprocess.STDOUT, check=True)
        subprocess.run([args.cmake, '--build', str(build / 'cmake'), '--config', 'Release'], stdout=output, stderr=subprocess.STDOUT, check=True)
        result = subprocess.run([str(build / 'cmake/Release/rel_detector_check.exe'), str(memory_path)], text=True, capture_output=True)
        output.write(result.stdout + result.stderr)
    evidence = {'source_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'baseline': args.baseline,
                'fixed_layout': args.fixed_layout,
                'extracted_methods_sha256': hashlib.sha256(extracted.encode()).hexdigest(),
                'snapshot_mem1_sha256': hashlib.sha256(memory).hexdigest(),
                'probe': str(args.probe_directory), 'exit_code': result.returncode,
                'checks': result.stdout.splitlines(), 'errors': result.stderr,
                'scope': 'Actual C++ detector and bidirectional address resolution with a state-only fixture; no native REL dispatch, full-core initialization test or relocation validation.'}
    (root / ('local/analysis/rel-detector-checks' + suffix + '.json')).write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
    print(result.stdout, end='')
    if result.returncode:
        raise RuntimeError(result.stderr)


if __name__ == '__main__':
    main()
