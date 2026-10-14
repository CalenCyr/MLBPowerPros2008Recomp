# SPDX-License-Identifier: GPL-3.0-or-later
"""Self-check of the PJ7M and tbl parsers on a small synthetic pack (no game data, no Blender).

usage: python tools/blender/powerpros_stadium/selftest.py
"""
import struct
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from powerpros_stadium import pj7m, pj7m_write, stadium_tbl
else:
    from . import pj7m, pj7m_write, stadium_tbl

P = 0x40000000


def put(buf, off, fmt, *values):
    struct.pack_into(">" + fmt, buf, off, *values)


def graphics_pack():
    d = bytearray(0x2B0)
    d[0:8] = b"PACKWII "
    put(d, 0x14, "I", 0x20)
    d[0x20:0x25] = b"TEST\0"
    put(d, 0x30, "4sIIIIIIIII", b"PJ7M", 0x28, P | 0x20, P | 0x60, 0, 0, 1, 4, 2, 0)
    put(d, 0x60, "IIII", 9, P | 0xC4, P | 0xB4, P | 0xBC)        # root: scene, textures, palettes
    put(d, 0xA0, "I", P | 0xA4)
    d[0xA4:0xB1] = b"_Wmodel_TEST\0"
    put(d, 0xB4, "II", P | 0x1A0, 0)                              # texture table
    put(d, 0xBC, "II", 0, 0)                                      # no palette (RGB5A3)
    put(d, 0xC4, "IIIIIIIII", 1, P | 0xE8, 1, P | 0xE8, 1, P | 0x120, 1, P | 0x16C, 0x37)
    put(d, 0xE8, "HHII", 1, 0, P | 0xF4, P | 0x118)               # node
    put(d, 0xF4, "HHI", 0, 1, P | 0xFC)                           # mesh list
    put(d, 0xFC, "IIIIIII", 0, 0x40, P | 0x1E0, P | 0x220, P | 0x250, P | 0x280, P | 0x290)
    d[0x118:0x120] = b"pPlane1\0"
    put(d, 0x120, "HH", 0, 4)                                     # texmap -> texture 0
    put(d, 0x12C, "HH", 3, 3)
    put(d, 0x16C, "HH4s4s4s", 3, 0, b"\0\0\0\xff", b"\xcc\xcc\xcc\xff", b"\0\0\0\xff")
    put(d, 0x16C + 0x1C, "8H", 0, *[0xFFFF] * 7)
    put(d, 0x1A0, "HHBxxxI", 4, 4, 0x81, P | 0x1C0)              # 4x4 RGB5A3
    put(d, 0x1C0, "16H", *[0xFFFF] * 16)
    put(d, 0x1E0, "BH", 0x98, 4)                                  # one strip of four vertices
    for i in range(4):
        put(d, 0x1E3 + i * 9, "BHHHH", 0, i, i, i, i)
    for i, (x, z) in enumerate([(0, 0), (10, 0), (0, -10), (10, -10)]):
        put(d, 0x220 + i * 12, "3f", x, 0, z)
        put(d, 0x250 + i * 12, "3f", 0, 1, 0)
        put(d, 0x280 + i * 4, "4B", 255, 128, 64, 255)
        put(d, 0x290 + i * 8, "2f", x / 10, -z / 10)
    return d


def table_pack():
    d = bytearray(0xE0)
    d[0:8] = b"PACKWII "
    put(d, 0x14, "I", 0x20)
    put(d, 0x20, "I19fI", P | 0x30, 1, 2, 3, 0, 0.5, 0, 1, 1, 1, 0, 0, -10, 10, 0, 0, 5, 0, -5, 8, 0x500)
    put(d, 0x74, "HHI4H", 1, 3, 0, 0, 1, 2, 7)                   # collision: 1 triangle, surface 7
    put(d, 0x84, "9f", 0, 0, 0, 10, 0, 0, 0, 0, -10)
    put(d, 0xA8, "I", 1)
    put(d, 0xAC, "I", P | 0x20)                                   # placements
    put(d, 0xAC + 5 * 4, "II", P | 0x84, P | 0x74)               # collision vertices, header
    return d


def main():
    g, t = graphics_pack(), table_pack()
    assert pj7m.find_models(g) == [0x30]
    m = pj7m.parse_model(g, 0x30)
    assert (m.name, m.wname, m.node_name) == ("TEST", "_Wmodel_TEST", "pPlane1")
    assert m.header == {"textures": 1, "positions": 4, "triangles": 2}
    tex = m.textures[0]
    assert (tex.width, tex.height, tex.fmt, tex.pixels, tex.palette) == (4, 4, 5, 0x1C0, None)
    assert m.materials[0].texmaps == [0] and m.materials[0].colors[1] == (0xCC, 0xCC, 0xCC, 0xFF)
    mesh = m.meshes[0]
    assert mesh.counts == {"pos": 4, "nrm": 4, "clr": 4, "tex": 4}
    assert pj7m.raw_triangle_count(mesh) == 2
    tris = pj7m.triangles(mesh)
    assert [tuple(v[1] for v in tri) for tri in tris] == [(0, 1, 2), (2, 1, 3)]   # odd strip triangle flipped
    assert pj7m.array(g, mesh, "pos")[3] == (10.0, 0.0, -10.0)
    assert pj7m.array(g, mesh, "clr")[0] == (255, 128, 64, 255)
    assert pj7m.array(g, mesh, "tex")[1] == (1.0, 0.0)
    try:
        g[0x1E0] = 0xA0                                           # a fan: not used by stadiums
        pj7m.parse_model(g, 0x30)
        raise AssertionError("unknown opcode accepted")
    except pj7m.FormatError:
        pass

    table = stadium_tbl.parse_table(t)
    assert table.root == 0xA8 and len(table.placements) == 1
    pl = table.placements[0]
    assert (pl.model, pl.translation, pl.rotation[1], pl.scale, pl.flags) == (0x30, (1, 2, 3), 0.5, (1, 1, 1), 0x500)
    assert table.triangles == [(0, 1, 2, 7)] and table.vertices[1] == (10.0, 0.0, 0.0)
    # Writer: replace the geometry, add a material with a new texture, move the placement.
    g = graphics_pack()
    w = pj7m_write.PackWriter(g)
    model = pj7m.parse_model(w.d, 0x30)
    tex = w.add_texture_rgb5a3(bytes([0xFF]) * 32, 4, 4)
    new_mat = w.add_material(model, model.materials[0].raw, tex)
    assert new_mat == 1
    tri = pj7m_write.MeshData(new_mat, [(0, 0, 0), (0, 0, -5), (5, 0, 0)], [(0, 1, 0)], [(1, 2, 3, 4)], [(0, 0)],
                              [(0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0)])
    assert w.set_meshes(model, [tri]) == (3, 1)
    assert bytes(w.d[:len(g)]) == bytes(g[:0x30]) + bytes(w.d[0x30:len(g)]) and len(w.d) % 4 == 0
    m2 = pj7m.parse_model(w.d, 0x30)
    assert m2.header == {"textures": 2, "positions": 3, "triangles": 1}
    assert len(m2.materials) == 2 and m2.materials[1].texmaps == [1] and m2.texmaps[1].texture == 1
    assert m2.textures[1].offset == tex and (m2.textures[1].width, m2.textures[1].fmt) == (4, 5)
    root2 = pj7m.ptr(w.d, 0x30 + 0x0C)
    for table in (pj7m.ptr(w.d, root2 + 8), pj7m.ptr(w.d, root2 + 12)):      # zero-terminated tables
        assert bytes(w.d[table + 16:table + 24]) == bytes(8)
    mesh2 = m2.meshes[0]
    assert mesh2.material == 1 and pj7m.raw_triangle_count(mesh2) == 1 and mesh2.dl % 32 == 0
    assert pj7m.array(w.d, mesh2, "pos") == [(0, 0, 0), (0, 0, -5), (5, 0, 0)]
    assert pj7m.array(w.d, mesh2, "clr") == [(1, 2, 3, 4)]
    t = table_pack()
    pj7m_write.set_placement(t, 0x20, (4, 5, 6), (0, 1, 0), (2, 2, 2), (0, 0, 0, 1, 1, 1), (0.5, 0.5, 0.5, 1))
    pl = stadium_tbl.parse_table(t).placements[0]
    assert (pl.translation, pl.scale, pl.sphere, pl.flags, pl.model) == ((4, 5, 6), (2, 2, 2), (0.5, 0.5, 0.5, 1), 0x500, 0x30)
    print("selftest OK")


if __name__ == "__main__":
    main()
