"""Integração isolada com provedores de IA (Gemini, OpenAI e Ollama)."""

from __future__ import annotations

import json
import logging
import os
import random
import time
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


class OpenAIResponsesClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: int = 35):
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("ESTUDA_AI_MODEL", "gpt-4o-mini")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key.strip())

    def respond(self, messages: list[dict[str, str]], complex_task: bool = False) -> dict:
        if not self.available:
            raise AIUnavailable("Assistente indisponível: configure OPENAI_API_KEY no ambiente.")
        payload: dict = {
            "model": self.model,
            "store": False,
            "instructions": SYSTEM_INSTRUCTION + (COMPLEX_TASK_SUFFIX if complex_task else ""),
            "input": messages[-20:],
        }
        if complex_task:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "study_suggestions",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "response": {"type": "string"},
                            "subtasks": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                        },
                        "required": ["response", "subtasks"],
                        "additionalProperties": False,
                    },
                }
            }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise AIUnavailable("O serviço de IA está temporariamente indisponível.") from exc
        output_text = self._extract_text(body)
        if not output_text.strip():
            raise AIUnavailable("O serviço de IA retornou uma resposta vazia.")
        if not complex_task:
            return {"response": output_text, "subtasks": []}
        return _parse_and_validate_suggestions(output_text)

    @staticmethod
    def _extract_text(body: dict) -> str:
        if isinstance(body.get("output_text"), str):
            return body["output_text"]
        parts = []
        for item in body.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    parts.append(content["text"])
        return "\n".join(parts)


class GeminiClient:
    """Cliente REST da Gemini API, sem dependência adicional."""

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: int = 35):
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("ESTUDA_AI_MODEL", "gemini-3.8-flash")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key.strip())

    def respond(self, messages: list[dict[str, str]], complex_task: bool = False) -> dict:
        if not self.available:
            raise AIUnavailable("Assistente indisponível: configure GEMINI_API_KEY no ambiente.")

        contents = []
        for message in messages[-20:]:
            role = "model" if message.get("role") == "assistant" else "user"
            content = message.get("content", "")
            if isinstance(content, str) and content.strip():
                contents.append({"role": role, "parts": [{"text": content}]})

        generation_config: dict = {"temperature": 0.7}
        system_instruction = SYSTEM_INSTRUCTION
        if complex_task:
            system_instruction += COMPLEX_TASK_SUFFIX
            generation_config.update({
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "response": {"type": "STRING"},
                        "subtasks": {"type": "ARRAY", "items": {"type": "STRING"}},
                    },
                    "required": ["response", "subtasks"],
                },
            })

        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": generation_config,
        }
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        body_text = ""
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body_text = response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                if exc.code == 503 and attempt < 2:
                    time.sleep((2 ** attempt) + random.uniform(0, 0.25))
                    continue
                hints = {
                    400: "Confira se GEMINI_API_KEY é uma chave da Gemini API e se o modelo está correto.",
                    401: "A chave Gemini foi recusada. Gere outra no Google AI Studio e atualize a configuração.",
                    403: "A conta ou a chave não tem acesso a este modelo/serviço.",
                    404: "Modelo não encontrado. Remova ESTUDA_AI_MODEL para usar o modelo padrão.",
                    429: "Limite gratuito ou cota da Gemini API atingido. Confira o uso no Google AI Studio.",
                    503: "A Gemini está temporariamente sobrecarregada. Tente novamente daqui a pouco.",
                }
                hint = hints.get(exc.code, "Verifique a conexão e a configuração da Gemini API.")
                raise AIUnavailable(f"Gemini API respondeu HTTP {exc.code}. {hint}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt < 2:
                    time.sleep((2 ** attempt) + random.uniform(0, 0.25))
                    continue
                raise AIUnavailable("O serviço de IA está temporariamente indisponível.") from exc
            try:
                body = json.loads(body_text)
            except ValueError as exc:
                raise AIUnavailable("O serviço de IA retornou uma resposta inválida.") from exc
            break

        try:
            parts = body["candidates"][0]["content"]["parts"]
            output_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        except (KeyError, IndexError, TypeError) as exc:
            raise AIUnavailable("O serviço de IA retornou uma resposta inválida.") from exc
        if not output_text.strip():
            raise AIUnavailable("O serviço de IA retornou uma resposta vazia.")
        if not complex_task:
            return {"response": output_text.strip(), "subtasks": []}
        return _parse_and_validate_suggestions(output_text)


class OllamaClient:
    """Cliente REST para o Ollama local (/api/chat), sem dependências adicionais."""

    def __init__(self, host: str | None = None, model: str | None = None, timeout: int = 60):
        raw_host = host if host is not None else os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.host = raw_host.strip()
        if self.host and not self.host.startswith(("http://", "https://")):
            self.host = f"http://{self.host}"
        self.model = model or os.getenv("ESTUDA_AI_MODEL", "llama3.2")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.host.strip())

    def respond(self, messages: list[dict[str, str]], complex_task: bool = False) -> dict:
        if not self.available:
            raise AIUnavailable("Assistente indisponível: configure OLLAMA_HOST no ambiente.")

        system_instruction = SYSTEM_INSTRUCTION
        if complex_task:
            system_instruction += COMPLEX_TASK_SUFFIX + (
                ' Responda estritamente em formato JSON contendo as chaves "response" (texto explicativo) '
                'e "subtasks" (lista com no máximo 5 subtarefas curtas).'
            )

        payload_messages = [{"role": "system", "content": system_instruction}]
        for msg in messages[-20:]:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                payload_messages.append({"role": role, "content": content})

        payload: dict = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,
            "options": {"temperature": 0.7},
        }
        if complex_task:
            payload["format"] = "json"

        endpoint = f"{self.host.rstrip('/')}/api/chat"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise AIUnavailable(f"Modelo '{self.model}' não encontrado no Ollama. Execute 'ollama pull {self.model}'.") from exc
            raise AIUnavailable(f"Ollama respondeu HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise AIUnavailable(f"Não foi possível conectar ao Ollama em {self.host}. Verifique se o serviço está ativo.") from exc

        try:
            output_text = body.get("message", {}).get("content", "")
        except (AttributeError, TypeError) as exc:
            raise AIUnavailable("O serviço de IA retornou uma resposta inválida.") from exc

        if not isinstance(output_text, str) or not output_text.strip():
            raise AIUnavailable("O serviço de IA retornou uma resposta vazia.")

        if not complex_task:
            return {"response": output_text.strip(), "subtasks": []}
        return _parse_and_validate_suggestions(output_text)


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
        client = OllamaClient()
    elif provider == "openai":
        client = OpenAIResponsesClient()
    elif provider == "gemini":
        client = GeminiClient()
    elif not provider:
        # Sem provedor explícito: verifica chaves de API ou auto-detecta Ollama ativo
        if gemini_key:
            client = GeminiClient()
        elif openai_key:
            client = OpenAIResponsesClient()
        elif os.getenv("OLLAMA_HOST") or _is_ollama_online():
            client = OllamaClient()
        else:
            client = GeminiClient()
    else:
        raise ValueError("ESTUDA_AI_PROVIDER deve ser 'gemini', 'openai' ou 'ollama'.")

    logger.info("Cliente de IA selecionado: %s (modelo=%s)", client.__class__.__name__, getattr(client, "model", "padrão"))
    return client
