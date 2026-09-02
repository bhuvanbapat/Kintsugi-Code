import { useEffect, useState } from 'react';
import { api } from "../api/client";
import { EmptyState, ErrorBox, Spinner } from "../components/common";
import type { Repository, SearchResponse } from "../types";

export default function Search() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repoId, setRepoId] = useState("");
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.listRepositories().then((r) => {
      setRepos(r.repositories);
      const indexed = r.repositories.find((x) => x.status === "indexed");
      if (indexed) setRepoId(indexed.id);
    });
  }, []);

  async function run() {
    if (!repoId || !query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await api.search(repoId, query.trim(), mode));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
      setLoaded(true);
    }
  }

  return (
    <div style={{ maxWidth: 900 }}>
      <h1>Search</h1>
      <div className="panel" style={{ padding: 14 }}>
        <div style={{ display: "flex", gap: 8 }}>
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
            style={{ width: 130 }}
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            aria-label="Search mode"
          >
            <option value="hybrid">hybrid</option>
            <option value="lexical">lexical</option>
            <option value="symbol">symbol</option>
          </select>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <input
            className="input"
            placeholder='e.g. "task completion" or "TaskRepository"'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            aria-label="Search query"
          />
          <button className="btn btn-primary" onClick={run} disabled={loading || !query.trim()}>
            Search
          </button>
        </div>
      </div>

      {loading && <Spinner label="Searching…" />}
      {error && <div style={{ marginTop: 12 }}><ErrorBox message={error} /></div>}
      {loaded && !loading && !result?.ranked_files.length && !result?.symbol_results.length && (
        <EmptyState title="No results" hint="Try a different query or mode." />
      )}

      {result && (
        <div style={{ marginTop: 16 }}>
          <h2>Ranked files</h2>
          <table className="panel" style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              {result.ranked_files.map((f) => (
                <tr key={f.path} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td className="mono" style={{ padding: "6px 12px", width: "60%" }}>{f.path}</td>
                  <td className="dim mono" style={{ padding: 6 }}>{f.language}</td>
                  <td className="mono" style={{ padding: 6, textAlign: "right" }}>{f.score}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {result.symbol_results.length > 0 && (
            <>
              <h2>Symbols</h2>
              <table className="panel" style={{ width: "100%", borderCollapse: "collapse" }}>
                <tbody>
                  {result.symbol_results.map((s) => (
                    <tr key={s.id + s.file_path} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td className="mono" style={{ padding: "6px 12px" }}>{s.name}</td>
                      <td style={{ padding: 6 }}><span className="tag">{s.kind}</span></td>
                      <td className="mono dim" style={{ padding: 6 }}>{s.file_path}:{s.start_line}</td>
                      <td className="mono" style={{ padding: 6, textAlign: "right" }}>{s.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}
    </div>
  );
}
