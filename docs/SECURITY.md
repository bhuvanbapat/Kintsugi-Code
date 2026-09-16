# CodeForge — Security

## Threat model

Asset: the developer's machine, filesystem, and any configured LLM credentials.
Attacker: malicious content inside an imported repository (untrusted input).

| Threat | Vector | Mitigation | Verified by |
|---|---|---|---|
| Arbitrary code execution | repo scripts, package hooks | CodeForge never runs repo code; only allow-listed git/test commands — the dangerous-command policy is enforced at the subprocess execution boundary (`_run_command`, TestRunner) | test_dangerous_command_policy, test_dangerous_command_policy_enforced_in_production_path |
| Path traversal | `../` in tool args or API | every path resolved and `relative_to(repo_root)` checked | test_tool_path_security, test_api_file_traversal_blocked |
| Command injection | test scope strings | scope appended to a fixed argv list; `shell=False` everywhere | review + code path (no string-built commands) |
| Dangerous commands | crafted scope | regex policy blocks rm -rf / curl\|sh / fork bombs | test_dangerous_command_policy |
| Secret exposure | indexed repo content | conservative regex detection → `[REDACTED_SECRET]` at INGESTION — before SQLite persistence, retrieval, LLM context, tool output | test_secret_detection_and_redaction, test_secrets_never_persist_raw_in_file_docs |
| Secret exposure | log messages | redaction at LogRecord creation (msg, args, exception/traceback text) via a global record factory + root/uvicorn filters | test_logging_security.py (emitted-output tests) |
| Credential leakage | settings API | key stored in process env only, masked in GET (`llm_api_key_set: bool`), never echoed | API code review |
| Prompt injection | malicious README/comments | repo content is treated as retrieval **data**; system prompt fixes behavior; mock provider composes answers from structured retrieval output only | design (ADR-005) |
| Oversized input | huge files / floods | per-file size cap (2MB default), repo file-count cap (20k), output truncation (200KB) on tools and tests | test_scanner_skips_ignored_and_large |
| Test-runner abuse | slow/hanging tests | subprocess timeout (default 300s) with structured timeout response | TestRunner code + e2e |
| Unbounded agent loops | adversarial tasks | max iterations + repeated-call + no-progress detection | agent engine tests |
| Unsafe modification | agent overwrites files | modification tools gated by ExecutionMode; apply endpoint validates via tests and auto-rolls-back on failure OR timeout, restoring exact pre-apply state (including removing newly created files) | test_api_diff_apply_rollback, test_api_diff_apply_rollback_removes_new_file, test_api_diff_apply_rollback_on_test_timeout |
| Symlink escape | crafted repo symlinks | `os.walk(followlinks=False)` in scanner | scanner code |

## Input boundaries

```
repository path  → normalize (resolve + exists + is_dir) before any use
file path (tool) → resolve_in_repo() containment check
file path (API)  → same containment check in /file and /diff/apply
test scope      → appended to argv, never interpolated into a shell string
LLM response    → rendered as text, never executed
```

## What is deliberately NOT protected against

- A malicious repository that the developer *chooses* to run tests for is
  still executing that project's own test suite on the developer's machine —
  that is the product's purpose. The allow-list limits *which* commands run,
  not what third-party test code itself does. Run unfamiliar repositories in
  a container/VM.
- The local API has no authentication: it is a single-user local tool. Do
  not expose port 8000 publicly.

## Secret-storage remediation for existing databases

Redaction at ingestion landed after the first release. SQLite databases
created by earlier builds may contain unredacted `file_docs` rows. The
remediation path is re-indexing: `POST /api/index` replaces per-repo
content atomically, so one re-index per repository rewrites every stored
file with redacted text. There is no in-place migration by design — the
store has no schema-version layer, and re-index is the existing,
idempotent, already-tested operation.

## Secret detection patterns

OpenAI-style keys, GitHub PATs/OAuth, Slack tokens, AWS access key IDs,
private key blocks, password/credential assignments — with key names
preserved (`API_KEY=[REDACTED_SECRET]`) so surrounding code stays readable.

## Reporting

Security issues: open a GitHub issue with the `security` label; do not post
exploit details publicly.
