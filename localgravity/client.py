"""OllamaClient — isolates the model backend.

Talks to Ollama's HTTP API directly via urllib (stdlib only): no third-party
dependency, and it's exactly what the gate test proved works. Everything
Ollama-specific lives here. If the endpoint or tool-call format changes, only this
file is touched (provider-fallback discipline). Tool-call shape is validated before
the harness acts on it: local models are less reliable than Gemini, so a malformed
call is tolerated rather than crashing.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Any

DEFAULT_HOST = "http://localhost:11434"


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    raw: Any = None


@dataclass
class ModelTurn:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class OllamaClient:
    def __init__(self, model: str = "gemma4:26b", host: str | None = None, temperature: float = 0.0):
        self.model = model
        self.host = (host or DEFAULT_HOST).rstrip("/")
        self.temperature = temperature

    def preflight(self) -> str | None:
        """Return None if Ollama is reachable and the model is present, else a friendly message."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                tags = json.load(resp)
        except Exception:
            return (
                f"Cannot reach Ollama at {self.host}. Is it running? "
                f"Start it (`ollama serve`) or pass --host."
            )
        names = {m.get("name", "") for m in tags.get("models", [])}
        base = self.model.split(":")[0]
        if self.model not in names and not any(n.split(":")[0] == base for n in names):
            return f"Model '{self.model}' not found in Ollama. Pull it: `ollama pull {self.model}`."
        return None

    def chat(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {"temperature": self.temperature},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.load(resp)
        msg = data.get("message", {})
        return ModelTurn(
            content=msg.get("content", "") or "",
            tool_calls=self._parse_tool_calls(msg.get("tool_calls") or []),
        )

    @staticmethod
    def _parse_tool_calls(raw_calls: list) -> list[ToolCall]:
        """Validate shape. Tolerate the two arg encodings (dict or JSON string)."""
        calls: list[ToolCall] = []
        for c in raw_calls:
            fn = c.get("function", {}) if isinstance(c, dict) else {}
            name = fn.get("name")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}
            if not name:
                continue
            calls.append(ToolCall(name=name, arguments=args or {}, raw=c))
        return calls
