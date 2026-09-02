import { useState } from "react";
import { api } from "../api/client";
import { EmptyState, Spinner, useAsync } from "../components/common";
import type { AgentRun, Repository } from "../types";

function stateColor(state: string): string {
  if (state === "completed") return "tag-green";
  if (state === "failed" || state === "cancelled") return "tag-red";
  return "";
}

export default function AgentTrace() {
  const [repoId, setRepoId] = useState("");
  const { data: reposData } = useAsync(() => api.listRepositories(), []);
  const repos: Repository[] = reposData?.repositories ?? [];
  const { data, loading, error, reload } = useAsync(
    () => (repoId ? api.listRuns(repoId) : Promise.resolve({ runs: [] })),
    [repoId]
  );
  const [openRun, setOpenRun] = useState<AgentRun | null>(null);

  if (!repoId && repos.length > 0) {
    const indexed = repos.find((r) => r.status === "indexed");
    if (indexed) setRepoId(indexed.id);
  }

  const runs: AgentRun[] = data?.runs ?? [];

  return (
    <div style={{ display: "flex", height: "100%", gap: 12 }}>
      <div style={{ width: 380, minWidth: 380, display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <h1 style={{ margin: 0, fontSize: 20, flex: 1 }}>Agent Trace</h1>
          <select
            className="input"
            value={repoId}
            onChange={(e) => setRepoId(e.target.value)}
            aria-label="Repository"
            style={{ width: 180 }}
          >
            {repos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
        {loading && <Spinner label="Loading runs…" />}
        {error && <p className="error-text">{error}</p>}
        {!loading && runs.length === 0 && (
          <EmptyState title="No agent runs yet" hint="Ask something in the AI Workspace." />
        )}
        <div style={{ overflow: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
          {runs.map((r) => (
            <button
              key={r.id}
              className="panel"
              style={{
                textAlign: "left",
                padding: "8px 12px",
                cursor: "pointer",
                background: openRun?.id === r.id ? "var(--bg-elevated)" : "var(--bg-panel)",
              }}
              onClick={() => setOpenRun(r)}
            >
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span className={`tag ${stateColor(r.state)}`}>{r.state}</span>
                <span className="dim" style={{ fontSize: 11 }}>
                  {r.mode}
                </span>
                <span className="dim" style={{ fontSize: 11, marginLeft: "auto" }}>
                  {r.tool_calls.length} tools
                </span>
              </div>
              <div className="mono" style={{ fontSize: 12, marginTop: 4 }}>
                {r.task.length > 60 ? r.task.slice(0, 59) + "…" : r.task}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="panel" style={{ flex: 1, overflow: "auto", padding: 16 }}>
        {!openRun && <EmptyState title="Select a run" />}
        {openRun && (
          <>
            <h2 style={{ marginTop: 0 }}>{openRun.task}</h2>
            <div className="dim" style={{ marginBottom: 12 }}>
              mode: {openRun.mode} · state: {openRun.state} · iterations: {openRun.iterations} ·
              usage:{" "}
              {(openRun.usage as Record<string, unknown>).usage_available === true
                ? `${(openRun.usage as Record<string, number>).input_tokens} in / ${(openRun.usage as Record<string, number>).output_tokens} out`
                : "unavailable"}
            </div>

            {openRun.result && (
              <div style={{ marginBottom: 16 }}>
                <div className="dim" style={{ fontSize: 11, marginBottom: 4 }}>RESULT</div>
                <div style={{ whiteSpace: "pre-wrap" }}>{openRun.result}</div>
              </div>
            )}

            <div className="dim" style={{ fontSize: 11, marginBottom: 4 }}>
              TOOL CALLS ({openRun.tool_calls.length})
            </div>
            <div style={{ borderLeft: "2px solid var(--border)", paddingLeft: 12 }}>
              {openRun.tool_calls.map((tc) => (
                <div key={tc.id} style={{ padding: "4px 0" }}>
                  <span className="mono" style={{ color: "var(--accent)" }}>{tc.tool_name}</span>
                  <span className="dim mono"> — {tc.duration_ms}ms — </span>
                  {tc.error ? (
                    <span className="mono error-text" style={{ fontSize: 12 }}>
                      {tc.error}
                    </span>
                  ) : (
                    <span className="mono dim" style={{ fontSize: 12 }}>
                      {tc.result_summary}
                    </span>
                  )}
                  <div className="mono dim" style={{ fontSize: 11 }}>
                    {JSON.stringify(tc.arguments).slice(0, 160)}
                  </div>
                </div>
              ))}
              {openRun.tool_calls.length === 0 && (
                <div className="dim">No tool calls recorded.</div>
              )}
            </div>

            <button className="btn" style={{ marginTop: 12 }} onClick={reload}>
              Refresh runs
            </button>
          </>
        )}
      </div>
    </div>
  );
}
