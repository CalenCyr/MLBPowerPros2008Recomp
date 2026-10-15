# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn any model (glTF, OBJ, SketchUp through a glTF converter...) into pieces of an imported stadium.

The game draws a stadium as a fixed list of pieces (PJ7M models) placed by the tbl, and culls each
piece by its box. A new model is therefore spread over the existing pieces: every face goes to the
piece whose box centre is nearest (ground-level flat faces to the ground piece). The game draws
stadiums unlit (texture x vertex colour), so the material colour and a simple sun are baked into
the vertex colours. Faces of two-sided materials get their back too: the game culls back faces.
The model must already be in the game's frame: metres, home plate at the origin, second base on +Y.
"""
import math

import bmesh
import bpy
from mathutils import Vector

# Pieces that receive the model: stands, fences and ground, never the special ones (alpha, additive,
# camera-dependent, crowd, lights, the video board the game may draw into, bases, z-test pieces).
TARGET = ("stand", "fence", "ground", "turf")
SKIP = ("ALP", "ADD", "EVC", "NOUPCAM", "FLG", "Audience", "lumine", "LIGHT", "BCL", "ANT", "ZTEST",
        "score", "aurora", "board")
SUN = Vector((0.35, -0.45, 0.82)).normalized()


class ConvertFailure(Exception):
    pass


def srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def material_info(mat):
    """(image or None, sRGB colour): the colour only matters for untextured materials."""
    if mat is None or mat.node_tree is None:
        return None, (tuple(srgb(v) for v in mat.diffuse_color[:3]) if mat else (1.0, 1.0, 1.0))
    img = next((n.image for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image), None)
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if img is not None or bsdf is None:
        return img, (1.0, 1.0, 1.0)
    return None, tuple(srgb(v) for v in bsdf.inputs["Base Color"].default_value[:3])


def targets(coll):
    """(ground piece, other opaque pieces) of an imported stadium."""
    pieces = [o for o in coll.all_objects if o.get("pp_kind") == "model" and not any(s in o.name for s in SKIP)
              and any(t in o.name.lower() for t in TARGET)]
    if not pieces:
        raise ConvertFailure("El estadio no tiene gradas, vallas ni suelo donde poner el modelo")

    def footprint(o):
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        return (max(p.x for p in pts) - min(p.x for p in pts)) * (max(p.y for p in pts) - min(p.y for p in pts))
    grounds = [o for o in pieces if "ground" in o.name.lower() or "turf" in o.name.lower()]
    ground = max(grounds or pieces, key=footprint)
    return ground, [o for o in pieces if o is not ground]


def box_centre(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(pts, Vector()) / 8


def convert(coll, sources, replace=True, bake_light=True):
    """Spread the faces of `sources` (mesh objects in the game's frame) over the stadium's pieces.
    replace: the pieces lose their own geometry and the pieces left without any are deleted.
    Returns {piece name: faces}. The source objects are removed."""
    ground, others = targets(coll)
    centres = {o.name: box_centre(o).xy for o in others}
    pieces = {o.name: o for o in [ground] + others}
    buckets, slots, plain, tex_mats = {}, {}, None, {}

    def bucket(name):
        if name not in buckets:
            bm = bmesh.new()
            bm.loops.layers.uv.new("UVMap")
            bm.loops.layers.float_color.new("Color")
            buckets[name], slots[name] = bm, []
        return buckets[name]

    def game_material(img):
        nonlocal plain
        if img is None:
            if plain is None:
                plain = bpy.data.materials.new("pp_color")       # untextured: colour in the vertices
                plain.use_nodes = True
            return plain
        if img.name not in tex_mats:
            m = bpy.data.materials.new("pp_" + img.name)
            m.use_nodes = True
            m.node_tree.nodes.new("ShaderNodeTexImage").image = img
            tex_mats[img.name] = m
        return tex_mats[img.name]

    info = {}
    for src in sources:
        me = src.data
        mw = src.matrix_world
        normal_mw = mw.to_3x3().inverted().transposed()
        uv = me.uv_layers.active
        for p in me.polygons:
            mat = src.material_slots[p.material_index].material if p.material_index < len(src.material_slots) else None
            if mat not in info:
                info[mat] = material_info(mat)
            img, colour = info[mat]
            vs = [mw @ me.vertices[i].co for i in p.vertices]
            c = sum(vs, Vector()) / len(vs)
            n = (normal_mw @ p.normal).normalized()
            flat = abs(n.z) > 0.95 and c.z < 1.0 and c.xy.length < 160
            name = ground.name if flat else min(centres, key=lambda k: (centres[k] - c.xy).length) if centres else ground.name
            bm = bucket(name)
            gm = game_material(img)
            if gm not in slots[name]:
                slots[name].append(gm)
            uvs = [tuple(uv.data[li].uv) for li in p.loop_indices] if uv else [(0.0, 0.0)] * len(vs)
            double = mat is not None and not mat.use_backface_culling
            sides = [False, True] if double else [False]
            if flat:                                # the field is only seen from above
                sides = [n.z < 0] if double else ([False] if n.z > 0 else [])
            for flip in sides:
                normal = -n if flip else n
                light = 0.55 + 0.45 * max(0.0, normal.dot(SUN)) if bake_light else 1.0
                col = (*(min(1.0, v * light) for v in colour), 1.0)
                order = list(range(len(vs)))[::-1] if flip else list(range(len(vs)))
                try:
                    f = bm.faces.new([bm.verts.new(vs[i]) for i in order])
                except ValueError:
                    continue
                f.material_index = slots[name].index(gm)
                for loop, i in zip(f.loops, order):
                    loop[bm.loops.layers.uv["UVMap"]].uv = uvs[i]
                    loop[bm.loops.layers.float_color["Color"]] = col
    if not buckets:
        raise ConvertFailure("Los objetos elegidos no tienen caras")

    result = {}
    if replace:                                 # the rest of the original stadium goes too
        for obj in [o for o in coll.all_objects if o.get("pp_kind") == "model" and o.name not in buckets]:
            pieces.pop(obj.name, None)
            bpy.data.objects.remove(obj)
    for name, obj in pieces.items():
        bm = buckets.get(name)
        if bm is None:
            continue
        bm.transform(obj.matrix_world.inverted())
        if replace:
            me = bpy.data.meshes.new(name)
            bm.to_mesh(me)
            obj.data = me
            for m in slots[name]:
                me.materials.append(m)
        else:
            old = bmesh.new()
            old.from_mesh(obj.data)
            offset = len(obj.data.materials)
            for m in slots[name]:
                obj.data.materials.append(m)
            _append(old, bm, offset)
            old.to_mesh(obj.data)
            old.free()
        bm.free()
        result[name] = len(obj.data.polygons)
    for src in sources:
        bpy.data.objects.remove(src)
    return result


def _append(dst, src, material_offset):
    """Copy the faces of bmesh `src` into `dst` (UV and Color layers created when missing)."""
    uv_d = dst.loops.layers.uv.active or dst.loops.layers.uv.new("UVMap")
    col_d = dst.loops.layers.float_color.get("Color") or dst.loops.layers.float_color.new("Color")
    uv_s, col_s = src.loops.layers.uv["UVMap"], src.loops.layers.float_color["Color"]
    for f in src.faces:
        try:
            nf = dst.faces.new([dst.verts.new(v.co) for v in f.verts])
        except ValueError:
            continue
        nf.material_index = f.material_index + material_offset
        for ld, ls in zip(nf.loops, f.loops):
            ld[uv_d].uv = ls[uv_s].uv
            ld[col_d] = ls[col_s]


def check_frame(objects):
    """Rough check that a model is in the game's frame (metres, home at the origin)."""
    pts = [o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
    if not pts:
        return None
    size = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(2))
    if size > 2000:
        return f"El modelo mide {size:.0f} m: ¿está en milímetros? Escálalo a metros primero"
    if size < 20:
        return f"El modelo mide {size:.1f} m: demasiado pequeño para un estadio"
    return None
