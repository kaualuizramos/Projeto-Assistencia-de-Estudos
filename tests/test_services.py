"""Testes de regras de negócio sem GUI, rede ou uso do banco pessoal local."""

import hashlib
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from estuda.ai_chat import AIChatService, ChatError
from estuda.authentication import AuthenticationError, AuthenticationService
from estuda.database import Database
from estuda.focus_sessions import FocusError, FocusSessionsService
from estuda.integrations.ai import (
    AIUnavailable,
    GeminiClient,
    OllamaClient,
    OpenAIResponsesClient,
    create_ai_client,
)
from estuda.notifications import NotificationsService
from estuda.tasks import TaskError, TasksService


def future(hours=24):
    return datetime.now(timezone.utc) + timedelta(hours=hours)


class FakeAI:
    def __init__(self, answer=None, error=None):
        self.answer = answer or {"response": "Vamos dividir em etapas.", "subtasks": []}
        self.error = error
        self.calls = []
        self.available = True

    def respond(self, messages, complex_task=False):
        self.calls.append((messages, complex_task))
        if self.error:
            raise self.error
        return self.answer


class FakeMailer:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    def send(self, recipient, subject, body):
        if self.fail:
            raise OSError("simulated SMTP failure")
        self.sent.append((recipient, subject, body))


class ServiceCase(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.db.initialize()
        self.auth = AuthenticationService(self.db)
        self.tasks = TasksService(self.db)
        self.focus = FocusSessionsService(self.db)
        self.notifications = NotificationsService(self.db)
        self.user_id = self.auth.register("Maria estudante", "maria@example.test", "senha-super-segura")
        self.user = self.auth.login("maria@example.test", "senha-super-segura")

    def test_registration_login_and_scrypt_storage(self):
        with self.db.connection() as db:
            row = db.execute("SELECT password_algorithm,password_hash FROM users WHERE id=?", (self.user_id,)).fetchone()
            self.assertEqual(row["password_algorithm"], "scrypt")
            self.assertNotEqual(row["password_hash"], b"senha-super-segura")
        with self.assertRaises(AuthenticationError):
            self.auth.register("Outro", "MARIA@example.test", "outra-senha")
        with self.assertRaises(AuthenticationError) as error:
            self.auth.login("unknown@example.test", "senha-incorreta")
        self.assertEqual(str(error.exception), "E-mail ou senha inválidos.")

    def test_auth_rate_limit_and_reset_token_is_single_use(self):
        for _ in range(5):
            with self.assertRaises(AuthenticationError):
                self.auth.login("nobody@example.test", "wrong")
        with self.db.connection() as db:
            attempts = db.execute("SELECT attempts,locked_until FROM login_attempts WHERE email=?", ("nobody@example.test",)).fetchone()
        self.assertEqual(attempts["attempts"], 5)
        self.assertIsNotNone(attempts["locked_until"])
        token = self.auth.create_password_reset("maria@example.test")
        self.assertTrue(token)
        self.auth.reset_password(token, "nova-senha-valida")
        self.assertEqual(self.auth.login("maria@example.test", "nova-senha-valida")["id"], self.user_id)
        with self.assertRaises(AuthenticationError):
            self.auth.reset_password(token, "outra-senha-valida")

    def test_account_deletion_requires_confirmation_and_cascades_private_data(self):
        task_id = self.tasks.create_task(self.user_id, "Apagar no fim", future())
        subtask_id = self.tasks.add_subtask(self.user_id, task_id, "Uma etapa")
        conversation_id = self.chat_conversation()
        with self.db.connection() as db:
            db.execute("INSERT INTO messages(user_id,conversation_id,role,content) VALUES(?,?,?,?)", (self.user_id, conversation_id, "user", "texto"))
            db.execute("INSERT INTO suggestions(user_id,conversation_id,task_id,title) VALUES(?,?,?,?)", (self.user_id, conversation_id, task_id, "Proposta"))
        self.notifications.add(self.user_id, "Aviso")
        with self.assertRaises(AuthenticationError):
            self.auth.delete_account(self.user_id, confirmed=False)
        self.auth.delete_account(self.user_id, confirmed=True)
        with self.db.connection() as db:
            for table in ("users", "tasks", "subtasks", "conversations", "messages", "suggestions", "notifications", "reminders", "focus_sessions", "password_resets"):
                self.assertEqual(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0, table)

    def test_task_validation_crud_subtasks_and_completion(self):
        due = future()
        task_id = self.tasks.create_task(self.user_id, "Revisar química", due, description="Capítulo 3")
        with self.assertRaises(TaskError):
            self.tasks.create_task(self.user_id, "  ", due)
        with self.assertRaises(TaskError):
            self.tasks.create_task(self.user_id, "x" * 121, due)
        with self.assertRaises(TaskError):
            self.tasks.create_task(self.user_id, "Prazo antigo", datetime.now(timezone.utc) - timedelta(seconds=1))
        self.edit_task_id = task_id
        self.tasks.edit_task(self.user_id, task_id, "Química orgânica", future(), "Alta", "Resumo")
        subtask_id = self.tasks.add_subtask(self.user_id, task_id, "Ler as anotações")
        with self.assertRaisesRegex(TaskError, "1 subtarefa"):
            self.tasks.set_completed(self.user_id, task_id, True)
        self.assertTrue(self.tasks.set_subtask_done(self.user_id, subtask_id, True))
        self.tasks.set_completed(self.user_id, task_id, True)
        completed = self.tasks.get_task(self.user_id, task_id)
        self.assertEqual(completed["status"], "Concluída")
        self.assertIsNotNone(completed["completed_at"])
        self.tasks.set_completed(self.user_id, task_id, False)
        reopened = self.tasks.get_task(self.user_id, task_id)
        self.assertEqual(reopened["status"], "Pendente")
        self.assertIsNone(reopened["completed_at"])
        self.assertEqual(self.tasks.list_tasks(self.user_id, priority="Alta")[0]["title"], "Química orgânica")

    def test_ownership_is_enforced_and_task_delete_preserves_focus_history(self):
        other_id = self.auth.register("Outro estudante", "outro@example.test", "senha-super-segura")
        task_id = self.tasks.create_task(self.user_id, "Minha tarefa", future())
        with self.assertRaises(TaskError):
            self.tasks.get_task(other_id, task_id)
        self.focus.start(self.user_id, task_id)
        with self.assertRaisesRegex(TaskError, "sessão de foco estiver ativa"):
            self.tasks.delete_task(self.user_id, task_id)
        self.focus.terminate(self.user_id)
        self.tasks.delete_task(self.user_id, task_id)
        history = self.focus.history(self.user_id, "Todo o período")
        self.assertEqual(len(history), 1)
        self.assertIsNone(history[0]["task_id"])
        with self.assertRaises(FocusError):
            self.focus.start(other_id, task_id)

    def test_overdue_deadline_filter(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        with self.db.connection() as db:
            db.execute("INSERT INTO tasks(user_id,title,deadline,status) VALUES(?,?,?,'Pendente')", (self.user_id, "Vencida", past.isoformat()))
        overdue = self.tasks.list_tasks(self.user_id, status="Atrasada")
        self.assertEqual([row["title"] for row in overdue], ["Vencida"])

    def test_focus_pause_resume_completion_and_history_metrics(self):
        task_id = self.tasks.create_task(self.user_id, "Sessão de teste", future())
        session_id = self.focus.start(self.user_id, task_id, 1)
        with self.assertRaises(FocusError):
            self.focus.start(self.user_id, task_id, 25)
        self.focus.pause(self.user_id)
        with self.db.connection() as db:
            db.execute("UPDATE focus_sessions SET paused_at=? WHERE id=?", ((datetime.now(timezone.utc)-timedelta(seconds=4)).isoformat(), session_id))
        self.focus.resume(self.user_id)
        active = self.focus.active(self.user_id)
        self.assertGreaterEqual(active["paused_seconds"], 3)
        with self.db.connection() as db:
            db.execute("UPDATE focus_sessions SET started_at=? WHERE id=?", ((datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat(), session_id))
        completed = self.focus.tick(self.user_id)
        self.assertEqual(completed["status"], "Completed")
        self.assertEqual(self.notifications.list_notifications(self.user_id)[0]["kind"], "Focus")
        self.assertEqual(self.focus.metrics(self.user_id, "Todo o período")["completed_sessions"], 1)

    def test_reminder_validation_delivery_and_three_retries(self):
        task_id = self.tasks.create_task(self.user_id, "Trabalho", future(48))
        due = datetime.now(timezone.utc) + timedelta(minutes=1)
        reminder_id = self.tasks.add_reminder(self.user_id, task_id, due, email_enabled=True)
        with self.assertRaises(TaskError):
            self.tasks.add_reminder(self.user_id, task_id, due, now=due)
        mailer = FakeMailer(fail=True)
        current = due + timedelta(seconds=1)
        for attempt in range(4):
            self.tasks.process_due_reminders(mailer, current)
            current += timedelta(minutes=5, seconds=1)
        with self.db.connection() as db:
            reminder = db.execute("SELECT * FROM reminders WHERE id=?", (reminder_id,)).fetchone()
        self.assertEqual(reminder["status"], "Sent")
        self.assertEqual(reminder["email_attempts"], 4)
        self.assertIsNone(reminder["retry_at"])
        notifications = self.notifications.list_notifications(self.user_id)
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["kind"], "Reminder")

    def test_chat_sanitizes_identity_limits_context_and_requires_acceptance(self):
        task_id = self.tasks.create_task(self.user_id, "Plano de estudos", future())
        with self.db.connection() as db:
            conversation_id = db.execute("INSERT INTO conversations(user_id,title) VALUES(?,?)", (self.user_id, "Teste")).lastrowid
            for index in range(25):
                db.execute("INSERT INTO messages(user_id,conversation_id,role,content) VALUES(?,?,?,?)",
                           (self.user_id, conversation_id, "user", f"mensagem {index} de Maria estudante maria@example.test senha: segredo"))
        fake = FakeAI({"response": "Aqui vai um plano.", "subtasks": ["Ler a teoria", "Resolver exercícios"]})
        service = AIChatService(self.db, fake, self.auth, self.tasks)
        result = service.send(self.user, conversation_id, "Me ajuda a dividir meu projeto", complex_task=False)
        context, complex_task = fake.calls[0]
        self.assertLessEqual(len(context), 20)
        self.assertTrue(complex_task)
        serialized = str(context)
        self.assertNotIn("Maria estudante", serialized)
        self.assertNotIn("maria@example.test", serialized)
        self.assertNotIn("segredo", serialized)
        self.assertEqual(result["subtasks"], ["Ler a teoria", "Resolver exercícios"])
        proposals = service.list_suggestions(self.user_id, conversation_id)
        service.accept_suggestion(self.user_id, proposals[0]["id"], task_id, "Ler o capítulo 1")
        service.reject_suggestion(self.user_id, proposals[1]["id"])
        subtasks = self.tasks.list_subtasks(self.user_id, task_id)
        self.assertEqual([item["title"] for item in subtasks], ["Ler o capítulo 1"])
        self.assertEqual(service.list_suggestions(self.user_id, conversation_id), [])

    def test_chat_failure_is_persisted_and_can_be_resent(self):
        conversation_id = self.chat_conversation()
        preserved_task = self.tasks.create_task(self.user_id, "Persistir mesmo sem IA", future())
        failing = FakeAI(error=AIUnavailable("Gemini API respondeu HTTP 503. Tente novamente."))
        service = AIChatService(self.db, failing, self.auth, self.tasks)
        with self.assertRaises(AIUnavailable):
            service.send(self.user, conversation_id, "Ajude a começar")
        rows = service.messages(self.user_id, conversation_id)
        self.assertEqual(rows[0]["status"], "Failed")
        self.assertEqual(self.tasks.get_task(self.user_id, preserved_task)["title"], "Persistir mesmo sem IA")
        with self.assertRaisesRegex(AIUnavailable, "HTTP 503"):
            service.resend(self.user, rows[0]["id"])
        self.assertEqual(service.messages(self.user_id, conversation_id)[0]["status"], "Failed")
        service.client = FakeAI()
        result = service.resend(self.user, rows[0]["id"])
        self.assertIn("response", result)
        self.assertEqual(service.messages(self.user_id, conversation_id)[0]["status"], "Sent")

    def test_admin_ai_toggle_and_daily_limit(self):
        with self.assertRaises(AuthenticationError):
            self.auth.update_ai_settings(self.user_id, False, 10)
        with self.db.connection() as db:
            db.execute("UPDATE users SET role='admin' WHERE id=?", (self.user_id,))
        self.auth.update_ai_settings(self.user_id, True, 1)
        conversation_id = self.chat_conversation()
        service = AIChatService(self.db, FakeAI(), self.auth, self.tasks)
        service.send(self.user, conversation_id, "Uma pergunta")
        with self.assertRaisesRegex(ChatError, "limite diário"):
            service.send(self.user, conversation_id, "Outra pergunta")
        self.auth.update_ai_settings(self.user_id, False, 1)
        with self.assertRaisesRegex(ChatError, "desativado"):
            service.send(self.user, conversation_id, "Outra pergunta")

    def chat_conversation(self):
        return self.chat_conversation_for(self.user_id)

    def chat_conversation_for(self, user_id):
        with self.db.connection() as db:
            return db.execute("INSERT INTO conversations(user_id) VALUES(?)", (user_id,)).lastrowid


class MigrationAndAdapterTests(unittest.TestCase):
    def test_legacy_database_migrates_idempotently_and_upgrades_password(self):
        db = Database(":memory:")
        with db.connection() as conn:
            conn.executescript("""
                CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,salt BLOB,password_hash BLOB);
                CREATE TABLE tasks(id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,description TEXT,deadline TEXT,priority TEXT,status TEXT);
                CREATE TABLE subtasks(id INTEGER PRIMARY KEY,task_id INTEGER,title TEXT,done INTEGER);
                CREATE TABLE messages(id INTEGER PRIMARY KEY,user_id INTEGER,role TEXT,content TEXT,sent_at TEXT);
            """)
            salt = b"1234567890123456"
            legacy_hash = hashlib.pbkdf2_hmac("sha256", b"legacy-password", salt, 240_000)
            conn.execute("INSERT INTO users(name,email,salt,password_hash) VALUES(?,?,?,?)", ("Legacy", "legacy@example.test", salt, legacy_hash))
            conn.execute("INSERT INTO tasks(user_id,title,description,deadline,priority,status) VALUES(1,'Tarefa antiga','','2030-01-01 12:00','Média','Pendente')")
            conn.execute("INSERT INTO messages(user_id,role,content) VALUES(1,'user','mensagem antiga')")
        db.initialize(); db.initialize()
        user = AuthenticationService(db).login("legacy@example.test", "legacy-password")
        self.assertEqual(user["id"], 1)
        with db.connection() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT password_algorithm FROM users WHERE id=1").fetchone()[0], "scrypt")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages WHERE conversation_id IS NOT NULL").fetchone()[0], 1)
            self.assertTrue(conn.execute("SELECT deadline FROM tasks").fetchone()[0].endswith("+00:00"))

    def test_openai_output_extraction_and_api_key_configuration(self):
        client = OpenAIResponsesClient(api_key="test-secret", model="test-model")
        self.assertTrue(client.available)
        self.assertEqual(client._extract_text({"output": [{"type": "message", "content": [{"type": "output_text", "text": "resposta"}]}]}), "resposta")
        self.assertFalse(OpenAIResponsesClient(api_key="").available)

    @patch("urllib.request.urlopen")
    def test_ollama_client_respond(self, mock_urlopen):
        client = OllamaClient(host="http://localhost:11434", model="llama3.2")
        self.assertTrue(client.available)
        self.assertEqual(client.host, "http://localhost:11434")

        # Resposta simples
        mock_ctx = MagicMock()
        mock_ctx.read.return_value = json.dumps({"message": {"content": "Olá estudante!"}}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_ctx
        result = client.respond([{"role": "user", "content": "Olá"}], complex_task=False)
        self.assertEqual(result, {"response": "Olá estudante!", "subtasks": []})

        # Resposta com tarefa complexa (JSON)
        mock_ctx.read.return_value = json.dumps({
            "message": {"content": json.dumps({"response": "Plano de estudo", "subtasks": ["Passo 1", "Passo 2"]})}
        }).encode("utf-8")
        result = client.respond([{"role": "user", "content": "Como estudar?"}], complex_task=True)
        self.assertEqual(result["response"], "Plano de estudo")
        self.assertEqual(result["subtasks"], ["Passo 1", "Passo 2"])

    def test_ollama_client_availability_and_host_format(self):
        client = OllamaClient(host="localhost:11434")
        self.assertTrue(client.available)
        self.assertEqual(client.host, "http://localhost:11434")

        empty_client = OllamaClient(host="")
        self.assertFalse(empty_client.available)
        with self.assertRaises(AIUnavailable):
            empty_client.respond([{"role": "user", "content": "teste"}])

    def test_create_ai_client_factory(self):
        with patch.dict(os.environ, {"ESTUDA_AI_PROVIDER": "ollama"}):
            client = create_ai_client()
            self.assertIsInstance(client, OllamaClient)

        with patch.dict(os.environ, {"ESTUDA_AI_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}):
            client = create_ai_client()
            self.assertIsInstance(client, OpenAIResponsesClient)

        with patch.dict(os.environ, {"ESTUDA_AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}):
            client = create_ai_client()
            self.assertIsInstance(client, GeminiClient)

        with patch.dict(os.environ, {"ESTUDA_AI_PROVIDER": "invalido"}):
            with self.assertRaises(ValueError):
                create_ai_client()


if __name__ == "__main__":
    unittest.main()
