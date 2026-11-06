"""Testes automatizados dos fluxos principais da interface Qt sem rede ou banco local."""

from __future__ import annotations

import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from estuda.ai_chat import AIUnavailable
from estuda.authentication import AuthenticationService
from estuda.database import Database
from estuda.ui import StudyWindow


class FakeAI:
    available = True

    def __init__(self, *responses):
        self.responses = list(responses) or [{"response": "Vamos começar por uma ideia simples.", "subtasks": []}]
        self.calls = []

    def respond(self, messages, complex_task=False):
        self.calls.append((messages, complex_task))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class StudyWindowChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.database = Database(":memory:")
        self.database.initialize()
        auth = AuthenticationService(self.database)
        auth.register("Estudante de teste", "ui@example.test", "senha-de-teste-segura")
        self.user = auth.login("ui@example.test", "senha-de-teste-segura")
        self.ai = FakeAI()
        self.ai_factory = patch("estuda.ui.create_ai_client", return_value=self.ai)
        self.ai_factory.start()
        self.window = StudyWindow(self.database)
        self.window.user = self.user
        self.window.show_main()
        self.window._set_page(3)
        self.window.show()
        self.application.processEvents()

    def tearDown(self):
        self.window.timer.stop()
        self.window.idle_timer.stop()
        self.window.close()
        self.window.deleteLater()
        self.application.processEvents()
        self.database.close()
        self.ai_factory.stop()

    def _wait_for_chat(self):
        deadline = time.monotonic() + 5
        while self.window.chat_workers and time.monotonic() < deadline:
            QCoreApplication.processEvents()
            time.sleep(0.01)
        QCoreApplication.processEvents()
        self.assertFalse(self.window.chat_workers, "A solicitação do chat não terminou no tempo esperado.")

    def test_chat_screen_has_conversation_and_easy_start_controls(self):
        self.assertEqual(self.window.page_heading.text(), "Assistente")
        self.assertEqual(self.window.conversation_box.count(), 1)
        self.assertTrue(self.window.chat_connection.isVisible())
        self.assertIn("configurada", self.window.chat_connection.text())

        prompt = "Explique de forma simples este assunto: "
        self.window._use_chat_prompt(prompt)
        self.assertEqual(self.window.chat_entry.text(), prompt)

    def test_send_message_displays_response_and_structured_proposals(self):
        self.ai.responses = [{
            "response": "Divida o trabalho em pequenas etapas e comece pelo tema.",
            "subtasks": ["Escolher o tema", "Pesquisar fontes"],
        }]
        self.window.chat_entry.setText("Ajude-me a dividir este trabalho em etapas")
        self.window._send_chat()
        self._wait_for_chat()

        messages = self.window.chat.messages(self.user["id"], self.window.active_conversation_id)
        self.assertEqual([row["role"] for row in messages], ["user", "assistant"])
        self.assertIn("pequenas etapas", self.window.chat_log.toPlainText())
        self.assertTrue(self.window.proposals_card.isVisible())
        self.assertEqual(self.window.suggestion_table.rowCount(), 2)
        self.assertTrue(self.ai.calls[0][1])

    def test_failed_message_can_be_resent_without_duplicate(self):
        self.ai.responses = [
            AIUnavailable("O provedor está temporariamente indisponível."),
            {"response": "Tente estudar em blocos de 25 minutos.", "subtasks": []},
        ]
        self.window.chat_entry.setText("Como começo a estudar matemática?")
        self.window._send_chat()
        self._wait_for_chat()

        self.assertEqual(self.window.failed_messages.count(), 1)
        self.assertTrue(self.window.retry_card.isVisible())
        self.assertIn("salva para reenvio", self.window.chat_status.text())

        self.window._resend_failed()
        self._wait_for_chat()
        messages = self.window.chat.messages(self.user["id"], self.window.active_conversation_id)
        self.assertEqual([row["role"] for row in messages], ["user", "assistant"])
        self.assertEqual(messages[0]["status"], "Sent")
        self.assertIn("25 minutos", self.window.chat_log.toPlainText())

    def test_rejected_message_is_restored_to_input(self):
        with self.database.connection() as db:
            db.execute("UPDATE app_settings SET ai_enabled=0 WHERE id=1")
        self.window.chat_entry.setText("Texto que quero preservar")

        self.window._send_chat()
        self._wait_for_chat()

        self.assertEqual(self.window.chat_entry.text(), "Texto que quero preservar")
        self.assertEqual(self.window.chat.messages(self.user["id"], self.window.active_conversation_id), [])
        self.assertIn("desativado", self.window.chat_status.text())

    def test_empty_message_is_ignored_and_8000_characters_are_accepted(self):
        self.window.chat_entry.setText("   ")
        self.window._send_chat()
        self.assertFalse(self.window.chat_workers)
        self.assertEqual(self.ai.calls, [])

        boundary_message = "x" * 8000
        self.window.chat_entry.setText(boundary_message)
        self.window._send_chat()
        self._wait_for_chat()

        rows = self.window.chat.messages(self.user["id"], self.window.active_conversation_id)
        self.assertEqual(rows[0]["content"], boundary_message)
        self.assertEqual(len(self.ai.calls), 1)

    def test_message_over_8000_characters_is_restored_and_not_sent(self):
        oversized_message = "x" * 8001
        self.window.chat_entry.setText(oversized_message)

        self.window._send_chat()
        self._wait_for_chat()

        self.assertEqual(self.window.chat_entry.text(), oversized_message)
        self.assertEqual(self.window.chat.messages(self.user["id"], self.window.active_conversation_id), [])
        self.assertEqual(self.ai.calls, [])
        self.assertIn("8000", self.window.chat_status.text())

    def test_daily_limit_rejection_preserves_message(self):
        with self.database.connection() as db:
            db.execute("UPDATE app_settings SET daily_message_limit=1 WHERE id=1")
            db.execute(
                "INSERT INTO messages(user_id,conversation_id,role,content,status) VALUES(?,?,'assistant','resposta anterior','Sent')",
                (self.user["id"], self.window.active_conversation_id),
            )
        self.window.chat_entry.setText("Mais uma pergunta")

        self.window._send_chat()
        self._wait_for_chat()

        rows = self.window.chat.messages(self.user["id"], self.window.active_conversation_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.window.chat_entry.text(), "Mais uma pergunta")
        self.assertIn("limite diário", self.window.chat_status.text())
        self.assertEqual(self.ai.calls, [])

    def test_unexpected_ai_error_is_kept_as_failed_message(self):
        self.ai.responses = [RuntimeError("erro interno simulado")]
        self.window.chat_entry.setText("Me ajude a revisar esta matéria")

        self.window._send_chat()
        self._wait_for_chat()

        rows = self.window.chat.messages(self.user["id"], self.window.active_conversation_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "Failed")
        self.assertTrue(self.window.retry_card.isVisible())
        self.assertIn("temporariamente indisponível", self.window.chat_status.text())


if __name__ == "__main__":
    unittest.main()
