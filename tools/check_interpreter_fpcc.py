# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the actual float-compare helpers with Dolphin's actual FPSCR bitfields."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

HARNESS = r'''
#include <cmath>
#include <cstring>
#include <cstdio>
#include <initializer_list>
#include "Core/PowerPC/Gekko.h"
enum class FPCC { FL=8, FG=4, FE=2, FU=1 };
namespace PowerPC {
struct CR { u32 fields[8]{}; void SetField(u32 i,u32 v) { fields[i]=v; } };
struct PowerPCState { UReg_FPSCR fpscr; CR cr; };
}
namespace Common {
bool IsSNAN(double value) {
  u64 bits; std::memcpy(&bits,&value,8);
  return (bits & 0x7ff0000000000000ULL)==0x7ff0000000000000ULL &&
    (bits & 0xfffffffffffffULL) && !(bits & 0x8000000000000ULL);
}
}
void SetFPException(PowerPC::PowerPCState& p,u32 flag) { p.fpscr.Hex |= flag; }
class Interpreter { public:
static void Helper_FloatCompareOrdered(PowerPC::PowerPCState&,UGeckoInstruction,double,double);
static void Helper_FloatCompareUnordered(PowerPC::PowerPCState&,UGeckoInstruction,double,double);
};
#include "helpers.inc"
int main() {
  const double pairs[][2]={{1,2},{2,1},{1,1},{0,-0.0}};
  u32 cases=0;
  for (u32 initial=0; initial<32; ++initial)
    for (u32 field=0; field<8; ++field)
      for (bool ordered : {false,true})
        for (const auto& pair : pairs) {
          PowerPC::PowerPCState p;
          // Other fields, including sticky exception and rounding bits, must survive.
          const u32 before=0x82000003u | (initial<<12);
          p.fpscr.Hex=before;
          for (u32 i=0;i<8;++i) p.cr.fields[i]=0xf;
          UGeckoInstruction instruction{}; instruction.CRFD=field;
          if (ordered) Interpreter::Helper_FloatCompareOrdered(p,instruction,pair[0],pair[1]);
          else Interpreter::Helper_FloatCompareUnordered(p,instruction,pair[0],pair[1]);
          const u32 comparison=pair[0]<pair[1]?8:pair[0]>pair[1]?4:2;
          if (p.fpscr.Hex != ((before & ~0xf000u)|(comparison<<12))) return 1;
          for (u32 i=0;i<8;++i) if(p.cr.fields[i] != (i==field?comparison:0xf)) return 2;
          ++cases;
        }
  std::printf("PASS %u actual FPCC helper cases, class/exception/rounding preservation and all CR fields\n",cases);
}
'''


def main():
    root = Path(__file__).resolve().parents[1]
    chassis = root/'local/vendor/ModernGekko/vendor/dolphin'
    path = chassis/'Source/Core/Core/PowerPC/Interpreter/Interpreter_FloatCompare.cpp'
    source = path.read_text()
    helper = source[source.index('void Interpreter::Helper_FloatCompareOrdered'):source.index('void Interpreter::fcmpo(')]
    folder = root/'local/analysis'/('interpreter-fpcc-check-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir()
    (folder/'helpers.inc').write_text(helper)
    (folder/'check.cpp').write_text(HARNESS)
    include = (chassis/'Source/Core').as_posix()
    fmt_include = (chassis/'Externals/fmt/fmt/include').as_posix()
    (folder/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(FpccCheck LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 23)\nadd_executable(fpcc_check check.cpp)\ntarget_compile_options(fpcc_check PRIVATE /utf-8)\ntarget_include_directories(fpcc_check PRIVATE "'+include+'" "'+fmt_include+'")\n')
    with (folder/'build.log').open('w') as log:
        subprocess.run(['cmake', '-S', str(folder), '-B', str(folder/'build'), '-G', 'Visual Studio 17 2022', '-A', 'x64'], check=True, stdout=log, stderr=log)
        subprocess.run(['cmake', '--build', str(folder/'build'), '--config', 'Release'], check=True, stdout=log, stderr=log)
    output = subprocess.check_output([str(folder/'build/Release/fpcc_check.exe')], text=True)
    (folder/'result.json').write_text(json.dumps({'helper_sha256': hashlib.sha256(helper.encode()).hexdigest(),
        'actual_helpers_and_fpscr_bitfields_compiled': True, 'finite_compare_cases': 2048,
        'scope': 'Normal comparisons, all old FPRF values and CR fields. Exception raising uses a stub; NaN handling is not validated here.'}, indent=2)+'\n')
    print(output.strip(), folder)


if __name__ == '__main__':
    main()
