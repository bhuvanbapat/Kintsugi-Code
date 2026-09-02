"""Refresh the Graphify graph after substantial code changes (skill: --update semantics).

Re-runs detection + AST extraction over the current tree and rebuilds
graph.json/GRAPH_REPORT.md so architectural queries reflect the new code.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PY_EXE = (ROOT / "graphify-out" / ".graphify_python").read_text(encoding="utf-8").strip()

STEPS = {
    "detect": """
import json
from pathlib import Path
from graphify.detect import detect
result = detect(Path('.'))
Path('graphify-out/.graphify_detect.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
print('detected', result['total_files'], 'files')
""",
    "ast": """
import json
from pathlib import Path
from graphify.extract import collect_files, extract
detect = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
code_files = []
for f in detect.get('files', {}).get('code', []):
    p = Path(f)
    code_files.extend(collect_files(p) if p.is_dir() else [p])
if code_files:
    result = extract(code_files, cache_root=Path('.'), parallel=False)
    Path('graphify-out/.graphify_ast.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    print('AST:', len(result['nodes']), 'nodes', len(result['edges']), 'edges')
""",
    "semantic": """
import json
from pathlib import Path
# Code-only corpus: empty semantic layer (docs re-indexed via AST rationale nodes).
Path('graphify-out/.graphify_semantic.json').write_text(json.dumps(
    {'nodes': [], 'edges': [], 'hyperedges': [], 'input_tokens': 0, 'output_tokens': 0}), encoding='utf-8')
""",
    "merge": """
import json
from pathlib import Path
ast = json.loads(Path('graphify-out/.graphify_ast.json').read_text(encoding='utf-8'))
sem = json.loads(Path('graphify-out/.graphify_semantic.json').read_text(encoding='utf-8'))
seen = {n['id'] for n in ast['nodes']}
merged_nodes = list(ast['nodes']) + [n for n in sem['nodes'] if n['id'] not in seen]
merged = {'nodes': merged_nodes, 'edges': ast['edges'] + sem['edges'],
          'hyperedges': [], 'input_tokens': 0, 'output_tokens': 0}
Path('graphify-out/.graphify_extract.json').write_text(json.dumps(merged, ensure_ascii=False), encoding='utf-8')
print('merged:', len(merged_nodes), 'nodes')
""",
    "build": """
import json
from pathlib import Path
from graphify.analyze import god_nodes, suggest_questions, surprising_connections
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.export import to_json
from graphify.report import generate
extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding='utf-8'))
detection = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
G = build_from_json(extraction, root='.', directed=False)
if G.number_of_nodes() == 0:
    raise SystemExit('empty graph')
communities = cluster(G)
cohesion = score_all(G, communities)
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
labels = {cid: 'Community ' + str(cid) for cid in communities}
questions = suggest_questions(G, communities, labels)
wrote = to_json(G, communities, 'graphify-out/graph.json', community_labels=labels)
if not wrote:
    raise SystemExit('shrink-guard refused')
report = generate(G, communities, cohesion, labels, gods, surprises, detection,
                  {'input': 0, 'output': 0}, '.', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding='utf-8')
analysis = {'communities': {str(k): v for k, v in communities.items()},
            'cohesion': {str(k): v for k, v in cohesion.items()},
            'gods': gods, 'surprises': surprises, 'questions': questions}
Path('graphify-out/.graphify_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False), encoding='utf-8')
print('graph:', G.number_of_nodes(), 'nodes', G.number_of_edges(), 'edges', len(communities), 'communities')
""",
}


def run_step(name: str, code: str) -> None:
    print(f"--- {name} ---")
    result = subprocess.run([PY_EXE, "-c", code], cwd=str(ROOT), capture_output=True, text=True)
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    if out:
        print(out)
    if result.returncode != 0:
        print("STDERR:", err[-1500:])
        raise SystemExit(f"step {name} failed")
    if "warning" in err.lower() and "parallel" not in err.lower():
        print("note:", err[:300])


if __name__ == "__main__":
    for step_name, code in STEPS.items():
        run_step(step_name, code)
    # cleanup temp sidecars, keep persistent outputs
    for sidecar in (".graphify_detect.json", ".graphify_extract.json",
                    ".graphify_ast.json", ".graphify_semantic.json",
                    ".graphify_analysis.json"):
        (ROOT / "graphify-out" / sidecar).unlink(missing_ok=True)
    print("graph refresh complete")
