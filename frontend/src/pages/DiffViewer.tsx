import { useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState, Spinner } from "../components/common";
import type { Repository, TestRunResult } from "../types";

function parseDiff(diff: string): { line: string; cls: string }[] {
  return diff.split("\n").map((line) => ({
    line,
    cls: line.startsWith("+++") || line.startsWith("---")
      ? "dim"
      : line.startsWith("@@")
        ? "var(--accent)"
        : line.startsWith("+")
          ? "var(--accent-2)"
          : line.startsWith("-")
            ? "var(--danger)"
            : "var(--text)",
  }));
}

export default function DiffViewer() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repoId, setRepoId] = useState("");
  const [diffText, setDiffText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [patchPath, setPatchPath] = useState("");
  const [patchContent, setPatchContent] = useState("");
  const [patchMode, setPatchMode] = useState<"full" | "append">("full");
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<{
    ok: boolean;
    diff?: string;
    rolled_back?: boolean;
    test_result?: TestRunResult;
    message?: string;
  } | null>(null);

  useEffect(() => {
    api.listRepositories().then((r) => {
      setRepos(r.repositories);
      const indexed = r.repositories.find((x) => x.status === "indexed");
      if (indexed) setRepoId(indexed.id);
    });
  }, []);

  async function loadDiff() {
    if (!repoId) return;
    setLoading(true);
    setDiffText(null);
    try {
      const res = await api.getDiff(repoId);
      setDiffText(res.result?.diff ?? "(no changes)");
    } catch (e) {
      setDiffText(`Error: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }

  async function apply() {
    if (!repoId || !patchPath.trim() || !patchContent.trim()) return;
    setApplying(true);
    setApplyResult(null);
    try {
      setApplyResult(
        await api.applyPatch(repoId, patchPath.trim(), patchContent, patchMode, true)
      );
      loadDiff();
    } catch (e) {
      setApplyResult({ ok: false, message: (e as Error).message });
    } finally {
      setApplying(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 10 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <h1 style={{ margin: 0, fontSize: 20 }}>Diff & Controlled Changes</h1>
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
        <button className="btn" onClick={loadDiff} disabled={loading || !repoId}>
          {loading ? "…" : "Load git diff"}
        </button>
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0, gap: 12 }}>
        <div className="panel" style={{ flex: 1, overflow: "auto", padding: 12 }}>
          <div className="dim" style={{ fontSize: 11, marginBottom: 8 }}>
            CURRENT GIT DIFF
          </div>
          {diffText === null && !loading && (
            <EmptyState title="No diff loaded" hint="Load the git diff or apply a change." />
          )}
          {loading && <Spinner />}
          {diffText !== null && !loading && (
            <div className="mono" style={{ fontSize: 12, whiteSpace: "pre-wrap" }}>
              {parseDiff(diffText).map((l, i) => (
                <div key={i} style={{ color: l.cls }}>
                  {l.line || " "}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="panel" style={{ width: 420, minWidth: 420, overflow: "auto", padding: 12 }}>
          <div className="dim" style={{ fontSize: 11, marginBottom: 8 }}>
            CONTROLLED CHANGE (validated, rolled back if tests fail)
          </div>
          <input
            className="input mono"
            placeholder="relative/file/path.py"
            value={patchPath}
            onChange={(e) => setPatchPath(e.target.value)}
            aria-label="File path"
            style={{ marginBottom: 8 }}
          />
          <select
            className="input"
            value={patchMode}
            onChange={(e) => setPatchMode(e.target.value as "full" | "append")}
            aria-label="Patch mode"
            style={{ marginBottom: 8 }}
          >
            <option value="full">full replace</option>
            <option value="append">append</option>
          </select>
          <textarea
            className="input mono"
            placeholder="new file content (full) or text to append"
            value={patchContent}
            onChange={(e) => setPatchContent(e.target.value)}
            rows={10}
            aria-label="New content"
            style={{ marginBottom: 8, resize: "vertical" }}
          />
          <button
            className="btn btn-primary"
            onClick={apply}
            disabled={applying || !repoId || !patchPath.trim() || !patchContent.trim()}
          >
            {applying ? "Applying & testing…" : "Apply change + run tests"}
          </button>

          {applyResult && (
            <div style={{ marginTop: 12 }}>
              <span className={`tag ${applyResult.ok ? "tag-green" : "tag-red"}`}>
                {applyResult.ok ? "APPLIED" : applyResult.rolled_back ? "ROLLED BACK" : "FAILED"}
              </span>
              {applyResult.message && (
                <div className="dim" style={{ marginTop: 6, fontSize: 12 }}>
                  {applyResult.message}
                </div>
              )}
              {applyResult.test_result && (
                <div className="dim" style={{ marginTop: 6, fontSize: 12 }}>
                  tests: {applyResult.test_result.passed ?? 0} passed /{" "}
                  {applyResult.test_result.failed ?? 0} failed
                </div>
              )}
              {applyResult.diff && (
                <div className="mono" style={{ marginTop: 8, fontSize: 11, whiteSpace: "pre-wrap", color: "var(--text-dim)" }}>
                  {applyResult.diff.slice(0, 2000)}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
