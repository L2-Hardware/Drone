"""Project-level files: .kicad_pro (from the FCV00 template), lib tables."""
import json
import os
import shutil

KICAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEMPLATE = os.path.join(KICAD_DIR, "FCV00", "FCV00.kicad_pro")
_TEMPLATE_CACHE = None


def _template():
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        _TEMPLATE_CACHE = json.load(open(TEMPLATE))
    return json.loads(json.dumps(_TEMPLATE_CACHE))


def netclass(name, track, clearance=0.15, via_d=0.45, via_drill=0.2, dp_w=None, dp_gap=None):
    return {"bus_width": 12, "clearance": clearance, "diff_pair_gap": dp_gap or 0.15, "diff_pair_via_gap": 0.25,
            "diff_pair_width": dp_w or 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "name": name, "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647 if name == "Default" else 0,
            "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": track, "via_diameter": via_d, "via_drill": via_drill,
            "wire_width": 6}


def write_project(name, classes, patterns, rules=None):
    d = os.path.join(KICAD_DIR, name)
    os.makedirs(d, exist_ok=True)
    pro = _template()
    pro["meta"]["filename"] = f"{name}.kicad_pro"
    pro["net_settings"]["classes"] = classes
    pro["net_settings"]["netclass_patterns"] = [{"netclass": c, "pattern": p} for p, c in patterns]
    ds = pro["board"]["design_settings"]
    r = {"min_clearance": 0.1, "min_track_width": 0.1, "min_via_diameter": 0.4, "min_via_annular_width": 0.1,
         "min_through_hole_diameter": 0.2, "min_hole_to_hole": 0.25, "min_hole_clearance": 0.2,
         "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0, "min_microvia_diameter": 0.2,
         "min_microvia_drill": 0.1, "max_error": 0.005, "solder_mask_to_copper_clearance": 0.0}
    r.update(rules or {})
    ds["rules"] = r
    ds["track_widths"] = [0.0, 0.1, 0.15, 0.2, 0.3, 0.5, 0.8, 1.2]
    ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.45, "drill": 0.2}, {"diameter": 0.6, "drill": 0.3},
                            {"diameter": 0.8, "drill": 0.4}]
    json.dump(pro, open(os.path.join(d, f"{name}.kicad_pro"), "w"), indent=2)
    for t in ("sym-lib-table", "fp-lib-table"):
        if name != "FCV00":
            shutil.copyfile(os.path.join(KICAD_DIR, "FCV00", t), os.path.join(d, t))
    return d
