import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState, Spinner, useAsync } from "../components/common";
import type { GraphResponse, Repository } from "../types";

const KIND_COLORS: Record<string, string> = {
  imports: "#58a6ff",
  contains: "#3fb950",
  calls: "#d29922",
};

interface Positioned {
  id: string;
  label: string;
  x: number;
  y: number;
  type: string;
}

/** Deterministic layered layout: nodes sorted, placed on a grid by community of connectivity. */
function layout(nodes: GraphResponse["nodes"], edges: GraphResponse["edges"]): Positioned[] {
  const degree = new Map<string, number>();
  for (const n of nodes) degree.set(n.id, 0);
  for (const e of edges) {
    degree.set(e.source, (degree.get(e.source) ?? 0) + 1);
    degree.set(e.target, (degree.get(e.target) ?? 0) + 1);
  }
  const sorted = [...nodes].sort((a, b) => (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0));
  const perRow = Math.ceil(Math.sqrt(sorted.length) || 1);
  return sorted.map((n, i) => ({
    id: n.id,
    label: n.label,
    type: n.type,
    x: 60 + (i % perRow) * 180,
    y: 50 + Math.floor(i / perRow) * 110,
  }));
}

export default function Graph() {
  const [repoId, setRepoId] = useState("");
  const [kind, setKind] = useState<"files" | "symbols">("files");
  const [repos, setRepos] = useState<Repository[]>([]);

  useEffect(() => {
    api.listRepositories().then((r) => {
      setRepos(r.repositories);
      const indexed = r.repositories.find((x) => x.status === "indexed");
      if (indexed) setRepoId(indexed.id);
    });
  }, []);

  const { data, loading, error } = useAsync<GraphResponse | null>(
    () => (repoId ? api.graph(repoId, kind) : Promise.resolve(null)),
    [repoId, kind]
  );

  const positioned = useMemo(() => (data ? layout(data.nodes, data.edges) : []), [data]);
  const posIndex = useMemo(() => new Map(positioned.map((p) => [p.id, p])), [positioned]);
  const [selected, setSelected] = useState<string | null>(null);

  const selectedNode = data?.nodes.find((n) => n.id === selected);
  const connected = data?.edges.filter(
    (e) => e.source === selected || e.target === selected
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 10 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <h1 style={{ margin: 0, fontSize: 20 }}>Dependency Graph</h1>
        <select
          className="input"
          style={{ width: 220 }}
          value={repoId}
          onChange={(e) => setRepoId(e.target.value)}
          aria-label="Repository"
        >
          {repos.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
        <select
          className="input"
          style={{ width: 150 }}
          value={kind}
          onChange={(e) => setKind(e.target.value as "files" | "symbols")}
          aria-label="Graph kind"
        >
          <option value="files">file dependencies</option>
          <option value="symbols">symbol relationships</option>
        </select>
        {data && (
          <span className="dim">
            {data.nodes.length} nodes · {data.edges.length} edges
          </span>
        )}
      </div>

      {loading && <Spinner label="Building graph…" />}
      {error && <p className="error-text">{error}</p>}
      {data && data.nodes.length === 0 && (
        <EmptyState title="No graph data" hint="Index a repository first." />
      )}

      <div style={{ display: "flex", flex: 1, minHeight: 0, gap: 10 }}>
        {data && data.nodes.length > 0 && (
          <div className="panel" style={{ flex: 1, position: "relative", overflow: "auto" }}>
            <svg
              width={Math.max(1200, Math.sqrt(data.nodes.length) * 190)}
              height={Math.max(700, Math.ceil(data.nodes.length / Math.ceil(Math.sqrt(data.nodes.length))) * 120)}
              role="img"
              aria-label="Dependency graph"
            >
              {data.edges.map((e, i) => {
                const s = posIndex.get(e.source);
                const t = posIndex.get(e.target);
                if (!s || !t) return null;
                const highlight = selected === e.source || selected === e.target;
                return (
                  <line
                    key={i}
                    x1={s.x + 70}
                    y1={s.y + 16}
                    x2={t.x + 70}
                    y2={t.y + 16}
                    stroke={KIND_COLORS[e.kind] ?? "#30363d"}
                    strokeOpacity={selected ? (highlight ? 0.9 : 0.08) : 0.35}
                    strokeWidth={highlight ? 2 : 1}
                  />
                );
              })}
              {positioned.map((n) => (
                <g
                  key={n.id}
                  transform={`translate(${n.x}, ${n.y})`}
                  onClick={() => setSelected(selected === n.id ? null : n.id)}
                  style={{ cursor: "pointer" }}
                >
                  <rect
                    width={140}
                    height={32}
                    rx={5}
                    fill={selected === n.id ? "#1f6feb" : "var(--bg-elevated)"}
                    stroke={selected === n.id ? "#58a6ff" : "var(--border)"}
                  />
                  <text
                    x={70}
                    y={20}
                    textAnchor="middle"
                    fill="#e6edf3"
                    fontSize={11}
                    fontFamily="monospace"
                  >
                    {n.label.length > 18 ? n.label.slice(0, 17) + "…" : n.label}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        )}

        {selectedNode && (
          <div className="panel" style={{ width: 300, padding: 12, overflow: "auto" }}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{selectedNode.label}</div>
            <div className="dim mono" style={{ fontSize: 12, marginBottom: 10 }}>
              {selectedNode.id}
            </div>
            <div className="dim" style={{ fontSize: 12, marginBottom: 4 }}>RELATIONSHIPS</div>
            {(connected ?? []).slice(0, 30).map((e, i) => (
              <div key={i} className="mono dim" style={{ fontSize: 11, padding: "1px 0" }}>
                {e.source === selected ? "→ " : "← "}
                {e.source === selected ? e.target : e.source} ({e.kind})
              </div>
            ))}
            {(connected ?? []).length === 0 && (
              <div className="dim" style={{ fontSize: 12 }}>No relationships.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
