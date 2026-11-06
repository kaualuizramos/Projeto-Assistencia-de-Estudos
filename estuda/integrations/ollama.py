"""Cliente REST do Ollama local, compatível com o contrato AIClient."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .ai import AIUnavailable, COMPLEX_TASK_SUFFIX, SYSTEM_INSTRUCTION, _parse_and_validate_suggestions


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
