# SPDX-License-Identifier: GPL-3.0-or-later
"""Decode PJ7M textures to RGBA arrays with tools/packwii.py's GX decoders (numpy)."""
import numpy as np

try:
    from . import packwii                  # copied into the add-on zip by build_addon.py
except ImportError:
    import packwii                         # repository: tools/ is on sys.path


def rgba(d, tex):
    """(height, width, 4) uint8 image, top row first, as the game samples it."""
    size = packwii.nbytes(tex.width, tex.height, tex.fmt)
    pixels = bytes(d[tex.pixels:tex.pixels + size])
    palette = None
    if tex.palette is not None and tex.palette_size:
        palette = np.frombuffer(d, ">u2", count=tex.palette_size, offset=tex.palette)
    return packwii.decode(pixels, tex.width, tex.height, tex.fmt, palette)
