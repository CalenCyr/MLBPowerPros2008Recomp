# SPDX-License-Identifier: GPL-3.0-or-later
"""Headless check of the add-on inside Blender: install the zip, import a stadium, count, render.

blender --background --factory-startup --python tools/blender/test_import.py -- <addon.zip> <project.bin> <code> <out dir>
Run with BLENDER_USER_RESOURCES pointing at a scratch folder so the player's Blender is untouched.
Prints PASS/FAIL lines and exits 1 on failure; renders <code>-top.png and <code>-plate.png.
"""
import importlib
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

zip_path, project_bin, code, out_dir = sys.argv[sys.argv.index("--") + 1:][:4]
out_dir = Path(out_dir)
failures = []


def check(ok, label):
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        failures.append(label)


bpy.ops.extensions.package_install_files(filepath=zip_path, repo="user_default", enable_on_install=True)
check(hasattr(bpy.ops.import_scene, "powerpros_stadium"), "extension installs and registers the import operator")
pkg = "bl_ext.user_default.powerpros_stadium"
pj7m = importlib.import_module(pkg + ".pj7m")
tbl_mod = importlib.import_module(pkg + ".stadium_tbl")
projectbin = importlib.import_module(pkg + ".projectbin")

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
result = bpy.ops.import_scene.powerpros_stadium(filepath=project_bin, stadium=code, collision=True)
check(result == {"FINISHED"}, f"import of {code} finishes")

archive = projectbin.Archive(project_bin)
gfx = archive.read(f"stadium_{code}.pack")
table = tbl_mod.parse_table(archive.read(f"stadium_{code}tbl.pack"))
models = [pj7m.parse_model(gfx, p.model) for p in table.placements]
want_faces = sum(len(pj7m.triangles(mesh)) for mod in models for mesh in mod.meshes)
pieces = [o for o in bpy.data.objects if o.get("pp_kind") == "model"]
faces = sum(len(o.data.polygons) for o in pieces)
textures = {t.offset for mod in models for t in mod.textures}
images = [i for i in bpy.data.images if "pp_texture_offset" in i]
coll = [o for o in bpy.data.objects if o.get("pp_kind") == "collision"]
check(len(pieces) == len(table.placements), f"{len(pieces)} pieces == {len(table.placements)} placements")
check(abs(faces - want_faces) <= want_faces // 200, f"{faces} faces ~ {want_faces} triangles from the display lists")
used = {m.textures[m.texmaps[mat.texmaps[0]].texture].offset for m in models for mat in m.materials if mat.texmaps}
check(len(images) == len(used), f"{len(images)} images == {len(used)} textures in use ({len(textures)} listed)")
proper = len({tuple(sorted((a, b, c))) for a, b, c, _ in table.triangles if len({a, b, c}) == 3})  # no degenerate/duplicate
check(len(coll) == 1 and len(coll[0].data.polygons) == proper,
      f"collision has {len(coll[0].data.polygons) if coll else 0} faces of {proper} ({len(table.triangles)} with degenerate)")
check(all(i.packed_file is not None for i in images), "images are packed into the .blend")

# Renders to compare with the game (EEVEE, unlit materials as imported).
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.eevee.taa_render_samples = 8
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
views = {
    "top": dict(loc=(0, 45, 250), rot=(0, 0, 0), ortho=170),
    "plate": dict(loc=(0, -6, 3), rot=(math.radians(94), 0, 0), ortho=None),
}
for name, v in views.items():
    cam.location = Vector(v["loc"])
    cam.rotation_euler = Euler(v["rot"])
    cam.data.type = "ORTHO" if v["ortho"] else "PERSP"
    if v["ortho"]:
        cam.data.ortho_scale = v["ortho"]
    cam.data.lens = 24
    cam.data.clip_end = 2000
    scene.render.filepath = str(out_dir / f"{code}-{name}.png")
    bpy.ops.render.render(write_still=True)
    check((out_dir / f"{code}-{name}.png").is_file(), f"render {name}")

print("RESULT:", "FAIL" if failures else "PASS")
sys.exit(1 if failures else 0)
