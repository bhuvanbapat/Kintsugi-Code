"""Second adversarial wave: concurrency, unicode, size limits, agent internals."""
import concurrent.futures
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"
PASS, FAIL = [], []


def call(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return -1, {"transport": f"{type(e).__name__}: {e}"}


def check(label, cond, detail=""):
    (PASS if cond else FAIL).append(f"{label}{(' — ' + str(detail)[:150]) if not cond and detail else ''}")


repos = call("GET", "/repositories")[1]
repo = next((r for r in repos["repositories"] if r["status"] == "indexed"), None)
assert repo, "no indexed repo — run import first"
rid = repo["id"]

# 1. Unicode path + query handling
code, out = call("GET", f"/repositories/{rid}/file?path=services%2Ftask_service.py")
check("normal file read", code == 200 and "complete_task" in out.get("content", ""), f"{code} {out}")
code, out = call("POST", "/search", {"repository_id": rid, "query": "café ☕ ünïcode", "mode": "hybrid"})
check("unicode query search", code == 200, f"{code} {out}")

# 2. Oversized inputs
code, out = call("POST", "/search", {"repository_id": rid, "query": "word " * 5000, "mode": "hybrid"})
check("10k-word query survives", code == 200, f"{code}")
code, out = call("POST", "/search", {"repository_id": rid, "query": "x", "limit": 999999})
check("huge limit clamped server-side", code == 200, f"{code} {out}")

# 3. Concurrency: 12 parallel chat requests (thread-safety of store+retriever)
def one_chat(i):
    return call("POST", "/chat", {"repository_id": rid, "message": f"Where is complete_task? {i}",
                                  "mode": "locate"})

with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    results = list(ex.map(one_chat, range(12)))
codes = [c for c, _ in results]
check("12 concurrent chats all 200", all(c == 200 for c in codes), codes)
states = [out.get("run", {}).get("state") for _, out in results]
check("12 concurrent chats all completed", all(s == "completed" for s in states), states)

# 4. Concurrent evaluation + chat (the old thread-bug trigger, now under load)
def mixed(i):
    if i % 2:
        return call("POST", "/evaluation/run", {"repository_id": rid})
    return call("POST", "/chat", {"repository_id": rid, "message": "Explain the layers", "mode": "explain"})

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    mixed_results = list(ex.map(mixed, range(10)))
mcodes = [c for c, _ in mixed_results]
check("10 concurrent mixed eval/chat all 200", all(c == 200 for c in mcodes), mcodes)

# 5. Settings round-trip with adversarial values
code, out = call("POST", "/settings", {"context_budget_tokens": -5})
check("negative budget rejected or clamped", code in (200, 422), f"{code}")
code, out = call("POST", "/settings", {"llm_provider": "mock", "context_budget_tokens": 8000})
check("settings restore", code == 200)

# 6. Graph endpoints both kinds under load
for kind in ("files", "symbols"):
    code, out = call("GET", f"/graph?repo_id={rid}&kind={kind}")
    check(f"graph {kind}", code == 200 and out.get("nodes") is not None, f"{code}")

# 7. Conversation listing with limit param
code, out = call("GET", f"/conversations?repo_id={rid}&limit=1")
check("conversations limit", code == 200, f"{code}")

# 8. Agent FIX-mode end-to-end via chat (uses run_tests -> real subprocess)
code, out = call("POST", "/chat", {"repository_id": rid, "message": "Diagnose the failing test",
                                   "mode": "fix", "execution_mode": "analysis_only"})
check("FIX mode via chat", code == 200 and out.get("run", {}).get("state") == "completed",
      f"{code} {out.get('run', {}).get('state')}")

# 9. REVIEW mode without a git repo must degrade gracefully, not 500
code, out = call("POST", "/chat", {"repository_id": rid, "message": "Review the diff", "mode": "review"})
check("REVIEW mode handles no-diff gracefully",
      code == 200 and out.get("run", {}).get("state") == "completed",
      f"{code} {str(out)[:150]}")

print()
for p in PASS:
    print("PASS", p)
for f in FAIL:
    print("FAIL", f)
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
