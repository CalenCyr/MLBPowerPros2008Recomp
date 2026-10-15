# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender menu entry, import operator and side panel (texts in Spanish, like the launcher)."""
from pathlib import Path

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from . import collision_gen, convert, exporter, importer, names


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


def stadium_collection(context):
    """The imported stadium the active object belongs to, or the only one in the scene."""
    obj = context.active_object
    found = [c for c in bpy.data.collections if "pp_stadium" in c]
    if obj is not None:
        for c in found:
            if obj.name in c.all_objects:
                return c
    return found[0] if len(found) == 1 else None


class PP_OT_export_stadium(bpy.types.Operator):
    """Escribe el estadio editado como mod: mods/<nombre>/project/stadium_<código>.pack y su tabla"""
    bl_idname = "export_scene.powerpros_stadium"
    bl_label = "Exportar mod de estadio"
    bl_options = {"REGISTER"}

    mod_name: StringProperty(name="Nombre del mod", default="Mi estadio")
    mods_folder: StringProperty(name="Carpeta de mods", subtype="DIR_PATH",
                                description="La carpeta mods junto al juego instalado")
    mode: EnumProperty(name="Tipo", items=[
        ("new", "Estadio nuevo", "Se añade como una entrada más en la elección de estadio; no quita ninguno"),
        ("replace", "Reemplazar un estadio", "Sustituye a un estadio del juego")])
    new_code: StringProperty(name="Código", default="miestadio",
                             description="Identificador corto: letras minúsculas, números o _ (p. ej. truist)")
    new_name: StringProperty(name="Nombre", default="Mi estadio")
    target: EnumProperty(name="Reemplaza a", items=[("same", "El mismo estadio", "")] +
                         [(c, n, "") for c, n in names.STADIUMS])

    @classmethod
    def poll(cls, context):
        return stadium_collection(context) is not None

    def invoke(self, context, event):
        coll = stadium_collection(context)
        if not self.mods_folder and coll.get("pp_game_folder"):
            self.mods_folder = str(Path(coll["pp_game_folder"]) / "mods")
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "mod_name")
        layout.prop(self, "mods_folder")
        layout.prop(self, "mode", expand=True)
        if self.mode == "new":
            layout.prop(self, "new_code")
            layout.prop(self, "new_name")
            layout.label(text="Usa los datos de juego (medidas, menú) del estadio importado.")
        else:
            layout.prop(self, "target")
        layout.label(text="Solo se reescriben las piezas que cambiaste.")

    def execute(self, context):
        coll = stadium_collection(context)
        if not self.mods_folder:
            self.report({"ERROR"}, "Elige la carpeta mods del juego")
            return {"CANCELLED"}
        if self.mode == "new":
            target, new_name = self.new_code.strip().lower(), self.new_name.strip() or "Mi estadio"
        else:
            target, new_name = (coll["pp_stadium"] if self.target == "same" else self.target), None
        try:
            st = exporter.export_stadium(coll, bpy.path.abspath(self.mods_folder), self.mod_name.strip() or "Mi estadio",
                                         target, new_name)
        except (exporter.ExportFailure, ValueError) as e:            # tbl_write.TreeError is a ValueError
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        msg = (f"Mod en {st['folder']}: {st['pieces']} piezas reescritas, {st['moved']} movidas, "
               f"{st['emptied']} quitadas, {st['textures']} texturas nuevas, {st['size'] / 1048576:.1f} MB")
        if st["collision"]:
            msg += f", colisión nueva de {st['collision']} triángulos"
        if st["over_budget"]:
            self.report({"WARNING"}, msg + ". Pasa de 20 MB: puede que el partido no cargue.")
        else:
            self.report({"INFO"}, msg + ". Actívalo en MODS del launcher.")
        return {"FINISHED"}


class PP_OT_convert_objects(bpy.types.Operator):
    """Reparte las caras de los objetos seleccionados (un modelo propio) entre las piezas del estadio"""
    bl_idname = "object.powerpros_convert"
    bl_label = "Convertir objetos en piezas"
    bl_options = {"REGISTER", "UNDO"}

    replace: BoolProperty(name="Quitar el estadio original", default=True,
                          description="Las piezas pierden su geometría y las que no reciban nada se borran")
    bake_light: BoolProperty(name="Sombreado simple", default=True,
                             description="El juego dibuja los estadios sin luz: guarda un sol suave en los colores")

    @classmethod
    def poll(cls, context):
        return stadium_collection(context) is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.label(text="El modelo debe estar en metros, con el plato en el origen")
        layout.label(text="y la segunda base hacia +Y (como el estadio importado).")
        layout.prop(self, "replace")
        layout.prop(self, "bake_light")

    def execute(self, context):
        coll = stadium_collection(context)
        sources = [o for o in context.selected_objects if o.type == "MESH" and "pp_kind" not in o]
        if not sources:
            self.report({"ERROR"}, "Selecciona los objetos de tu modelo (no las piezas del estadio)")
            return {"CANCELLED"}
        warning = convert.check_frame(sources)
        if warning:
            self.report({"ERROR"}, warning)
            return {"CANCELLED"}
        try:
            result = convert.convert(coll, sources, self.replace, self.bake_light)
        except convert.ConvertFailure as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Modelo repartido en {len(result)} piezas ({sum(result.values())} caras). "
                              "Genera la colisión si cambiaste el campo o las vallas.")
        return {"FINISHED"}


class PP_OT_generate_collision(bpy.types.Operator):
    """Crea la colisión del estadio a partir de sus piezas: suelo, vallas, postes de foul y gradas"""
    bl_idname = "object.powerpros_generate_collision"
    bl_label = "Generar colisión"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return stadium_collection(context) is not None

    def execute(self, context):
        obj = collision_gen.generate(stadium_collection(context))
        if obj is None:
            self.report({"ERROR"}, "No encuentro el campo: hace falta suelo a la altura 0 y paredes alrededor del plato")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Colisión nueva: {len(obj.data.polygons)} triángulos")
        return {"FINISHED"}


class PP_PT_info(bpy.types.Panel):
    bl_label = "Power Pros"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Power Pros"

    def draw(self, context):
        layout = self.layout
        layout.operator(PP_OT_import_stadium.bl_idname, icon="IMPORT")
        layout.operator(PP_OT_export_stadium.bl_idname, icon="EXPORT")
        layout.operator(PP_OT_convert_objects.bl_idname, icon="MESH_DATA")
        layout.operator(PP_OT_generate_collision.bl_idname, icon="MOD_PHYSICS")
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


def menu_export(self, context):
    self.layout.operator(PP_OT_export_stadium.bl_idname, text="Mod de estadio de Power Pros 2008")


CLASSES = (PP_OT_import_stadium, PP_OT_export_stadium, PP_OT_convert_objects, PP_OT_generate_collision, PP_PT_info)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
