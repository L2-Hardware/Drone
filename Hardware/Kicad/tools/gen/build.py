"""Regenerate libraries + all four KiCad projects.  Usage: python3 build.py [--no-lib] [boards...]"""
import importlib
import os
import sys

import libbuild

sys.dont_write_bytecode = True
args = [a for a in sys.argv[1:] if not a.startswith("--")]
libbuild.build_all(write="--no-lib" not in sys.argv)

import project  # noqa: E402

BOARDS = args or ["fcv00", "escv00", "rxv00", "vtxv00"]
for mod in BOARDS:
    m = importlib.import_module(mod)
    d = project.write_project(m.B.name, *m.NETCLASSES) if hasattr(m, "NETCLASSES") else project.write_project(m.B.name, [project.netclass("Default", 0.15)], [])
    m.B.write(d)
    import bom
    bom.write_bom(m.B, d)
    print("wrote", d)
