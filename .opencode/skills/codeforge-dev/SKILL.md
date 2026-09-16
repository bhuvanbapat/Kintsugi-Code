---
name: codeforge-dev
description: Project-local conventions for working on CodeForge itself — run backend tests and evaluation, apply a controlled patch with test validation, and verify the e2e workflow. Use when developing, testing, or changing this repository.
---

# CodeForge development skill

Conventions for working on this codebase.

## Commands

Backend tests (71 must pass):
```powershell
cd backend
& .venv\Scripts\python.exe -m pytest tests -q
```

Evaluation (must stay 8/8, mean recall >= 0.875):
```powershell
& .venv\Scripts\python.exe scripts\run_evaluation.py
```

Frontend typecheck + build:
```powershell
cd frontend
npx tsc -b --noEmit
npm run build
```

Full end-to-end (backend must be running on :8000):
```powershell
& ..\backend\.venv\Scripts\python.exe ..\scripts\e2e_demo.py
```

## Rules

1. Retrieval/ranking changes: re-run the evaluation; recall regressions are
   blockers (docs/EVALUATION.md documents the sym-2 history).
2. Tool or file-access changes: keep path containment and add/extend a
   security test in tests/test_agent_api.py.
3. Sample repo is a fixture: never fix its intentional bug
   (`complete_task` status check) — demos depend on it failing.
4. Schema changes: update Store INSERT column lists (two past bugs were
   count mismatches — tests catch them now).
5. Mock provider must stay offline-deterministic and compose only from
   retrieval context (ADR-004).
