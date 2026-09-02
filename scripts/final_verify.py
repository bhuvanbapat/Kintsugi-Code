"""Final live verification: graph-symbols regression, eval, execution modes."""
import json
import sys
import urllib.request


def call(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api" + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    repos = call("GET", "/repositories")["repositories"]
    repo = next(r for r in repos if r["status"] == "indexed")
    repo_id = repo["id"]
    ok = True

    # 1. symbols graph (the mypy-caught regression, runtime-verified)
    g = call("GET", f"/graph?repo_id={repo_id}&kind=symbols")
    print(f"symbols graph: {len(g['nodes'])} nodes, {len(g['edges'])} edges")
    print("types:", sorted({n["type"] for n in g["nodes"]}))
    if not g["nodes"]:
        ok = False
        print("FAIL: symbols graph empty")

    # 2. evaluation via API
    res = call("POST", "/evaluation/run", {"repository_id": repo_id})
    s = res["summary"]
    print(f"eval: {s['passed']}/{s['total_cases']} recall={s['mean_recall']}")
    if s["passed"] != s["total_cases"]:
        ok = False
        print("FAIL: evaluation regressed")

    # 3. execution modes exposed via chat API
    r = call("POST", "/chat", {
        "repository_id": repo_id,
        "message": "Where is complete_task defined?",
        "mode": "locate",
        "execution_mode": "analysis_only",
    })
    print("analysis_only run state:", r["run"]["state"])
    if r["run"]["state"] != "completed":
        ok = False

    r2 = call("POST", "/chat", {
        "repository_id": repo_id,
        "message": "Run tests",
        "mode": "test",
        "execution_mode": "controlled_execution",
    })
    print("controlled_execution run state:", r2["run"]["state"])
    if r2["run"]["state"] != "completed":
        ok = False

    # 4. git URL import rejects bad URLs
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/repositories/import",
        data=json.dumps({"git_url": "http://bad/x"}).encode(),
        method="POST", headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        ok = False
        print("FAIL: bad git_url accepted")
    except urllib.error.HTTPError as e:
        print(f"git_url rejection: HTTP {e.code}")
        if e.code != 400:
            ok = False

    print("FINAL LIVE VERIFICATION:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
