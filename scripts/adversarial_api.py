"""Adversarial bug hunt: actually exercise every endpoint + edge cases live."""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"
PASS, FAIL = [], []


def call(method, path, body=None, expect=None, label=""):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            code, out = r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        code, out = e.code, {}
        try:
            out = json.loads(e.read().decode() or "{}")
        except Exception:
            pass
    except Exception as e:
        FAIL.append(f"{label or path}: transport {type(e).__name__} {e}")
        return None
    if expect is not None and code != expect:
        FAIL.append(f"{label or path}: expected {expect} got {code} — {str(out)[:200]}")
        return None
    PASS.append(f"{label or path} ({code})")
    return out


# --- health & settings
call("GET", "/health", expect=200, label="health")
call("GET", "/settings", expect=200, label="settings")
s = call("POST", "/settings", body={"llm_provider": "bogus"}, expect=422,
         label="settings rejects bogus provider")
call("POST", "/settings", body={"llm_provider": "mock"}, expect=200,
     label="settings accepts mock")

# --- repo import edge cases
call("POST", "/repositories/import", body={"path": "C:\\DOES\\NOT\\EXIST"}, expect=400,
     label="import nonexistent path -> 400")
call("POST", "/repositories/import", body={}, expect=422,
     label="import empty body -> 422 (validation)")
call("POST", "/repositories/import", body={"git_url": "ssh://git@evil/x"}, expect=400,
     label="import ssh url -> 400")
call("POST", "/repositories/import", body={"git_url": "https://github.com/x/../../y"}, expect=400,
     label="import traversal url -> 400")

# --- nonexistent repo everywhere
call("GET", "/repositories/repo_nope", expect=404, label="get unknown repo -> 404")
call("POST", "/index", body={"repository_id": "repo_nope"}, expect=404, label="index unknown -> 404")
call("POST", "/search", body={"repository_id": "repo_nope", "query": "x"}, expect=404,
     label="search unknown repo -> 404")
call("GET", "/symbols?repo_id=repo_nope", expect=404, label="symbols unknown -> 404")
call("GET", "/graph?repo_id=repo_nope", expect=404, label="graph unknown -> 404")
call("GET", "/diff?repo_id=repo_nope", expect=404, label="diff unknown -> 404")
call("POST", "/chat", body={"repository_id": "repo_nope", "message": "hi"}, expect=404,
     label="chat unknown repo -> 404")
call("POST", "/tests/run", body={"repository_id": "repo_nope"}, expect=404,
     label="tests unknown repo -> 404")
call("POST", "/evaluation/run", body={"repository_id": "repo_nope"}, expect=404,
     label="eval unknown repo -> 404")
call("GET", "/agent/runs/never_existed", expect=404, label="unknown run -> 404")
call("GET", "/conversations/never_existed", expect=404, label="unknown conv -> 404")

# --- tool execution edge cases
call("POST", "/tools/execute", body={"repository_id": "x", "tool": "nope", "args": {}},
     expect=404, label="execute unknown tool -> 404 (repo checked first)")

# --- import + index a real repo for positive paths
repos = call("GET", "/repositories", expect=200, label="list repos")
repo = next((r for r in repos["repositories"] if r["status"] == "indexed"), None)
if not repo:
    import pathlib
    sample = pathlib.Path(__file__).resolve().parent.parent / "examples" / "sample_repo"
    r = call("POST", "/repositories/import", body={"path": str(sample)}, expect=200,
             label="import sample")
    repo = r["repository"]
    call("POST", "/index", body={"repository_id": repo["id"]}, expect=200, label="index sample")
rid = repo["id"]

# file path traversal & weird inputs
call("GET", f"/repositories/{rid}/file?path=..%2F..%2F..%2Fetc%2Fpasswd", expect=400,
     label="file traversal -> 400")
call("GET", f"/repositories/{rid}/file?path=definitely_missing.py", expect=404,
     label="missing file -> 404")
call("GET", f"/repositories/{rid}/file?path=", expect=400, label="empty path -> 400")
call("GET", f"/repositories/{rid}/file?path=services", expect=400,
     label="directory path -> 400")

# search edge cases
call("POST", "/search", body={"repository_id": rid, "query": "", "mode": "hybrid"},
     expect=200, label="empty query -> 200 (no results)")
call("POST", "/search", body={"repository_id": rid, "query": "x", "mode": "bogus"},
     expect=422, label="bogus mode -> 422")

# diff apply edge cases
call("POST", "/diff/apply", body={"repository_id": rid, "path": "../evil.py",
     "content": "x", "mode": "full"}, expect=400, label="patch traversal -> 400")
call("POST", "/diff/apply", body={"repository_id": rid, "path": "a/b/c/d.py",
     "content": "same", "mode": "full"}, expect=200, label="create file -> 200")
# cleanup the created file so the sample repo stays pristine
import pathlib
created = pathlib.Path(repo["root_path"]) / "a" / "b" / "c" / "d.py"
if created.exists():
    created.unlink()
    for d in ("a/b/c", "a/b", "a"):
        try:
            (pathlib.Path(repo["root_path"]) / d).rmdir()
        except OSError:
            pass

# tools endpoint on the real repo
call("GET", "/tools", expect=200, label="tools list")
call("POST", "/tools/execute", body={"repository_id": rid, "tool": "find_path",
     "args": {}}, expect=200, label="find_path missing args -> structured error (ok:false)")
call("POST", "/tools/execute", body={"repository_id": rid, "tool": "read_file",
     "args": {"path": "../x.py"}}, expect=200, label="read traversal -> structured error")

# conversations
c = call("GET", f"/conversations?repo_id={rid}", expect=200, label="list conversations")

# evaluation on indexed repo
e = call("POST", "/evaluation/run", body={"repository_id": rid}, expect=200,
         label="evaluation run")
if e and e.get("summary", {}).get("passed") != 8:
    FAIL.append(f"evaluation: expected 8/8 got {e.get('summary')}")

print()
for p in PASS:
    print("PASS", p)
for f in FAIL:
    print("FAIL", f)
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
