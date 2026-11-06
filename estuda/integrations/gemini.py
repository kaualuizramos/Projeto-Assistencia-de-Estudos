"""Cliente Gemini API, compatível com o contrato AIClient."""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request

from .ai import AIUnavailable, COMPLEX_TASK_SUFFIX, SYSTEM_INSTRUCTION, _parse_and_validate_suggestions


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
