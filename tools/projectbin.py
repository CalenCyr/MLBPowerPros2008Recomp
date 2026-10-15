"""Read and rebuild MLB Power Pros 2008's PROJECT.BIN archive (files/project.bin on the disc).

Layout (big-endian, sectors of 0x800 bytes), found by reading the file and checked on all 2,424
entries of RL8E54; the game's own reading (mount 0x80059E7C, index 0x8005A334, lookup 0x800599E4)
confirmed the id table and the order buckets:
  0x00     u32 version (2), u32 sector size (0x800), u32 header sectors (0xA), u32 file ids (0x1211)
  0x10     u32 records sectors (0x40), u32 record table offset (0x6000), u32 bucket table offset
           (0x5800), u32 its sectors (1)
  0x20     u32 bucket count (2), u32 order sectors (0xA), u32 order table offset (0x26000),
           u32 name table offset (0x2B000)
  0x30     u32 name sectors (0x25), u32 data offset (0x3D800)
  0x800    file id table: slot i (from 1) holds the record-table offset of record i - 1; the game
           reads slot id + 1, so file id n is record n. It asks for files by id, never by name
  records  0x1C bytes each: u32 0, u32 name offset (into the name table), u32 size in sectors,
           u32 alignment (0x800), u32 0, u32 0, u32 size in bytes
  order    buckets (offsets from the order table in the bucket table): u32 count, u32 0, then
           count pairs u32 file id, u32 start sector (relative to the data offset). The disc has an
           empty bucket at 0 and one with all 2,423 files at 8; this module reads the bucket header
           (2423, 0) as a nameless first pair, which is harmless for list/extract/build.
  names    NUL-terminated paths ("/ClaimTheTitle.pack"); offset 0 is the empty name
Files are .pack (PACKWII, two PACKPS2), .dat and .arc. Only data moves when a file is replaced:
the header, hash table and name table are kept as they are.

usage:
  projectbin.py list <project.bin>
  projectbin.py extract <project.bin> <out dir> [name substring]
  projectbin.py build <project.bin> <replacements dir> <out project.bin>
      replacements dir holds files named like the archive paths (e.g. team_logo.pack); every
      other file is copied from the original. Rebuilding with an empty dir reproduces the input.
"""
import struct
import sys
from pathlib import Path

SECTOR = 0x800


class Archive:
    def __init__(self, path):
        self.path = Path(path)
        with open(self.path, "rb") as f:
            head = f.read(0x40)
            self.records_off = struct.unpack_from(">I", head, 0x14)[0]
            self.order_off = struct.unpack_from(">I", head, 0x28)[0]
            self.names_off = struct.unpack_from(">I", head, 0x2C)[0]
            self.data_off = struct.unpack_from(">I", head, 0x34)[0]
            f.seek(0)
            self.header = bytearray(f.read(self.data_off))
        h = self.header
        count = (self.order_off - self.records_off) // 0x1C
        self.records = [list(struct.unpack_from(">7I", h, self.records_off + i * 0x1C)) for i in range(count)]
        self.order = []
        i = 1
        while True:
            pos = self.order_off + i * 8
            if pos + 8 > self.names_off:
                break
            index, sector = struct.unpack_from(">2I", h, pos)
            if index == 0 and sector == 0:
                break
            self.order.append([index, sector])
            i += 1

    def name(self, record):
        start = self.names_off + record[1]
        return self.header[start:self.header.index(b"\0", start)].decode("ascii")

    def entries(self):
        """(path, record index, byte offset, byte size) in data order."""
        for index, sector in self.order:
            record = self.records[index]
            yield self.name(record), index, self.data_off + sector * SECTOR, record[6]

    def read(self, name):
        """Bytes of the entry called name ("/stadium_col.pack" or "stadium_col.pack"), or None."""
        name = "/" + name.lstrip("/").lower()
        for path, _, offset, size in self.entries():
            if path.lower() == name:
                with open(self.path, "rb") as f:
                    f.seek(offset)
                    return f.read(size)
        return None

    def build(self, replacements, out):
        header = bytearray(self.header)
        sector = 0
        with open(self.path, "rb") as src, open(out, "wb") as dst:
            dst.write(b"\0" * self.data_off)
            for slot, (path, index, offset, size) in enumerate(self.entries(), start=1):
                replacement = replacements.get(path.lstrip("/").lower())
                if replacement is not None:
                    data = replacement.read_bytes()
                else:
                    src.seek(offset)
                    data = src.read(size)
                sectors = (len(data) + SECTOR - 1) // SECTOR
                dst.write(data + b"\0" * (sectors * SECTOR - len(data)))
                record = self.records[index]
                struct.pack_into(">7I", header, self.records_off + index * 0x1C,
                                 record[0], record[1], sectors, record[3], record[4], record[5], len(data))
                struct.pack_into(">2I", header, self.order_off + slot * 8, index, sector)
                sector += sectors
            dst.seek(0)
            dst.write(header)


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    command, archive = argv[0], Archive(argv[1])
    if command == "list":
        for path, index, offset, size in archive.entries():
            print(f"{offset:#010x} {size:10d}  {path}")
    elif command == "extract":
        out = Path(argv[2])
        pattern = argv[3].lower() if len(argv) > 3 else ""
        with open(archive.path, "rb") as f:
            for path, index, offset, size in archive.entries():
                if not path or pattern not in path.lower():
                    continue
                f.seek(offset)
                target = out / path.lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(f.read(size))
    elif command == "build":
        folder = Path(argv[2])
        replacements = {p.relative_to(folder).as_posix().lower(): p for p in folder.rglob("*") if p.is_file()}
        archive.build(replacements, argv[3])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
