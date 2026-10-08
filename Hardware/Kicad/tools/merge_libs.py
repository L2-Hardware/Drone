"""Merge the components in Hardware/Kicad/KiCad_Libs_ToAdd into the official KiCad_Libs library.

    python merge_libs.py [DEST] [--force] [--clean]

    DEST     library folder (default: Hardware/Kicad/KiCad_Libs, the bring_libs.bat junction
             pointing to C:\\git\\PCB\\Kicad_Libs)
    --force  overwrite footprints / 3D models / datasheets that already exist
    --clean  after a successful merge empty KiCad_Libs_ToAdd (only README.md is kept)

For every eXxx library:
  * symbols  : appended to <eXxx>.kicad_sym (names that already exist are skipped; a .bak is kept)
  * footprints, 3D models, datasheets : copied into <eXxx>.pretty / <eXxx>.3dshapes / datasheet
After merging: open the touched libraries once in the Symbol Editor and save (upgrades the format),
then commit + push in the Kicad_Libs repo.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "KiCad_Libs_ToAdd"))
SYM_TABLE = os.path.abspath(os.path.join(HERE, "..", "FCV00", "sym-lib-table"))


def top_level_symbols(text):
    """{name: block_text} for symbols directly inside (kicad_symbol_lib ...)."""
    out = {}
    depth = 0
    i = 0
    in_str = False
    start = None
    name = None
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
            if depth == 2:
                m = re.match(r'\(symbol\s+"((?:[^"\\]|\\.)*)"', text[i:])
                if m:
                    start, name = i, m.group(1)
        elif c == ")":
            if depth == 2 and start is not None:
                out[name] = text[start:i + 1]
                start = None
            depth -= 1
        i += 1
    return out


def merge_symbols(src_file, dst_file):
    if not os.path.exists(src_file):
        return [], []
    src = open(src_file, encoding="utf-8").read()
    if not os.path.exists(dst_file):
        shutil.copyfile(src_file, dst_file)
        return list(top_level_symbols(src)), []
    dst = open(dst_file, encoding="utf-8").read()
    have = top_level_symbols(dst)
    added, skipped, blocks = [], [], []
    for name, block in top_level_symbols(src).items():
        if name in have:
            skipped.append(name)
        else:
            added.append(name)
            blocks.append(block)
    if blocks:
        shutil.copyfile(dst_file, dst_file + ".bak")
        end = dst.rstrip().rfind(")")
        dst = dst[:end].rstrip() + "\n" + "\n".join("\t" + b for b in blocks) + "\n)\n"
        open(dst_file, "w", encoding="utf-8").write(dst)
    return added, skipped


def copy_tree(src_dir, dst_dir, force):
    n = 0
    if not os.path.isdir(src_dir):
        return 0
    os.makedirs(dst_dir, exist_ok=True)
    for f in os.listdir(src_dir):
        s, d = os.path.join(src_dir, f), os.path.join(dst_dir, f)
        if os.path.isfile(s) and (force or not os.path.exists(d)):
            shutil.copyfile(s, d)
            n += 1
    return n


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    clean = "--clean" in sys.argv
    dest = os.path.abspath(args[0]) if args else os.path.abspath(os.path.join(HERE, "..", "KiCad_Libs"))
    if not os.path.isdir(dest):
        sys.exit(f"Library {dest} not found: run bring_libs.bat first or pass the Kicad_Libs path.")
    libs = [d for d in sorted(os.listdir(SRC)) if os.path.isdir(os.path.join(SRC, d))]
    if not libs:
        print("KiCad_Libs_ToAdd is empty: nothing to merge.")
        return
    known = open(SYM_TABLE).read() if os.path.exists(SYM_TABLE) else ""
    for lib in libs:
        s = os.path.join(SRC, lib)
        d = os.path.join(dest, lib)
        os.makedirs(d, exist_ok=True)
        added, skipped = merge_symbols(os.path.join(s, f"{lib}.kicad_sym"), os.path.join(d, f"{lib}.kicad_sym"))
        nf = copy_tree(os.path.join(s, f"{lib}.pretty"), os.path.join(d, f"{lib}.pretty"), force)
        n3 = copy_tree(os.path.join(s, f"{lib}.3dshapes"), os.path.join(d, f"{lib}.3dshapes"), force)
        nd = copy_tree(os.path.join(s, "datasheet"), os.path.join(d, "datasheet"), force)
        if os.path.exists(os.path.join(s, ".gitignore")) and not os.path.exists(os.path.join(d, ".gitignore")):
            shutil.copyfile(os.path.join(s, ".gitignore"), os.path.join(d, ".gitignore"))
        print(f"{lib:16s} symbols +{len(added)} (already present, skipped: {', '.join(skipped) or '-'}) | "
              f"footprints +{nf} | 3D +{n3} | datasheets +{nd}")
        if known and f'(name "{lib}")' not in known:
            print(f"   !! {lib} is a new library: add it to the projects' sym-lib-table / fp-lib-table")
    if clean:
        for lib in libs:
            shutil.rmtree(os.path.join(SRC, lib))
        print("KiCad_Libs_ToAdd emptied.")
    print("\nNext: open the touched libraries in the Symbol Editor and save, then commit + push in the Kicad_Libs repo.")


if __name__ == "__main__":
    main()
