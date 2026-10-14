# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a Blender collection from a stadium of the player's project.bin."""
import colorsys
import tomllib
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix

from . import names, pj7m, stadium_tbl, textures

try:
    from . import projectbin                 # copied into the add-on zip by build_addon.py
except ImportError:
    import projectbin                        # repository: tools/ is on sys.path

# Game space: decimetres, Y up, -Z towards centre field. Blender: metres, Z up, +Y towards centre field.
TO_BLENDER = Matrix.Scale(0.1, 4) @ Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
FROM_BLENDER = TO_BLENDER.inverted()


class ImportFailure(Exception):
    pass


def find_project_bin(path):
    """project.bin from what the player picked: the file itself, the game folder or the data folder."""
    path = Path(path)
    if path.is_file() and path.name.lower() == "project.bin":
        return path
    folder = path if path.is_dir() else path.parent
    config = folder / "UserData" / "Config.toml"
    candidates = []
    if config.is_file():
        try:
            dvd = tomllib.loads(config.read_text(encoding="utf-8")).get("paths", {}).get("dvd_root")
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            dvd = None
        if dvd:
            candidates.append(Path(dvd) / "files" / "project.bin")
    candidates += [folder / "files" / "project.bin", folder / "project.bin"]
    for c in candidates:
        if c.is_file():
            return c
    raise ImportFailure("No encuentro project.bin. Elige la carpeta del juego instalado con el Setup "
                        "(la que tiene UserData) o el archivo files/project.bin.")


def to_blender(v):
    x, y, z = v
    return (0.1 * x, -0.1 * z, 0.1 * y)


def placement_matrix(pl):
    if pl is None:
        return Matrix.Identity(4)
    game = (Matrix.Translation(pl.translation) @ Euler(pl.rotation, "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal((*pl.scale, 1.0)))
    return TO_BLENDER @ game @ FROM_BLENDER


def make_image(gfx, tex, cache):
    """(image, has transparent texels), decoded once per texture."""
    if tex.offset in cache:
        return cache[tex.offset]
    pixels = textures.rgba(gfx, tex)
    img = bpy.data.images.new(f"tex_{tex.offset:06X}", tex.width, tex.height, alpha=True)
    img.pixels.foreach_set((pixels[::-1].astype(np.float32) / 255.0).ravel())   # Blender rows go bottom-up
    img.pack()
    img["pp_texture_offset"] = tex.offset
    cache[tex.offset] = (img, bool((pixels[..., 3] < 255).any()))
    return cache[tex.offset]


def make_material(gfx, model, index, images, cache):
    """Unlit like the stadium in the game: texture x vertex colour, alpha blended.
    Pieces named *_ADD_* are drawn additive (name convention of the game's artists; the flag
    that selects the blend mode is not decoded yet)."""
    mat_data = model.materials[index]
    tex = model.textures[model.texmaps[mat_data.texmaps[0]].texture] if mat_data.texmaps else None
    additive = "_ADD_" in model.name + "_"
    key = (mat_data.raw, tex.offset if tex else None, additive)
    if key in cache:
        return cache[key]
    mat = bpy.data.materials.new(f"{model.name}_mat{index}")
    mat["pp_material"] = mat_data.raw.hex()
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    vcol = nt.nodes.new("ShaderNodeVertexColor")
    vcol.layer_name = "Color"
    vcol.location = (-600, -100)
    color, alpha, transparent = vcol.outputs["Color"], vcol.outputs["Alpha"], False
    if tex is not None:
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image, transparent = make_image(gfx, tex, images)
        node.location = (-600, 250)
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.location = (-300, 200)
        nt.links.new(node.outputs["Color"], mix.inputs[6])         # A and B of the RGBA mode
        nt.links.new(vcol.outputs["Color"], mix.inputs[7])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.location = (-300, -100)
        nt.links.new(node.outputs["Alpha"], mul.inputs[0])
        nt.links.new(vcol.outputs["Alpha"], mul.inputs[1])
        color, alpha = mix.outputs[2], mul.outputs["Value"]
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.location = (-50, 150)
    nt.links.new(color, emit.inputs["Color"])
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    clear.location = (-50, -100)
    if additive:
        nt.links.new(alpha, emit.inputs["Strength"])
        both = nt.nodes.new("ShaderNodeAddShader")
        nt.links.new(emit.outputs[0], both.inputs[0])
        nt.links.new(clear.outputs[0], both.inputs[1])
    else:
        both = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(alpha, both.inputs["Fac"])
        nt.links.new(clear.outputs[0], both.inputs[1])
        nt.links.new(emit.outputs[0], both.inputs[2])
    both.location = (200, 0)
    nt.links.new(both.outputs[0], out.inputs["Surface"])
    if transparent or additive:
        mat.surface_render_method = "BLENDED"
        mat.use_backface_culling = False
    cache[key] = mat
    return mat


def build_mesh(gfx, model, images, materials):
    verts, loops_v, loop_nrm, loop_uv, loop_col, face_mat = [], [], [], [], [], []
    me = bpy.data.meshes.new(model.name)
    slots = {}
    for mesh in model.meshes:
        base = len(verts)
        pos = pj7m.array(gfx, mesh, "pos")
        nrm = pj7m.array(gfx, mesh, "nrm")
        clr = pj7m.array(gfx, mesh, "clr")
        tex = pj7m.array(gfx, mesh, "tex")
        verts += [to_blender(p) for p in pos]
        if mesh.material not in slots:
            slots[mesh.material] = len(slots)
            me.materials.append(make_material(gfx, model, mesh.material, images, materials))
        for tri in pj7m.triangles(mesh):
            for v in (tri[0], tri[2], tri[1]):          # GX is clockwise-front; Blender counter-clockwise
                loops_v.append(base + v[1])
                loop_nrm.append(to_blender(nrm[v[2]]))
                loop_col.append(clr[v[3]])
                u, t = tex[v[4]]
                loop_uv.append((u, 1.0 - t))
            face_mat.append(slots[mesh.material])
    nface = len(face_mat)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", np.asarray(verts, np.float32).ravel())
    me.loops.add(len(loops_v))
    me.loops.foreach_set("vertex_index", np.asarray(loops_v, np.int32))
    me.polygons.add(nface)
    me.polygons.foreach_set("loop_start", np.arange(0, 3 * nface, 3, dtype=np.int32))
    me.polygons.foreach_set("material_index", np.asarray(face_mat, np.int32))
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", np.asarray(loop_uv, np.float32).ravel())
    col = me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
    col.data.foreach_set("color", (np.asarray(loop_col, np.float32) / 255.0).ravel())
    nrm_attr = me.attributes.new("pp_normal", "FLOAT_VECTOR", "CORNER")
    nrm_attr.data.foreach_set("vector", np.asarray(loop_nrm, np.float32).ravel())
    me.validate(clean_customdata=False)
    me.update()
    normals = np.empty(len(me.loops) * 3, np.float32)
    me.attributes["pp_normal"].data.foreach_get("vector", normals)
    me.attributes.remove(me.attributes["pp_normal"])
    me.normals_split_custom_set(normals.reshape(-1, 3))
    return me


def build_collision(table, parent):
    me = bpy.data.meshes.new("Colisión")
    me.from_pydata([to_blender(v) for v in table.vertices], [],
                   [(a, c, b) for a, b, c, _ in table.triangles])
    ids = sorted({t[3] for t in table.triangles})
    for i in ids:
        mat = bpy.data.materials.new(f"Superficie {i}")
        r, g, b = colorsys.hsv_to_rgb((i * 0.618034) % 1.0, 0.65, 0.95)
        mat.diffuse_color = (r, g, b, 1.0)
        me.materials.append(mat)
    slot = {i: k for k, i in enumerate(ids)}
    me.polygons.foreach_set("material_index", np.asarray([slot[t[3]] for t in table.triangles], np.int32))
    attr = me.attributes.new("surface_id", "INT", "FACE")
    attr.data.foreach_set("value", np.asarray([t[3] for t in table.triangles], np.int32))
    me.validate()
    me.update()
    obj = bpy.data.objects.new("Colisión", me)
    obj["pp_kind"] = "collision"
    parent.objects.link(obj)
    return obj


def import_stadium(context, path, code, collision=True):
    project_bin = find_project_bin(path)
    archive = projectbin.Archive(project_bin)
    gfx = archive.read(f"stadium_{code}.pack")
    tbl = archive.read(f"stadium_{code}tbl.pack")
    if gfx is None:
        raise ImportFailure(f"project.bin no tiene stadium_{code}.pack")
    table = stadium_tbl.parse_table(tbl) if tbl else None
    if table is None:
        offsets = pj7m.find_models(gfx)
        placements = [None] * len(offsets)
    else:
        placements = table.placements
        offsets = [pl.model for pl in placements]

    coll = bpy.data.collections.new(names.NAMES.get(code, code))
    coll["pp_stadium"] = code
    context.scene.collection.children.link(coll)
    images, materials, objects = {}, {}, []
    for off, pl in zip(offsets, placements):
        model = pj7m.parse_model(gfx, off)
        obj = bpy.data.objects.new(model.name, build_mesh(gfx, model, images, materials))
        obj.matrix_world = placement_matrix(pl)
        obj["pp_kind"] = "model"
        obj["pp_model_offset"] = off
        obj["pp_wmodel"] = model.wname
        obj["pp_node"] = model.node_name
        if pl is not None:
            obj["pp_placement_flags"] = f"0x{pl.flags:08X}"
            obj["pp_translation"] = pl.translation
            obj["pp_rotation"] = pl.rotation
            obj["pp_scale"] = pl.scale
        coll.objects.link(obj)
        objects.append(obj)

    if collision and table and table.triangles:
        sub = bpy.data.collections.new(f"{coll.name} · Colisión")
        sub.hide_render = True           # its 70 m invisible walls would hide the stands in renders
        coll.children.link(sub)
        build_collision(table, sub)
        layer = context.view_layer.layer_collection.children[coll.name].children[sub.name]
        layer.hide_viewport = True
    return coll, objects, images
