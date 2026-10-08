"""Create the .kicad_pcb for each project with KiCad's pcbnew API:
outline, mounting holes, layer count, GND plane, and every footprint loaded from the eXxx libraries with its
nets assigned and linked to its schematic symbol (so 'Update PCB from Schematic' just works).
Footprints are parked next to the board, grouped by schematic sheet: placement and routing are done in KiCad.
"""
import importlib
import math
import os
import sys

import pcbnew

import libbuild
from schgen import U
from check import kicad_netlist

sys.dont_write_bytecode = True
LIBROOT = libbuild.ROOT
MM = pcbnew.FromMM

BOARDS = {
    # name: (w, h, layers, hole_pitch, hole_fp, corner_r)
    "FCV00": (36.0, 36.0, 4, 30.5, "MountingHole_4mm", 3.0),
    "ESCV00": (42.0, 42.0, 6, 30.5, "MountingHole_3.2mm_M3", 3.0),
    "RXV00": (22.0, 14.0, 4, None, None, 1.0),
    "VTXV00": (27.0, 27.0, 4, 20.0, "MountingHole_2.2mm_M2", 2.0),
}


OX, OY = 70.0, 60.0  # board centre on the drawing sheet


def V(x, y):
    return pcbnew.VECTOR2I(MM(x + OX), MM(y + OY))


def outline(board, w, h, r):
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a)); s.SetEnd(V(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
        board.Add(s)

    def arc(c, a0):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        p = [(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a))) for a in (a0, a0 + 45, a0 + 90)]
        s.SetArcGeometry(V(*p[0]), V(*p[1]), V(*p[2]))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
        board.Add(s)

    x0, y0, x1, y1 = -w / 2, -h / 2, w / 2, h / 2
    seg((x0 + r, y0), (x1 - r, y0)); seg((x1, y0 + r), (x1, y1 - r))
    seg((x1 - r, y1), (x0 + r, y1)); seg((x0, y1 - r), (x0, y0 + r))
    arc((x1 - r, y0 + r), 270); arc((x1 - r, y1 - r), 0); arc((x0 + r, y1 - r), 90); arc((x0 + r, y0 + r), 180)


def text(board, s, x, y, size=1.0, layer=pcbnew.Cmts_User):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(V(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(t)


def load_fp(fp_id):
    lib, name = fp_id.split(":", 1)
    path = os.path.join(LIBROOT, lib, f"{lib}.pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError(f"footprint not found {fp_id}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def build(mod, proj_dir):
    m = importlib.import_module(mod)
    B = m.B
    B.annotate()
    name = B.name
    w, h, layers, pitch, hole_fp, r = BOARDS[name]
    nets, comps = kicad_netlist(proj_dir, name)
    node_net = {}
    for nm, nodes in nets.items():
        for ref, pin in nodes:
            node_net[(ref, pin)] = nm

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(layers)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(MM(1.6))
    tb = board.GetTitleBlock()
    tb.SetTitle(B.title)
    tb.SetRevision(B.rev)
    tb.SetCompany(B.company)
    tb.SetDate("2026-10-08")
    for i, c in enumerate(B.comments[:4]):
        tb.SetComment(i, c)

    netinfo = {}
    for nm in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, nm)
        board.Add(ni)
        netinfo[nm] = ni

    outline(board, w, h, r)

    # zones: GND on In1 (and bottom for RF boards)
    def zone(layer, netname):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(netinfo[netname])
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((-w / 2 + 0.3, -h / 2 + 0.3), (w / 2 - 0.3, -h / 2 + 0.3), (w / 2 - 0.3, h / 2 - 0.3), (-w / 2 + 0.3, h / 2 - 0.3)):
            ol.Append(MM(x + OX), MM(y + OY))
        z.SetLocalClearance(MM(0.2))
        z.SetMinThickness(MM(0.2))
        z.SetIsFilled(False)
        board.Add(z)

    zone(pcbnew.In1_Cu, "GND")
    if layers >= 6:
        zone(pcbnew.In4_Cu, "GND")

    # footprints, grouped by sheet instance, parked to the right of the board
    gx = w / 2 + 8
    gy = -h / 2
    col_w = 0
    holes = []
    for s in B.sheets:
        for path, iname, base, _ in B.sheet_paths(s):
            sheet_uuid = path.split("/")[-1]
            text(board, f"[{iname}]", gx, gy - 2, 1.2)
            x, y, row_h = gx, gy, 0
            row_limit = gx + 60
            for it in s.items:
                if it.ref_prefix.startswith("#") or not it.fp:
                    continue
                ref = it.refs[path]
                fp = load_fp(it.fp)
                fp.SetReference(ref)
                fp.SetValue(it.value)
                fp.SetPath(pcbnew.KIID_PATH(f"/{sheet_uuid}/{U(name, 'sym', (s.filename, it.idx))}"))
                try:
                    fp.SetSheetname(iname)
                    fp.SetSheetfile(s.filename)
                except AttributeError:
                    pass
                if it.dnp:
                    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM)
                for pad in fp.Pads():
                    nm = node_net.get((ref, pad.GetNumber()))
                    if nm:
                        pad.SetNet(netinfo[nm])
                if it.lib_id == "eMechanical:MountingHole":
                    holes.append(fp)
                    board.Add(fp)
                    continue
                bb = fp.GetBoundingBox(False, False)
                fw, fh = pcbnew.ToMM(bb.GetWidth()) + 1.0, pcbnew.ToMM(bb.GetHeight()) + 1.0
                if x + fw > row_limit and x > gx:
                    x = gx
                    y += row_h
                    row_h = 0
                # position so that the bounding box top-left lands on (x, y)
                fp.SetPosition(V(0, 0))
                bb = fp.GetBoundingBox(False, False)
                fp.SetPosition(V(x - (pcbnew.ToMM(bb.GetX()) - OX) + 0.5, y - (pcbnew.ToMM(bb.GetY()) - OY) + 0.5))
                board.Add(fp)
                x += fw
                row_h = max(row_h, fh)
            gy = y + row_h + 6
            col_w = max(col_w, row_limit - gx)
    # mounting holes on the pitch square
    if pitch and holes:
        pts = [(-pitch / 2, -pitch / 2), (pitch / 2, -pitch / 2), (pitch / 2, pitch / 2), (-pitch / 2, pitch / 2)]
        for fp, (x, y) in zip(holes, pts):
            fp.SetPosition(V(x, y))
    elif name == "VTXV00":
        pass
    text(board, f"{name} - footprints imported and netted from the schematic.", -w / 2, h / 2 + 3, 1.0)
    text(board, "Placement + routing to do in KiCad (see Hardware/Kicad/Readme.md).", -w / 2, h / 2 + 4.6, 1.0)
    ds.SetAuxOrigin(V(0, 0))
    ds.SetGridOrigin(V(0, 0))
    out = os.path.join(proj_dir, f"{name}.kicad_pcb")
    board.Save(out)
    nfp = len(board.GetFootprints())
    print(f"{name}: board {w}x{h} mm, {layers} layers, {nfp} footprints, {len(nets)} nets -> {out}")


if __name__ == "__main__":
    libbuild.build_all(write=False)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for mod in sys.argv[1:] or ["fcv00", "escv00", "rxv00", "vtxv00"]:
        build(mod, os.path.join(base, mod.upper()))
