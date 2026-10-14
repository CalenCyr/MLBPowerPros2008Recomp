# SPDX-License-Identifier: GPL-3.0-or-later
"""Reverse-engineering checks for MLB Power Pros 2008 stadium packs (PJ7M models + tbl tables).

usage:
  stadium_re.py info  <project.bin> [filter]   models, meshes, textures and collision per stadium
  stadium_re.py check <project.bin>            every stadium_*.pack / *tbl.pack against the invariants
  stadium_re.py stats <project.bin>            histograms of the fields not decoded yet
Reads the player's project.bin; writes nothing.
"""
import collections
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "blender"))
from projectbin import Archive                          # noqa: E402
from powerpros_stadium import pj7m, stadium_tbl         # noqa: E402


def stadiums(archive, flt=""):
    """(code, graphics bytes, table bytes or None) for every stadium_<code>.pack with models."""
    names = {p.lstrip("/").lower() for p, *_ in archive.entries()}
    for name in sorted(names):
        if not (name.startswith("stadium_") and name.endswith(".pack")) or name.endswith("tbl.pack"):
            continue
        code = name[len("stadium_"):-len(".pack")]
        if flt and flt not in code:
            continue
        tbl = f"stadium_{code}tbl.pack"
        yield code, archive.read(name), archive.read(tbl) if tbl in names else None


def check_model(d, model, problems):
    where = f"{model.name} 0x{model.offset:X}"
    if sum(m.counts["pos"] for m in model.meshes) != model.header["positions"]:
        problems.append(f"{where}: position count {model.header['positions']} != arrays")
    ntri = sum(pj7m.raw_triangle_count(m) for m in model.meshes)
    if ntri != model.header["triangles"]:
        problems.append(f"{where}: triangle count {model.header['triangles']} != {ntri} from the lists")
    for mesh in model.meshes:
        if mesh.dl % 32 or mesh.dl_size % 32:
            problems.append(f"{where}: display list 0x{mesh.dl:X} not 32-byte aligned")
        if not 0 <= mesh.material < len(model.materials):
            problems.append(f"{where}: mesh material {mesh.material} out of range")
        for n in pj7m.array(d, mesh, "nrm"):
            length = math.sqrt(sum(c * c for c in n))
            if length > 1e-6 and abs(length - 1) > 1e-3:          # a few zero normals exist
                problems.append(f"{where}: normal {n} is not unit length")
                break
    for mat in model.materials:
        if any(s >= len(model.texmaps) for s in mat.texmaps):
            problems.append(f"{where}: material 0x{mat.offset:X} slot out of range")
    for tm in model.texmaps:
        if tm.texture >= len(model.textures):
            problems.append(f"{where}: texmap 0x{tm.offset:X} texture {tm.texture} out of range")


def load(code, gfx, tbl, problems):
    table = stadium_tbl.parse_table(tbl) if tbl else None
    offsets = pj7m.find_models(gfx)
    if table and sorted(p.model for p in table.placements) != sorted(offsets):
        problems.append(f"{code}: placements point at {len(table.placements)} models, pack has {len(offsets)}")
    models = [pj7m.parse_model(gfx, o) for o in offsets]
    if table:
        for a, b, c, _ in table.triangles:
            if max(a, b, c) >= len(table.vertices):
                problems.append(f"{code}: collision index out of range")
                break
    return models, table


def cmd_info(archive, flt=""):
    for code, gfx, tbl in stadiums(archive, flt):
        problems = []
        models, table = load(code, gfx, tbl, problems)
        tex = {t.offset for m in models for t in m.textures}
        tris = sum(m.header["triangles"] for m in models)
        coll = f"{len(table.triangles)} collision triangles" if table else "no table"
        print(f"{code:10} {len(gfx):8} B  {len(models):3} models  {tris:6} triangles  {len(tex):4} textures  {coll}")


def cmd_check(archive):
    total = bad = 0
    for code, gfx, tbl in stadiums(archive):
        problems = []
        try:
            models, _ = load(code, gfx, tbl, problems)
            for m in models:
                check_model(gfx, m, problems)
        except (pj7m.FormatError, stadium_tbl.FormatError) as e:
            problems.append(f"{code}: {e}")
            models = []
        total += 1
        bad += bool(problems)
        print(f"{code:10} {len(models):3} models  {'OK' if not problems else 'FAIL'}")
        for p in problems[:8]:
            print("    " + p)
    print(f"{total - bad}/{total} stadium packs pass")
    return 1 if bad else 0


def cmd_stats(archive):
    c = collections.defaultdict(collections.Counter)
    for code, gfx, tbl in stadiums(archive):
        models, table = load(code, gfx, tbl, [])
        for m in models:
            for mesh in m.meshes:
                for _, verts in mesh.draws:
                    c["vertex u8"].update(v[0] for v in verts)
                c["draw opcodes"].update(op for op, _ in mesh.draws)
            c["material flags"].update(f"0x{mat.flags:04X}" for mat in m.materials)
            c["material slots used"].update(len(mat.texmaps) for mat in m.materials)
            c["texture formats"].update(t.fmt for t in m.textures)
            c["texmap +2..+0x0C"].update(tm.raw[2:12].hex() for tm in m.texmaps)
        if table:
            c["placement flags"].update(f"0x{p.flags:08X}" for p in table.placements)
            c["surface ids"].update(t[3] for t in table.triangles)
    for name, counter in c.items():
        print(f"{name}: " + ", ".join(f"{k}x{v}" for k, v in counter.most_common(24)))


def main(argv):
    if len(argv) < 3 or argv[1] not in ("info", "check", "stats"):
        print(__doc__)
        return 2
    archive = Archive(argv[2])
    if argv[1] == "info":
        return cmd_info(archive, argv[3] if len(argv) > 3 else "") or 0
    return cmd_check(archive) if argv[1] == "check" else cmd_stats(archive) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
