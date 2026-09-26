"""Cliente LLM opcional para o agente epidemiológico VNext.

Reutiliza variáveis de ambiente já aceitas pelo projeto. O cliente nunca altera
artefatos canônicos; apenas produz uma proposta de resposta para validação.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    url: str
    model: str
    provider: str
    available: bool


def resolve_llm_config() -> LLMConfig:
    try:
        from meningites_env import load_meningites_env
        load_meningites_env()
    except Exception:
        pass

    api_key = (
        os.environ.get("LLM_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("MENINGITES_OPENAI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )
    model = (
        os.environ.get("LLM_MODEL")
        or os.environ.get("GEMINI_MODEL")
        or os.environ.get("MENINGITES_OPENAI_MODEL")
        or "gemini-2.5-flash"
    )
    url = os.environ.get("LLM_API_URL") or os.environ.get("OPENAI_BASE_URL") or ""
    gemini_default = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    if not url:
        url = gemini_default if ("gemini" in model.lower() or os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")) else "https://api.openai.com/v1/chat/completions"
    if "gemini" in model.lower() and "googleapis.com" not in url and "openai.com" in url:
        url = gemini_default
    provider = "gemini" if "googleapis.com" in url or "gemini" in model.lower() else "openai"
    return LLMConfig(api_key=api_key, url=url, model=model, provider=provider, available=bool(api_key))


class OptionalLLMClient:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or resolve_llm_config()

    def complete(self, prompt: str) -> dict[str, Any]:
        if not self.config.available:
            return {
                "status": "unavailable",
                "provider": self.config.provider,
                "model": self.config.model,
                "text": "",
                "error": "Credencial LLM não configurada.",
            }

        body = json.dumps({
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você é uma camada de síntese do agente epidemiológico VNext. "
                        "Preserve integralmente os fatos canônicos fornecidos, cite fontes normativas "
                        "quando usadas e não crie regra clínica."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }).encode("utf-8")

        req = urllib.request.Request(
            self.config.url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip()
            return {
                "status": "ok",
                "provider": self.config.provider,
                "model": self.config.model,
                "text": text,
                "error": "",
            }
        except Exception as exc:
            return {
                "status": "error",
                "provider": self.config.provider,
                "model": self.config.model,
                "text": "",
                "error": f"{type(exc).__name__}: {exc}",
            }
