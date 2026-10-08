"""Build the drone part libraries in the eXxx folder layout:

  KiCad_Libs_Drone/<eLib>/
      datasheet/            datasheets (PDF when redistributable here, otherwise links in README.md)
      <eLib>.3dshapes/      STEP models (from the official KiCad 3D library)
      <eLib>.pretty/        footprints (from the official KiCad footprint library)
      <eLib>.kicad_sym      symbols
      .gitignore
"""
import os
import re
import shutil
import subprocess
import tempfile
import sys

import parts as P
from symlib import ic_symbol, small_symbol, conn_symbol, power_symbol

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "KiCad_Libs_Drone"))
KICAD_FP = "/usr/share/kicad/footprints"
MODEL_CACHE = os.path.join(tempfile.gettempdir(), "kicad_models")
P3D_GIT = "/home/user/kicadlib/p3d"
MODEL_URL = "https://raw.githubusercontent.com/KiCad/kicad-packages3D/master/"
OPENVTX_DOCS = "/home/user/openvtx/openvtx/docs"

POWER_NETS = ["GND", "+3V3", "+3V3_GYRO", "+3V3_OSD", "+5V", "+10V", "VBAT", "VBUS", "+5V_PA", "+3V3_RF"]

SYMBOLS = {}  # lib_id -> dict(text, geo, bbox, types)


def build_symbols():
    for part in P.PARTS.values():
        fp = part.fp_id or P.PartDefaults.get(part.name, "")
        if part.kind == "ic":
            text, geo, bbox = ic_symbol(part.name, part.pins, part.left, part.right, part.ref, fp, part.fields)
            types = {n: t for n, _, t in part.pins}
            names = {n: nm for n, nm, _ in part.pins}
        elif part.kind == "conn":
            text, geo, bbox = conn_symbol(part.name, part.npins, part.ref, fp, part.fields)
            types = {k: "passive" for k in geo}
            names = {k: k for k in geo}
        else:
            text, geo, bbox = small_symbol(part.name, part.kind, part.ref, fp, part.fields)
            types, names = {}, {}
            for m in re.finditer(r'\(pin (\w+) line .*?\(name "([^"]*)".*?\(number "([^"]+)"', text, re.S):
                types[m.group(3)] = m.group(1)
                names[m.group(3)] = m.group(2) if m.group(2) not in ("~", m.group(3)) else m.group(3)
        SYMBOLS[part.lib_id] = dict(text=text, geo=geo, bbox=bbox, types=types, names=names, part=part)
    for net in POWER_NETS + ["PWR_FLAG"]:
        kind = "flag" if net == "PWR_FLAG" else P.power_kind(net)
        SYMBOLS[f"ePowerSym:{net}"] = dict(text=power_symbol(net, kind), geo={"1": (0, 0, 0)}, bbox=(-1.27, -2.54, 1.27, 2.54),
                                            types={"1": "power_out" if kind == "flag" else "power_in"},
                                            names={"1": net}, part=None, power=kind)


def write_symbol_libs():
    libs = {}
    for lib_id, s in SYMBOLS.items():
        lib = lib_id.split(":")[0]
        libs.setdefault(lib, []).append(s["text"])
    for lib, texts in libs.items():
        d = os.path.join(ROOT, lib)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{lib}.kicad_sym"), "w") as f:
            f.write("(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)\n")
            f.write("".join(texts))
            f.write(")\n")


def fetch_model(rel):
    dst = os.path.join(MODEL_CACHE, rel)
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        return dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = MODEL_URL + rel
    r = subprocess.run(["curl", "-sS", "-f", "-L", "-o", dst, url], capture_output=True, text=True)
    if r.returncode != 0:  # fall back to the GitLab master (lazy blob fetch)
        with open(dst, "wb") as f:
            r = subprocess.run(["git", "-C", P3D_GIT, "show", "HEAD:" + rel], stdout=f, stderr=subprocess.PIPE)
    if r.returncode != 0:
        print("  !! model download failed:", rel, r.stderr.strip(), file=sys.stderr)
        return None
    return dst


def copy_footprint(lib, fp_name, src, model_rel):
    srclib, srcname = src.split(":", 1)
    txt = open(os.path.join(KICAD_FP, srclib + ".pretty", srcname + ".kicad_mod")).read()
    txt = re.sub(r'^\(footprint "[^"]+"', f'(footprint "{fp_name}"', txt, count=1)
    txt = re.sub(r'\(fp_text value "[^"]+"', f'(fp_text value "{fp_name}"', txt, count=1)
    # drop original model blocks, then add ours
    txt = re.sub(r'\n\s*\(model "[^"]*"(?:\s*\((?:offset|scale|rotate) \(xyz [^)]*\)\))*\s*\)', "", txt)
    if model_rel:
        path = fetch_model(model_rel)
        if path:
            d3 = os.path.join(ROOT, lib, f"{lib}.3dshapes")
            os.makedirs(d3, exist_ok=True)
            out_name = os.path.basename(model_rel)
            shutil.copyfile(path, os.path.join(d3, out_name))
            model = (f'  (model "${{KIPRJMOD}}/../KiCad_Libs/{lib}/{lib}.3dshapes/{out_name}"\n'
                     f"    (offset (xyz 0 0 0))\n    (scale (xyz 1 1 1))\n    (rotate (xyz 0 0 0))\n  )\n")
            txt = txt.rstrip()
            assert txt.endswith(")")
            txt = txt[:-1].rstrip() + "\n" + model + ")\n"
    if fp_name.startswith("PQFN-8_3.3x3.3mm"):
        # NexFET land pattern: the drain leads are unnamed copper pads overlapping the tab -> make them pad 5 (drain)
        txt = re.sub(r'\(pad "" (smd roundrect [^\n]*"F\.Cu")', r'(pad "5" \1', txt)
    d = os.path.join(ROOT, lib, f"{lib}.pretty")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, fp_name + ".kicad_mod"), "w") as f:
        f.write(txt)


def custom_pad(lib, name, w, h):
    txt = f"""(footprint "{name}" (version 20221018) (generator pcbnew)
  (layer "F.Cu")
  (descr "Solder pad {w}x{h}mm for wires (battery / motor leads)")
  (tags "solder pad wire")
  (attr smd)
  (fp_text reference "REF**" (at 0 {-(h / 2 + 1.2):.2f}) (layer "F.SilkS")
    (effects (font (size 0.8 0.8) (thickness 0.12)))
  )
  (fp_text value "{name}" (at 0 {h / 2 + 1.2:.2f}) (layer "F.Fab")
    (effects (font (size 0.8 0.8) (thickness 0.12)))
  )
  (fp_rect (start {-w / 2 - 0.25:.2f} {-h / 2 - 0.25:.2f}) (end {w / 2 + 0.25:.2f} {h / 2 + 0.25:.2f})
    (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
  (pad "1" smd roundrect (at 0 0) (size {w} {h}) (layers "F.Cu" "F.Mask") (roundrect_rratio 0.1))
)
"""
    d = os.path.join(ROOT, lib, f"{lib}.pretty")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, name + ".kicad_mod"), "w").write(txt)


def build_footprints():
    for part in P.PARTS.values():
        if part.fp and part.fp_src:
            copy_footprint(part.lib, part.fp, part.fp_src, part.model)
    for (_, name), (lib, src, model) in P.GENERIC_FP.items():
        copy_footprint(lib, name, src, model)
    for name, (lib, w, h) in P.CUSTOM_FP.items():
        custom_pad(lib, name, w, h)


def build_docs():
    libs = {}
    for part in P.PARTS.values():
        if part.fields.get("MPN"):
            libs.setdefault(part.lib, []).append(part)
    for lib, plist in libs.items():
        d = os.path.join(ROOT, lib, "datasheet")
        os.makedirs(d, exist_ok=True)
        lines = [f"# {lib} datasheets\n", "| Part | Manufacturer | MPN | Datasheet |", "|---|---|---|---|"]
        for part in sorted(plist, key=lambda x: x.name):
            f = part.fields
            lines.append(f"| {part.name} | {f.get('Manufacturer', '')} | {f.get('MPN', '')} | {f.get('Datasheet', '')} |")
        open(os.path.join(d, "README.md"), "w").write("\n".join(lines) + "\n")
    for pdf, lib in (("RTC6705-RichWave.pdf", "eRFModule"), ("RFPA5542-Qorvo.pdf", "eAmplifier")):
        src = os.path.join(OPENVTX_DOCS, pdf)
        if os.path.exists(src):
            os.makedirs(os.path.join(ROOT, lib, "datasheet"), exist_ok=True)
            shutil.copyfile(src, os.path.join(ROOT, lib, "datasheet", pdf))
    for lib in os.listdir(ROOT):
        if os.path.isdir(os.path.join(ROOT, lib)):
            open(os.path.join(ROOT, lib, ".gitignore"), "w").write("*.bak\n*-bak\n*.lck\n~*\n_autosave-*\n")


def build_all(write=True):
    build_symbols()
    if write:
        write_symbol_libs()
        build_footprints()
        build_docs()


if __name__ == "__main__":
    build_all()
    print("libraries written to", ROOT)
