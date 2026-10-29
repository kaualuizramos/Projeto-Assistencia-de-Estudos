"""Integração isolada com o endpoint Responses API da OpenAI."""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request


class AIUnavailable(RuntimeError):
    pass


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
            "instructions": (
                "Você é um assistente de estudos. Responda em português, de forma acolhedora, objetiva "
                "e educativa. Ajude o estudante a escolher próximos passos concretos."
            ),
            "input": messages[-20:],
        }
        if complex_task:
            payload["instructions"] += " Para a última solicitação, sugira no máximo cinco subtarefas curtas e concretas."
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
        try:
            result = json.loads(output_text)
        except ValueError as exc:
            raise AIUnavailable("O serviço de IA retornou uma resposta inválida.") from exc
        subtasks = result.get("subtasks") if isinstance(result, dict) else None
        response_text = result.get("response") if isinstance(result, dict) else None
        if (not isinstance(response_text, str) or not response_text.strip() or not isinstance(subtasks, list)
                or len(subtasks) > 5 or any(not isinstance(item, str) or not item.strip() or len(item.strip()) > 120 for item in subtasks)):
            raise AIUnavailable("O serviço de IA retornou uma resposta fora do formato esperado.")
        return {"response": response_text.strip(), "subtasks": [item.strip() for item in subtasks]}

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
        system_instruction = (
            "Você é um assistente de estudos. Responda em português, de forma acolhedora, objetiva "
            "e educativa. Ajude o estudante a escolher próximos passos concretos."
        )
        if complex_task:
            system_instruction += " Para a última solicitação, sugira no máximo cinco subtarefas curtas e concretas."
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
                # Informa status e próximo passo sem exibir o corpo da resposta nem a chave.
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
        try:
            result = json.loads(output_text)
        except ValueError as exc:
            raise AIUnavailable("O serviço de IA retornou uma resposta inválida.") from exc
        response_text = result.get("response") if isinstance(result, dict) else None
        subtasks = result.get("subtasks") if isinstance(result, dict) else None
        if (not isinstance(response_text, str) or not response_text.strip() or not isinstance(subtasks, list)
                or len(subtasks) > 5 or any(not isinstance(item, str) or not item.strip() or len(item.strip()) > 120 for item in subtasks)):
            raise AIUnavailable("O serviço de IA retornou uma resposta fora do formato esperado.")
        return {"response": response_text.strip(), "subtasks": [item.strip() for item in subtasks]}


def create_ai_client():
    """Escolhe Gemini por padrão; permite OpenAI quando selecionado e configurado."""
    provider = os.getenv("ESTUDA_AI_PROVIDER", "").strip().casefold()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    # A chave Gemini do protótipo prevalece sobre variáveis OpenAI antigas no ambiente.
    if gemini_key and not (provider == "openai" and openai_key):
        return GeminiClient()
    if not provider:
        provider = "gemini"
    if provider == "gemini":
        return GeminiClient()
    if provider == "openai":
        return OpenAIResponsesClient()
    raise ValueError("ESTUDA_AI_PROVIDER deve ser 'openai' ou 'gemini'.")

