# SPDX-License-Identifier: GPL-3.0-or-later
"""Fingerprints taken at import so the exporter rewrites only what the player changed."""
import hashlib

import numpy as np


def _feed(h, collection, attr, size, dtype):
    data = np.empty(len(collection) * size, dtype)
    if len(collection):
        collection.foreach_get(attr, data)
    h.update(data.tobytes())


def mesh_signature(obj):
    """Hash of the object's mesh data and material assignment (not its transform)."""
    me = obj.data
    h = hashlib.sha1()
    _feed(h, me.vertices, "co", 3, np.float32)
    _feed(h, me.loops, "vertex_index", 1, np.int32)
    _feed(h, me.polygons, "loop_start", 1, np.int32)
    _feed(h, me.polygons, "material_index", 1, np.int32)
    if me.uv_layers.active is not None:
        _feed(h, me.uv_layers.active.data, "uv", 2, np.float32)
    col = me.color_attributes.get("Color")
    if col is not None:
        _feed(h, col.data, "color", 4, np.float32)
    h.update("|".join(m.name if m else "" for m in me.materials).encode())
    for m in me.materials:
        if m is not None and m.node_tree is not None:
            for node in m.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image is not None:
                    h.update(node.image.name.encode())
    return h.hexdigest()


def matrix_signature(obj):
    return hashlib.sha1(np.asarray(obj.matrix_world, np.float32).round(5).tobytes()).hexdigest()


def image_hash(img):
    data = np.empty(len(img.pixels), np.float32)
    img.pixels.foreach_get(data)
    return hashlib.sha1((data * 255 + 0.5).astype(np.uint8).tobytes()).hexdigest()
