import { useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState, Spinner, StatRow } from "../components/common";
import type { EvaluationSummary, Repository } from "../types";

export default function Evaluation() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repoId, setRepoId] = useState("");
  const [result, setResult] = useState<EvaluationSummary | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api.listRepositories().then((r) => {
      setRepos(r.repositories);
      const indexed = r.repositories.find((x) => x.status === "indexed");
      if (indexed) setRepoId(indexed.id);
    });
  }, []);

  async function run() {
    if (!repoId) return;
    setRunning(true);
    try {
      setResult(await api.runEvaluation(repoId));
    } catch (e) {
      setResult(null);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={{ maxWidth: 900 }}>
      <h1>Evaluation</h1>
      <p className="dim">
        Measures real retrieval quality over 8 curated benchmark cases
        (architecture, symbol location, dependency lookup, bug finding,
        planning, test diagnosis). Metrics come from actual retriever output —
        nothing simulated.
      </p>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
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
        <button className="btn btn-primary" onClick={run} disabled={running || !repoId}>
          {running ? "Running…" : "Run evaluation"}
        </button>
      </div>

      {running && <Spinner label="Evaluating retrieval…" />}
      {!running && !result && (
        <EmptyState title="No evaluation yet" hint="Run against the indexed sample_repo." />
      )}

      {result && !running && (
        <>
          <div className="panel" style={{ marginBottom: 12 }}>
            <StatRow
              items={[
                {
                  label: "Cases passed",
                  value: `${result.summary.passed}/${result.summary.total_cases}`,
                },
                { label: "Mean recall", value: result.summary.mean_recall.toFixed(3) },
                { label: "Mean precision", value: result.summary.mean_precision.toFixed(3) },
                {
                  label: "Mean latency",
                  value: result.summary.mean_latency_ms.toFixed(1) + "ms",
                },
              ]}
            />
          </div>
          <table className="panel" style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr className="dim" style={{ textAlign: "left" }}>
                <th style={{ padding: "6px 12px" }}>Case</th>
                <th style={{ padding: 6 }}>Recall</th>
                <th style={{ padding: 6 }}>Precision</th>
                <th style={{ padding: 6 }}>Latency</th>
                <th style={{ padding: 6 }}>Result</th>
              </tr>
            </thead>
            <tbody>
              {result.cases.map((c) => (
                <tr key={c.case_id} style={{ borderTop: "1px solid var(--border)" }}>
                  <td className="mono" style={{ padding: "6px 12px" }}>{c.case_id}</td>
                  <td className="mono" style={{ padding: 6 }}>{c.recall.toFixed(2)}</td>
                  <td className="mono" style={{ padding: 6 }}>{c.precision.toFixed(2)}</td>
                  <td className="mono dim" style={{ padding: 6 }}>{c.latency_ms}ms</td>
                  <td style={{ padding: 6 }}>
                    <span className={`tag ${c.passed ? "tag-green" : "tag-red"}`}>
                      {c.passed ? "PASS" : "FAIL"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
