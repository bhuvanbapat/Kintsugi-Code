"""Verify the Kintsugi-Code MCP server over real stdio (subprocess round-trip)."""
import json
import pathlib
import subprocess
import sys
import urllib.request

BASE = "http://127.0.0.1:8000/api"


def call_api(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> int:
    repos = call_api("GET", "/repositories")["repositories"]
    repo_id = next((r["id"] for r in repos if r["status"] == "indexed"), None)
    if not repo_id:
        print("FAIL: no indexed repository in running backend")
        return 1

    # Run the MCP server module from the repo's backend/ directory (portable:
    # derived from this script's location, no machine-specific paths).
    backend_dir = pathlib.Path(__file__).resolve().parent.parent / "backend"
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.mcp.server"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8",
        cwd=str(backend_dir),
    )
    try:
        def send(msg: dict) -> dict:
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            return json.loads(line)

        r = send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert r["result"]["serverInfo"]["name"] == "Kintsugi-Code", r
        print("PASS initialize ->", r["result"]["serverInfo"])

        r = send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = [t["name"] for t in r["result"]["tools"]]
        assert "search_code" in tool_names and "get_symbol" in tool_names, tool_names
        print("PASS tools/list ->", tool_names)

        r = send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "set_repository", "arguments": {"repository_id": repo_id}}})
        assert "active repository" in r["result"]["content"][0]["text"], r
        print("PASS set_repository")

        r = send({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
            "name": "get_symbol", "arguments": {"name": "TaskService"}}})
        payload = json.loads(r["result"]["content"][0]["text"])
        assert any(s["name"] == "TaskService" for s in payload["symbols"]), payload
        print("PASS get_symbol TaskService ->", len(payload["symbols"]), "matches")

        r = send({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
            "name": "search_code", "arguments": {"query": "task completion"}}})
        payload = json.loads(r["result"]["content"][0]["text"])
        assert payload["ranked_files"], payload
        print("PASS search_code -> top:", payload["ranked_files"][0]["path"])

        print("MCP STDIO VERIFICATION: ALL PASS")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())

