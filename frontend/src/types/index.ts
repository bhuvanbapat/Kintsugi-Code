export interface FileEntry {
  path: string;
  language: string | null;
  size_bytes: number;
  line_count: number;
  is_test: boolean;
  is_doc: boolean;
  is_config: boolean;
  is_manifest: boolean;
  is_source: boolean;
  sha256: string;
}

export interface Repository {
  id: string;
  name: string;
  root_path: string;
  kind: string;
  status: string;
  scan_stats: Record<string, unknown>;
  error: string | null;
}

export interface Symbol {
  id: string;
  name: string;
  kind: string;
  file_path: string;
  start_line: number;
  end_line: number;
  parent: string | null;
  language: string | null;
  signature: string | null;
}

export interface Evidence {
  file_path: string;
  start_line: number | null;
  end_line: number | null;
  symbol_id: string | null;
  snippet: string | null;
  confidence: string;
}

export interface ToolCall {
  id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  result_summary: string | null;
  error: string | null;
  duration_ms: number;
}

export interface AgentRun {
  id: string;
  repository_id: string;
  task: string;
  mode: string;
  execution_mode: string;
  state: string;
  iterations: number;
  status_message: string;
  result: string | null;
  evidence: Evidence[];
  tool_calls: ToolCall[];
  usage: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  evidence: Evidence[];
}

export interface SearchResponse {
  query: string;
  mode: string;
  lexical_results: { path: string; score: number; language: string | null }[];
  symbol_results: {
    id: string;
    name: string;
    kind: string;
    file_path: string;
    start_line: number;
    end_line: number;
    score: number;
    signature: string | null;
  }[];
  ranked_files: { path: string; score: number; language: string | null }[];
}

export interface GraphResponse {
  nodes: { id: string; label: string; type: string; language?: string; file?: string; line?: number }[];
  edges: { source: string; target: string; kind: string }[];
}

export interface TestRunResult {
  ok: boolean;
  command?: string[];
  exit_code?: number | null;
  stdout: string;
  stderr: string;
  passed?: number;
  failed?: number;
  errors?: number;
  failed_tests?: string[];
  error?: string;
}

export interface EvaluationSummary {
  ok: boolean;
  cases: {
    case_id: string;
    retrieved_files: string[];
    recall: number;
    precision: number;
    latency_ms: number;
    passed: boolean;
  }[];
  summary: {
    total_cases: number;
    passed: number;
    mean_recall: number;
    mean_precision: number;
    mean_latency_ms: number;
  };
}
