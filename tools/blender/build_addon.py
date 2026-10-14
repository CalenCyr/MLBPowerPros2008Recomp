# SPDX-License-Identifier: GPL-3.0-or-later
"""Package the Blender add-on (extension zip) with the shared modules it needs.

usage: build_addon.py [out dir]      default local/build/blender
The zip holds only project code (no game data): the add-on reads the player's project.bin.
"""
import re
import sys
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
PACKAGE = TOOLS / "blender" / "powerpros_stadium"
SHARED = [TOOLS / "projectbin.py", TOOLS / "packwii.py"]


def build(out_dir):
    version = re.search(r'^version = "([^"]+)"', (PACKAGE / "blender_manifest.toml").read_text(), re.M).group(1)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"powerpros_stadium-{version}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(PACKAGE.iterdir()):
            if f.is_file() and f.suffix in (".py", ".toml"):
                z.write(f, f.name)
        for f in SHARED:
            z.write(f, f.name)
    return out


if __name__ == "__main__":
    root = TOOLS.parent
    print(build(Path(sys.argv[1]) if len(sys.argv) > 1 else root / "local" / "build" / "blender"))
