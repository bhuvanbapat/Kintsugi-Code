"""Safe test runner with project-type detection, timeouts, output capture.

Detects the ecosystem before executing anything, uses an allow-list of
commands, never pipes curl|sh, and parses pytest/npm output for pass/fail
counts.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.indexing.secrets import redact

log = get_logger(__name__)


def detect_project_type(root: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"root": str(root)}
    has = lambda p: (root / p).exists()  # noqa: E731
    if has("pyproject.toml") or has("setup.py") or has("requirements.txt"):
        info["type"] = "python"
        info["test_command"] = [sys.executable, "-m", "pytest", "-q"]
        info["lint_command"] = [sys.executable, "-m", "ruff", "check", "."]
        info["build_files"] = [p for p in ("pyproject.toml", "setup.py", "requirements.txt") if has(p)]
    elif has("package.json"):
        pkg = {}
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
        scripts = pkg.get("scripts", {})
        pm = "npm"
        if has("pnpm-lock.yaml"):
            pm = "pnpm"
        elif has("yarn.lock"):
            pm = "yarn"
        info["type"] = "javascript"
        info["package_manager"] = pm
        test_script = scripts.get("test", "test")
        info["test_command"] = [pm, "run", test_script] if test_script != "test" else [pm, "test"]
        info["build_files"] = ["package.json"]
    elif has("go.mod"):
        info["type"] = "go"
        info["test_command"] = ["go", "test", "./..."]
        info["build_files"] = ["go.mod"]
    elif has("Cargo.toml"):
        info["type"] = "rust"
        info["test_command"] = ["cargo", "test"]
        info["build_files"] = ["Cargo.toml"]
    elif has("pom.xml"):
        info["type"] = "java-maven"
        info["test_command"] = ["mvn", "-q", "test"]
        info["build_files"] = ["pom.xml"]
    elif has("build.gradle") or has("build.gradle.kts"):
        info["type"] = "java-gradle"
        info["test_command"] = ["gradle", "test"]
        info["build_files"] = ["build.gradle"]
    else:
        info["type"] = "unknown"
        info["test_command"] = None
        info["build_files"] = []
    return info


class TestRunner:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.settings = get_settings()

    async def run(self, scope: str = "auto", timeout: float | None = None) -> dict[str, Any]:
        import time as _time

        from app.tools.registry import assert_safe_command

        info = detect_project_type(self.root)
        cmd = info.get("test_command")
        if not cmd:
            return {"ok": False, "error": "unknown project type; no test command detected",
                    "project_type": info["type"]}
        if isinstance(scope, str) and scope not in ("auto", "", None):
            cmd = cmd + [scope]
        # The scope string is user input appended to argv — enforce the
        # dangerous-command policy at this boundary too (argv stays fixed;
        # this rejects e.g. a scope crafted to contain 'rm -rf').
        try:
            assert_safe_command(cmd)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"command rejected by safety policy: {exc}",
                    "command": cmd}
        timeout = timeout or self.settings.command_timeout_seconds
        started = _time.monotonic()
        try:
            proc = subprocess.run(
                cmd, cwd=str(self.root), capture_output=True, text=True,
                timeout=timeout, shell=False,
            )
            stdout, stderr = proc.stdout, proc.stderr
            exit_code: int | None = proc.returncode
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"tests timed out after {timeout}s",
                    "command": cmd, "duration_ms": int(timeout * 1000)}
        except FileNotFoundError:
            return {"ok": False, "error": f"command not found: {cmd[0]}", "command": cmd}
        duration_ms = int((_time.monotonic() - started) * 1000)

        stdout, stderr = redact(stdout), redact(stderr)
        max_out = self.settings.max_tool_output_bytes
        if len(stdout) > max_out:
            stdout = stdout[:max_out] + "\n...[truncated]"
        parsed = parse_test_output(stdout + "\n" + stderr, info["type"])
        return {
            "ok": exit_code == 0,
            "command": cmd,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms,
            **parsed,
        }

    async def static_check(self) -> dict[str, Any]:
        from app.tools.registry import assert_safe_command

        info = detect_project_type(self.root)
        cmd = info.get("lint_command")
        if not cmd:
            return {"ok": True, "skipped": True, "reason": "no configured lint command for this project type"}
        assert_safe_command(cmd)
        try:
            proc = subprocess.run(cmd, cwd=str(self.root), capture_output=True, text=True,
                                  timeout=120, shell=False)
            return {"ok": proc.returncode == 0, "command": cmd, "exit_code": proc.returncode,
                    "stdout": redact(proc.stdout), "stderr": redact(proc.stderr)}
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {"ok": False, "command": cmd, "error": str(e)}


def parse_test_output(output: str, project_type: str) -> dict[str, Any]:
    """Extract pass/fail counts from common test output formats."""
    passed = failed = errors = skipped = 0
    failed_tests: list[str] = []
    if project_type.startswith("python") or "pytest" in output:
        import re

        m = re.search(r"(\d+) passed", output)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", output)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+) error", output)
        if m:
            errors = int(m.group(1))
        m = re.search(r"(\d+) skipped", output)
        if m:
            skipped = int(m.group(1))
        failed_tests = re.findall(r"FAILED\s+(\S+)", output)
    elif project_type in ("javascript", "go", "rust", "java-maven", "java-gradle"):
        import re

        m = re.search(r"(\d+)\s+pass(?:ing|ed)?", output, re.I)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+)\s+fail(?:ing|ed)?", output, re.I)
        if m:
            failed = int(m.group(1))
        failed_tests = re.findall(r"FAIL(?:URE)?\s+(?:- )?(\S+)", output)
    return {
        "passed": passed, "failed": failed, "errors": errors,
        "skipped": skipped, "failed_tests": failed_tests[:50],
        "project_type": project_type,
    }
