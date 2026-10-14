# SPDX-License-Identifier: GPL-3.0-or-later
"""MLB Power Pros 2008 stadiums for Blender. The format modules (pj7m, stadium_tbl) do not need
Blender, so tools/stadium_re.py imports this package outside it; bpy is only loaded on register."""


def register():
    from . import blender_ui
    blender_ui.register()


def unregister():
    from . import blender_ui
    blender_ui.unregister()
