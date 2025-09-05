import argparse, pandas as pd, re
from xml.sax.saxutils import escape

SBGN_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<sbgn xmlns="http://sbgn.org/libsbgn/0.3">
  <map language="process description">
"""
SBGN_FOOTER = """  </map>
</sbgn>
"""

def glyph_for(row):
    t = row["Type"].strip()
    c = row["Class"].strip()
    if t == "process" and c == "biological activity":
        return "biological activity"
    return "macromolecule" if c == "macromolecule" else "biological activity"

def sanitize_id(name):
    return "n_" + re.sub(r"[^0-9A-Za-z_]", "_", str(name))[:64]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", required=True)
    ap.add_argument("--edges", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    nodes = pd.read_csv(args.nodes)
    edges = pd.read_csv(args.edges)

    groups = {}
    for _, r in nodes.iterrows():
        groups.setdefault(r["Type"], []).append(r)
    x0, y0, dx, dy = 100, 100, 220, 140
    coords, row_i = {}, 0
    for g, rows in groups.items():
        for col_i, r in enumerate(rows):
            coords[r["Nodes"]] = (x0 + col_i*dx, y0 + row_i*dy)
        row_i += 1

    xml = [SBGN_HEADER]
    for _, r in nodes.iterrows():
        nid = sanitize_id(r["Nodes"])
        x, y = coords[r["Nodes"]]
        clazz = glyph_for(r)
        label = escape(str(r["Nodes"]))
        xml += [
            f'    <glyph id="{nid}" class="{clazz}">',
            f'      <label text="{label}"/>',
            f'      <bbox x="{x}" y="{y}" w="150" h="50"/>',
            f'    </glyph>'
        ]

    CLASS_TO_SBGN = {
        "positive influence": "positive influence",
        "negative influence": "negative influence",
        "logic arc": "logic arc",
        "necessary stimulation": "necessary stimulation"
    }
    for _, e in edges.iterrows():
        sid = sanitize_id(e["source"]); tid = sanitize_id(e["target"])
        clazz = CLASS_TO_SBGN.get(e["Class"].strip(), "positive influence")
        xml.append(f'    <arc class="{clazz}" source="{sid}" target="{tid}"><port idref="{sid}"/><port idref="{tid}"/></arc>')

    xml.append(SBGN_FOOTER)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(xml))
    print(f"SBGN written to {args.out}")

if __name__ == "__main__":
    main()
