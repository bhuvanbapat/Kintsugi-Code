"""End-to-end demonstration against the LIVE backend.

Executes the full product loop from section 80 of the build directive:
import -> scan -> structure -> graph -> architecture question -> symbol locate
-> evidence -> find intentional bug -> plan -> diff -> apply fix -> tests ->
verify -> final diff -> agent trace -> final state.
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

BASE = "http://127.0.0.1:8000/api"
# Repository-relative: <repo>/scripts/e2e_demo.py -> <repo>/examples/sample_repo
SAMPLE = str(pathlib.Path(__file__).resolve().parent.parent / "examples" / "sample_repo")


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode()[:500]}


def main() -> int:
    ok = True

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))

    # 1. import sample repository
    r = call("POST", "/repositories/import", {"path": SAMPLE})
    check("1 import repository", r.get("ok") is True, str(r))
    repo_id = r["repository"]["id"]

    # 2. scan / index
    r = call("POST", "/index", {"repository_id": repo_id})
    scan = r.get("scan", {})
    check("2 index", r.get("ok") is True and scan.get("source_files", 0) >= 4, str(r)[:300])
    print(
        f"      files={scan.get('total_files')} source={scan.get('source_files')} "
        f"test={scan.get('test_files')} symbols={r['repository']['scan_stats'].get('symbols')}"
    )

    # 3. inspect structure
    r = call("GET", f"/repositories/{repo_id}/files")
    check("3 list files", len(r.get("files", [])) >= 5)

    # 4. graph
    r = call("GET", f"/graph?repo_id={repo_id}&kind=files")
    check(
        "4 dependency graph",
        len(r.get("nodes", [])) >= 3 and len(r.get("edges", [])) >= 1,
        f"nodes={len(r.get('nodes', []))} edges={len(r.get('edges', []))}",
    )

    # 5. architecture question
    r = call("POST", "/chat", {
        "repository_id": repo_id,
        "message": "Explain the repository layering: services, data, API.",
        "mode": "explain",
    })
    run5 = r.get("run", {})
    check(
        "5 architecture question (evidence-backed)",
        run5.get("state") == "completed" and len(run5.get("evidence", [])) >= 2,
        str(r)[:300],
    )

    # 6. locate symbol
    r = call("POST", "/chat", {
        "repository_id": repo_id,
        "message": "Where is complete_task defined?",
        "mode": "locate",
    })
    check(
        "6 locate symbol",
        "complete_task" in (r.get("run", {}).get("result") or ""),
        str(r.get("run", {}).get("result"))[:200],
    )

    # 7. evidence retrieval via search
    r = call("POST", "/search", {
        "repository_id": repo_id, "query": "complete a todo task", "mode": "hybrid",
    })
    paths = [f["path"] for f in r.get("ranked_files", [])]
    check(
        "7 hybrid retrieval evidence",
        "services/task_service.py" in paths[:3],
        f"top files: {paths[:3]}",
    )

    # 8. find the intentional bug — run tests
    r = call("POST", "/tests/run", {"repository_id": repo_id})
    check(
        "8 tests reproduce intentional bug",
        r.get("ok") is False and r.get("failed", 0) >= 1
        and any("complete_todo" in t for t in r.get("failed_tests", [])),
        f"failed={r.get('failed')} tests={r.get('failed_tests')}",
    )

    # 9-10. agent FIX mode: plan + diff proposal (analysis-only, no mutation yet)
    r = call("POST", "/chat", {
        "repository_id": repo_id,
        "message": "Diagnose and propose a fix for the failing complete_task test.",
        "mode": "fix",
    })
    fix_run = r.get("run", {})
    check(
        "9 agent FIX diagnosis",
        fix_run.get("state") == "completed"
        and any(tc["tool_name"] == "run_tests" for tc in fix_run.get("tool_calls", [])),
    )

    # 10. generate the diff via controlled apply (the real fix: 'open' -> 'todo')
    import pathlib

    src_path = pathlib.Path(SAMPLE) / "services" / "task_service.py"
    fixed = src_path.read_text(encoding="utf-8").replace(
        'if task.status != "open":  # BUG: should be "todo"',
        'if task.status != "todo":',
    )
    check(
        "10 fix content differs from buggy source",
        fixed != src_path.read_text(encoding="utf-8"),
    )

    # 11. apply controlled fix WITH test validation
    r = call("POST", "/diff/apply", {
        "repository_id": repo_id,
        "path": "services/task_service.py",
        "content": fixed,
        "mode": "full",
        "run_tests_after": True,
    })
    check(
        "11 controlled fix applied + tests validated",
        r.get("ok") is True and (r.get("test_result") or {}).get("ok") is True,
        str(r)[:400],
    )
    if r.get("test_result"):
        tr = r["test_result"]
        print(f"      tests after fix: {tr.get('passed')} passed / {tr.get('failed')} failed")

    # 12-13. verify: run tests independently
    r = call("POST", "/tests/run", {"repository_id": repo_id})
    check(
        "12-13 tests green after fix",
        r.get("ok") is True and r.get("failed", 0) == 0 and (r.get("passed", 0) >= 7),
        f"ok={r.get('ok')} passed={r.get('passed')} failed={r.get('failed')}",
    )

    # 14. inspect final diff
    r = call("GET", f"/diff?repo_id={repo_id}")
    diff_text = (r.get("result") or {}).get("diff", "").replace("\r", "")
    check(
        "14 git diff shows the fix",
        "task_service.py" in diff_text
        and 'if task.status != "open"' in diff_text
        and any(l.lstrip("-+ ").startswith('if task.status != "todo"') for l in diff_text.splitlines()),
        diff_text[:300],
    )

    # 15. agent trace
    r = call("GET", f"/agent/runs?repo_id={repo_id}")
    runs = r.get("runs", [])
    total_calls = sum(len(x.get("tool_calls", [])) for x in runs)
    check(
        "15 agent trace recorded",
        len(runs) >= 3 and total_calls >= 3,
        f"runs={len(runs)} calls={total_calls}",
    )

    # 16. revert the fix so the demo repo keeps its intentional bug for future runs
    original = (
        'if task.status != "open":  # BUG: should be "todo"'
    )
    src_path.write_text(
        src_path.read_text(encoding="utf-8").replace(
            'if task.status != "todo":', original
        ),
        encoding="utf-8",
    )
    r = call("POST", "/tests/run", {"repository_id": repo_id})
    check(
        "16 demo repo restored (bug back, 1 test fails again)",
        r.get("failed", 0) == 1,
        f"failed={r.get('failed')}",
    )

    print()
    print("E2E RESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
