"""Grouped BOM (CSV) straight from the generator data: one line per value/footprint/MPN."""
import csv
import os
import re


def natkey(ref):
    m = re.match(r"([A-Za-z#]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def write_bom(B, outdir):
    B.annotate()
    groups = {}
    for s in B.sheets:
        for path, iname, base, _ in B.sheet_paths(s):
            for it in s.items:
                if it.ref_prefix.startswith("#") or it.lib_id == "eMechanical:MountingHole":
                    continue
                part = it.sym["part"]
                f = dict(part.fields) if part else {}
                f.update(it.fields)
                key = (it.value, it.fp.split(":")[-1], f.get("Manufacturer", ""), f.get("MPN", ""), it.dnp)
                groups.setdefault(key, []).append(it.refs[path])
    rows = sorted(groups.items(), key=lambda kv: (kv[0][4], natkey(sorted(kv[1], key=natkey)[0])))
    path = os.path.join(outdir, f"{B.name}_BOM.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Qty", "References", "Value", "Footprint", "Manufacturer", "MPN", "Populate"])
        for (val, fp, mfr, mpn, dnp), refs in rows:
            refs = sorted(refs, key=natkey)
            w.writerow([len(refs), " ".join(refs), val, fp, mfr, mpn, "DNP" if dnp else "yes"])
    return path
