# SPDX-License-Identifier: GPL-3.0-or-later
"""Spanish/English texts of the add-on: T("texto", "text") picks one by the add-on preference.

Auto follows Blender's interface language (Spanish when it starts with "es", English otherwise).
bpy is imported lazily: the format modules use T in their errors and also run outside Blender
(selftest.py, tools/stadium_re.py), where the texts stay in Spanish as before.
"""

CONTEXT = "PowerPros"       # own translation context: Blender must not translate our labels again


def blender_is_spanish():
    import bpy
    view = bpy.context.preferences.view
    if not getattr(view, "use_translate_interface", True):
        return False
    locale = bpy.app.translations.locale or ""
    if not locale and view.language not in ("DEFAULT", "en_US"):
        locale = view.language
    return locale.lower().startswith("es")


def language():
    """'es' or 'en'."""
    try:
        import bpy
    except ImportError:
        return "es"
    try:
        addon = bpy.context.preferences.addons.get(__package__)
        choice = addon.preferences.language if addon is not None and addon.preferences is not None else "AUTO"
        if choice in ("ES", "EN"):
            return choice.lower()
        return "es" if blender_is_spanish() else "en"
    except AttributeError:          # restricted context while Blender starts
        return "es" if (bpy.app.translations.locale or "").lower().startswith("es") else "en"


def T(es, en):
    return es if language() == "es" else en
