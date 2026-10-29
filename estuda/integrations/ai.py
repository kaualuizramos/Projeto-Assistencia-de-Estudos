"""Integração isolada com o endpoint Responses API da OpenAI."""

from __future__ import annotations

import json
import os
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

