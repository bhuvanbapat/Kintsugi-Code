"""LLM provider abstraction.

Supports:
- OpenAIProvider: any OpenAI-compatible endpoint (OpenAI, Ollama, vLLM, LM Studio...)
- MockProvider: deterministic, offline answers built from retrieved evidence.

Configuration: LLM_PROVIDER / LLM_BASE_URL / LLM_MODEL / LLM_API_KEY
(CODEFORGE_ env prefix). Never hard-codes credentials.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class LLMResponse:
    def __init__(self, content: str, provider: str, model: str,
                 input_tokens: int | None = None, output_tokens: int | None = None,
                 usage_unavailable: bool = False) -> None:
        self.content = content
        self.provider = provider
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.usage_unavailable = usage_unavailable

    @property
    def usage(self) -> dict[str, Any]:
        if self.usage_unavailable or self.input_tokens is None:
            return {"available": False, "reason": "provider does not report usage"}
        return {
            "available": True,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens or 0,
            "estimated_cost_usd": 0.0,
        }


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(self, system: str, prompt: str, context: dict | None = None) -> LLMResponse:
        ...

    async def close(self) -> None:  # noqa: B027 — optional lifecycle hook
        """Optional cleanup hook; providers override when they hold resources."""


class MockProvider(LLMProvider):
    """Deterministic offline provider: composes answers from retrieved context.

    This is the demo mode: no network, no key, fully reproducible answers
    grounded in the retrieval evidence passed via `context`.
    """
    name = "mock"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def complete(self, system: str, prompt: str, context: dict | None = None) -> LLMResponse:
        ctx = context or {}
        files = ctx.get("files", [])
        citations = ctx.get("citations", [])
        intent = ctx.get("intent", "explain")
        task = ctx.get("task_mode", "explain")
        query = ctx.get("query", prompt)

        if not files:
            content = (
                "I could not find relevant code in the indexed repository for this question.\n\n"
                "CONFIDENCE: uncertain — no retrieval evidence matched the query."
            )
            return LLMResponse(content, self.name, "mock-offline", 120, 40)

        lines: list[str] = []
        if task in ("locate",) or intent == "locate":
            lines.append("LOCATED\n")
        elif task in ("analyze", "fix") or intent == "analyze":
            lines.append("ANALYSIS\n")
        elif task == "plan":
            lines.append("PLAN\n")
        else:
            lines.append("ANALYSIS\n")

        lines.append(f"Query: {query}\n")

        # Build the answer body from the retrieved evidence, most relevant first.
        lines.append("The most relevant code is:\n")
        for f in files[:6]:
            path = f["path"]
            lines.append(f"- {path}:{f.get('start_line', 1)}-{f.get('end_line', 1)}")
        lines.append("")

        top = files[0]
        symbols_in_top: list[str] = re.findall(
            r"(?:def|class|function|const|let)\s+([A-Za-z_][A-Za-z0-9_]*)", top.get("snippet", "")
        )
        lines.append("Key definitions found in the top match:")
        if symbols_in_top:
            for s in symbols_in_top[:6]:
                lines.append(f"- {s}")
        else:
            lines.append("- (structural summary not available for this file type)")
        lines.append("")

        if citations:
            lines.append("EVIDENCE\n")
            for c in citations[:8]:
                loc = c["file_path"]
                if c.get("start_line"):
                    loc += f":{c['start_line']}"
                    if c.get("end_line") and c["end_line"] != c["start_line"]:
                        loc += f"-{c['end_line']}"
                lines.append(f"- {loc}")
            lines.append("")

        lines.append("CONFIDENCE: confirmed_from_code — answer grounded in indexed repository files.")

        content = "\n".join(lines)
        in_tok = 300 + sum(len(f.get("snippet", "")) for f in files) // 4
        return LLMResponse(content, self.name, "mock-offline", in_tok, len(content) // 4)


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible chat completion provider (httpx, no vendor SDK)."""
    name = "openai"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.settings.llm_api_key:
                headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.settings.llm_base_url,
                headers=headers,
                timeout=self.settings.llm_timeout_seconds,
            )
        return self._client

    async def complete(self, system: str, prompt: str, context: dict | None = None) -> LLMResponse:
        client = self._get_client()
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        resp = await client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage")
        in_tok = usage.get("prompt_tokens") if usage else None
        out_tok = usage.get("completion_tokens") if usage else None
        return LLMResponse(
            content, self.name, self.settings.llm_model,
            in_tok, out_tok, usage_unavailable=usage is None,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def create_provider(settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    if s.llm_provider == "openai":
        return OpenAIProvider(s)
    return MockProvider(s)


_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = create_provider()
    return _provider


def reset_provider() -> None:
    global _provider
    _provider = None
