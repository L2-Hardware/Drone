"""Symbol generation for the eXxx libraries (KiCad 7 file format, opens in KiCad 7/8/9).

Every IC symbol is a plain rectangle with pins on the left/right, generated from a pin
table. Pin tables either come from the official KiCad libraries (so pin numbers are the
librarian-checked ones) or from the datasheet, as noted per part in parts.py.
"""
import os
import re

from sexp import parse, find, find_all, walk, Sym

KICAD_SYM_LOCAL = "/usr/share/kicad/symbols"
KICAD_SYM_UPSTREAM = "/home/user/kicadlib/sym"
G = 2.54


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# --------------------------------------------------------------------------- pin tables
def kicad_pins(lib, name):
    """Pin table [(num, name, type)] from the official KiCad library (local 7.x, else upstream)."""
    def load(libtxt, nm):
        tree = parse(libtxt)
        for s in find_all(tree, "symbol"):
            if s[1] == nm:
                return s
        return None

    sym = None
    p = os.path.join(KICAD_SYM_LOCAL, lib + ".kicad_sym")
    if os.path.exists(p):
        txt = open(p).read()
        if f'(symbol "{name}"' in txt:
            sym = load(txt, name)
            ext = find(sym, "extends")
            if ext:
                sym = load(txt, ext[1])
    if sym is None:
        p = os.path.join(KICAD_SYM_UPSTREAM, lib + ".kicad_symdir", name + ".kicad_sym")
        txt = open(p).read()
        sym = load(txt, name)
        ext = find(sym, "extends")
        if ext:
            p = os.path.join(KICAD_SYM_UPSTREAM, lib + ".kicad_symdir", ext[1] + ".kicad_sym")
            sym = load(open(p).read(), ext[1])
    pins = []
    seen = set()
    for pin in walk(sym, "pin"):
        if len(pin) < 3 or not isinstance(pin[1], Sym):
            continue
        typ = str(pin[1])
        nm = find(pin, "name")[1]
        num = find(pin, "number")[1]
        if num in seen:
            continue
        seen.add(num)
        pins.append((num, nm, typ))
    return pins


# --------------------------------------------------------------------------- symbol text
def _prop(name, val, x, y, hide=False, size=1.27, justify=None):
    eff = f"(font (size {size} {size}))"
    if justify:
        eff += f" (justify {justify})"
    if hide:
        eff += " hide"
    return f'    (property {q(name)} {q(val)} (at {fmt(x)} {fmt(y)} 0)\n      (effects {eff})\n    )\n'


def _pin(typ, x, y, rot, length, name, num, hide=False):
    h = " hide" if hide else ""
    return (f"      (pin {typ} line (at {fmt(x)} {fmt(y)} {rot}) (length {fmt(length)}){h}\n"
            f"        (name {q(name)} (effects (font (size 1.27 1.27))))\n"
            f"        (number {q(num)} (effects (font (size 1.27 1.27))))\n      )\n")


def _common_props(ref, value, fp, fields, ry, vy, rx=0.0, vx=0.0, rjust=None, vjust=None):
    s = _prop("Reference", ref, rx, ry, justify=rjust)
    s += _prop("Value", value, vx, vy, justify=vjust)
    s += _prop("Footprint", fp, 0, 0, hide=True)
    s += _prop("Datasheet", fields.get("Datasheet", ""), 0, 0, hide=True)
    if fields.get("Description"):
        s += _prop("ki_description", fields["Description"], 0, 0, hide=True)
    if fields.get("Keywords"):
        s += _prop("ki_keywords", fields["Keywords"], 0, 0, hide=True)
    for k, v in fields.items():
        if k in ("Datasheet", "Description", "Keywords"):
            continue
        s += _prop(k, v, 0, 0, hide=True)
    return s


def ic_symbol(name, pins, left, right, ref="U", fp="", fields=None, top=None, bottom=None):
    """Rectangle symbol. `left`/`right` are lists of pin numbers (None = spacer).
    Returns (text, pin_geometry) where pin_geometry[num] = (x, y, rot)."""
    fields = fields or {}
    bynum = {p[0]: p for p in pins}
    used = [n for n in (left + right + (top or []) + (bottom or [])) if n is not None]
    missing = set(bynum) - set(used)
    if missing:
        raise ValueError(f"{name}: pins not placed: {sorted(missing)}")
    if len(used) != len(set(used)):
        raise ValueError(f"{name}: duplicate pin in layout")

    def tl(lst):
        return max([len(bynum[n][1]) for n in lst if n is not None] or [0])

    w = (tl(left) + tl(right)) * 1.27 * 0.85 + 5.08
    w = max(w, 10.16)
    half = G * round((w / 2) / G + 0.49)
    n = max(len(left), len(right))
    y0 = G * ((n - 1) // 2)
    geo = {}
    body = ""
    for i, num in enumerate(left):
        if num is None:
            continue
        y = y0 - i * G
        geo[num] = (-half - G, y, 0)
        body += _pin(bynum[num][2], -half - G, y, 0, G, bynum[num][1], num)
    for i, num in enumerate(right):
        if num is None:
            continue
        y = y0 - i * G
        geo[num] = (half + G, y, 180)
        body += _pin(bynum[num][2], half + G, y, 180, G, bynum[num][1], num)
    ytop = y0 + G
    ybot = y0 - (n - 1) * G - G
    text = f"  (symbol {q(name)} (pin_names (offset 1.016)) (in_bom yes) (on_board yes)\n"
    text += _common_props(ref, name, fp, fields, ytop + 1.27, ybot - 1.27,
                          rx=half, vx=half, rjust="right", vjust="right")
    text += (f"    (symbol {q(name + '_0_1')}\n      (rectangle (start {fmt(-half)} {fmt(ytop)}) "
             f"(end {fmt(half)} {fmt(ybot)})\n        (stroke (width 0.254) (type default))\n"
             f"        (fill (type background))\n      )\n    )\n")
    text += f"    (symbol {q(name + '_1_1')}\n{body}    )\n  )\n"
    bbox = (-half - G, ybot, half + G, ytop)
    return text, geo, bbox


# Two-pin and small symbols ------------------------------------------------------------
def _stroke(w=0.2032):
    return f"(stroke (width {w}) (type default))"


def _poly(pts, fill="none", w=0.2032):
    p = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in pts)
    return f"      (polyline (pts {p}) {_stroke(w)} (fill (type {fill})))\n"


def _arc(s, m, e, w=0.2032):
    return (f"      (arc (start {fmt(s[0])} {fmt(s[1])}) (mid {fmt(m[0])} {fmt(m[1])}) "
            f"(end {fmt(e[0])} {fmt(e[1])}) {_stroke(w)} (fill (type none)))\n")


def _rect(x1, y1, x2, y2, fill="none", w=0.254):
    return (f"      (rectangle (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) "
            f"{_stroke(w)} (fill (type {fill})))\n")


def _circle(x, y, r, fill="none", w=0.2032):
    return f"      (circle (center {fmt(x)} {fmt(y)}) (radius {fmt(r)}) {_stroke(w)} (fill (type {fill})))\n"


def small_symbol(name, kind, ref, fp="", fields=None, npins=None):
    """Generic small symbols. Returns (text, geo, bbox)."""
    fields = fields or {}
    gfx = ""
    pins = ""
    geo = {}
    hide_names = True
    bbox = None

    def P(typ, x, y, rot, length, nm, num):
        nonlocal pins
        geo[num] = (x, y, rot)
        pins += _pin(typ, x, y, rot, length, nm, num)

    ry, vy, rx, vx = 2.54, -2.54, 0, 0
    if kind == "R":
        gfx += _rect(-2.54, 0.889, 2.54, -0.889)
        P("passive", -3.81, 0, 0, 1.27, "~", "1"); P("passive", 3.81, 0, 180, 1.27, "~", "2")
    elif kind == "C":
        gfx += _poly([(-0.508, 1.778), (-0.508, -1.778)], w=0.3048)
        gfx += _poly([(0.508, 1.778), (0.508, -1.778)], w=0.3048)
        P("passive", -3.81, 0, 0, 3.302, "~", "1"); P("passive", 3.81, 0, 180, 3.302, "~", "2")
    elif kind == "CP":
        gfx += _rect(-0.762, 1.778, -0.254, -1.778)
        gfx += _poly([(0.508, 1.778), (0.508, -1.778)], w=0.3048)
        gfx += _poly([(-1.778, 1.524), (-1.778, 0.508)]) + _poly([(-2.286, 1.016), (-1.27, 1.016)])
        P("passive", -3.81, 0, 0, 3.048, "~", "1"); P("passive", 3.81, 0, 180, 3.302, "~", "2")
    elif kind == "L":
        for i in range(4):
            x0 = -2.54 + i * 1.27
            gfx += _arc((x0, 0), (x0 + 0.635, 0.635), (x0 + 1.27, 0))
        P("passive", -3.81, 0, 0, 1.27, "~", "1"); P("passive", 3.81, 0, 180, 1.27, "~", "2")
    elif kind == "FB":
        gfx += _poly([(-2.032, -0.254), (-1.016, 1.524), (2.032, 0.254), (1.016, -1.524), (-2.032, -0.254)])
        P("passive", -3.81, 0, 0, 1.778, "~", "1"); P("passive", 3.81, 0, 180, 1.778, "~", "2")
    elif kind in ("D", "DS", "DZ", "LED"):
        # anode left (pin 2), cathode right (pin 1)
        gfx += _poly([(-1.27, 1.27), (-1.27, -1.27), (1.27, 0), (-1.27, 1.27)], fill="none", w=0.254)
        if kind == "D" or kind == "LED":
            gfx += _poly([(1.27, 1.27), (1.27, -1.27)], w=0.254)
        elif kind == "DS":
            gfx += _poly([(0.762, 0.762), (0.762, 1.27), (1.27, 1.27), (1.27, -1.27), (1.778, -1.27), (1.778, -0.762)], w=0.254)
        elif kind == "DZ":
            gfx += _poly([(0.762, 1.27), (1.27, 1.27), (1.27, -1.27), (1.778, -1.27)], w=0.254)
        if kind == "LED":
            gfx += _poly([(-0.254, 1.778), (0.762, 2.794)]) + _poly([(0.254, 2.794), (0.762, 2.794), (0.762, 2.286)])
            gfx += _poly([(0.762, 1.778), (1.778, 2.794)]) + _poly([(1.27, 2.794), (1.778, 2.794), (1.778, 2.286)])
        P("passive", -3.81, 0, 0, 2.54, "A", "2"); P("passive", 3.81, 0, 180, 2.54, "K", "1")
        ry = 3.81
    elif kind == "XTAL":
        gfx += _rect(-1.143, 2.032, 1.143, -2.032)
        gfx += _poly([(-2.032, 1.778), (-2.032, -1.778)], w=0.3048) + _poly([(2.032, 1.778), (2.032, -1.778)], w=0.3048)
        P("passive", -3.81, 0, 0, 1.778, "1", "1"); P("passive", 3.81, 0, 180, 1.778, "2", "2")
        ry = 3.81; vy = -3.81
    elif kind == "XTAL4":
        gfx += _rect(-1.143, 2.032, 1.143, -2.032)
        gfx += _poly([(-2.032, 1.778), (-2.032, -1.778)], w=0.3048) + _poly([(2.032, 1.778), (2.032, -1.778)], w=0.3048)
        gfx += _poly([(0, -2.032), (0, -2.54)]) + _poly([(-2.54, -2.54), (2.54, -2.54)])
        P("passive", -3.81, 0, 0, 1.778, "1", "1"); P("passive", 3.81, 0, 180, 1.778, "3", "3")
        P("passive", -1.27, -5.08, 90, 2.54, "GND", "2"); P("passive", 1.27, -5.08, 90, 2.54, "GND", "4")
        gfx += _poly([(-1.27, -2.54), (-1.27, -2.54)])
        ry = 3.81; vy = 3.81; rx = 3.81; vx = -3.81
        bbox = (-3.81, -5.08, 3.81, 2.54)
    elif kind == "NMOS":  # SOT-23: 1 G, 2 S, 3 D
        gfx += _poly([(0.254, 1.905), (0.254, -1.905)], w=0.254)
        gfx += _poly([(0.762, 2.286), (0.762, 1.27)], w=0.254) + _poly([(0.762, 0.508), (0.762, -0.508)], w=0.254)
        gfx += _poly([(0.762, -1.27), (0.762, -2.286)], w=0.254)
        gfx += _poly([(0.762, 1.778), (2.54, 1.778), (2.54, 2.54)]) + _poly([(0.762, -1.778), (2.54, -1.778), (2.54, -2.54)])
        gfx += _poly([(0.762, 0), (2.54, 0), (2.54, -1.778)])
        gfx += _poly([(1.016, 0), (2.032, 0.381), (2.032, -0.381), (1.016, 0)], fill="outline")
        P("input", -2.54, 0, 0, 2.794, "G", "1"); P("passive", 2.54, -5.08, 90, 2.54, "S", "2")
        P("passive", 2.54, 5.08, 270, 2.54, "D", "3")
        rx = vx = 5.08; ry = 1.27; vy = -1.27
        bbox = (-2.54, -5.08, 5.08, 5.08)
    elif kind == "NMOS_PWR":  # PQFN 3.3x3.3: 1-3 S, 4 G, 5 D(tab)
        gfx += _poly([(0.254, 1.905), (0.254, -1.905)], w=0.254)
        gfx += _poly([(0.762, 2.286), (0.762, 1.27)], w=0.254) + _poly([(0.762, 0.508), (0.762, -0.508)], w=0.254)
        gfx += _poly([(0.762, -1.27), (0.762, -2.286)], w=0.254)
        gfx += _poly([(0.762, 1.778), (2.54, 1.778), (2.54, 2.54)]) + _poly([(0.762, -1.778), (2.54, -1.778), (2.54, -2.54)])
        gfx += _poly([(0.762, 0), (2.54, 0), (2.54, -1.778)])
        gfx += _poly([(1.016, 0), (2.032, 0.381), (2.032, -0.381), (1.016, 0)], fill="outline")
        P("input", -2.54, 0, 0, 2.794, "G", "4")
        P("passive", 2.54, 5.08, 270, 2.54, "D", "5")
        P("passive", 2.54, -5.08, 90, 2.54, "S", "1")
        pins += _pin("passive", 2.54, -5.08, 90, 2.54, "S", "2", hide=True)
        pins += _pin("passive", 2.54, -5.08, 90, 2.54, "S", "3", hide=True)
        geo["2"] = geo["3"] = geo["1"]
        rx = vx = 5.08; ry = 1.27; vy = -1.27
        bbox = (-2.54, -5.08, 5.08, 5.08)
    elif kind == "NPN":  # SOT-23: 1 B, 2 E, 3 C
        gfx += _poly([(0.635, 1.905), (0.635, -1.905)], w=0.508)
        gfx += _poly([(0.635, 0.635), (2.54, 2.54)]) + _poly([(0.635, -0.635), (2.54, -2.54)])
        gfx += _poly([(1.651, -1.778), (2.159, -1.27), (2.413, -2.286), (1.651, -1.778)], fill="outline")
        P("input", -2.54, 0, 0, 3.175, "B", "1"); P("passive", 2.54, -5.08, 90, 2.54, "E", "2")
        P("passive", 2.54, 5.08, 270, 2.54, "C", "3")
        rx = vx = 5.08; ry = 1.27; vy = -1.27
        bbox = (-2.54, -5.08, 5.08, 5.08)
    elif kind == "SW":
        gfx += _circle(-2.032, 0, 0.508) + _circle(2.032, 0, 0.508)
        gfx += _poly([(0, 1.27), (0, 3.048)]) + _poly([(2.54, 1.27), (-2.54, 1.27)])
        P("passive", -5.08, 0, 0, 2.54, "1", "1"); P("passive", 5.08, 0, 180, 2.54, "2", "2")
        ry = 3.81
    elif kind == "TP":
        gfx += _circle(0, 3.302, 0.762)
        P("passive", 0, 0, 90, 2.54, "1", "1")
        rx = vx = 1.524; ry = 4.064; vy = 2.286
        bbox = (-1.27, 0, 1.27, 4.064)
    elif kind == "JUMPER3":  # solder jumper, 1-2 / 2-3, pin 2 common (bottom)
        gfx += _rect(-3.81, 1.27, 3.81, -1.27)
        P("passive", -6.35, 0, 0, 2.54, "A", "1"); P("passive", 6.35, 0, 180, 2.54, "B", "3")
        P("passive", 0, -3.81, 90, 2.54, "C", "2")
        ry = 2.54; vy = 2.54; rx = -6.35; vx = 6.35
        bbox = (-6.35, -3.81, 6.35, 1.27)
    elif kind == "COAX":
        gfx += _circle(0, 0, 0.508) + _circle(0, 0, 1.778, w=0.254)
        P("passive", -5.08, 0, 0, 4.572, "In", "1"); P("passive", 0, -5.08, 90, 3.302, "Ext", "2")
        ry = 3.81; vy = 3.81; rx = 2.54; vx = 2.54
        bbox = (-5.08, -5.08, 2.54, 2.54)
    elif kind == "ANT":
        gfx += _poly([(0, 0), (0, 3.81)]) + _poly([(-1.27, 5.08), (0, 3.81), (1.27, 5.08), (-1.27, 5.08)])
        P("input", 0, -2.54, 90, 2.54, "FEED", "1")
        P("no_connect", 2.54, -2.54, 90, 2.54, "NC", "2")
        rx = vx = 2.54; ry = 3.81; vy = 1.27
        bbox = (-1.27, -2.54, 2.54, 5.08)
    elif kind == "HOLE":
        gfx += _circle(0, 0, 1.27, w=0.635)
        rx = vx = 0; ry = 2.54; vy = -2.54
        bbox = (-1.27, -1.27, 1.27, 1.27)
    else:
        raise ValueError(kind)
    if bbox is None:
        xs = [g[0] for g in geo.values()]
        bbox = (min(xs), -1.905, max(xs), 1.905)
    in_bom = "no" if kind in ("HOLE",) else "yes"
    pn = "(pin_numbers hide) (pin_names (offset 0) hide)" if hide_names else ""
    if kind in ("XTAL4", "COAX", "JUMPER3", "NMOS", "NMOS_PWR", "NPN"):
        pn = "(pin_numbers hide) (pin_names (offset 0.254) hide)"
    text = f"  (symbol {q(name)} {pn} (in_bom {in_bom}) (on_board yes)\n"
    text += _common_props(ref, name, fp, fields, ry, vy, rx, vx)
    text += f"    (symbol {q(name + '_0_1')}\n{gfx}    )\n"
    text += f"    (symbol {q(name + '_1_1')}\n{pins}    )\n  )\n"
    return text, geo, bbox


def power_symbol(name, kind):
    """kind: 'gnd' or 'vcc' or 'flag'. Pin at origin."""
    if kind == "gnd":
        gfx = _poly([(0, 0), (0, -1.27), (1.27, -1.27), (0, -2.54), (-1.27, -1.27), (0, -1.27)], w=0)
        pin = _pin("power_in", 0, 0, 270, 0, name, "1", hide=True)
        refy, valy = -6.35, -3.81
    elif kind == "vcc":
        gfx = _poly([(-0.762, 1.27), (0, 2.54)], w=0) + _poly([(0, 0), (0, 2.54)], w=0) + _poly([(0, 2.54), (0.762, 1.27)], w=0)
        pin = _pin("power_in", 0, 0, 90, 0, name, "1", hide=True)
        refy, valy = -3.81, 3.556
    else:  # PWR_FLAG
        gfx = _poly([(0, 0), (0, 1.27), (-1.016, 1.905), (0, 2.54), (1.016, 1.905), (0, 1.27)], w=0)
        pin = _pin("power_out", 0, 0, 90, 0, "pwr", "1", hide=True)
        refy, valy = 1.905, 3.81
    ref = "#FLG" if kind == "flag" else "#PWR"
    text = f"  (symbol {q(name)} (power) (pin_names (offset 0)) (in_bom yes) (on_board yes)\n"
    text += _prop("Reference", ref, 0, refy, hide=True)
    text += _prop("Value", name, 0, valy)
    text += _prop("Footprint", "", 0, 0, hide=True)
    text += _prop("Datasheet", "", 0, 0, hide=True)
    desc = "Special symbol for telling ERC where power comes from" if kind == "flag" else f'Power symbol creates a global label with name "{name}"'
    text += _prop("ki_description", desc, 0, 0, hide=True)
    text += f"    (symbol {q(name + '_0_1')}\n{gfx}    )\n"
    text += f"    (symbol {q(name + '_1_1')}\n{pin}    )\n  )\n"
    return text


def conn_symbol(name, n, ref="J", fp="", fields=None, mp=True):
    """1xN connector, pins on the left, optional MP (mounting pads) pin at the bottom."""
    fields = fields or {}
    geo = {}
    pins = ""
    y0 = G * ((n - 1) // 2)
    for i in range(n):
        y = y0 - i * G
        geo[str(i + 1)] = (-5.08, y, 0)
        pins += _pin("passive", -5.08, y, 0, 3.81, f"Pin_{i + 1}", str(i + 1))
    ybot = y0 - (n - 1) * G - 1.27
    ytop = y0 + 1.27
    gfx = _rect(-1.27, ytop, 1.27, ybot, fill="background")
    for i in range(n):
        y = y0 - i * G
        gfx += _rect(-1.27, y + 0.127, 0, y - 0.127, fill="outline", w=0.1524)
    if mp:
        geo["MP"] = (0, ybot - 2.54 - 1.27, 90)
        pins += _pin("passive", 0, ybot - 3.81, 90, 3.81, "MountPin", "MP")
    text = f"  (symbol {q(name)} (pin_names (offset 1.016) hide) (in_bom yes) (on_board yes)\n"
    text += _common_props(ref, name, fp, fields, ytop + 1.27, ybot - 1.27 - (3.81 if mp else 0), rx=1.27, vx=1.27,
                          rjust="left", vjust="left")
    text += f"    (symbol {q(name + '_0_1')}\n{gfx}    )\n"
    text += f"    (symbol {q(name + '_1_1')}\n{pins}    )\n  )\n"
    bbox = (-5.08, ybot - (3.81 if mp else 0), 1.27, ytop)
    return text, geo, bbox
