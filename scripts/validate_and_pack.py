import argparse, pandas as pd, pathlib, json, re

NODE_REQUIRED = ["Nodes","Type","Class","compartmentRef"]
EDGE_REQUIRED = ["source","target","Class","Confidence","Papers","Notes short explanation of edge"]
EDGE_CLASS_ALLOWED = {"positive influence","negative influence","logic arc","necessary stimulation"}

def sanitize(s: str) -> str:
    return "n_" + re.sub(r"[^0-9A-Za-z_]", "_", s)[:64]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", required=True)
    ap.add_argument("--edges", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    nodes = pd.read_csv(args.nodes)
    edges = pd.read_csv(args.edges)

    for h in NODE_REQUIRED:
        if h not in nodes.columns: raise SystemExit(f"nodes.csv missing column: {h}")
    for h in EDGE_REQUIRED:
        if h not in edges.columns: raise SystemExit(f"edges.csv missing column: {h}")

    # enforce: process => biological activity
    mask = nodes["Type"].str.strip().eq("process")
    nodes.loc[mask, "Class"] = "biological activity"

    nodes = nodes.applymap(lambda x: x.strip() if isinstance(x,str) else x)
    edges = edges.applymap(lambda x: x.strip() if isinstance(x,str) else x)

    bad = ~edges["Class"].isin(EDGE_CLASS_ALLOWED)
    if bad.any():
        raise SystemExit(f"Unsupported edge Class values: {edges.loc[bad,'Class'].unique()}")

    edges = edges.drop_duplicates()

    id_map = {row["Nodes"]: sanitize(row["Nodes"]) for _, row in nodes.iterrows()}
    unknown_sources = set(edges["source"]) - set(nodes["Nodes"])
    unknown_targets = set(edges["target"]) - set(nodes["Nodes"])
    if unknown_sources or unknown_targets:
        raise SystemExit(f"Edges reference unknown nodes:\n sources={unknown_sources}\n targets={unknown_targets}")

    nodes_out = outdir / "nodes.cleaned.csv"
    edges_out = outdir / "edges.cleaned.csv"
    nodes.to_csv(nodes_out, index=False)
    edges.to_csv(edges_out, index=False)

    meta = {"n_nodes": int(len(nodes)), "n_edges": int(len(edges)), "id_map_sample": dict(list(id_map.items())[:10])}
    (outdir / "bundle.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Bundle wrote to {outdir}")

if __name__ == "__main__":
    main()
