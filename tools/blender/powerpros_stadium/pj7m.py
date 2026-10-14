# SPDX-License-Identifier: GPL-3.0-or-later
"""PJ7M models inside MLB Power Pros 2008 PACKWII files (stadiums, docs/ingenieria-inversa.md).

Big-endian; a pointer is 0x40000000 | file offset. Layout, checked on every stadium pack:

  PJ7M header (0x28)  'PJ7M', u32 0x28, -> name, -> root, 0, 0, u32 texture count,
                      u32 position count (sum over meshes), u32 triangle count, 0
  root                u32 9, -> scene, -> texture table, -> palette table, ..., +0x40 -> "_Wmodel_<name>"
  scene               {u32 1, -> node}, {u32 1, -> ?}, {u32 n, -> texmaps}, {u32 n, -> materials}, u32 0x37
  node (0x0C)         u16 mesh count, u16 0, -> mesh list, -> Maya node name
  mesh list entry (8) u16 material index, u16 1, -> mesh
  mesh (0x1C)         u32 0, u32 display list size, -> display list, -> POS, -> NRM, -> CLR0, -> TEX0
  material (0x34)     u16 3, u16 flags, RGBA8 x3, ..., +0x1C u16 texmap slot x8 (0xFFFF unused)
  texmap (0x4C)       u16 texture index, ..., +0x0C u16 width - 1, u16 height - 1
  texture / palette   tables of 8-byte entries {-> header, 0}; headers as in tools/packwii.py

Vertex arrays are direct f32 (POS/NRM xyz, TEX0 uv) and RGBA8 (CLR0). Display lists are 32-byte
aligned GX lists using only 0x98 (strip) and 0x90 (triangles) with VAT 0; each vertex is 9 bytes:
u8 (unknown, 0 so far), u16 POS, NRM, CLR0 and TEX0 indices. Units are decimetres, Y up.
"""
import struct
from dataclasses import dataclass, field

TAG = b"PJ7M"
MODEL_FMT = {0x80: 6, 0x81: 5, 0x82: 9, 0x84: 8}   # texture type byte -> GX format (RGBA8, RGB5A3, C8, C4)


def u16(d, o):
    return struct.unpack_from(">H", d, o)[0]


def u32(d, o):
    return struct.unpack_from(">I", d, o)[0]


def ptr(d, o):
    p = u32(d, o)
    return p & 0x3FFFFFFF if p >> 30 == 1 else None


def cstr(d, o):
    return d[o:d.index(b"\0", o)].decode("ascii", "replace")


class FormatError(ValueError):
    pass


@dataclass
class Texture:
    offset: int
    width: int
    height: int
    fmt: int                       # GX texture format
    pixels: int                    # file offset of the tiled texels
    palette: int | None = None     # file offset of the RGB5A3 palette data
    palette_size: int = 0


@dataclass
class TexMap:
    offset: int
    texture: int                   # index into Model.textures
    raw: bytes = b""


@dataclass
class Material:
    offset: int
    flags: int
    colors: list                   # three RGBA tuples (ambient?, diffuse?, specular?)
    texmaps: list                  # used texmap slots (indices into Model.texmaps)
    raw: bytes = b""


@dataclass
class Mesh:
    offset: int
    material: int
    dl: int
    dl_size: int
    arrays: dict                   # 'pos', 'nrm', 'clr', 'tex' -> file offset
    draws: list = field(default_factory=list)       # (opcode, [vertex tuples])
    counts: dict = field(default_factory=dict)      # array -> element count (max index + 1)


@dataclass
class Model:
    offset: int
    name: str
    wname: str
    node_name: str
    header: dict
    textures: list
    texmaps: list
    materials: list
    meshes: list


def walk_display_list(d, off, size):
    """[(opcode, [(u8, pos, nrm, clr, tex), ...])] for one mesh display list (see gx_dl.cpp)."""
    draws, o, end = [], off, off + size
    while o < end:
        op = d[o]
        if op == 0:                                # NOP padding
            o += 1
            continue
        if op & 0xF8 not in (0x90, 0x98) or op & 7:
            raise FormatError(f"display list 0x{off:X}: opcode 0x{op:02X} at 0x{o:X}")
        n = u16(d, o + 1)
        o += 3
        verts = [struct.unpack_from(">BHHHH", d, o + i * 9) for i in range(n)]
        o += n * 9
        if o > end:
            raise FormatError(f"display list 0x{off:X}: draw runs past its end")
        draws.append((op & 0xF8, verts))
    return draws


def raw_triangle_count(mesh):
    """Triangles as the PJ7M header counts them: strips give n - 2, degenerate ones included."""
    return sum(len(v) - 2 if op == 0x98 else len(v) // 3 for op, v in mesh.draws)


def triangles(mesh):
    """Triangles as vertex tuples in GX winding (strips expanded)."""
    out = []
    for op, v in mesh.draws:
        if op == 0x90:
            out += [(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v) - 2, 3)]
        else:
            for i in range(len(v) - 2):
                tri = (v[i], v[i + 1], v[i + 2]) if i % 2 == 0 else (v[i + 1], v[i], v[i + 2])
                if tri[0][1] != tri[1][1] and tri[1][1] != tri[2][1] and tri[0][1] != tri[2][1]:
                    out.append(tri)
    return out


def array(d, mesh, name):
    """Elements of one vertex array: tuples of floats (pos, nrm, tex) or RGBA bytes (clr)."""
    off, n = mesh.arrays[name], mesh.counts[name]
    if name == "clr":
        return [tuple(d[off + i * 4:off + i * 4 + 4]) for i in range(n)]
    k = 2 if name == "tex" else 3
    return [struct.unpack_from(f">{k}f", d, off + i * 4 * k) for i in range(n)]


def texture_header(d, off, palette_off):
    h, w, kind = u16(d, off), u16(d, off + 2), d[off + 4]
    if kind not in MODEL_FMT:
        raise FormatError(f"texture 0x{off:X}: unknown type 0x{kind:02X}")
    tex = Texture(off, w, h, MODEL_FMT[kind], ptr(d, off + 8))
    if tex.fmt in (8, 9) and palette_off is not None:
        tex.palette_size = u16(d, palette_off)
        tex.palette = ptr(d, palette_off + 8)
    return tex


def parse_model(d, off):
    if d[off:off + 4] != TAG or u32(d, off + 4) != 0x28:
        raise FormatError(f"0x{off:X}: not a PJ7M header")
    header = {"textures": u32(d, off + 0x18), "positions": u32(d, off + 0x1C), "triangles": u32(d, off + 0x20)}
    name = cstr(d, ptr(d, off + 8))
    root = ptr(d, off + 0x0C)
    if u32(d, root) != 9:
        raise FormatError(f"0x{off:X}: root 0x{root:X} does not start with 9")
    scene, textab, paltab = ptr(d, root + 4), ptr(d, root + 8), ptr(d, root + 12)
    wname = cstr(d, ptr(d, root + 0x40))
    if u32(d, scene) != 1 or u32(d, scene + 0x20) != 0x37:
        raise FormatError(f"0x{off:X}: unexpected scene 0x{scene:X}")
    node = ptr(d, scene + 4)
    ntexmap, texmaps_off = u32(d, scene + 0x10), ptr(d, scene + 0x14)
    nmat, mats_off = u32(d, scene + 0x18), ptr(d, scene + 0x1C)

    textures = []
    for i in range(header["textures"]):
        pal = ptr(d, paltab + i * 8) if paltab is not None else None
        textures.append(texture_header(d, ptr(d, textab + i * 8), pal))
    texmaps = [TexMap(o, u16(d, o), bytes(d[o:o + 0x4C])) for o in (texmaps_off + i * 0x4C for i in range(ntexmap))]
    materials = []
    for i in range(nmat):
        o = mats_off + i * 0x34
        colors = [tuple(d[o + 4 + k * 4:o + 8 + k * 4]) for k in range(3)]
        slots = [s for s in struct.unpack_from(">8H", d, o + 0x1C) if s != 0xFFFF]
        materials.append(Material(o, u16(d, o + 2), colors, slots, bytes(d[o:o + 0x34])))

    nmesh, mesh_list = u16(d, node), ptr(d, node + 4)
    node_name = cstr(d, ptr(d, node + 8))
    meshes = []
    for i in range(nmesh):
        e = mesh_list + i * 8
        mo = ptr(d, e + 4)
        arrays = dict(zip(("pos", "nrm", "clr", "tex"), (ptr(d, mo + 8 + k * 4) for k in range(1, 5))))
        mesh = Mesh(mo, u16(d, e), ptr(d, mo + 8), u32(d, mo + 4), arrays)
        mesh.draws = walk_display_list(d, mesh.dl, mesh.dl_size)
        for k, name_ in enumerate(("pos", "nrm", "clr", "tex")):
            mesh.counts[name_] = 1 + max((v[k + 1] for _, vs in mesh.draws for v in vs), default=-1)
        meshes.append(mesh)
    return Model(off, name, wname, node_name, header, textures, texmaps, materials, meshes)


def find_models(d):
    """Offsets of every PJ7M header in a pack (tag followed by the 0x28 header size)."""
    out, o = [], d.find(TAG)
    while o >= 0:
        if o % 4 == 0 and u32(d, o + 4) == 0x28:
            out.append(o)
        o = d.find(TAG, o + 1)
    return out
