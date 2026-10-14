# SPDX-License-Identifier: GPL-3.0-or-later
"""Textures inside MLB Power Pros 2008's PACKWII files (the .pack entries of PROJECT.BIN).

A PACKWII file is a big-endian object graph: "PACKWII " + u32 0, u32 entry count, pointer to the
entry table, u32 0x20 (header size), then objects. A pointer is 0x40000000 | file offset; an entry
is {u32 0, u32 id, pointer}. Most packs have no table: the game reaches their objects through a
root structure. Textures come in two header layouts (docs/ingenieria-inversa.md, section 5):

  model   u16 w, u16 h, u8 type (0x80 RGBA8, 0x81 RGB5A3, 0x82 C8, 0x84 C4), ..., +0x08 pixels,
          four 0x82000000 words; a C4/C8 texture is followed (+0x24) by its palette header.
  layout  u16 w, u16 h, u32 GX format, +0x08 pixels, +0x14 1, +0x18 1; +0x24 u16 palette size,
          +0x28 u32 palette format, +0x2C palette data (0 when the palette lives elsewhere).
  palette u16 entries (16 or 256), u16 0, u8 0x81, u8 0, u16 0x6000, +0x08 RGB5A3 data.

A layout palette that lives elsewhere is found through texture sets: {u32 n, -> n texture
headers, u32 m, -> m palettes} (one palette for all, or one each). About 96% of the paletted
textures pair this way. Others pair by position (palette data right after the pixels; checked
against the runtime's texture dumps). The game can swap palettes at run time, so a position-paired
palette is kept on import. The rest (palette in another pack) export in grey and cannot be imported.

usage:
  packwii.py info <file.pack>
  packwii.py export <file.pack> <out dir>          PNGs + textures.json (keep it for import)
  packwii.py import <file.pack> <png dir> <out.pack>
      re-encodes every PNG that differs from the original texture (same size). An exclusive
      palette is rebuilt; a shared or position-paired one keeps its colours and pixels take the
      nearest one.
  packwii.py selftest                              encoder/decoder check, no game data needed
Needs numpy and Pillow. Never commit extracted textures or packs: they are game content.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

POW2 = {4, 8, 16, 32, 64, 128, 256, 512, 1024}
MODEL_FMT = {0x80: 6, 0x81: 5, 0x82: 9, 0x84: 8}       # model type byte -> GX format
BPP = {0: 4, 1: 8, 2: 8, 3: 16, 4: 16, 5: 16, 6: 32, 8: 4, 9: 8, 10: 16, 14: 4}
BLOCK = {0: (8, 8), 1: (8, 4), 2: (8, 4), 3: (4, 4), 4: (4, 4), 5: (4, 4), 6: (4, 4), 8: (8, 8),
         9: (8, 4), 10: (4, 4), 14: (8, 8)}
SUPPORTED = {0, 1, 5, 6, 8, 9}                         # I4, I8, RGB5A3, RGBA8, C4, C8


def ptr(d, o):
    p = struct.unpack_from(">I", d, o)[0]
    return p & 0x3FFFFFFF if p >> 30 == 1 else None


def padded(w, h, fmt):
    bw, bh = BLOCK[fmt]
    return (w + bw - 1) // bw * bw, (h + bh - 1) // bh * bh


def nbytes(w, h, fmt):
    pw, ph = padded(w, h, fmt)
    return pw * ph * BPP[fmt] // 8


# ---- pixel formats -------------------------------------------------------------------------------

def from_rgb5a3(v):
    v = v.astype(np.uint32)
    opaque = (v & 0x8000) != 0
    out = np.empty(v.shape + (4,), np.uint8)
    out[..., 0] = np.where(opaque, ((v >> 10) & 31) * 255 // 31, ((v >> 8) & 15) * 17)
    out[..., 1] = np.where(opaque, ((v >> 5) & 31) * 255 // 31, ((v >> 4) & 15) * 17)
    out[..., 2] = np.where(opaque, (v & 31) * 255 // 31, (v & 15) * 17)
    out[..., 3] = np.where(opaque, 255, ((v >> 12) & 7) * 255 // 7)
    return out


def to_rgb5a3(rgba):
    r, g, b, a = (rgba[..., i].astype(np.uint32) for i in range(4))
    opaque = (1 << 15) | ((r * 31 + 127) // 255 << 10) | ((g * 31 + 127) // 255 << 5) | ((b * 31 + 127) // 255)
    clear = ((a * 7 + 127) // 255 << 12) | ((r * 15 + 127) // 255 << 8) | ((g * 15 + 127) // 255 << 4) | ((b * 15 + 127) // 255)
    return np.where(a >= 0xE0, opaque, clear).astype(">u2")


def untile(values, w, h, fmt):
    bw, bh = BLOCK[fmt]
    pw, ph = padded(w, h, fmt)
    return values[:pw * ph].reshape(ph // bh, pw // bw, bh, bw).transpose(0, 2, 1, 3).reshape(ph, pw)[:h, :w]


def tile(image, fmt):
    bw, bh = BLOCK[fmt]
    h, w = image.shape[:2]
    pw, ph = padded(w, h, fmt)
    full = np.zeros((ph, pw) + image.shape[2:], image.dtype)
    full[:h, :w] = image
    return full.reshape(ph // bh, bh, pw // bw, bw, *image.shape[2:]).swapaxes(1, 2).reshape(-1, *image.shape[2:])


def values(pixels, w, h, fmt):
    """Untiled texel values (h, w) of a 4-, 8- or 16-bit format."""
    raw = np.frombuffer(pixels, np.uint8, count=nbytes(w, h, fmt))
    if fmt in (0, 8):
        vals = np.empty(raw.size * 2, np.uint8)
        vals[0::2], vals[1::2] = raw >> 4, raw & 15
    elif fmt in (1, 9):
        vals = raw
    else:
        vals = raw.view(">u2")
    return untile(vals, w, h, fmt)


def decode(pixels, w, h, fmt, palette=None):
    """RGBA image (h, w, 4). palette: RGB5A3 u16 entries, or None (grey indices)."""
    if fmt == 6:
        raw = np.frombuffer(pixels, np.uint8, count=nbytes(w, h, fmt))
        pw, ph = padded(w, h, fmt)
        t = raw.reshape(-1, 2, 16, 2)
        rgba = np.stack([t[:, 0, :, 1], t[:, 1, :, 0], t[:, 1, :, 1], t[:, 0, :, 0]], -1).reshape(-1, 4)
        return rgba[untile(np.arange(pw * ph), w, h, fmt)]
    img = values(pixels, w, h, fmt)
    if fmt == 5:
        return from_rgb5a3(img)
    if fmt in (8, 9):
        if palette is None:
            img = (img * (17 if fmt == 8 else 1)).astype(np.uint8)
        else:
            return from_rgb5a3(palette)[np.minimum(img, len(palette) - 1)]
    if fmt == 0:
        img = (img * 17).astype(np.uint8)
    return np.stack([img, img, img, np.full_like(img, 255)], -1).astype(np.uint8)


def encode(rgba, fmt, palette=None, keep=None):
    """Pixel bytes for an RGBA image; C4/C8 need the palette (RGB5A3 u16) to index into.
    keep: (original indices, mask of unchanged pixels) so those keep their exact index."""
    if fmt == 6:
        t = tile(rgba, fmt).reshape(-1, 16, 4)
        out = np.empty((t.shape[0], 2, 16, 2), np.uint8)
        out[:, 0, :, 0], out[:, 0, :, 1] = t[..., 3], t[..., 0]
        out[:, 1, :, 0], out[:, 1, :, 1] = t[..., 1], t[..., 2]
        return out.tobytes()
    if fmt == 5:
        return tile(to_rgb5a3(rgba), fmt).astype(">u2").tobytes()
    if fmt in (0, 1):
        grey = (rgba[..., :3].astype(np.uint32).sum(-1) // 3).astype(np.uint8)
        idx = tile(grey >> 4 if fmt == 0 else grey, fmt)
    else:
        colors = from_rgb5a3(palette).astype(np.int32)
        flat = rgba.reshape(-1, 4).astype(np.int32)
        dist = ((flat[:, None, :] - colors[None, :, :]) ** 2).sum(-1)
        idx = dist.argmin(1).astype(np.uint8).reshape(rgba.shape[:2])
        if keep is not None:                     # a palette can repeat a colour: keep the index
            idx = np.where(keep[1], keep[0], idx)
        idx = tile(idx, fmt)
    if fmt in (0, 8):
        return ((idx[0::2] << 4) | idx[1::2]).astype(np.uint8).tobytes()
    return idx.astype(np.uint8).tobytes()


def new_palette(rgba, entries):
    """A palette of `entries` RGB5A3 colours for the image (Pillow's quantizer)."""
    from PIL import Image
    q = Image.fromarray(rgba, "RGBA").quantize(colors=entries, method=Image.Quantize.FASTOCTREE)
    pal = np.array(q.getpalette("RGBA")[:entries * 4], np.uint8).reshape(-1, 4)
    pal = np.vstack([pal, np.zeros((entries - len(pal), 4), np.uint8)])
    return to_rgb5a3(pal)


# ---- finding textures ----------------------------------------------------------------------------

def find_textures(d):
    texs, pals = [], {}
    for o in range(0x20, len(d) - 12, 4):
        w, h = struct.unpack_from(">HH", d, o)
        p = ptr(d, o + 8)
        if p is None or p >= len(d):
            continue
        kind_byte = d[o + 4]
        if h == 0 and kind_byte == 0x81 and w in (16, 256) and p + 2 * w <= len(d):
            pals[o] = (w, p)
            continue
        if w not in POW2 or h not in POW2:
            continue
        if kind_byte in MODEL_FMT and d[o + 5] == 0:
            fmt, kind = MODEL_FMT[kind_byte], "model"
        elif d[o + 4] == 0 and struct.unpack_from(">I", d, o + 4)[0] in BPP:
            fmt, kind = struct.unpack_from(">I", d, o + 4)[0], "layout"
        else:
            continue
        if p + nbytes(w, h, fmt) > len(d):
            continue
        t = dict(off=o, w=w, h=h, fmt=fmt, data=p, kind=kind, pal=None, fixed=False)
        if kind == "layout" and o + 0x30 <= len(d):
            n = struct.unpack_from(">H", d, o + 0x24)[0]
            pp = ptr(d, o + 0x2C)
            if n in (16, 256) and pp is not None and pp + 2 * n <= len(d):
                t["pal"] = (n, pp)
        texs.append(t)
    byoff = {t["off"]: t for t in texs}
    for o in range(0x20, len(d) - 16, 4):         # texture sets
        c1, c2 = struct.unpack_from(">I", d, o)[0], struct.unpack_from(">I", d, o + 8)[0]
        l1, l2 = ptr(d, o + 4), ptr(d, o + 12)
        if not (0 < c1 < 4096 and 0 < c2 < 4096) or l1 is None or l2 is None:
            continue
        if l1 + 4 * c1 > len(d) or l2 + 4 * c2 > len(d):
            continue
        tl = [ptr(d, l1 + 4 * i) for i in range(c1)]
        pl = [ptr(d, l2 + 4 * i) for i in range(c2)]
        if all(x in byoff for x in tl) and all(x in pals for x in pl):
            for i, x in enumerate(tl):
                if byoff[x]["fmt"] in (8, 9) and byoff[x]["pal"] is None:
                    byoff[x]["pal"] = pals[pl[i] if len(pl) == len(tl) else pl[0]]
    # Pairing by position only: the game may draw these with another palette (env_mainmenu.pack
    # 0x163a0 does), so import keeps their palette and the indices of unedited pixels.
    for t in texs:
        if t["fmt"] not in (8, 9) or t["pal"] is not None:
            continue
        t["fixed"] = True
        want = 16 if t["fmt"] == 8 else 256
        end = t["data"] + nbytes(t["w"], t["h"], t["fmt"])
        if t["kind"] == "model" and t["off"] + 0x24 in pals:          # palette header follows
            t["pal"] = pals[t["off"] + 0x24]
        else:      # palette data right after the pixels (the header just before is the previous texture's)
            t["pal"] = next((pal for pal in pals.values() if pal == (want, end)), None)
    return texs


def palette_of(d, t):
    if t["pal"] is None:
        return None
    n, p = t["pal"]
    return np.frombuffer(d, ">u2", count=n, offset=p).copy()


def image_of(d, t):
    return decode(d[t["data"]:], t["w"], t["h"], t["fmt"], palette_of(d, t))


# ---- commands ------------------------------------------------------------------------------------

def check_pack(d):
    if d[:8] != b"PACKWII ":
        sys.exit("not a PACKWII file")


def info(path):
    d = Path(path).read_bytes()
    check_pack(d)
    count, table = struct.unpack_from(">I", d, 0x0C)[0], ptr(d, 0x10)
    print(f"{path}: {len(d)} bytes, {count} table entries" + (f" at {table:#x}" if count else ""))
    for i in range(count):
        _, ident, _ = struct.unpack_from(">III", d, table + 12 * i)
        print(f"  entry {i}: id {ident:#x} -> {ptr(d, table + 12 * i + 8):#x}")
    names = {0: "I4", 1: "I8", 5: "RGB5A3", 6: "RGBA8", 8: "C4", 9: "C8"}
    for t in find_textures(d):
        pal = "" if t["fmt"] not in (8, 9) else f" palette {t['pal'][1]:#x}" if t["pal"] else " palette ?"
        print(f"  texture {t['off']:#x} {t['w']}x{t['h']} {names.get(t['fmt'], t['fmt'])} ({t['kind']}){pal}")


def export(path, out):
    from PIL import Image
    d = Path(path).read_bytes()
    check_pack(d)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for t in find_textures(d):
        if t["fmt"] not in SUPPORTED:
            continue
        name = f"{t['off']:06x}_{t['w']}x{t['h']}.png"
        Image.fromarray(image_of(d, t), "RGBA").save(out / name)
        manifest.append({**t, "file": name, "pal": list(t["pal"]) if t["pal"] else None})
    (out / "textures.json").write_text(json.dumps({"pack": Path(path).name, "textures": manifest}, indent=1))
    print(f"{len(manifest)} textures -> {out}")


def import_(path, pngs, out):
    from PIL import Image
    d = bytearray(Path(path).read_bytes())
    check_pack(d)
    pngs = Path(pngs)
    texs = find_textures(bytes(d))
    users = {}
    for t in texs:
        if t["pal"]:
            users[tuple(t["pal"])] = users.get(tuple(t["pal"]), 0) + 1
    changed = 0
    for t in texs:
        f = pngs / f"{t['off']:06x}_{t['w']}x{t['h']}.png"
        if not f.is_file() or t["fmt"] not in SUPPORTED:
            continue
        img = np.array(Image.open(f).convert("RGBA"))
        if img.shape[:2] != (t["h"], t["w"]):
            sys.exit(f"{f.name}: must stay {t['w']}x{t['h']}")
        if np.array_equal(img, image_of(bytes(d), t)):
            continue                                  # unchanged: keep the original bytes
        palette = keep = None
        if t["fmt"] in (8, 9):
            if t["pal"] is None:
                sys.exit(f"{f.name}: its palette is in another pack; it cannot be imported")
            n, p = t["pal"]
            if users[tuple(t["pal"])] == 1 and not t["fixed"]:   # exclusive palette: rebuild it
                palette = new_palette(img, n)
                d[p:p + 2 * n] = palette.tobytes()
            else:
                palette = palette_of(bytes(d), t)
                old = values(bytes(d[t["data"]:]), t["w"], t["h"], t["fmt"])
                keep = (old, (img == image_of(bytes(d), t)).all(-1))
        data = encode(img, t["fmt"], palette, keep)
        d[t["data"]:t["data"] + len(data)] = data
        changed += 1
    Path(out).write_bytes(bytes(d))
    print(f"{changed} textures re-encoded -> {out}")


def selftest():
    rng = np.random.default_rng(1)
    for fmt, (w, h) in ((6, (16, 8)), (5, (8, 8)), (1, (16, 8)), (0, (16, 16))):
        img = rng.integers(0, 256, (h, w, 4), dtype=np.uint8)
        if fmt == 5:
            img = from_rgb5a3(to_rgb5a3(img))                   # representable colours
        if fmt in (0, 1):
            g = (img[..., 0] >> 4) * 17 if fmt == 0 else img[..., 0]
            img = np.stack([g, g, g, np.full_like(g, 255)], -1).astype(np.uint8)
        back = decode(encode(img, fmt), w, h, fmt)
        assert np.array_equal(back, img), f"format {fmt}"
    pal = to_rgb5a3(rng.integers(0, 256, (16, 4), dtype=np.uint8))
    colors = from_rgb5a3(pal)
    idx = rng.integers(0, 16, (16, 8))
    img = colors[idx]
    back = decode(encode(img, 8, pal), 8, 16, 8, pal)
    assert np.array_equal(back, img), "C4"
    pal[5] = pal[3]                                             # repeated colour: indices must stay
    data = encode(colors[idx], 8, pal)
    idx = values(data, 8, 16, 8)
    idx[0, 0] = 5
    data = encode(from_rgb5a3(pal)[idx], 8, pal, (idx, np.ones(idx.shape, bool)))
    assert np.array_equal(values(data, 8, 16, 8), idx), "C4 kept indices"
    print("selftest ok")


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "info" and len(args) == 1:
        info(*args)
    elif cmd == "export" and len(args) == 2:
        export(*args)
    elif cmd == "import" and len(args) == 3:
        import_(*args)
    elif cmd == "selftest":
        selftest()
    else:
        sys.exit(__doc__)
