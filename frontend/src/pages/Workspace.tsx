import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, Spinner } from "../components/common";
import type { AgentRun, ChatMessage, Evidence, Repository } from "../types";

const MODES = ["explain", "locate", "analyze", "plan", "test", "fix", "review"];

function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) return null;
  const navigate = useNavigate();
  return (
    <div style={{ marginTop: 8 }}>
      <div className="dim" style={{ fontSize: 11, marginBottom: 4 }}>
        EVIDENCE
      </div>
      {evidence.slice(0, 10).map((e, i) => (
        <button
          key={i}
          className="btn mono"
          style={{ fontSize: 11, marginRight: 6, marginBottom: 4, padding: "2px 8px" }}
          onClick={() =>
            navigate(
              `/explore?file=${encodeURIComponent(e.file_path)}&line=${e.start_line ?? 1}`
            )
          }
          title="Open in explorer"
        >
          {e.file_path}
          {e.start_line ? `:${e.start_line}` : ""}
        </button>
      ))}
    </div>
  );
}

function RunTrace({ run }: { run: AgentRun }) {
  return (
    <details style={{ marginTop: 8 }}>
      <summary className="dim" style={{ cursor: "pointer", fontSize: 12 }}>
        Agent trace — {run.tool_calls.length} tool calls, {run.iterations} iterations, state: {run.state}
      </summary>
      <div style={{ marginTop: 6, paddingLeft: 8, borderLeft: "2px solid var(--border)" }}>
        {run.tool_calls.map((tc) => (
          <div key={tc.id} className="mono" style={{ fontSize: 12, padding: "2px 0" }}>
            <span style={{ color: "var(--accent)" }}>{tc.tool_name}</span>
            <span className="dim"> — {tc.duration_ms}ms — </span>
            {tc.error ? <span className="error-text">{tc.error}</span> : tc.result_summary}
          </div>
        ))}
        {run.usage &&
          (run.usage as Record<string, unknown>).usage_available === true && (
            <div className="dim" style={{ fontSize: 11, marginTop: 4 }}>
              tokens: {String((run.usage as Record<string, number>).input_tokens ?? 0)} in /{" "}
              {String((run.usage as Record<string, number>).output_tokens ?? 0)} out
            </div>
          )}
      </div>
    </details>
  );
}

export default function Workspace() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repoId, setRepoId] = useState<string>("");
  const [mode, setMode] = useState("explain");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [runsByMessage, setRunsByMessage] = useState<Record<string, AgentRun>>({});
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listRepositories().then((r) => {
      setRepos(r.repositories);
      const indexed = r.repositories.find((x) => x.status === "indexed");
      if (indexed) setRepoId(indexed.id);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send() {
    if (!repoId || !input.trim() || busy) return;
    const text = input.trim();
    setInput("");
    setMessages((m) => [...m, { id: `u${Date.now()}`, role: "user", content: text, evidence: [] }]);
    setBusy(true);
    try {
      const res = await api.chat(repoId, text, mode);
      setMessages((m) => [...m, res.message]);
      setRunsByMessage((r) => ({ ...r, [res.message.id]: res.run }));
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          id: `e${Date.now()}`,
          role: "assistant",
          content: `Error: ${(e as Error).message}`,
          evidence: [],
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 12 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <h1 style={{ margin: 0, fontSize: 20 }}>AI Workspace</h1>
        <select
          className="input"
          style={{ width: 220 }}
          value={repoId}
          onChange={(e) => setRepoId(e.target.value)}
          aria-label="Repository"
        >
          <option value="">— select repository —</option>
          {repos.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name} ({r.status})
            </option>
          ))}
        </select>
        <select
          className="input"
          style={{ width: 130 }}
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          aria-label="Task mode"
        >
          {MODES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div
        className="panel"
        style={{ flex: 1, overflow: "auto", padding: 16 }}
        role="log"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <EmptyState
            title="Ask a repository question"
            hint='Try: "Where is complete_task defined?" · "Explain the service layer" · mode: fix → "Fix the failing test"'
          />
        )}
        {messages.map((m) => (
          <div key={m.id} style={{ marginBottom: 14 }}>
            <div
              className="tag"
              style={{
                color: m.role === "user" ? "var(--accent)" : "var(--accent-2)",
                marginBottom: 4,
              }}
            >
              {m.role === "user" ? "YOU" : "CODEFORGE"}
            </div>
            <div style={{ whiteSpace: "pre-wrap" }}>
              {m.content}
              {m.role === "assistant" && runsByMessage[m.id] && <RunTrace run={runsByMessage[m.id]} />}
              {m.role === "assistant" && m.evidence.length > 0 && <EvidenceList evidence={m.evidence} />}
            </div>
          </div>
        ))}
        {busy && <Spinner label="Agent working — retrieving, running tools…" />}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          className="input"
          placeholder={repoId ? "Ask about the repository…" : "Select a repository first"}
          value={input}
          disabled={!repoId}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          aria-label="Message"
        />
        <button className="btn btn-primary" onClick={send} disabled={busy || !repoId || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
