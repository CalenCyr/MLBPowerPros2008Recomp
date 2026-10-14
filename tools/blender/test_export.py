# SPDX-License-Identifier: GPL-3.0-or-later
"""Headless round trip of the add-on: import Coors Field, edit it, export a mod, read the packs back.

blender --background --factory-startup --python tools/blender/test_export.py -- <addon.zip> <project.bin> <mods dir>
Edits: DP_stand_C raised 15 m (transform), DP_score geometry raised 10 m (mesh), one flag deleted,
DP_ground's texture tinted blue (image). Writes <mods dir>/BlenderTest; exits 1 on failure.
"""
import importlib
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

zip_path, project_bin, mods_dir = sys.argv[sys.argv.index("--") + 1:][:3]
failures = []


def check(ok, label):
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        failures.append(label)


bpy.ops.extensions.package_install_files(filepath=zip_path, repo="user_default", enable_on_install=True)
pkg = "bl_ext.user_default.powerpros_stadium"
pj7m = importlib.import_module(pkg + ".pj7m")
tbl_mod = importlib.import_module(pkg + ".stadium_tbl")
projectbin = importlib.import_module(pkg + ".projectbin")
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
bpy.ops.import_scene.powerpros_stadium(filepath=project_bin, stadium="col", collision=False)

objs = {o.name: o for o in bpy.data.objects if o.get("pp_kind") == "model"}
offsets = {n: o["pp_model_offset"] for n, o in objs.items()}
objs["DP_stand_C"].location.z += 15.0
for v in objs["DP_score"].data.vertices:
    v.co.z += 10.0
flag = next(n for n in objs if n.startswith("DP_FLG_"))
bpy.data.objects.remove(objs.pop(flag))
ground_img = next(n.image for m in objs["DP_ground"].data.materials for n in m.node_tree.nodes
                  if n.type == "TEX_IMAGE")
px = np.empty(len(ground_img.pixels), np.float32)
ground_img.pixels.foreach_get(px)
px = px.reshape(-1, 4)
px[:, 0] *= 0.2
px[:, 1] *= 0.4
ground_img.pixels.foreach_set(px.ravel())

bpy.context.view_layer.objects.active = objs["DP_ground"]
result = bpy.ops.export_scene.powerpros_stadium(mod_name="BlenderTest", mods_folder=mods_dir, target="same")
check(result == {"FINISHED"}, "export finishes")

out = Path(mods_dir) / "BlenderTest" / "project"
gfx = (out / "stadium_col.pack").read_bytes()
tbl = (out / "stadium_coltbl.pack").read_bytes()
archive = projectbin.Archive(project_bin)
orig = archive.read("stadium_col.pack")
orig_tbl = tbl_mod.parse_table(archive.read("stadium_coltbl.pack"))
table = tbl_mod.parse_table(tbl)
check(len(gfx) > len(orig) and len(gfx) % 32 == 0, f"graphics pack grew {len(orig)} -> {len(gfx)}")
place = {p.model: p for p in table.placements}
old_place = {p.model: p for p in orig_tbl.placements}
stand = place[offsets["DP_stand_C"]]
check(abs(stand.translation[1] - old_place[offsets["DP_stand_C"]].translation[1] - 150.0) < 0.5,
      f"DP_stand_C placement raised 150 dm (y {stand.translation[1]:.1f})")
score = pj7m.parse_model(gfx, offsets["DP_score"])
old_score = pj7m.parse_model(orig, offsets["DP_score"])
ys = [p[1] for m in score.meshes for p in pj7m.array(gfx, m, "pos")]
old_ys = [p[1] for m in old_score.meshes for p in pj7m.array(orig, m, "pos")]
check(abs((max(ys) - max(old_ys)) - 100.0) < 0.5, f"DP_score geometry raised 100 dm (max y {max(old_ys):.0f} -> {max(ys):.0f})")
check(score.header["triangles"] == sum(pj7m.raw_triangle_count(m) for m in score.meshes), "DP_score header counts match")
emptied = pj7m.parse_model(gfx, offsets[flag])
check(len(emptied.meshes) == 0, f"deleted {flag} has no meshes")
ground = pj7m.parse_model(gfx, offsets["DP_ground"])
new_tex = [t for t in ground.textures if t.offset >= len(orig)]
check(len(new_tex) >= 1 and new_tex[0].fmt == 5, "DP_ground uses a new RGB5A3 texture")
untouched = pj7m.parse_model(gfx, offsets["DP_MIP_turf"])
check(all(m.dl < len(orig) for m in untouched.meshes), "untouched DP_MIP_turf still points at the original data")
check(gfx[:len(orig)].count(b"PJ7M") == orig.count(b"PJ7M"), "original model headers kept in place")
check((Path(mods_dir) / "BlenderTest" / "mod.toml").is_file(), "mod.toml written")
print("RESULT:", "FAIL" if failures else "PASS")
sys.exit(1 if failures else 0)
