# SPDX-License-Identifier: GPL-3.0-or-later
"""Write an imported (and edited) stadium back as mod packs: mods/<mod>/project/stadium_<code>[tbl].pack.

Only pieces whose mesh, materials or transform changed since the import are rewritten; the rest of
the original packs is kept byte-for-byte. Deleted pieces are emptied (no meshes). Edited or new
images become RGB5A3 textures. New pieces and collision edits come in later phases.
"""
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import fingerprint, importer, packwii, pj7m, pj7m_write, stadium_tbl

try:
    from . import projectbin
except ImportError:
    import projectbin


class ExportFailure(Exception):
    pass


def to_game(v):
    """Blender metres, Z up -> game decimetres, Y up (inverse of importer.to_blender)."""
    return (10.0 * v[0], 10.0 * v[2], -10.0 * v[1])


def to_game_dir(v):
    return (v[0], v[2], -v[1])


def game_matrix(obj):
    return importer.FROM_BLENDER @ obj.matrix_world @ importer.TO_BLENDER


def image_of(mat):
    if mat is None or mat.node_tree is None:
        return None
    for node in mat.node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image is not None:
            return node.image
    return None


def pow2(n):
    return 1 << max(2, min(10, round(math.log2(max(n, 1)))))


class Exporter:
    def __init__(self, gfx, tbl):
        self.w = pj7m_write.PackWriter(gfx)
        self.tbl = bytearray(tbl) if tbl else None
        self.table = stadium_tbl.parse_table(self.tbl) if tbl else None
        self.textures = {}          # texture offset -> pj7m.Texture (original ones)
        for off in pj7m.find_models(gfx):
            for t in pj7m.parse_model(gfx, off).textures:
                self.textures.setdefault(t.offset, t)
        self.new_textures = {}      # image name -> texture offset
        self._image_checks = {}     # image name -> pixels differ from the import
        self.stats = {"pieces": 0, "emptied": 0, "moved": 0, "textures": 0}

    # ---- textures ------------------------------------------------------------------------------

    def texture_for(self, img):
        """(texture offset, palette offset) for an image: the original if unchanged, else a new one."""
        if img is None:
            return None, None
        off = img.get("pp_texture_offset")
        if off is not None and img.get("pp_pixels_hash") == fingerprint.image_hash(img) and off in self.textures:
            return off, self._palette_header(off)
        if img.name not in self.new_textures:
            w, h = img.size
            if w == 0 or h == 0:
                raise ExportFailure(f"La imagen {img.name} está vacía")
            px = np.empty(w * h * 4, np.float32)
            img.pixels.foreach_get(px)
            rgba = (px.reshape(h, w, 4)[::-1] * 255 + 0.5).astype(np.uint8)        # top row first
            tw, th = pow2(w), pow2(h)
            if (tw, th) != (w, h):
                ys = (np.arange(th) * h // th)
                xs = (np.arange(tw) * w // tw)
                rgba = rgba[ys][:, xs]
            texels = packwii.tile(packwii.to_rgb5a3(rgba), 5).astype(">u2").tobytes()
            self.new_textures[img.name] = self.w.add_texture_rgb5a3(texels, tw, th)
            self.stats["textures"] += 1
        return self.new_textures[img.name], None

    def image_changed(self, img):
        if img is None or "pp_pixels_hash" not in img:
            return img is not None                     # a new image counts as a change
        if img.name not in self._image_checks:
            self._image_checks[img.name] = img["pp_pixels_hash"] != fingerprint.image_hash(img)
        return self._image_checks[img.name]

    def _palette_header(self, texture_offset):
        """The palette header an original model uses with this texture (palette tables are per model)."""
        if not hasattr(self, "_palettes"):
            self._palettes = {}
            d = self.w.d
            for off in pj7m.find_models(d):
                root = pj7m.ptr(d, off + 0x0C)
                textab, paltab = pj7m.ptr(d, root + 8), pj7m.ptr(d, root + 12)
                for i in range(pj7m.u32(d, off + 0x18)):
                    t, p = pj7m.ptr(d, textab + 8 * i), pj7m.ptr(d, paltab + 8 * i)
                    if p is not None:
                        self._palettes.setdefault(t, p)
        return self._palettes.get(texture_offset)

    # ---- materials -----------------------------------------------------------------------------

    def local_material(self, model, mat, cache):
        """Index of a material of this model matching the Blender material, adding one if needed."""
        img = image_of(mat)
        tex, pal = self.texture_for(img)
        raw = bytes.fromhex(mat["pp_material"]) if mat is not None and "pp_material" in mat else None
        key = (raw, tex)
        if key in cache:
            return cache[key]
        # Blender materials are shared between pieces at import, so the same texture is enough:
        # prefer the identical material, else any of this model's materials with that texture.
        candidates = []
        for i, m in enumerate(model.materials):
            mt = model.textures[model.texmaps[m.texmaps[0]].texture].offset if m.texmaps else None
            if mt == tex:
                candidates.append((m.raw != raw, i))
        if candidates and tex is not None:
            cache[key] = min(candidates)[1]
            return cache[key]
        if tex is None:                                        # untextured: plain white texture
            white = np.full((4, 4, 4), 255, np.uint8)
            tex = self.w.add_texture_rgb5a3(packwii.tile(packwii.to_rgb5a3(white), 5).astype(">u2").tobytes(), 4, 4)
        template = raw or model.materials[0].raw
        cache[key] = self.w.add_material(model, template, tex, pal)
        return cache[key]

    # ---- pieces --------------------------------------------------------------------------------

    def mesh_groups(self, obj, model):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(depsgraph)
        me = ev.to_mesh()
        try:
            me.calc_loop_triangles()
            normals = np.empty(len(me.loops) * 3, np.float32)
            if hasattr(me, "corner_normals"):                  # Blender 4.1+
                me.corner_normals.foreach_get("vector", normals)
            else:
                me.loops.foreach_get("normal", normals)
            normals = normals.reshape(-1, 3)
            uv = me.uv_layers.active
            uvs = np.zeros((len(me.loops), 2), np.float32)
            if uv is not None:
                uv.data.foreach_get("uv", uvs.reshape(-1))
            col = me.color_attributes.get("Color")
            colors = np.full((len(me.loops), 4), 1.0, np.float32)
            if col is not None:
                raw = np.empty(len(col.data) * 4, np.float32)
                col.data.foreach_get("color", raw)
                raw = raw.reshape(-1, 4)
                if col.domain == "CORNER":
                    colors = raw
                else:
                    vi = np.empty(len(me.loops), np.int32)
                    me.loops.foreach_get("vertex_index", vi)
                    colors = raw[vi]
            co = np.empty(len(me.vertices) * 3, np.float32)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)

            cache, groups = {}, {}
            for lt in me.loop_triangles:
                slot = obj.material_slots[lt.material_index].material if lt.material_index < len(obj.material_slots) else None
                mi = self.local_material(model, slot, cache)
                g = groups.setdefault(mi, {"pos": {}, "nrm": {}, "clr": {}, "uv": {}, "corners": []})
                v0, v1, v2 = lt.vertices
                l0, l1, l2 = lt.loops
                for v, l in ((v0, l0), (v2, l2), (v1, l1)):             # back to GX clockwise order
                    p = g["pos"].setdefault(v, len(g["pos"]))
                    n = g["nrm"].setdefault(tuple(np.round(normals[l], 4)), len(g["nrm"]))
                    c = g["clr"].setdefault(tuple(int(x * 255 + 0.5) for x in colors[l]), len(g["clr"]))
                    t = g["uv"].setdefault((round(float(uvs[l][0]), 5), round(1.0 - float(uvs[l][1]), 5)), len(g["uv"]))
                    g["corners"].append((p, n, c, t))
            out = []
            for mi, g in groups.items():
                out.append(pj7m_write.MeshData(
                    mi, [to_game(co[v]) for v in g["pos"]], [to_game_dir(n) for n in g["nrm"]],
                    list(g["clr"]), list(g["uv"]), g["corners"]))
            return out
        finally:
            ev.to_mesh_clear()

    def placement(self, obj, record, local_points):
        mg = game_matrix(obj)
        loc, rot, scale = mg.decompose()
        euler = rot.to_euler("XYZ")
        pts = [mg @ Vector(p) for p in local_points]
        if not pts:
            return
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        centre = Vector([(lo[i] + hi[i]) / 2 for i in range(3)])
        radius = max((p - centre).length for p in pts)
        pj7m_write.set_placement(self.tbl, record.offset, tuple(loc), tuple(euler), tuple(scale),
                                 (*lo, *hi), (*centre, radius))
        self.stats["moved"] += 1

    def export(self, coll):
        present = {o.get("pp_model_offset"): o for o in coll.all_objects if o.get("pp_kind") == "model"}
        records = {p.model: p for p in self.table.placements} if self.table else {}
        for off in pj7m.find_models(bytes(self.w.d)):        # the original models; appended data has no tags
            model = pj7m.parse_model(self.w.d, off)
            obj = present.get(off)
            if obj is None:
                self.w.set_meshes(model, [])
                self.stats["emptied"] += 1
                continue
            mesh_changed = (obj.get("pp_signature") != fingerprint.mesh_signature(obj) or bool(obj.modifiers)
                            or any(self.image_changed(image_of(s.material)) for s in obj.material_slots))
            moved = obj.get("pp_matrix") != fingerprint.matrix_signature(obj)
            if not (mesh_changed or moved):
                continue
            if mesh_changed:
                meshes = self.mesh_groups(obj, model)
                self.w.set_meshes(pj7m.parse_model(self.w.d, off), meshes)
                self.stats["pieces"] += 1
                points = [p for m in meshes for p in m.positions]
            else:
                points = [to_game(v.co) for v in obj.data.vertices]
            if off in records and self.tbl is not None:
                self.placement(obj, records[off], points)
        self.w.d.extend(b"\0" * (-len(self.w.d) % 32))          # original packs end 32-byte aligned
        return bytes(self.w.d), bytes(self.tbl) if self.tbl is not None else None


def export_stadium(coll, mods_folder, mod_name, target_code):
    code = coll.get("pp_stadium")
    project_bin = coll.get("pp_project_bin")
    if not code or not project_bin or not Path(project_bin).is_file():
        raise ExportFailure("Esta colección no es un estadio importado (o ya no encuentro su project.bin)")
    archive = projectbin.Archive(project_bin)
    gfx, tbl = archive.read(f"stadium_{code}.pack"), archive.read(f"stadium_{code}tbl.pack")
    ex = Exporter(gfx, tbl)
    gfx_out, tbl_out = ex.export(coll)
    folder = Path(mods_folder) / mod_name
    (folder / "project").mkdir(parents=True, exist_ok=True)
    (folder / "project" / f"stadium_{target_code}.pack").write_bytes(gfx_out)
    if tbl_out is not None:
        (folder / "project" / f"stadium_{target_code}tbl.pack").write_bytes(tbl_out)
    toml = folder / "mod.toml"
    if not toml.exists():
        toml.write_text(f'name = "{mod_name}"\ndescription = "Estadio hecho con el complemento de Blender"\n',
                        encoding="utf-8")
    ex.stats["size"] = len(gfx_out)
    ex.stats["over_budget"] = len(gfx_out) > pj7m_write.BUDGET
    ex.stats["folder"] = str(folder)
    return ex.stats
