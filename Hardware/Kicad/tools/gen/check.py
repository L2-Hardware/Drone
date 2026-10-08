"""Validate a generated project: export the netlist with kicad-cli and compare KiCad's connectivity
with the intended connectivity (as partitions of (ref, pin)), plus basic electrical-rule checks."""
import importlib
import os
import tempfile
import subprocess
import sys

import libbuild
from sexp import parse, find, find_all

sys.dont_write_bytecode = True


def kicad_netlist(proj_dir, name):
    out = os.path.join(tempfile.gettempdir(), f"{name}.net")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out,
                    f"{proj_dir}/{name}.kicad_sch"], check=True, capture_output=True)
    tree = parse(open(out).read())
    nets = {}
    for n in find_all(find(tree, "nets"), "net"):
        nm = find(n, "name")[1]
        nodes = frozenset((find(x, "ref")[1], find(x, "pin")[1]) for x in find_all(n, "node"))
        nets[nm] = nodes
    comps = {find(c, "ref")[1]: find(c, "value")[1] for c in find_all(find(tree, "components"), "comp")}
    return nets, comps


def expected(B):
    groups = {}
    types = {}
    for s in B.sheets:
        for path, iname, base, portmap in B.sheet_paths(s):
            for it in s.items:
                if it.ref_prefix.startswith("#"):
                    continue
                ref = it.refs[path]
                for num, net in it.pin_net().items():
                    types[(ref, num)] = it.sym["types"].get(num)
                    if net == "NC":
                        key = ("NC", ref, num)
                    elif net in libbuild.POWER_NETS or not s.instances or net in s.force_global:
                        key = net
                    elif net in s.ports:
                        key = portmap[net]
                    else:
                        key = (iname, net)
                    groups.setdefault(key, set()).add((ref, num))
    return groups, types


def run(mod, proj_dir):
    m = importlib.import_module(mod)
    B = m.B
    B.annotate()
    nets, comps = kicad_netlist(proj_dir, B.name)
    exp, types = expected(B)
    ok = True
    actual_parts = {}
    for nm, nodes in nets.items():
        for node in nodes:
            actual_parts[node] = nm
    # every intended net must be exactly one KiCad net
    for key, nodes in exp.items():
        if isinstance(key, tuple) and key[0] == "NC":
            continue
        names = {actual_parts.get(n) for n in nodes}
        if len(names) != 1 or None in names:
            ok = False
            print(f"  SPLIT/MISSING net {key}: {names}")
            continue
        nm = names.pop()
        if set(nets[nm]) != set(nodes):
            extra = set(nets[nm]) - set(nodes)
            ok = False
            print(f"  MERGED net {key} with {sorted(extra)[:6]}")
    # single-pin nets (excluding NC flags and test points)
    for key, nodes in exp.items():
        if isinstance(key, tuple) and key[0] == "NC":
            continue
        if len(nodes) == 1:
            ref, pin = next(iter(nodes))
            if not ref.startswith("TP"):
                print(f"  WARN single-pin net {key}: {ref}.{pin}")
    # driver check: nets with input pins but no output/bidir/passive/power_out source
    for key, nodes in exp.items():
        if isinstance(key, tuple) and key[0] == "NC":
            continue
        t = [types[n] for n in nodes]
        if "input" in t and not any(x in ("output", "bidirectional", "tri_state", "passive", "power_out", "open_collector") for x in t):
            print(f"  WARN input-only net {key}: {sorted(nodes)}")
        if t.count("output") + t.count("power_out") > 1 and key not in libbuild.POWER_NETS:
            print(f"  WARN multiple outputs on {key}: {sorted(n for n in nodes if types[n] in ('output', 'power_out'))}")
    n_comp = len([c for c in comps if not c.startswith("#")])
    print(f"{B.name}: {n_comp} components, {len(nets)} nets -> {'CONNECTIVITY OK' if ok else 'ERRORS'}")
    return ok


if __name__ == "__main__":
    libbuild.build_all(write=False)
    import os
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    good = True
    for mod in sys.argv[1:] or ["fcv00", "escv00", "rxv00", "vtxv00"]:
        name = mod.upper()
        good &= run(mod, os.path.join(base, name))
    sys.exit(0 if good else 1)
