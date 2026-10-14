# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender menu entry, import operator and side panel (texts in Spanish, like the launcher)."""
import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from . import importer, names


class PP_OT_import_stadium(bpy.types.Operator, ImportHelper):
    """Importa un estadio de MLB Power Pros 2008 desde tu juego instalado"""
    bl_idname = "import_scene.powerpros_stadium"
    bl_label = "Importar estadio"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ""
    filter_glob: StringProperty(default="*.bin;*.exe;*.toml", options={"HIDDEN"})
    stadium: EnumProperty(name="Estadio", items=[(c, n, "") for c, n in names.STADIUMS], default="col")
    collision: BoolProperty(name="Incluir colisión", default=True,
                            description="Malla de colisión del campo, oculta, coloreada por tipo de superficie")

    def draw(self, context):
        layout = self.layout
        layout.label(text="Elige la carpeta del juego o files/project.bin")
        layout.prop(self, "stadium")
        layout.prop(self, "collision")

    def execute(self, context):
        try:
            coll, objects, images = importer.import_stadium(context, self.filepath, self.stadium, self.collision)
        except importer.ImportFailure as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, f"{coll.name}: {len(objects)} piezas, {len(images)} texturas")
        return {"FINISHED"}


class PP_PT_info(bpy.types.Panel):
    bl_label = "Power Pros"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Power Pros"

    def draw(self, context):
        layout = self.layout
        layout.operator(PP_OT_import_stadium.bl_idname, icon="IMPORT")
        obj = context.active_object
        if obj is None or "pp_kind" not in obj:
            layout.label(text="Selecciona una pieza de un estadio importado")
            return
        box = layout.box()
        if obj["pp_kind"] == "collision":
            box.label(text="Malla de colisión")
            face = obj.data.polygons.active
            attr = obj.data.attributes.get("surface_id")
            if attr is not None and face is not None and face < len(attr.data):
                box.label(text=f"Superficie de la cara activa: {attr.data[face].value}")
            return
        box.label(text=f"Pieza: {obj.name}")
        box.label(text=f"Modelo: {obj.get('pp_wmodel', '')}")
        box.label(text=f"Nodo de Maya: {obj.get('pp_node', '')}")
        if "pp_placement_flags" in obj:
            box.label(text=f"Flags de colocación: {obj['pp_placement_flags']}")
        mat = obj.active_material
        if mat is not None:
            box.label(text=f"Material: {mat.name}")


def menu_import(self, context):
    self.layout.operator(PP_OT_import_stadium.bl_idname, text="Estadio de Power Pros 2008")


CLASSES = (PP_OT_import_stadium, PP_PT_info)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
