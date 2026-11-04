"""Serviço do chat, contexto, mensagens, propostas e limites diários."""

from __future__ import annotations

import logging
import re

from estuda.authentication import AuthenticationService
from estuda.database import Database
from estuda.integrations.ai import AIClient, AIUnavailable, OpenAIResponsesClient
from estuda.tasks import TasksService

logger = logging.getLogger(__name__)


class ChatError(ValueError):
    pass


class AIChatService:
    def __init__(self, database: Database, client: AIClient | OpenAIResponsesClient,
                 auth: AuthenticationService, tasks: TasksService):
        self.database, self.client, self.auth, self.tasks = database, client, auth, tasks

    def create_conversation(self, user_id: int, title: str = "Nova conversa") -> int:
        with self.database.connection() as db:
            return db.execute("INSERT INTO conversations(user_id,title) VALUES(?,?)", (user_id, title[:100])).lastrowid

    def list_conversations(self, user_id: int) -> list[dict]:
        with self.database.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM conversations WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()]

    def messages(self, user_id: int, conversation_id: int) -> list[dict]:
        with self.database.connection() as db:
            self._owned_conversation(db, user_id, conversation_id)
            return [dict(row) for row in db.execute("SELECT * FROM messages WHERE user_id=? AND conversation_id=? ORDER BY id", (user_id, conversation_id)).fetchall()]

    @staticmethod
    def _owned_conversation(db, user_id, conversation_id):
        if not db.execute("SELECT 1 FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id)).fetchone():
            raise ChatError("Conversa não encontrada.")

    @staticmethod
    def _sanitize(text: str, user: dict) -> str:
        text = text[:8000]
        email = user.get("email")
        name = user.get("name")
        if email:
            text = re.sub(re.escape(email), "[e-mail removido]", text, flags=re.IGNORECASE)
        if name and len(name.strip()) >= 2:
            text = re.sub(re.escape(name.strip()), "[nome removido]", text, flags=re.IGNORECASE)
        text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[e-mail removido]", text)
        text = re.sub(r"(?i)(senha|password|passcode|token|api[_ -]?key|chave)\s*(?::|=|é|is)\s*[^,.!?;\n]+", r"\1: [credencial removida]", text)
        return text

    def send(self, user: dict, conversation_id: int, content: str, complex_task: bool = False) -> dict:
        content = content.strip()
        if not content or len(content) > 8000:
            raise ChatError("A mensagem precisa ter entre 1 e 8000 caracteres.")
        settings = self.auth.get_settings()
        if not settings["ai_enabled"]:
            raise ChatError("O assistente de IA está desativado pelo administrador.")
        complex_task = complex_task or self._looks_complex(content)
        with self.database.connection() as db:
            self._owned_conversation(db, user["id"], conversation_id)
            count = db.execute("SELECT COUNT(*) FROM messages WHERE user_id=? AND role='assistant' AND status='Sent' AND date(sent_at)=date('now')", (user["id"],)).fetchone()[0]
            if count >= settings["daily_message_limit"]:
                raise ChatError("Você atingiu o limite diário de mensagens do assistente.")
            cursor = db.execute("INSERT INTO messages(user_id,conversation_id,role,content,status) VALUES(?,?,'user',?,'Pending')",
                                (user["id"], conversation_id, content))
            message_id = cursor.lastrowid
            rows = db.execute("SELECT role,content FROM messages WHERE user_id=? AND conversation_id=? AND status IN ('Sent','Pending') ORDER BY id DESC LIMIT 20",
                              (user["id"], conversation_id)).fetchall()
        context = [{"role": row["role"], "content": self._sanitize(row["content"], user)} for row in reversed(rows)]
        try:
            answer = self.client.respond(context, complex_task=complex_task)
            response = answer["response"].strip()
            suggestions = answer["subtasks"] if complex_task else []
            if (not response or len(suggestions) > 5
                    or any(not isinstance(item, str) or not item.strip() or len(item.strip()) > 120 for item in suggestions)):
                raise AIUnavailable("O serviço de IA retornou uma resposta fora do formato esperado.")
        except Exception as exc:
            with self.database.connection() as db:
                db.execute("UPDATE messages SET status='Failed' WHERE id=? AND user_id=?", (message_id, user["id"]))
            logger.warning("Falha ao chamar IA (user_id=%s conversation_id=%s error=%s)", user["id"], conversation_id, type(exc).__name__)
            if isinstance(exc, AIUnavailable):
                raise
            raise AIUnavailable("O serviço de IA está temporariamente indisponível.") from exc
        with self.database.connection() as db:
            db.execute("UPDATE messages SET status='Sent' WHERE id=? AND user_id=?", (message_id, user["id"]))
            db.execute("INSERT INTO messages(user_id,conversation_id,role,content,status) VALUES(?,?,'assistant',?,'Sent')",
                       (user["id"], conversation_id, response))
            for title in suggestions:
                db.execute("INSERT INTO suggestions(user_id,conversation_id,title) VALUES(?,?,?)",
                           (user["id"], conversation_id, title.strip()))
        return {"response": response, "subtasks": suggestions, "message_id": message_id}

    @staticmethod
    def _looks_complex(content: str) -> bool:
        text = content.casefold()
        cues = ("dividir", "complexo", "complexa", "trabalho", "projeto", "apresentação", "relatório", "etapas", "planejar")
        return any(cue in text for cue in cues)

    def resend(self, user: dict, message_id: int, complex_task: bool = False) -> dict:
        with self.database.connection() as db:
            row = db.execute("SELECT conversation_id,content FROM messages WHERE id=? AND user_id=? AND role='user' AND status='Failed'", (message_id, user["id"])).fetchone()
            if not row:
                raise ChatError("Mensagem com falha não encontrada.")
            db.execute("UPDATE messages SET status='Pending' WHERE id=?", (message_id,))
            conversation_id, original_content = row["conversation_id"], row["content"]
        # Preserve the original record and append no duplicate user message on retry.
        settings = self.auth.get_settings()
        if not settings["ai_enabled"]:
            with self.database.connection() as db:
                db.execute("UPDATE messages SET status='Failed' WHERE id=?", (message_id,))
            raise ChatError("O assistente de IA está desativado pelo administrador.")
        if not self.client.available:
            with self.database.connection() as db:
                db.execute("UPDATE messages SET status='Failed' WHERE id=?", (message_id,))
            if self.client.__class__.__name__ == "GeminiClient":
                raise AIUnavailable("Assistente indisponível: configure GEMINI_API_KEY no ambiente.")
            if self.client.__class__.__name__ == "OllamaClient":
                raise AIUnavailable("Assistente indisponível: configure OLLAMA_HOST no ambiente.")
            raise AIUnavailable("Assistente indisponível: configure OPENAI_API_KEY no ambiente.")
        with self.database.connection() as db:
            self._owned_conversation(db, user["id"], conversation_id)
            rows = db.execute("SELECT role,content FROM messages WHERE user_id=? AND conversation_id=? AND status IN ('Sent','Pending') ORDER BY id DESC LIMIT 20", (user["id"], conversation_id)).fetchall()
            count = db.execute("SELECT COUNT(*) FROM messages WHERE user_id=? AND role='assistant' AND status='Sent' AND date(sent_at)=date('now')", (user["id"],)).fetchone()[0]
        if count >= settings["daily_message_limit"]:
            with self.database.connection() as db:
                db.execute("UPDATE messages SET status='Failed' WHERE id=?", (message_id,))
            raise ChatError("Você atingiu o limite diário de mensagens do assistente.")
        context = [{"role": row["role"], "content": self._sanitize(row["content"], user)} for row in reversed(rows)]
        try:
            result = self.client.respond(context, complex_task=complex_task or self._looks_complex(original_content))
            response = result.get("response") if isinstance(result, dict) else None
            suggestions = result.get("subtasks") if isinstance(result, dict) else None
            if (not isinstance(response, str) or not response.strip()
                    or not isinstance(suggestions, list) or len(suggestions) > 5
                    or any(not isinstance(item, str) or not item.strip() or len(item.strip()) > 120
                           for item in suggestions)):
                raise AIUnavailable("O serviço de IA retornou uma resposta fora do formato esperado.")
        except Exception as exc:
            with self.database.connection() as db:
                db.execute("UPDATE messages SET status='Failed' WHERE id=?", (message_id,))
            logger.warning("Reenvio à IA falhou (user_id=%s error=%s)", user["id"], type(exc).__name__)
            if isinstance(exc, (AIUnavailable, ChatError)):
                raise
            raise AIUnavailable("O serviço de IA está temporariamente indisponível.") from exc
        with self.database.connection() as db:
            db.execute("UPDATE messages SET status='Sent' WHERE id=?", (message_id,))
            db.execute("INSERT INTO messages(user_id,conversation_id,role,content,status) VALUES(?,?,'assistant',?,'Sent')",
                       (user["id"], conversation_id, response.strip()))
            for title in suggestions:
                if isinstance(title, str) and title.strip() and len(title.strip()) <= 120:
                    db.execute("INSERT INTO suggestions(user_id,conversation_id,title) VALUES(?,?,?)", (user["id"], conversation_id, title.strip()))
        return {"response": response.strip(), "subtasks": suggestions, "message_id": message_id}

    def list_suggestions(self, user_id: int, conversation_id: int) -> list[dict]:
        with self.database.connection() as db:
            self._owned_conversation(db, user_id, conversation_id)
            return [dict(row) for row in db.execute("SELECT * FROM suggestions WHERE user_id=? AND conversation_id=? AND status='Proposed' ORDER BY id", (user_id, conversation_id)).fetchall()]

    def accept_suggestion(self, user_id: int, suggestion_id: int, task_id: int, edited_title: str | None = None) -> None:
        with self.database.connection() as db:
            suggestion = db.execute("SELECT * FROM suggestions WHERE id=? AND user_id=? AND status='Proposed'", (suggestion_id, user_id)).fetchone()
            if not suggestion:
                raise ChatError("Proposta não encontrada ou já resolvida.")
        title = (edited_title or suggestion["title"]).strip()
        self.tasks.add_subtask(user_id, task_id, title)
        with self.database.connection() as db:
            db.execute("UPDATE suggestions SET task_id=?,status='Accepted' WHERE id=? AND user_id=? AND status='Proposed'", (task_id, suggestion_id, user_id))

    def reject_suggestion(self, user_id: int, suggestion_id: int) -> None:
        with self.database.connection() as db:
            cursor = db.execute("UPDATE suggestions SET status='Rejected' WHERE id=? AND user_id=? AND status='Proposed'", (suggestion_id, user_id))
            if cursor.rowcount != 1:
                raise ChatError("Proposta não encontrada ou já resolvida.")
