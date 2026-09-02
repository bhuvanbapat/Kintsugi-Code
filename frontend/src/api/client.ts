import type {
  AgentRun,
  ChatMessage,
  EvaluationSummary,
  GraphResponse,
  Repository,
  SearchResponse,
  TestRunResult,
} from "../types";

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () =>
    req<{ status: string; provider: string; model: string; version: string }>("/health"),

  listRepositories: () =>
    req<{ repositories: Repository[] }>("/repositories"),

  importRepository: (path: string, name?: string) =>
    req<{ ok: boolean; repository: Repository }>("/repositories/import", {
      method: "POST",
      body: JSON.stringify({ path, name }),
    }),

  indexRepository: (repository_id: string) =>
    req<{ ok: boolean; scan: Record<string, unknown>; repository: Repository }>("/index", {
      method: "POST",
      body: JSON.stringify({ repository_id }),
    }),

  deleteRepository: (repository_id: string) =>
    req<{ ok: boolean }>(`/repositories/${repository_id}`, { method: "DELETE" }),

  listFiles: (repoId: string) =>
    req<{ files: import("../types").FileEntry[]; total: number }>(
      `/repositories/${repoId}/files`
    ),

  getFile: (repoId: string, path: string) =>
    req<{ path: string; content: string; total_lines: number; binary?: boolean }>(
      `/repositories/${repoId}/file?path=${encodeURIComponent(path)}`
    ),

  search: (repository_id: string, query: string, mode: string) =>
    req<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify({ repository_id, query, mode, limit: 20 }),
    }),

  listSymbols: (repoId: string, query?: string) =>
    req<{ symbols: import("../types").Symbol[]; total: number }>(
      `/symbols?repo_id=${repoId}${query ? `&query=${encodeURIComponent(query)}` : ""}`
    ),

  graph: (repoId: string, kind: "files" | "symbols") =>
    req<GraphResponse>(`/graph?repo_id=${repoId}&kind=${kind}`),

  chat: (
    repository_id: string,
    message: string,
    mode: string,
    conversation_id?: string | null,
    execution_mode: string = "analysis_only"
  ) =>
    req<{ conversation_id: string; message: ChatMessage; run: AgentRun }>("/chat", {
      method: "POST",
      body: JSON.stringify({ repository_id, message, mode, conversation_id, execution_mode }),
    }),

  listRuns: (repoId?: string) =>
    req<{ runs: AgentRun[] }>(`/agent/runs${repoId ? `?repo_id=${repoId}` : ""}`),

  runTests: (repository_id: string) =>
    req<TestRunResult>("/tests/run", {
      method: "POST",
      body: JSON.stringify({ repository_id }),
    }),

  getDiff: (repoId: string) => req<{ ok: boolean; result?: { stat: string; diff: string } }>(`/diff?repo_id=${repoId}`),

  applyPatch: (
    repository_id: string,
    path: string,
    content: string,
    mode: "full" | "append",
    run_tests_after: boolean
  ) =>
    req<{
      ok: boolean;
      diff?: string;
      rolled_back?: boolean;
      test_result?: TestRunResult;
      message?: string;
      additions?: number;
      deletions?: number;
    }>("/diff/apply", {
      method: "POST",
      body: JSON.stringify({ repository_id, path, content, mode, run_tests_after }),
    }),

  runEvaluation: (repository_id: string) =>
    req<EvaluationSummary>("/evaluation/run", {
      method: "POST",
      body: JSON.stringify({ repository_id }),
    }),

  getSettings: () =>
    req<Record<string, unknown>>("/settings"),

  updateSettings: (settings: Record<string, unknown>) =>
    req<{ ok: boolean; changed: string[] }>("/settings", {
      method: "POST",
      body: JSON.stringify(settings),
    }),
};
