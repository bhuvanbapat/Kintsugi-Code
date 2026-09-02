import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, Spinner } from "../components/common";
import type { FileEntry, Repository } from "../types";

function FileTree({
  files,
  onOpen,
  activePath,
}: {
  files: FileEntry[];
  onOpen: (path: string) => void;
  activePath: string | null;
}) {
  interface TreeNode {
    name: string;
    path: string;
    children: Map<string, TreeNode>;
    file?: FileEntry;
  }
  const root: TreeNode = { name: "", path: "", children: new Map() };
  for (const f of files) {
    let node = root;
    const parts = f.path.split("/");
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!node.children.has(part)) {
        node.children.set(part, {
          name: part,
          path: parts.slice(0, i + 1).join("/"),
          children: new Map(),
          file: i === parts.length - 1 ? f : undefined,
        });
      }
      node = node.children.get(part)!;
    }
  }

  const render = (node: TreeNode, depth: number): React.ReactNode[] => {
    const dirs = [...node.children.values()].filter((c) => c.children.size > 0);
    const leafs = [...node.children.values()].filter((c) => c.children.size === 0);
    dirs.sort((a, b) => a.name.localeCompare(b.name));
    leafs.sort((a, b) => a.name.localeCompare(b.name));
    const out: React.ReactNode[] = [];
    for (const d of dirs) {
      out.push(
        <div key={d.path} className="mono dim" style={{ paddingLeft: depth * 14, fontSize: 12.5, paddingTop: 2 }}>
          📁 {d.name}
        </div>
      );
      out.push(...render(d, depth + 1));
    }
    for (const l of leafs) {
      out.push(
        <button
          key={l.path}
          onClick={() => l.file && onOpen(l.path)}
          className="mono"
          style={{
            display: "block",
            width: "100%",
            textAlign: "left",
            paddingLeft: depth * 14,
            paddingTop: 2,
            paddingBottom: 2,
            background: activePath === l.path ? "var(--bg-elevated)" : "transparent",
            border: "none",
            color: l.file?.is_test ? "var(--warning)" : "var(--text)",
            cursor: "pointer",
            fontSize: 12.5,
          }}
          title={`${l.path} — ${l.file?.line_count ?? 0} lines`}
        >
          {l.file?.is_test ? "⚑" : "▸"} {l.name}
        </button>
      );
    }
    return out;
  };
  return <div>{render(root, 0)}</div>;
}

export default function Explorer() {
  const [params] = useSearchParams();
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repoId, setRepoId] = useState("");
  const [files, setFiles] = useState<FileEntry[] | null>(null);
  const [file, setFile] = useState<{ path: string; content: string; totalLines: number } | null>(null);
  const [loadingFile, setLoadingFile] = useState(false);
  const [filter, setFilter] = useState("");
  const [jumpLine, setJumpLine] = useState<number | null>(null);

  useEffect(() => {
    api.listRepositories().then((r) => {
      setRepos(r.repositories);
      const indexed =
        r.repositories.find((x) => x.status === "indexed") ?? r.repositories[0];
      if (indexed) setRepoId(indexed.id);
    });
  }, []);

  useEffect(() => {
    if (!repoId) return;
    setFiles(null);
    api.listFiles(repoId).then((r) => setFiles(r.files));
    const preselect = params.get("file");
    if (preselect) openFile(preselect, Number(params.get("line") ?? 1));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoId]);

  async function openFile(path: string, line?: number) {
    if (!repoId) return;
    setLoadingFile(true);
    setJumpLine(line ?? null);
    try {
      const res = await api.getFile(repoId, path);
      setFile({ path, content: res.content, totalLines: res.total_lines });
    } finally {
      setLoadingFile(false);
    }
  }

  const visibleFiles = useMemo(() => {
    if (!files) return [];
    if (!filter.trim()) return files;
    const f = filter.toLowerCase();
    return files.filter((x) => x.path.toLowerCase().includes(f));
  }, [files, filter]);

  const lines = file ? file.content.split("\n") : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 10 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <h1 style={{ margin: 0, fontSize: 20 }}>Code Explorer</h1>
        <select
          className="input"
          style={{ width: 220 }}
          value={repoId}
          onChange={(e) => setRepoId(e.target.value)}
          aria-label="Repository"
        >
          {repos.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name} ({r.status})
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0, gap: 10 }}>
        <div className="panel" style={{ width: 280, minWidth: 280, overflow: "auto", padding: 8 }}>
          <input
            className="input"
            placeholder="Filter files…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ marginBottom: 8 }}
            aria-label="Filter files"
          />
          {files === null && <Spinner label="Loading files…" />}
          {files !== null && visibleFiles.length === 0 && (
            <EmptyState title="No files match" />
          )}
          <FileTree files={visibleFiles} onOpen={(p) => openFile(p)} activePath={file?.path ?? null} />
        </div>

        <div className="panel" style={{ flex: 1, overflow: "auto" }}>
          {!file && !loadingFile && (
            <EmptyState title="Select a file" hint="Symbols marked ⚑ are test files." />
          )}
          {loadingFile && <Spinner label="Loading file…" />}
          {file && !loadingFile && (
            <>
              <div
                className="mono dim"
                style={{
                  padding: "8px 12px",
                  borderBottom: "1px solid var(--border)",
                  fontSize: 12,
                  position: "sticky",
                  top: 0,
                  background: "var(--bg-panel)",
                }}
              >
                {file.path} — {file.totalLines} lines
              </div>
              <table style={{ borderCollapse: "collapse", width: "100%" }}>
                <tbody>
                  {lines.map((line, i) => (
                    <tr
                      key={i}
                      id={`L${i + 1}`}
                      style={
                        jumpLine === i + 1
                          ? { background: "rgba(88,166,255,0.15)" }
                          : undefined
                      }
                    >
                      <td
                        className="mono dim"
                        style={{
                          width: 50,
                          textAlign: "right",
                          padding: "0 10px",
                          color: "#484f58",
                          userSelect: "none",
                          verticalAlign: "top",
                        }}
                      >
                        {i + 1}
                      </td>
                      <td
                        className="mono"
                        style={{ padding: "0 12px", whiteSpace: "pre-wrap", verticalAlign: "top" }}
                      >
                        {line || " "}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
