# SPDX-License-Identifier: GPL-3.0-or-later
"""Wrap a DOL as a big-endian PowerPC ELF executable, for disassemblers and
decompilers that do not read DOLs (rea). Each DOL text/data section becomes an
allocated PROGBITS section plus PT_LOAD segment; BSS becomes NOBITS. Optional
MAP.txt lines ("hexaddr name") become FUNC symbols sized up to the next one.
Usage: dol_to_elf.py DOL OUT_ELF [MAP_TXT]
"""
import struct
import sys


def read_dol(data):
    words = struct.unpack_from('>18I18I18I', data, 0)
    offsets, addrs, sizes = words[0:18], words[18:36], words[36:54]
    bss_addr, bss_size, entry = struct.unpack_from('>3I', data, 0xD8)
    sections = []
    for i in range(18):
        if sizes[i]:
            kind = 'text' if i < 7 else 'data'
            sections.append((f'.{kind}{i if i < 7 else i - 7}', addrs[i], data[offsets[i]:offsets[i] + sizes[i]], kind == 'text'))
    return sections, bss_addr, bss_size, entry


def read_map(path, sections):
    def inside(a):
        return any(addr <= a < addr + len(body) and is_text for _, addr, body, is_text in sections)
    names = {}
    for line in open(path):
        parts = line.split(None, 1)
        if len(parts) == 2:
            a = int(parts[0], 16)
            if inside(a) and not parts[1].strip().startswith('0x'):
                names.setdefault(a, parts[1].strip())
    return sorted(names.items())


def build_elf(sections, bss_addr, bss_size, entry, symbols):
    shstr = bytearray(b'\0')
    strtab = bytearray(b'\0')

    def add(table, s):
        off = len(table)
        table += s.encode() + b'\0'
        return off

    body = bytearray(0x34 + 0x20 * len(sections))  # ELF header + program headers, file data after
    phdrs, shdrs = [], [bytes(40)]
    for name, addr, data, is_text in sections:
        off = len(body)
        body += data
        flags = 5 if is_text else 6  # R+X / R+W
        phdrs.append(struct.pack('>8I', 1, off, addr, addr, len(data), len(data), flags, 4))
        shdrs.append(struct.pack('>10I', add(shstr, name), 1, 2 | (4 if is_text else 1), addr, off, len(data), 0, 0, 4, 0))
    if bss_size:
        shdrs.append(struct.pack('>10I', add(shstr, '.bss'), 8, 3, bss_addr, len(body), bss_size, 0, 0, 4, 0))

    def section_index(a):
        for i, (_, addr, data, _) in enumerate(sections):
            if addr <= a < addr + len(data):
                return i + 1
        return 0

    symtab = bytearray(16)
    for n, (a, name) in enumerate(symbols):
        end = symbols[n + 1][0] if n + 1 < len(symbols) else a + 4
        shndx = section_index(a)
        size = min(end, next(addr + len(d) for _, addr, d, _ in sections if addr <= a < addr + len(d))) - a
        symtab += struct.pack('>IIIBBH', add(strtab, name), a, size, 0x12, 0, shndx)  # GLOBAL FUNC
    for table, name, typ, link, entsize in ((symtab, '.symtab', 2, len(shdrs) + 1, 16), (strtab, '.strtab', 3, 0, 0)):
        off = len(body)
        body += table
        shdrs.append(struct.pack('>10I', add(shstr, name), typ, 0, 0, off, len(table), link, 1 if typ == 2 else 0, 4, entsize))
    shstr_index = len(shdrs)
    name_off = add(shstr, '.shstrtab')
    off = len(body)
    body += shstr
    shdrs.append(struct.pack('>10I', name_off, 3, 0, 0, off, len(shstr), 0, 0, 1, 0))
    while len(body) % 4:
        body += b'\0'
    shoff = len(body)
    for s in shdrs:
        body += s
    ident = b'\x7fELF\x01\x02\x01' + bytes(9)
    body[0:0x34] = ident + struct.pack('>HHIIIIIHHHHHH', 2, 20, 1, entry, 0x34, shoff, 0x80000000,
                                       0x34, 0x20, len(phdrs), 40, len(shdrs), shstr_index)
    body[0x34:0x34 + 0x20 * len(phdrs)] = b''.join(phdrs)
    return bytes(body)


def demo():
    dol = bytearray(0x100 + 8)
    struct.pack_into('>I', dol, 0x00, 0x100)        # text0 offset
    struct.pack_into('>I', dol, 0x48, 0x80003100)   # text0 address
    struct.pack_into('>I', dol, 0x90, 8)            # text0 size
    struct.pack_into('>3I', dol, 0xD8, 0x80004000, 0x10, 0x80003100)
    dol[0x100:0x108] = bytes.fromhex('3860000148000000')
    sections, bss_addr, bss_size, entry = read_dol(bytes(dol))
    elf = build_elf(sections, bss_addr, bss_size, entry, [(0x80003100, 'f'), (0x80003104, 'g')])
    assert elf[:4] == b'\x7fELF' and struct.unpack_from('>H', elf, 18)[0] == 20
    assert struct.unpack_from('>I', elf, 0x34 + 8)[0] == 0x80003100  # p_vaddr
    assert elf[struct.unpack_from('>I', elf, 0x34 + 4)[0]:][:8] == bytes(dol[0x100:0x108])


if __name__ == '__main__':
    demo()
    if len(sys.argv) >= 3:
        raw = open(sys.argv[1], 'rb').read()
        sections, bss_addr, bss_size, entry = read_dol(raw)
        symbols = read_map(sys.argv[3], sections) if len(sys.argv) > 3 else []
        open(sys.argv[2], 'wb').write(build_elf(sections, bss_addr, bss_size, entry, symbols))
        print(f'{len(sections)} sections, {len(symbols)} symbols -> {sys.argv[2]}')
