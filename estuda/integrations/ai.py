"""Contrato comum e fábrica dos provedores de IA do Estuda+."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class AIUnavailable(RuntimeError):
    pass


@runtime_checkable
class AIClient(Protocol):
    @property
    def available(self) -> bool:
        ...

    def respond(self, messages: list[dict[str, str]], complex_task: bool = False) -> dict:
        ...


SYSTEM_INSTRUCTION = (
    "Você é um assistente de estudos. Responda em português, de forma acolhedora, objetiva "
    "e educativa. Ajude o estudante a escolher próximos passos concretos."
)
COMPLEX_TASK_SUFFIX = " Para a última solicitação, sugira no máximo cinco subtarefas curtas e concretas."


def _parse_and_validate_suggestions(output_text: str) -> dict:
    cleaned = output_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        result = json.loads(cleaned)
    except ValueError as exc:
        raise AIUnavailable("O serviço de IA retornou uma resposta inválida.") from exc

    subtasks = result.get("subtasks") if isinstance(result, dict) else None
    response_text = result.get("response") if isinstance(result, dict) else None
    if (
        not isinstance(response_text, str)
        or not response_text.strip()
        or not isinstance(subtasks, list)
        or len(subtasks) > 5
        or any(not isinstance(item, str) or not item.strip() or len(item.strip()) > 120 for item in subtasks)
    ):
        raise AIUnavailable("O serviço de IA retornou uma resposta fora do formato esperado.")
    return {"response": response_text.strip(), "subtasks": [item.strip() for item in subtasks]}


def _is_ollama_online(host: str = "http://localhost:11434", timeout: float = 0.5) -> bool:
    try:
        req = urllib.request.Request(f"{host.rstrip('/')}/api/tags", headers={"User-Agent": "EstudaApp"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def create_ai_client() -> AIClient:
    """Cria o cliente de IA configurado por variáveis de ambiente ou auto-detecta Ollama local."""
    provider = os.getenv("ESTUDA_AI_PROVIDER", "").strip().casefold()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    client: AIClient
    if provider == "ollama":
        from .ollama import OllamaClient
        client = OllamaClient()
    elif provider == "openai":
        from .openai import OpenAIResponsesClient
        client = OpenAIResponsesClient()
    elif provider == "gemini":
        from .gemini import GeminiClient
        client = GeminiClient()
    elif not provider:
        # Sem provedor explícito: verifica chaves de API ou auto-detecta Ollama ativo
        if gemini_key:
            from .gemini import GeminiClient
            client = GeminiClient()
        elif openai_key:
            from .openai import OpenAIResponsesClient
            client = OpenAIResponsesClient()
        elif os.getenv("OLLAMA_HOST") or _is_ollama_online():
            from .ollama import OllamaClient
            client = OllamaClient()
        else:
            from .gemini import GeminiClient
            client = GeminiClient()
    else:
        raise ValueError("ESTUDA_AI_PROVIDER deve ser 'gemini', 'openai' ou 'ollama'.")

    logger.info("Cliente de IA selecionado: %s (modelo=%s)", client.__class__.__name__, getattr(client, "model", "padrão"))
    return client


def __getattr__(name: str):
    """Preserva os imports públicos antigos sem criar ciclos entre adaptadores."""
    if name == "OpenAIResponsesClient":
        from .openai import OpenAIResponsesClient
        return OpenAIResponsesClient
    if name == "GeminiClient":
        from .gemini import GeminiClient
        return GeminiClient
    if name == "OllamaClient":
        from .ollama import OllamaClient
        return OllamaClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AIClient", "AIUnavailable", "OpenAIResponsesClient", "GeminiClient", "OllamaClient",
    "create_ai_client",
]
