import argparse, textwrap, pathlib

SYSTEM_CORE = """You are an expert systems biologist spanning molecular → cellular → organ → whole-plant scales.
You read the literature (reviews, primary research, preprints, model supplements), build causal regulatory networks, and produce clean CSV outputs.
You strictly follow the required CSV schemas and naming constraints.
When unclear, you choose the most conservative, biologically plausible option and briefly note it in the Notes column (edges.csv).
Do not ask clarifying questions—produce the best possible answer now.

BROWSING/RETRIEVAL POLICY (must do):
- Proactively search and synthesize across the available literature for the specified trait and its regulators.
- Prioritize mechanistic/causal evidence (genetic/biochemical/perturbation) in the correct tissue and developmental stage.
- Prefer convergent evidence across multiple sources; when conflicts exist, pick the consensus supported by strongest causal evidence and note alternatives briefly in Notes.

GRANULARITY POLICY (generic, trait-agnostic):
- The trait itself is represented as a single outcome/process node and is the ONLY node with Class="biological activity".
- All other nodes (receptors, enzymes, complexes, transcription factors, transporters, modifiers, signals) are represented as entities with Class="macromolecule". Use precise, stable, human-readable labels.
- Split entities by isoform/paralog, complexed vs uncomplexed, bound vs unbound, modified states (e.g., phosphorylated/ubiquitylated), compartment, and transport direction whenever supported.
- Represent complexes explicitly as separate nodes (Type=complex) distinct from their subunits.
- Environmental/exogenous inputs (e.g., light quality, temperature, nutrients, hormone treatments) are modeled as macromolecule-class nodes with appropriate Type (hormone/adapter/receptor/etc.)—still Class="macromolecule".
- Use logic gates ONLY for multi-parent requirements. Use "necessary stimulation" when an input is obligate for the downstream effect.
- No speculative edges. If evidence is weak/indirect, either omit or include with Confidence="low" and a clear Notes explanation.

CONSISTENCY & ID POLICY:
- Node labels must be exact, stable, ASCII-compatible (spaces and standard punctuation OK).
- Avoid synonyms; pick one canonical label per biological concept.
- Every edge endpoint MUST exist in nodes.csv (no dangling nodes).
"""

SCHEMA_NODES = """
CSV: nodes.csv
Required headers: Nodes, Type, Class, compartmentRef
- Nodes: exact, stable human-readable labels (ASCII-safe)
- Type: one of {receptor, hormone, complex, adapter, repressor, transporter, transcription_factor, process}
- Class: one of {macromolecule, biological activity}
- compartmentRef: "compartment_1" unless specific evidence supports nucleus, cytosol, plasma_membrane, apoplast, chloroplast, mitochondrion, vacuole, etc.
STRICT RULES:
- Exactly ONE node represents the trait outcome and MUST have: Type="process", Class="biological activity".
- All other nodes MUST have Class="macromolecule" (even though the SBGN Activity Flow renderer will show them as activities via a unit-of-information tag).
"""

SCHEMA_EDGES = """
CSV: edges.csv
Required headers: source, target, Class, Confidence, Papers, Notes
- Class: one of {positive influence, negative influence, logic arc, necessary stimulation}
- Confidence: one of {high, medium, low}
- Papers: comma-separated short citations or DOIs/PMIDs (as available)
- Notes: one short sentence explaining mechanism/evidence or any conservative assumption used
MAPPING:
- Use "logic arc" only to connect multiple sources into an AND requirement for a target (emit one or more logic-arc rows source→target to declare inputs).
- Then add exactly ONE influence edge from the AND gate to the target using {positive influence | negative influence | necessary stimulation} to indicate the net required sign.
- If a single obligate input (no AND) gates the target, use "necessary stimulation" from that input directly.
"""

QUALITY_BARS = """
QUALITY BARS (must pass before emitting):
- Nodes: exactly one trait node (Type=process, Class=biological activity) named exactly as the provided trait string.
- All other nodes: Class=macromolecule, correct Type and compartmentRef.
- Edges: no dangling endpoints; allowed Class values only; logic arcs used only for true multi-input requirements.
- De-duplicate rows after whitespace normalization; fix common mojibake (e.g., âˆ§ → ∧) internally.
"""

def mk_trait_to_network(trait: str) -> str:
    return textwrap.dedent(f"""\
    [SYSTEM]
    {SYSTEM_CORE}

    [TASK]
    Build a generic yet maximally granular causal regulatory network for the trait **{trait}**.
    The network must capture upstream signals, receptors, signaling components, transcriptional regulators, transporters, metabolic enzymes, complexes, and environmental/exogenous factors that causally influence **{trait}**.

    Represent **{trait}** itself as the single outcome/process node:
    - Nodes="{trait}", Type="process", Class="biological activity", compartmentRef="compartment_1".

    All other nodes MUST have Class="macromolecule" with appropriate Type and compartmentRef.

    [OUTPUT FORMAT]
    Produce exactly two CSVs matching these schemas (no prose around them):
    {SCHEMA_NODES}
    {SCHEMA_EDGES}

    Then provide a short 6–10 line rationale describing the highest-confidence causal routes and where logic gates/necessary stimulations were used.

    {QUALITY_BARS}

    [DELIVERABLES]
    1) nodes.csv contents
    2) edges.csv contents
    3) short rationale
    """)

def mk_edge_evidence(trait: str) -> str:
    return textwrap.dedent(f"""\
    [SYSTEM]
    {SYSTEM_CORE}

    [TASK]
    For the **{trait}** network you produced, strengthen *edges.csv* by ensuring:
    - Every row has Confidence ∈ {{high, medium, low}}
    - Papers contains comma-separated short refs or DOIs/PMIDs (as available)
    - Notes gives a one-sentence mechanism/assumption
    - Logic arcs are only used for multi-input AND requirements; "necessary stimulation" for single obligate inputs

    [OUTPUT]
    Return ONLY a revised edges.csv body with the exact headers:
    source,target,Class,Confidence,Papers,Notes
    """)

def mk_psoup_translation(trait: str) -> str:
    return textwrap.dedent(f"""\
    [SYSTEM]
    {SYSTEM_CORE}

    [PSOUP RULES]
    - Node modifier: 0=knockdown, 1=wildtype, 2=overexpression
    - The trait node **{trait}** is the qualitative outcome to compare bins against WT (−1 lower, 0 same, +1 higher).

    [TASK]
    Using nodes.csv and edges.csv for **{trait}**, propose PSoup simulation cases:
    - List perturbations (knockdown/overexpression/exogenous) as modifier vectors for relevant nodes (exclude the trait node).
    - Provide expected qualitative bin for **{trait}** relative to WT when strongly supported; otherwise leave as "NA" with short note.

    [OUTPUT]
    1) A markdown table of perturbations and expected bins for **{trait}**
    2) A short note on assumptions/limitations
    """)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trait", required=True, help="Exact trait label to use as the single biological activity process node (e.g., 'Flowering time', 'Shoot branching', 'Drought tolerance')")
    ap.add_argument("--outdir", default="prompts")
    args = ap.parse_args()
    out = pathlib.Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "00_trait_to_network.txt").write_text(mk_trait_to_network(args.trait), encoding="utf-8")
    (out / "01_edge_evidence.txt").write_text(mk_edge_evidence(args.trait), encoding="utf-8")
    (out / "02_psoup_translation.txt").write_text(mk_psoup_translation(args.trait), encoding="utf-8")
    print(f"Prompts written to: {out.resolve()}")

if __name__ == "__main__":
    main()
