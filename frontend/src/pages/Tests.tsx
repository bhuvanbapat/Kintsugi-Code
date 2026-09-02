import { useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState, Spinner, StatRow } from "../components/common";
import type { Repository, TestRunResult } from "../types";

export default function Tests() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repoId, setRepoId] = useState("");
  const [result, setResult] = useState<TestRunResult | null>(null);
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
    setResult(null);
    try {
      setResult(await api.runTests(repoId));
    } catch (e) {
      setResult({ ok: false, stdout: "", stderr: (e as Error).message });
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 10 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <h1 style={{ margin: 0, fontSize: 20 }}>Tests</h1>
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
          {running ? "Running…" : "Run tests"}
        </button>
      </div>

      {running && <Spinner label="Executing test suite…" />}
      {!running && !result && (
        <EmptyState
          title="No test run yet"
          hint="The bundled sample_repo has one test that fails by design."
        />
      )}

      {result && !running && (
        <div className="panel" style={{ flex: 1, overflow: "auto", padding: 0 }}>
          <StatRow
            items={[
              {
                label: "Status",
                value: (
                  <span className={`tag ${result.ok ? "tag-green" : "tag-red"}`}>
                    {result.ok ? "PASS" : "FAIL"}
                  </span>
                ),
              },
              { label: "Passed", value: String(result.passed ?? 0) },
              { label: "Failed", value: String(result.failed ?? 0) },
              { label: "Errors", value: String(result.errors ?? 0) },
              { label: "Exit code", value: String(result.exit_code ?? "—") },
            ]}
          />
          {result.error && (
            <div className="error-text" style={{ padding: "8px 16px" }}>
              {result.error}
            </div>
          )}
          {result.failed_tests && result.failed_tests.length > 0 && (
            <div style={{ padding: "8px 16px" }}>
              <div className="dim" style={{ fontSize: 11, marginBottom: 4 }}>FAILED TESTS</div>
              {result.failed_tests.map((t) => (
                <div key={t} className="mono error-text" style={{ fontSize: 12 }}>
                  {t}
                </div>
              ))}
            </div>
          )}
          <div
            className="mono"
            style={{
              borderTop: "1px solid var(--border)",
              padding: 12,
              whiteSpace: "pre-wrap",
              fontSize: 12,
            }}
          >
            {(result.stdout || "") + (result.stderr ? "\n\n--- stderr ---\n" + result.stderr : "")}
          </div>
        </div>
      )}
    </div>
  );
}
