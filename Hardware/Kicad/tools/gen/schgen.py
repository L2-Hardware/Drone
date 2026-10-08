"""Hierarchical KiCad schematic writer (KiCad 7 file format; KiCad 8/9 open and upgrade it).

Connectivity is expressed with net labels: every connected pin gets a short wire stub that ends
in a power symbol (power rails), a local label (net used on one sheet only), a global label
(net shared between sheets) or a hierarchical label (port of a re-used sheet).
"""
import json
import os
import re
import uuid as uuidlib

import libbuild
import parts as P

G = 2.54
PAPERS = [("A4", 297, 210), ("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594)]
POWER = set(libbuild.POWER_NETS)
_ns = uuidlib.UUID("6c1a3f0e-9d5b-4c55-8f0a-5d2f0c0d1e00")


def U(*key):
    """Deterministic UUID so regenerating keeps the same ids."""
    return str(uuidlib.uuid5(_ns, "/".join(str(k) for k in key)))


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def snap(v, g=G):
    return round(v / g) * g


def label_len(net, glob=False):
    return len(net) * 1.05 + (3.5 if glob else 1.5)


class Inst:
    def __init__(self, sheet, lib_id, value, fp, pins, ref, fields, dnp, idx):
        self.sheet, self.lib_id, self.value, self.fp = sheet, lib_id, value, fp
        self.pins, self.ref_prefix, self.fields, self.dnp = pins, ref, fields, dnp
        self.idx = idx
        self.sym = libbuild.SYMBOLS[lib_id]
        self.x = self.y = 0.0
        self.refs = {}  # instance path -> reference

    def pin_net(self):
        """Resolve pin keys (numbers or names) to numbers. Returns {num: net}."""
        s = self.sym
        out = {}
        byname = {}
        for num, nm in s["names"].items():
            byname.setdefault(nm, []).append(num)
        for key, net in self.pins.items():
            key = str(key)
            if key in s["geo"]:
                out[key] = net
            elif key in byname:
                for n in byname[key]:
                    out[n] = net
            else:
                raise KeyError(f"{self.sheet.name}: {self.lib_id} has no pin '{key}'")
        return out


class Sheet:
    def __init__(self, board, name, filename, instances=None, ports=(), globals_=()):
        self.board, self.name, self.filename = board, name, filename
        self.items = []
        self.notes = []
        self.instances = instances  # list of dicts {name, ref_base, portmap} for re-used sheets
        self.ports = set(ports)
        self.force_global = set(globals_)
        self.uuid = U(board.name, "file", filename)

    # ------------------------------------------------------------------ adding parts
    def add(self, lib_id, value=None, fp=None, pins=None, ref=None, fields=None, dnp=False, auto_nc=False):
        sym = libbuild.SYMBOLS[lib_id]
        part = sym["part"]
        if part is None:
            value = value or lib_id.split(":")[1]
            fp = fp or ""
            ref = ref or "#PWR"
        else:
            value = value or part.name
            if fp is None:
                fp = part.fp_id or P.PartDefaults.get(part.name, "")
        it = Inst(self, lib_id, value, fp, dict(pins or {}), ref or part.ref, dict(fields or {}), dnp, len(self.items))
        pn = it.pin_net()
        for num, typ in sym["types"].items():
            if num not in pn and typ != "no_connect":
                if auto_nc:
                    it.pins[num] = "NC"
                else:
                    raise ValueError(f"{self.name}: {lib_id} pin {num} ({sym['names'][num]}) unassigned")
        self.items.append(it)
        return it

    def _two(self, lib_id, value, a, b, fp, **kw):
        return self.add(lib_id, value, fp, {"1": a, "2": b}, **kw)

    def R(self, value, a, b, fp=P.R0402, **kw):
        return self._two("eResistor:R", value, a, b, fp, **kw)

    def C(self, value, a, b="GND", fp=P.C0402, **kw):
        return self._two("eCapacitor:C", value, a, b, fp, **kw)

    def L(self, value, a, b, fp=P.L0805, **kw):
        return self._two("eCoil:L", value, a, b, fp, **kw)

    def FB(self, value, a, b, fp=P.FB0603, **kw):
        return self._two("eChoke:FB", value, a, b, fp, **kw)

    def D(self, kind, value, anode, cathode, fp, **kw):
        return self.add(f"eDiodes:{kind}", value, fp, {"2": anode, "1": cathode}, **kw)

    def LED(self, value, anode, cathode, fp=P.LED0603, **kw):
        return self.add("eLED:LED", value, fp, {"2": anode, "1": cathode}, **kw)

    def TP(self, net, fp=P.TP10, value=None, **kw):
        return self.add("eTestPoint:TestPoint", value or net, fp, {"1": net}, **kw)

    def note(self, text):
        self.notes.append(text)


class Board:
    def __init__(self, name, title, rev="V00", company="Drone project", comments=()):
        self.name, self.title, self.rev, self.company = name, title, rev, company
        self.comments = list(comments)
        self.sheets = []
        self.root_uuid = U(name, "root")
        self.root_notes = []
        self.extra_root_labels = []

    def sheet(self, name, filename, **kw):
        s = Sheet(self, name, filename, **kw)
        self.sheets.append(s)
        return s

    # ------------------------------------------------------------------ analysis
    def sheet_paths(self, s):
        """[(path, inst_name, ref_base, portmap)] for a sheet."""
        if s.instances:
            return [(f"/{self.root_uuid}/{U(self.name, 'sheet', s.filename, i['name'])}", i["name"], i["ref_base"], i["portmap"])
                    for i in s.instances]
        return [(f"/{self.root_uuid}/{U(self.name, 'sheet', s.filename)}", s.name, None, {})]

    def annotate(self):
        counters = {}
        for s in self.sheets:
            for path, iname, base, _ in self.sheet_paths(s):
                local = {}
                for it in s.items:
                    pre = it.ref_prefix
                    if base is not None:
                        local[pre] = local.get(pre, 0) + 1
                        it.refs[path] = f"{pre}{base + local[pre]}"
                    else:
                        counters[pre] = counters.get(pre, 0) + 1
                        it.refs[path] = f"{pre}{counters[pre]}"

    def net_scope(self):
        """net -> set(sheet filenames) (ports/global-forced count as global)."""
        scope = {}
        for s in self.sheets:
            for it in s.items:
                for num, net in it.pin_net().items():
                    if net == "NC" or net in POWER:
                        continue
                    scope.setdefault(net, set()).add(s.filename)
        return scope

    def drivers(self):
        """Nets that carry power_in pins but no power_out pin -> need PWR_FLAG."""
        info = {}
        for s in self.sheets:
            reuse = len(s.instances) if s.instances else 1
            for it in s.items:
                for num, net in it.pin_net().items():
                    if net == "NC":
                        continue
                    key = net if (net in POWER or not s.instances or net in s.force_global) else (s.filename, net)
                    t = it.sym["types"].get(num, "passive")
                    d = info.setdefault(key, set())
                    d.add(t)
        return [k for k, t in info.items() if "power_in" in t and "power_out" not in t]

    # ------------------------------------------------------------------ writing
    def write(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        self.annotate()
        scope = self.net_scope()
        need_flag = self.drivers()
        self._pwr = 0
        flagged = set()
        for s in self.sheets:
            flags = []
            for k in need_flag:
                if isinstance(k, tuple):
                    if k[0] == s.filename and k not in flagged:
                        flags.append(k[1]); flagged.add(k)
                else:
                    if k in flagged:
                        continue
                    on_sheet = any(k in it.pin_net().values() for it in s.items)
                    if on_sheet:
                        flags.append(k); flagged.add(k)
            for net in flags:
                s.add("ePowerSym:PWR_FLAG", "PWR_FLAG", "", {"1": net}, ref="#FLG")
            self._write_sheet(s, outdir, scope)
        self._write_root(outdir)

    # -- helpers
    def _lib_symbols(self, lib_ids):
        out = "  (lib_symbols\n"
        for lid in sorted(lib_ids):
            txt = libbuild.SYMBOLS[lid]["text"]
            name = lid.split(":", 1)[1]
            txt = txt.replace(f'(symbol {q(name)}', f'(symbol {q(lid)}', 1)
            out += "  " + txt.replace("\n", "\n  ").rstrip() + "\n"
        return out + "  )\n"

    def _title(self, sheet_title):
        c = "".join(f"    (comment {i + 1} {q(t)})\n" for i, t in enumerate(self.comments[:4]))
        return (f"  (title_block\n    (title {q(self.title + ' - ' + sheet_title)})\n    (date \"2026-10-08\")\n"
                f"    (rev {q(self.rev)})\n    (company {q(self.company)})\n{c}  )\n")

    def _symbol_inst(self, lib_id, x, y, rot, refs, value, fp, fields, dnp, props_xy, pins, key):
        sym = libbuild.SYMBOLS[lib_id]
        u = U(self.name, "sym", key)
        rx, ry, vx, vy = props_xy
        hide_ref = refs and list(refs.values())[0].startswith("#")
        first_ref = list(refs.values())[0]
        s = f"  (symbol (lib_id {q(lib_id)}) (at {f(x)} {f(y)} {rot}) (unit 1)\n"
        s += f"    (in_bom {'no' if hide_ref else 'yes'}) (on_board {'no' if hide_ref else 'yes'}) (dnp {'yes' if dnp else 'no'})\n"
        s += f"    (uuid {u})\n"
        eff = "(effects (font (size 1.27 1.27))" + (" hide" if hide_ref else "") + ")"
        s += f"    (property \"Reference\" {q(first_ref)} (at {f(rx)} {f(ry)} 0)\n      {eff}\n    )\n"
        pw = sym.get("power")
        veff = "(effects (font (size 1.27 1.27)))" if lib_id != "ePowerSym:PWR_FLAG" else "(effects (font (size 1.27 1.27)) hide)"
        s += f"    (property \"Value\" {q(value)} (at {f(vx)} {f(vy)} 0)\n      {veff}\n    )\n"
        s += f"    (property \"Footprint\" {q(fp)} (at {f(x)} {f(y)} 0)\n      (effects (font (size 1.27 1.27)) hide)\n    )\n"
        part = sym["part"]
        allf = dict(part.fields) if part else {}
        allf.update(fields)
        s += f"    (property \"Datasheet\" {q(allf.get('Datasheet', '~' if not pw else ''))} (at {f(x)} {f(y)} 0)\n      (effects (font (size 1.27 1.27)) hide)\n    )\n"
        for k, v in allf.items():
            if k in ("Datasheet", "Description", "Keywords"):
                continue
            s += f"    (property {q(k)} {q(v)} (at {f(x)} {f(y)} 0)\n      (effects (font (size 1.27 1.27)) hide)\n    )\n"
        for num in pins:
            s += f"    (pin {q(num)} (uuid {U(self.name, 'pin', key, num)}))\n"
        s += f"    (instances\n      (project {q(self.name)}\n"
        for path, r in refs.items():
            s += f"        (path {q(path)}\n          (reference {q(r)}) (unit 1)\n        )\n"
        s += "      )\n    )\n  )\n"
        return s

    def _write_sheet(self, s, outdir, scope):
        paths = self.sheet_paths(s)
        body = []
        used_libs = set()
        boxes = []
        # ---- measure every item
        for it in s.items:
            sym = it.sym
            x1, y1, x2, y2 = sym["bbox"]  # lib coords (y up)
            ext = {"L": 0, "R": 0, "U": 0, "D": 0}
            for num, net in it.pin_net().items():
                px, py, rot = sym["geo"][num]
                d = {0: "L", 180: "R", 90: "D", 270: "U"}[rot]
                if net == "NC":
                    e = 1
                elif net in POWER:
                    if d in ("L", "R"):
                        e = G + len(net) * 0.6 + 1.5
                        vy_extra = 6.0
                        ext["D" if P.power_kind(net) == "gnd" else "U"] = max(ext["D" if P.power_kind(net) == "gnd" else "U"],
                                                                                vy_extra - (py - y1 if P.power_kind(net) == "gnd" else y2 - py))
                    else:
                        e = G + 5.5
                else:
                    glob = self._is_global(s, net, scope)
                    e = G + label_len(net, glob)
                ext[d] = max(ext[d], e)
            if sym.get("power") or it.lib_id == "ePowerSym:PWR_FLAG":
                ext = {"L": 2, "R": 2, "U": 5, "D": 5}
            w = (x2 - x1) + ext["L"] + ext["R"] + 3.5
            w = max(w, len(it.value) * 1.15 + 3)
            h = (y2 - y1) + ext["U"] + ext["D"] + 6
            # offset of symbol origin inside the box
            ox = max(-x1 + ext["L"] + 1.5, w / 2)
            oy = y2 + ext["U"] + 3
            boxes.append((w, h, ox, oy))
        # ---- choose paper and pack (shelf algorithm, items kept in insertion order)
        note_h = 0
        if s.notes:
            note_h = 6 + 4.2 * sum(n.count("\n") + 1 for n in s.notes)
        for pname, pw, ph in PAPERS:
            margin = 12
            min_row = 38
            pos = []
            row_top = margin + note_h
            row_h = 0
            col_x, col_w, col_y = margin, 0, row_top
            for (w, h, ox, oy) in boxes:
                if pos and col_y + h <= row_top + row_h + 0.01:
                    pass  # stack in current column
                else:
                    nx = col_x + col_w
                    if pos and nx + w > pw - margin:
                        row_top += row_h
                        row_h = 0
                        nx = margin
                    col_x, col_w, col_y = nx, 0, row_top
                    row_h = max(row_h, h, min_row)
                pos.append((col_x + ox, col_y + oy))
                col_y += h
                col_w = max(col_w, w)
            if row_top + row_h <= ph - 45 or pname == PAPERS[-1][0]:
                break
        paper = pname
        for it, (px_, py_) in zip(s.items, pos):
            it.x, it.y = snap(px_), snap(py_)
        # ---- emit
        nets_local = set()
        for it in s.items:
            used_libs.add(it.lib_id)
            sym = it.sym
            if not it.ref_prefix.startswith("#"):
                refs = {p[0]: it.refs[p[0]] for p in paths}
            else:
                self._pwr += 1
                refs = {p[0]: f"{it.ref_prefix}0{self._pwr:03d}" for p in paths}
            # property positions
            text = sym["text"]
            m = re.search(r'\(property "Reference" "[^"]*" \(at ([-\d.]+) ([-\d.]+)', text)
            n = re.search(r'\(property "Value" "[^"]*" \(at ([-\d.]+) ([-\d.]+)', text)
            props = (it.x + float(m.group(1)), it.y - float(m.group(2)), it.x + float(n.group(1)), it.y - float(n.group(2)))
            pn = it.pin_net()
            body.append(self._symbol_inst(it.lib_id, it.x, it.y, 0, refs, it.value, it.fp, it.fields, it.dnp, props,
                                          sorted(sym["geo"].keys()), (s.filename, it.idx)))
            done_pts = set()
            groups = {}
            for num, net in sorted(pn.items()):
                px, py, rot = sym["geo"][num]
                ax, ay = it.x + px, it.y - py
                if (ax, ay) in done_pts:
                    continue
                done_pts.add((ax, ay))
                d = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[rot]
                key = (s.filename, it.idx, num)
                if net == "NC":
                    body.append(f"  (no_connect (at {f(ax)} {f(ay)}) (uuid {U(self.name, 'nc', *key)}))\n")
                    continue
                bx, by = ax + d[0] * G, ay + d[1] * G
                body.append(self._wire(ax, ay, bx, by, key))
                if net in POWER and d[0] != 0:
                    groups.setdefault((net, d), []).append((by, bx, key))
                elif net in POWER:
                    body.append(self._power(net, bx, by, d, key, paths))
                    used_libs.add(f"ePowerSym:{net}")
                else:
                    body.append(self._label(s, net, bx, by, d, key, scope))
            for (net, d), pts in groups.items():
                pts.sort()
                runs = [[pts[0]]]
                for p_ in pts[1:]:
                    if abs(p_[0] - runs[-1][-1][0] - G) < 0.01 and abs(p_[1] - runs[-1][-1][1]) < 0.01:
                        runs[-1].append(p_)
                    else:
                        runs.append([p_])
                for run in runs:
                    for a_, b_ in zip(run, run[1:]):
                        body.append(self._wire(a_[1], a_[0], b_[1], b_[0], ("join",) + b_[2]))
                    end = run[-1] if P.power_kind(net) == "gnd" else run[0]
                    body.append(self._power(net, end[1], end[0], d, end[2], paths))
                    used_libs.add(f"ePowerSym:{net}")
        # PWR_FLAG on power nets need a power symbol too (handled above since net in POWER)
        # ---- notes
        ny = 12
        for nt in s.notes:
            body.append(f"  (text {q(nt)} (at 12 {f(ny + 3)} 0)\n    (effects (font (size 1.5 1.5)) (justify left top))\n"
                        f"    (uuid {U(self.name, 'note', s.filename, nt[:40])})\n  )\n")
            ny += 4.2 * (nt.count("\n") + 1) + 2
        out = f"(kicad_sch (version 20230121) (generator eeschema)\n\n  (uuid {s.uuid})\n\n  (paper {q(paper)})\n\n"
        out += self._title(s.name) + "\n" + self._lib_symbols(used_libs) + "\n" + "".join(body)
        if s.instances is None and False:
            pass
        out += ")\n"
        open(os.path.join(outdir, s.filename), "w").write(out)

    def _is_global(self, s, net, scope):
        if s.instances:
            return net in s.force_global
        return len(scope.get(net, ())) > 1 or net in self.root_globals()

    def root_globals(self):
        g = set()
        for s in self.sheets:
            if s.instances:
                for i in s.instances:
                    g.update(i["portmap"].values())
                g.update(s.force_global)
        return g

    def _wire(self, x1, y1, x2, y2, key):
        return (f"  (wire (pts (xy {f(x1)} {f(y1)}) (xy {f(x2)} {f(y2)}))\n    (stroke (width 0) (type default))\n"
                f"    (uuid {U(self.name, 'wire', *key)})\n  )\n")

    def _power(self, net, x, y, d, key, paths):
        kind = P.power_kind(net)
        if kind == "gnd":
            rot = 180 if d == (0, -1) else 0
        else:
            rot = 180 if d == (0, 1) else 0
        self._pwr += 1
        refs = {p[0]: f"#PWR0{self._pwr:03d}" for p in paths}
        sym_v = 3.81 if kind == "vcc" else -3.81
        # value text position roughly beyond the symbol
        up = (kind == "vcc") == (rot == 0)
        vx, vy = x, (y - 3.6 if up else y + 3.9)
        return self._symbol_inst(f"ePowerSym:{net}", x, y, rot, refs, net, "", {}, False, (x, y, vx, vy), ["1"],
                                 ("pwr",) + key)

    def _label(self, s, net, x, y, d, key, scope):
        ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
        if s.instances and net in s.ports:
            just = "left" if ang in (0, 90) else "right"
            return (f"  (hierarchical_label {q(net)} (shape bidirectional) (at {f(x)} {f(y)} {ang}) (fields_autoplaced)\n"
                    f"    (effects (font (size 1.27 1.27)) (justify {just}))\n    (uuid {U(self.name, 'hl', *key)})\n  )\n")
        if self._is_global(s, net, scope):
            just = "left" if ang in (0, 90) else "right"
            return (f"  (global_label {q(net)} (shape bidirectional) (at {f(x)} {f(y)} {ang}) (fields_autoplaced)\n"
                    f"    (effects (font (size 1.27 1.27)) (justify {just}))\n    (uuid {U(self.name, 'gl', *key)})\n"
                    f"    (property \"Intersheetrefs\" \"${{INTERSHEET_REFS}}\" (at {f(x)} {f(y)} 0)\n"
                    f"      (effects (font (size 1.27 1.27)) (justify {just}) hide)\n    )\n  )\n")
        just = "left bottom" if ang in (0, 90) else "right bottom"
        return (f"  (label {q(net)} (at {f(x)} {f(y)} {ang}) (fields_autoplaced)\n"
                f"    (effects (font (size 1.27 1.27)) (justify {just}))\n    (uuid {U(self.name, 'lb', *key)})\n  )\n")

    def _write_root(self, outdir):
        body = []
        x, y = 25.4, 50.8
        page = 2
        col_w = 76.2
        for s in self.sheets:
            for path, iname, base, portmap in self.sheet_paths(s):
                suid = path.split("/")[-1]
                pins = sorted(s.ports) if s.instances else []
                h = max(15.24, G * (len(pins) + 2))
                w = 40.64
                if y + h > 180:
                    y = 50.8
                    x += col_w
                fname = s.filename
                body.append(f"  (sheet (at {f(x)} {f(y)}) (size {f(w)} {f(h)}) (fields_autoplaced)\n"
                            f"    (stroke (width 0.1524) (type solid))\n    (fill (color 0 0 0 0.0000))\n    (uuid {suid})\n"
                            f"    (property \"Sheetname\" {q(iname)} (at {f(x)} {f(y - 0.7)} 0)\n"
                            f"      (effects (font (size 1.27 1.27)) (justify left bottom))\n    )\n"
                            f"    (property \"Sheetfile\" {q(fname)} (at {f(x)} {f(y + h + 0.6)} 0)\n"
                            f"      (effects (font (size 1.27 1.27)) (justify left top))\n    )\n")
                for i, pn in enumerate(pins):
                    py = y + G * (i + 1)
                    body.append(f"    (pin {q(pn)} bidirectional (at {f(x + w)} {f(py)} 0)\n"
                                f"      (effects (font (size 1.27 1.27)) (justify right))\n"
                                f"      (uuid {U(self.name, 'sheetpin', suid, pn)})\n    )\n")
                body.append(f"    (instances\n      (project {q(self.name)}\n        (path \"/{self.root_uuid}\" (page {q(str(page))}))\n"
                            f"      )\n    )\n  )\n")
                for i, pn in enumerate(pins):
                    py = y + G * (i + 1)
                    net = portmap[pn]
                    key = ("root", suid, pn)
                    body.append(self._wire(x + w, py, x + w + G, py, key))
                    body.append(f"  (global_label {q(net)} (shape bidirectional) (at {f(x + w + G)} {f(py)} 0) (fields_autoplaced)\n"
                                f"    (effects (font (size 1.27 1.27)) (justify left))\n    (uuid {U(self.name, 'rgl', *key)})\n"
                                f"    (property \"Intersheetrefs\" \"${{INTERSHEET_REFS}}\" (at {f(x + w + G)} {f(py)} 0)\n"
                                f"      (effects (font (size 1.27 1.27)) (justify left) hide)\n    )\n  )\n")
                page += 1
                y += h + 12.7
        ny = 20
        for nt in self.root_notes:
            body.append(f"  (text {q(nt)} (at 180 {f(ny)} 0)\n    (effects (font (size 1.5 1.5)) (justify left top))\n"
                        f"    (uuid {U(self.name, 'rootnote', nt[:40])})\n  )\n")
            ny += 4.5 * (nt.count("\n") + 1) + 4
        out = f"(kicad_sch (version 20230121) (generator eeschema)\n\n  (uuid {self.root_uuid})\n\n  (paper \"A3\")\n\n"
        out += self._title("Overview") + "\n  (lib_symbols\n  )\n\n" + "".join(body)
        out += "\n  (sheet_instances\n    (path \"/\" (page \"1\"))\n  )\n)\n"
        open(os.path.join(outdir, f"{self.name}.kicad_sch"), "w").write(out)
