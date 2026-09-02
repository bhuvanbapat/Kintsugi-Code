import { useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorBox, Spinner, StatRow, useAsync } from "../components/common";
import type { Repository } from "../types";

export default function Repositories() {
  const { data, loading, error, reload } = useAsync(() => api.listRepositories(), []);
  const [path, setPath] = useState("");
  const [importing, setImporting] = useState(false);
  const [indexingId, setIndexingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function doImport() {
    setImporting(true);
    setActionError(null);
    try {
      const trimmed = path.trim();
      if (!trimmed) throw new Error("enter a repository path");
      const res = await api.importRepository(trimmed);
      await api.indexRepository(res.repository.id);
      setPath("");
      reload();
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setImporting(false);
    }
  }

  async function doIndex(id: string) {
    setIndexingId(id);
    setActionError(null);
    try {
      await api.indexRepository(id);
      reload();
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setIndexingId(null);
    }
  }

  const repos: Repository[] = data?.repositories ?? [];

  return (
    <div style={{ maxWidth: 900 }}>
      <h1>Repositories</h1>
      <div className="panel" style={{ padding: 14, marginBottom: 16 }}>
        <label htmlFor="repo-path" className="dim" style={{ display: "block", marginBottom: 6 }}>
          Import a local repository (it will be scanned and indexed)
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            id="repo-path"
            className="input mono"
            placeholder="C:\path\to\repo  (try the bundled examples/sample_repo)"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doImport()}
          />
          <button className="btn btn-primary" onClick={doImport} disabled={importing || !path.trim()}>
            {importing ? "Importing…" : "Import & Index"}
          </button>
        </div>
        {actionError && (
          <div style={{ marginTop: 8 }}>
            <ErrorBox message={actionError} />
          </div>
        )}
      </div>

      {loading && <Spinner label="Loading repositories…" />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {!loading && !error && repos.length === 0 && (
        <EmptyState
          title="No repositories indexed"
          hint="Paste a local path above — e.g. the sample_repo bundled with this project."
        />
      )}

      {repos.map((r) => {
        const stats = r.scan_stats as Record<string, number | string>;
        return (
          <div key={r.id} className="panel" style={{ padding: 0, marginBottom: 12 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 16px",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <strong style={{ flex: 1 }}>{r.name}</strong>
              <span className={`tag ${r.status === "indexed" ? "tag-green" : r.status === "failed" ? "tag-red" : ""}`}>
                {r.status}
              </span>
              <button className="btn" onClick={() => doIndex(r.id)} disabled={indexingId === r.id}>
                {indexingId === r.id ? "Indexing…" : "Re-index"}
              </button>
            </div>
            <div className="dim mono" style={{ padding: "4px 16px", fontSize: 12 }}>
              {r.root_path}
            </div>
            {r.status === "indexed" && (
              <StatRow
                items={[
                  { label: "Files", value: String(stats.total_files ?? 0) },
                  { label: "Source", value: String(stats.source_files ?? 0) },
                  { label: "Tests", value: String(stats.test_files ?? 0) },
                  { label: "Symbols", value: String(stats.symbols ?? 0) },
                  { label: "Relationships", value: String(stats.relationships ?? 0) },
                  { label: "Parse errors", value: String(stats.parse_errors ?? 0) },
                ]}
              />
            )}
            {r.error && (
              <div className="error-text" style={{ padding: "4px 16px 10px" }}>
                {r.error}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
