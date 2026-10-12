# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent PPC references for small real REL functions at the linked layout.

Function boundaries are dtk inferences; accepting a function means all selected
inputs returned in Unicorn. This is a bounded CPU check, not gameplay validation.
"""
import argparse
import csv
import hashlib
import json
import struct
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'local/python'))
from unicorn import Uc, UcError, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN
from unicorn import ppc_const as ppc

RETURN = 0xDEADC0DC
VALUES = [0,1,0x7F,0x80,0x7FFF,0x8000,0xFFFF,0xFFFFFFFF,0x80010040,0x01020304,0xAAAA5555,0x7FFFFFFF]
ALLOWED = {7,8,10,11,12,13,14,15,16,19,20,21,23,24,25,26,27,28,29,31,32,33,34,35,40,41,42,43}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_directory',type=Path)
    args = parser.parse_args()
    artifacts = args.probe_directory/'control/artifacts'
    memory = (artifacts/'mem1-low.bin').read_bytes()+(artifacts/'mem1-high.bin').read_bytes()
    layout = json.loads((ROOT/'local/generated/dolrecomp/rel-linked/layout.json').read_text())
    section = next(s for s in layout['sections'] if s['executable'])
    start = section['start']-0x80000000
    code = memory[start:start+section['size']]
    if hashlib.sha256(code).hexdigest() != section['sha256']:
        raise ValueError('Reference code differs from verified translation input')
    uc = Uc(UC_ARCH_PPC, UC_MODE_32|UC_MODE_BIG_ENDIAN)
    uc.mem_map(0x80000000,24*1024*1024)
    uc.mem_map(RETURN & ~0xFFF,0x1000)
    registers = [getattr(ppc,f'UC_PPC_REG_{i}') for i in range(32)]
    special = [ppc.UC_PPC_REG_CR,ppc.UC_PPC_REG_XER,ppc.UC_PPC_REG_CTR,ppc.UC_PPC_REG_LR,ppc.UC_PPC_REG_PC]
    candidates = {'absolute_address':[], 'integer_leaf':[]}
    for row in csv.DictReader((ROOT/'local/analysis/rel-functions.csv').open()):
        offset,size = int(row['address'],16),int(row['size'])
        if not 8<=size<=48 or size%4 or offset+size>len(code):
            continue
        words = struct.unpack('>'+'I'*(size//4),code[offset:offset+size])
        if words[-1]!=0x4E800020 or any(w>>26 not in ALLOWED for w in words):
            continue
        kind = 'absolute_address' if any(w>>26==15 and (w&0xFFFF)>=0x8000 for w in words) else 'integer_leaf'
        candidates[kind].append((offset,size,row['name']))
    fixtures,selected = [],[]
    for kind in candidates:
        accepted=0
        for offset,size,name in candidates[kind]:
            if accepted==3:
                break
            entry=section['start']+offset
            records=[]
            try:
                for case,value in enumerate(VALUES):
                    uc.mem_write(0x80000000,memory)
                    initial=[(value + i*0x10203)&0xFFFFFFFF for i in range(32)]
                    initial[1]=0x80020000;initial[3]=value;initial[4]=VALUES[(case+3)%len(VALUES)];initial[5]=case
                    for reg,val in zip(registers,initial):
                        uc.reg_write(reg,val)
                    for reg in special:
                        uc.reg_write(reg,0)
                    uc.reg_write(ppc.UC_PPC_REG_LR,RETURN)
                    uc.reg_write(ppc.UC_PPC_REG_MSR,0x2000)
                    uc.emu_start(entry,RETURN,timeout=100000,count=1000)
                    if uc.reg_read(ppc.UC_PPC_REG_PC)!=RETURN:
                        raise ValueError('Did not return within the reference limit')
                    expected=[uc.reg_read(reg)&0xFFFFFFFF for reg in registers+special]
                    digest=hashlib.sha256(uc.mem_read(0x80000000,len(memory))).digest()
                    records.append(struct.pack('<I',entry)+struct.pack('<32I',*initial)+struct.pack('<37I',*expected)+digest)
            except (UcError,ValueError):
                continue
            selected.append({'entry':f'0x{entry:08X}','dtk_name':name,'bytes':size,'kind':kind,'cases':len(records)})
            fixtures.extend(records);accepted+=1
        if accepted!=3:
            raise RuntimeError('Insufficient bounded reference functions: '+kind)
    output=ROOT/'local/analysis/rel-reference.bin'
    output.write_bytes(b'PPRELREF'+hashlib.sha256(memory).digest()+struct.pack('<I',len(fixtures))+b''.join(fixtures))
    summary={'functions':selected,'cases':len(fixtures),'snapshot_sha256':hashlib.sha256(memory).hexdigest(),
             'fixture_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
             'scope':'Independent original linked PPC instructions; all GPRs, CR/XER/CTR/LR/PC and full MEM1 SHA-256. No floating-point or gameplay claim.'}
    (ROOT/'local/analysis/rel-reference.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
