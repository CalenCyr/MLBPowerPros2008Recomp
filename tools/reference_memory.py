"""Run original PPC memory routines in Unicorn as an independent test oracle.

Unicorn is a verification dependency, not part of the game's proposed runtime.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'local/python'))
import unicorn
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN
from unicorn import ppc_const as ppc

BASE = 0x80000000
DATA = BASE + 0x10000
STACK = BASE + 0x20000
RETURN = 0xDEADC0DC
SIZES = [0, 1, 2, 3, 4, 7, 8, 15, 16, 20, 21, 31, 32, 33, 63, 64, 65, 255, 256, 257, 1024]
FILLS = [0, 1, 0x7F, 0x80, 0xFF, 0x1234]
SEED = bytes((i * 73 + (i >> 3) * 19) & 255 for i in range(8192))


def cases():
    for alignment in range(8):
        for size in SIZES:
            for fill in FILLS:
                yield (0x800065BC, 64 + alignment, fill, size)
    for destination in range(8):
        for source in range(8):
            for size in SIZES:
                yield (0x8000626C, 64 + destination, 2048 + source, size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dol', type=Path, default=ROOT / 'local/disc/DATA/sys/main.dol')
    args = parser.parse_args()
    dol = args.dol.read_bytes()
    digest = hashlib.sha256(dol).hexdigest()
    inventory = json.loads((ROOT / 'local/analysis/inventory.json').read_text())
    if digest != inventory['dol']['sha256']:
        raise ValueError('DOL differs from the inventoried input')
    uc = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    uc.mem_map(BASE, 24 * 1024 * 1024)
    uc.mem_map(RETURN & ~0xFFF, 0x1000)
    for index in range(7):
        offset = struct.unpack_from('>I', dol, index * 4)[0]
        address = struct.unpack_from('>I', dol, 0x48 + index * 4)[0]
        size = struct.unpack_from('>I', dol, 0x90 + index * 4)[0]
        if size:
            uc.mem_write(address, dol[offset:offset + size])
    registers = [getattr(ppc, f'UC_PPC_REG_{index}') for index in range(32)]
    plan = list(cases())
    differences = []
    output = ROOT / 'local/analysis/memory-reference.bin'
    with output.open('wb') as stream:
        stream.write(b'PPPMREF1' + digest.encode('ascii') + struct.pack('<I', len(plan)))
        for index, (entry, destination, source, size) in enumerate(plan):
            uc.mem_write(DATA, SEED)
            for register in registers:
                uc.reg_write(register, 0)
            uc.reg_write(registers[1], STACK)
            uc.reg_write(registers[3], DATA + destination)
            uc.reg_write(registers[4], source if entry == 0x800065BC else DATA + source)
            uc.reg_write(registers[5], size)
            uc.reg_write(registers[31], 0x12345678)
            uc.reg_write(ppc.UC_PPC_REG_LR, RETURN)
            uc.reg_write(ppc.UC_PPC_REG_CTR, 0)
            uc.reg_write(ppc.UC_PPC_REG_CR, 0)
            uc.reg_write(ppc.UC_PPC_REG_MSR, 0x2000)
            uc.emu_start(entry, RETURN, timeout=2000000, count=100000)
            if uc.reg_read(ppc.UC_PPC_REG_PC) != RETURN:
                raise ValueError(f'PPC reference did not return for case {index}')
            if uc.reg_read(registers[3]) != DATA + destination or uc.reg_read(registers[1]) != STACK or uc.reg_read(registers[31]) != 0x12345678:
                raise ValueError(f'PPC reference ABI mismatch for case {index}')
            actual = bytes(uc.mem_read(DATA, len(SEED)))
            expected = bytearray(SEED)
            expected[destination:destination + size] = (bytes([source & 255]) * size if entry == 0x800065BC else SEED[source:source + size])
            if actual != expected:
                mismatches = [i for i, (a, b) in enumerate(zip(actual, expected)) if a != b]
                differences.append(dict(case=index, entry=f'0x{entry:08X}', destination=destination,
                                        source=source, size=size, differing_bytes=len(mismatches),
                                        first_difference=mismatches[0]))
            stream.write(struct.pack('<IIII', entry, destination, source, size) + actual)
    summary = dict(unicorn_version=unicorn.__version__, dol_sha256=digest, cases=len(plan),
                   fixture_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                   cases_differing_from_host_c=len(differences), differences=differences,
                   note='The reference executes original PPC. Host C semantics are reported separately and do not replace the game behavior.')
    (ROOT / 'local/analysis/memory-reference.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key != 'differences'}, indent=2))


if __name__ == '__main__':
    main()
