# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile the actual loop alignment classifier; catch premature return-site stops."""
import datetime
import hashlib
import json
import subprocess
import struct
from pathlib import Path

HARNESS = r'''
#include <cstdint>
#include <cstdio>
#include <vector>
#include <fstream>
using u8=std::uint8_t; using u32=std::uint32_t; using s32=std::int32_t;
using s16=std::int16_t;
namespace Common { u32 swap32(const u8* p) {
  return u32(p[0])<<24 | u32(p[1])<<16 | u32(p[2])<<8 | p[3];
} }
#include "classifier.inc"
void word(std::vector<u8>& ram,u32 address,u32 instruction) {
  u32 i=address-0x80000000u;
  ram[i]=instruction>>24; ram[i+1]=instruction>>16;
  ram[i+2]=instruction>>8; ram[i+3]=instruction;
}
int main(int argc,char** argv) {
  unsigned failures=0,cases=0;
  auto expect=[&](const char* name,const std::vector<u8>& ram,u32 pc,bool wanted) {
    ++cases;
    if(LsIsLoopHeader(ram.data(),static_cast<u32>(ram.size()),pc)!=wanted) {
      ++failures; std::printf("FAIL %s: premature stop or false loop classification\n",name);
    }
  };
  std::vector<u8> ram(8192,0);
  // Return site inside loop: addi; cmpwi; blt to an earlier loop-body address.
  word(ram,0x80000008u,0x3bff0001u);
  word(ram,0x8000000cu,0x2c1f0010u);
  word(ram,0x80000010u,0x4180fff0u);
  expect("call return inside loop tail",ram,0x80000008u,true);
  // A direct call back to PC returns to its caller; it isn't a loop back-edge.
  ram.assign(8192,0); word(ram,0x80000004u,0x4bfffffdu);
  expect("backwards call is not a loop",ram,0x80000000u,false);
  ram.assign(8192,0); word(ram,0x80000008u,0x4180fff8u);
  expect("exact conditional header",ram,0x80000000u,true);
  ram.assign(8192,0); word(ram,0x80000008u,0x4bfffff8u);
  expect("exact unconditional header",ram,0x80000000u,true);
  ram.assign(8192,0); word(ram,0x80000004u,0x48000020u);
  expect("forward jump",ram,0x80000000u,false);
  // Don't borrow a loop from another function after a return.
  ram.assign(8192,0); word(ram,0x8000000cu,0x4e800020u);
  word(ram,0x80000010u,0x4180fff0u);
  expect("return bounds new tail inference",ram,0x80000008u,false);
  ram.assign(8192,0); word(ram,0x80000004u,0x41800010u);
  word(ram,0x80000008u,0x4180fff8u);
  expect("exact loop with conditional path",ram,0x80000000u,true);
  expect("out of MEM1",ram,0x7ffffffcu,false);
  expect("past snapshot",ram,0x80002000u,false);
  expect("unaligned PC",ram,0x80000001u,false);
  // Real instruction tails from the game's DOL, expectations derived by disassembly.
  ram.assign(8192,0);
  word(ram,0x80001000u,0x3bff0001u); // addi r31,r31,1
  word(ram,0x80001004u,0x2c1f0010u); // cmpwi r31,16
  word(ram,0x80001008u,0x4180fff0u); // blt 8 bytes before return site
  expect("80081CE0 loop return",ram,0x80001000u,true);
  ram.assign(8192,0);
  word(ram,0x80001800u,0x3b7b0070u);
  word(ram,0x80001804u,0x3b5a0001u);
  word(ram,0x80001808u,0x800d9620u);
  word(ram,0x8000180cu,0x7c1a0040u);
  word(ram,0x80001810u,0x4180e9ccu);
  expect("800C1188 loop return",ram,0x80001800u,true);
  // Real DOL windows include intervening inline callees and their returns.
  // Exact headers must retain their historical classification across that layout.
  if(argc!=2) return 2;
  ram.assign(24*1024*1024,0);
  std::ifstream file(argv[1],std::ios::binary);
  if(!file.read(reinterpret_cast<char*>(ram.data()),ram.size())) return 3;
  for(u32 pc : {0x800BC468u,0x80121E90u,0x800231B8u,0x8002FDA8u,
                 0x800BFB64u,0x800CE084u,0x801075F0u,0x80040C98u,
                 0x80081CE0u,0x800C1188u})
    expect("real DOL header/tail across inline functions",ram,pc,true);
  std::printf("%s %u actual classifier cases; %u failures\n",failures?"FAIL":"PASS",cases,failures);
  return failures?1:0;
}
'''


def main():
    root = Path(__file__).resolve().parents[1]
    path = root/'local/vendor/ModernGekko/vendor/dolphin/Source/Core/Core/PowerPC/StaticRecomp/StaticRecompLockstep_Check.cpp'
    source = path.read_text()
    helper = source[source.index('bool LsIsLoopHeader('):source.index('}  // namespace')]
    folder = root/'local/analysis'/('lockstep-alignment-check-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    (folder/'classifier.inc').write_text(helper)
    (folder/'check.cpp').write_text(HARNESS)
    (folder/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(AlignmentCheck LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 17)\nadd_executable(alignment_check check.cpp)\n')
    dol = (root/'local/disc/DATA/sys/main.dol').read_bytes()
    memory = bytearray(24*1024*1024)
    for index in range(18):
        offset, address, size = (struct.unpack_from('>I',dol,base+index*4)[0] for base in (0,0x48,0x90))
        if size:
            start = address-0x80000000
            if start < 0 or start+size > len(memory):
                raise ValueError('DOL section outside MEM1')
            memory[start:start+size] = dol[offset:offset+size]
    (folder/'dol-memory.bin').write_bytes(memory)
    with (folder/'build.log').open('w') as log:
        subprocess.run(['cmake','-S',str(folder),'-B',str(folder/'build'),'-G','Visual Studio 17 2022','-A','x64'],check=True,stdout=log,stderr=log)
        subprocess.run(['cmake','--build',str(folder/'build'),'--config','Release'],check=True,stdout=log,stderr=log)
    result = subprocess.run([str(folder/'build/Release/alignment_check.exe'),str(folder/'dol-memory.bin')],text=True,capture_output=True)
    (folder/'result.json').write_text(json.dumps({'helper_sha256':hashlib.sha256(helper.encode()).hexdigest(),
       'actual_helper_compiled':True,'exit_code':result.returncode,'output':result.stdout},indent=2)+'\n')
    print(result.stdout.strip(),folder)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
