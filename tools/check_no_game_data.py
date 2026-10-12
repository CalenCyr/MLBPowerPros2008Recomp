"""Refuse to commit anything that could be game data.

The repository ships only tools, patches, configs and docs. The disc, anything extracted or
generated from it, saves and traces live in local/ (ignored). This check runs over the files git
would commit (staged by default, or every tracked file with --all) and fails on:
  - Nintendo/game file types (disc images, executables, archives, textures, audio, video, saves);
  - binary content;
  - files over 512 KiB;
  - long hex or base64 blobs (a lone 64-digit SHA-256 is allowed).

Install as a pre-commit hook:  python tools/check_no_game_data.py --install-hook
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANNED_EXT = {
    # disc images and containers
    "iso", "gcm", "wbfs", "rvz", "gcz", "ciso", "wia", "nkit", "nfs", "wad",
    # executables and code
    "dol", "rel", "elf", "app",
    # archives, layouts, textures, models
    "arc", "szs", "u8", "carc", "brres", "bmd", "bdl", "tpl", "bti", "brlyt", "brlan", "bnr", "img", "bin",
    # audio and video
    "thp", "brstm", "bfstm", "brsar", "rsar", "dsp", "adp", "ast", "wav", "ogg", "mp3",
    # saves and dumps
    "sav", "gci", "raw", "dump", "dtm",
}
MAX_BYTES = 512 * 1024
HEX_BLOB = re.compile(r"(?:0x)?[0-9A-Fa-f]{65,}")
HEX_WORDS = re.compile(r"(?:\b(?:0x)?[0-9A-Fa-f]{2,8}\b[,\s]+){32,}")
BASE64_BLOB = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")
SYMBOL_LINE = re.compile(r"([0-9a-f]{8}) (\S.{0,500})$")
HEX_NAME = re.compile(r"(?:0x)?[0-9A-Fa-f]+$")


def files(all_tracked: bool) -> list[str]:
    args = ["git", "ls-files"] if all_tracked else ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    out = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def problems(path: str, data: bytes) -> list[str]:
    found = []
    ext = path.rsplit(".", 1)[-1].lower() if "." in Path(path).name else ""
    if ext in BANNED_EXT:
        found.append(f"game file type .{ext}")
    # Symbol maps (address + name per line, like a decomp's symbols.txt) may be larger.
    is_symbol_map = path.startswith("config/") and ext == "map"
    limit = 2 * 1024 * 1024 if is_symbol_map else MAX_BYTES
    if len(data) > limit:
        found.append(f"{len(data)} bytes (> {limit})")
    if b"\0" in data:
        found.append("binary content")
        return found
    text = data.decode("utf-8", errors="replace")
    if is_symbol_map:
        for number, line in enumerate(text.splitlines(), 1):
            match = SYMBOL_LINE.match(line)
            # A bare hex word as the name could smuggle instruction words; only the address itself
            # (the translator's auto name "0x<address>") is allowed in that form.
            if not match or (HEX_NAME.match(match[2]) and match[2].lower() not in (match[1], "0x" + match[1])):
                found.append(f"symbol map line {number} is not '<address> <name>'")
                break
        return found
    for name, pattern in (("hex blob", HEX_BLOB), ("hex word table", HEX_WORDS), ("base64 blob", BASE64_BLOB)):
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            found.append(f"{name} at line {line}")
    return found


def install_hook() -> None:
    hook = ROOT / ".git" / "hooks" / "pre-commit"
    hook.write_text('#!/bin/sh\nexec python tools/check_no_game_data.py\n', newline="\n")
    print(f"installed {hook}")


def demo() -> None:
    assert problems("a/main.dol", b"x") == ["game file type .dol"]
    assert problems("x.txt", b"a\0b") == ["binary content"]
    assert problems("x.md", b"sha256 " + b"ab" * 32) == []
    assert problems("x.md", b"ab" * 40)[0].startswith("hex blob")
    assert problems("x.py", b", ".join([b"0x3C"] * 40))[0].startswith("hex word table")
    assert problems("x.json", b"QUJD" * 60)[0].startswith("base64 blob")
    assert problems("config/a.map", b"80004000 __start\n8000403c main\n") == []
    assert problems("config/a.map", b"80004000 __start\n80004010 0x80004010\n") == []
    assert problems("config/a.map", b"80004000 __start\x00")[0] == "binary content"
    assert problems("config/a.map", b"80004000 x\nnot a symbol\n")[0].startswith("symbol map line 2")
    assert problems("config/a.map", b"80004000 x\n3c600000 38630000\n")[0].startswith("symbol map line 2")


if __name__ == "__main__":
    demo()
    if "--install-hook" in sys.argv:
        install_hook()
        sys.exit(0)
    bad = 0
    for path in files("--all" in sys.argv):
        full = ROOT / path
        if not full.is_file():
            continue
        for issue in problems(path, full.read_bytes()):
            print(f"{path}: {issue}")
            bad += 1
    if bad:
        print("Refusing: game data must stay in local/ (see README).", file=sys.stderr)
        sys.exit(1)
