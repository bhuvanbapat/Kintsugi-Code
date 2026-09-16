import { api } from "../api/client";
import { useAsync } from "../components/common";

export default function Home() {
  const { data: health, loading, error, reload } = useAsync(() => api.health(), []);
  const { data: repos } = useAsync(() => api.listRepositories(), []);

  return (
    <div style={{ maxWidth: 720 }}>
      <h1 style={{ marginTop: 0 }}>Kintsugi-Code</h1>
      <p className="dim">
        An AI-assisted software engineering workspace: index a repository, ask
        evidence-backed questions about the codebase, run tests, and apply
        controlled fixes — with a full agent trace for every run.
      </p>

      <h2>System</h2>
      {loading && <p className="dim">Checking backend…</p>}
      {error && (
        <p className="error-text">
          Backend unreachable ({error}). Start it with{" "}
          <code>uvicorn app.main:app</code> in <code>backend/</code>.
        </p>
      )}
      {health && (
        <div className="panel" style={{ padding: 12 }}>
          <div>
            Status: <span className="tag tag-green">{health.status}</span>{" "}
            Provider: <span className="tag">{health.provider}</span> Model:{" "}
            <span className="tag mono">{health.model}</span> Version:{" "}
            <span className="tag mono">{health.version}</span>
          </div>
          {health.provider === "mock" && (
            <div className="dim" style={{ marginTop: 8, fontSize: 12 }}>
              Running in offline demo mode — answers are composed deterministically
              from retrieval evidence. No API key or network required.
            </div>
          )}
          <button className="btn" style={{ marginTop: 8 }} onClick={reload}>
            Refresh
          </button>
        </div>
      )}

      <h2>Indexed repositories ({repos?.repositories.length ?? 0})</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {(repos?.repositories ?? []).map((r) => (
          <div key={r.id} className="panel" style={{ padding: "10px 14px" }}>
            <div style={{ fontWeight: 600 }}>{r.name}</div>
            <div className="dim mono" style={{ fontSize: 12 }}>
              {r.root_path} — {String((r.scan_stats as Record<string, number>).symbols ?? 0)} symbols
            </div>
          </div>
        ))}
        {repos?.repositories.length === 0 && (
          <div className="dim">No repositories yet — import one from the Repositories page.</div>
        )}
      </div>

      <h2>Quick tour</h2>
      <ol className="dim" style={{ lineHeight: 1.8 }}>
        <li>
          <b>Repositories</b> — import a local path (try{" "}
          <code>examples/sample_repo</code>) and index it.
        </li>
        <li>
          <b>AI Workspace</b> — ask "Where is complete_task defined?" with evidence
          citations.
        </li>
        <li>
          <b>Tests</b> — run the suite; one test fails by design in the sample
          repo.
        </li>
        <li>
          <b>Agent Trace</b> — inspect every tool call the agent made.
        </li>
        <li>
          <b>Evaluation</b> — measured retrieval quality over 8 benchmark cases.
        </li>
      </ol>
    </div>
  );
}

