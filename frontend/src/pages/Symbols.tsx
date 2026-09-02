import { useState } from "react";
import { api } from "../api/client";
import { EmptyState, Spinner, useAsync } from "../components/common";
import type { Repository, Symbol } from "../types";

export default function Symbols() {
  const [repoId, setRepoId] = useState("");
  const { data: reposData } = useAsync(() => api.listRepositories(), []);
  const [filter, setFilter] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const { data, loading, error } = useAsync(
    () => (repoId ? api.listSymbols(repoId) : Promise.resolve({ symbols: [], total: 0 })),
    [repoId]
  );

  const repos: Repository[] = reposData?.repositories ?? [];
  const symbols: Symbol[] = data?.symbols ?? [];
  const visible = symbols.filter(
    (s) =>
      (!filter || s.name.toLowerCase().includes(filter.toLowerCase())) &&
      (!kindFilter || s.kind === kindFilter)
  );

  if (!repoId && repos.length > 0) {
    const indexed = repos.find((r) => r.status === "indexed");
    if (indexed) setRepoId(indexed.id);
  }

  return (
    <div style={{ maxWidth: 900 }}>
      <h1>Symbols</h1>
      <div className="panel" style={{ padding: 14 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <select
            className="input"
            style={{ width: 220 }}
            value={repoId}
            onChange={(e) => setRepoId(e.target.value)}
            aria-label="Repository"
          >
            <option value="">— repository —</option>
            {repos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
          <select
            className="input"
            style={{ width: 130 }}
            value={kindFilter}
            onChange={(e) => setKindFilter(e.target.value)}
            aria-label="Kind filter"
          >
            <option value="">all kinds</option>
            <option value="class">class</option>
            <option value="function">function</option>
            <option value="method">method</option>
            <option value="import">import</option>
          </select>
          <input
            className="input"
            placeholder="Filter by name…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-label="Symbol filter"
          />
        </div>
      </div>

      {loading && <Spinner label="Loading symbols…" />}
      {error && <p className="error-text">{error}</p>}
      {!loading && repoId && visible.length === 0 && (
        <EmptyState title="No symbols match" hint="Index a repository first." />
      )}

      <table className="panel" style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
        <tbody>
          {visible.slice(0, 300).map((s) => (
            <tr key={s.id} style={{ borderBottom: "1px solid var(--border)" }}>
              <td className="mono" style={{ padding: "6px 12px" }}>{s.name}</td>
              <td style={{ padding: 6 }}><span className="tag">{s.kind}</span></td>
              <td className="mono dim" style={{ padding: 6 }}>{s.file_path}:{s.start_line}</td>
              <td className="mono dim" style={{ padding: 6, maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis" }}>
                {s.signature}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {visible.length > 300 && (
        <p className="dim">Showing 300 of {visible.length} symbols.</p>
      )}
    </div>
  );
}
