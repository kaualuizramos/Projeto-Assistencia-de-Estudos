"""Interface desktop Estuda+ feita com Qt Widgets (PySide6)."""

from __future__ import annotations

import html
import logging
import queue
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from PySide6.QtCore import QDateTime, QEvent, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateTimeEdit, QDialog, QFormLayout,
    QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QSpinBox, QStackedWidget, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from estuda.ai_chat import AIChatService, ChatError
from estuda.authentication import AuthenticationError, AuthenticationService
from estuda.database import Database
from estuda.focus_sessions import FocusError, FocusSessionsService
from estuda.integrations.ai import AIUnavailable, create_ai_client
from estuda.integrations.email import SMTPMailer
from estuda.notifications import NotificationsService
from estuda.tasks import TaskError, TasksService

logger = logging.getLogger(__name__)

COLORS = {
    "canvas": "#F4F6F4", "surface": "#FFFFFF", "ink": "#172B27",
    "muted": "#71817C", "line": "#E3EAE6", "brand": "#2C766A",
    "brand_hover": "#236458", "sidebar": "#173D36", "sidebar_active": "#28574E",
    "mint": "#E4F2EC", "lime": "#C8E6A0", "red": "#B84B54",
}

APP_STYLE = """
QWidget { background: #F4F6F4; color: #172B27; font-family: 'Segoe UI'; font-size: 10pt; }
QLabel { background: transparent; }
QMainWindow { background: #F4F6F4; }
QLabel[role='title'] { font-size: 23pt; font-weight: 700; color: #172B27; }
QLabel[role='heading'] { font-size: 14pt; font-weight: 650; color: #172B27; }
QLabel[role='subtitle'] { color: #71817C; font-size: 10pt; }
QLabel[role='chatReady'] { color: #246B50; background: #E4F2EC; border-radius: 9px; padding: 8px 12px; font-weight: 650; }
QLabel[role='chatWarning'] { color: #805A19; background: #FFF4D9; border-radius: 9px; padding: 8px 12px; font-weight: 650; }
QLabel[role='chatError'] { color: #9D343C; background: #FFF0F0; border-radius: 9px; padding: 8px 12px; }
QLabel[role='metric'] { font-size: 23pt; font-weight: 700; color: #173D36; }
QLabel[role='eyebrow'] { color: #71817C; font-size: 9pt; font-weight: 650; letter-spacing: 1px; }
QLabel[role='whiteTitle'] { color: white; font-size: 16pt; font-weight: 700; }
QLabel[role='heroTitle'] { color: white; font-size: 28pt; font-weight: 750; }
QLabel[role='heroText'] { color: #D4E5DF; font-size: 11pt; }
QFrame#hero QLabel[role='eyebrow'], QFrame#sidebar QLabel[role='eyebrow'] { color: #C9D9D4; }
QFrame#card, QFrame#authCard { background: #FFFFFF; border: 1px solid #E3EAE6; border-radius: 16px; }
QFrame#sidebar { background: #173D36; border: none; }
QFrame#hero { background: #173D36; border-radius: 20px; }
QFrame#heroAccent { background: #28574E; border-radius: 16px; }
QFrame#topbar { background: #FFFFFF; border: none; border-bottom: 1px solid #E3EAE6; }
QLabel#brandMark { color: #173D36; background: #C8E6A0; border-radius: 14px; font-size: 18pt; font-weight: 800; }
QLabel#heroTitle { color: white; font-size: 28pt; font-weight: 750; }
QLabel#heroText { color: #D4E5DF; font-size: 11pt; }
QLabel#whiteTitle { color: white; font-size: 16pt; font-weight: 700; }
QPushButton { background: #FFFFFF; color: #29423B; border: 1px solid #D9E3DE; border-radius: 9px; padding: 9px 14px; font-weight: 600; }
QPushButton:hover { background: #F0F6F2; border-color: #AFC9BD; }
QPushButton:pressed { background: #E2EEE8; }
QPushButton[variant='primary'] { color: #FFFFFF; background: #2C766A; border: 1px solid #2C766A; }
QPushButton[variant='primary']:hover { background: #236458; }
QPushButton[variant='danger'] { color: #A53B45; background: #FFF5F5; border-color: #F2D8D9; }
QPushButton[variant='nav'] { color: #C9D9D4; background: transparent; border: none; text-align: left; padding: 11px 13px; font-size: 10.5pt; }
QPushButton[variant='nav']:hover { color: white; background: #214C43; }
QPushButton[variant='nav']:checked { color: white; background: #28574E; border-left: 3px solid #C8E6A0; }
QPushButton:disabled { color: #98A6A0; background: #E9EEEB; border-color: #E9EEEB; }
QLineEdit, QPlainTextEdit, QComboBox, QDateTimeEdit, QSpinBox {
  background: #FFFFFF; border: 1px solid #D9E3DE; border-radius: 9px; padding: 9px 11px; selection-background-color: #2C766A;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus, QSpinBox:focus { border: 1px solid #2C766A; }
QComboBox::drop-down { border: none; width: 26px; }
QTableWidget { background: #FFFFFF; border: 1px solid #E3EAE6; border-radius: 12px; gridline-color: #EEF2EF; selection-background-color: #E4F2EC; selection-color: #173D36; alternate-background-color: #FAFCFA; }
QHeaderView::section { color: #71817C; background: #F8FAF8; padding: 11px 9px; border: none; border-bottom: 1px solid #E3EAE6; font-size: 9pt; font-weight: 700; }
QTableWidget::item { padding: 7px; border: none; }
QProgressBar { background: #E4ECE7; border: none; border-radius: 7px; text-align: center; height: 14px; color: #173D36; }
QProgressBar::chunk { background: #72AA84; border-radius: 7px; }
QTabWidget::pane { background: #FFFFFF; border: 1px solid #E3EAE6; border-radius: 12px; top: -1px; }
QTabWidget QWidget { background: #FFFFFF; }
QTabBar::tab { background: #EDF2EE; color: #71817C; border: none; border-radius: 8px; padding: 10px 18px; margin: 3px; font-weight: 650; }
QTabBar::tab:selected { color: #FFFFFF; background: #2C766A; }
QCheckBox { spacing: 8px; }
QTextBrowser { background: #FFFFFF; border: none; border-radius: 12px; padding: 12px; }
QDialog { background: #F4F6F4; }
"""


class ResetLinkServer:
    """Callback local para receber o link de redefinição enquanto o app está aberto."""

    def __init__(self):
        self.tokens: queue.Queue[str] = queue.Queue()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                path = unquote(handler_self.path)
                token = path.removeprefix("/reset/").strip("/")
                if not token or token == path:
                    handler_self.send_error(404)
                    return
                self.tokens.put(token)
                body = b"<!doctype html><meta charset='utf-8'><p>Volte ao Estuda+ para criar sua nova senha.</p>"
                handler_self.send_response(200)
                handler_self.send_header("Content-Type", "text/html; charset=utf-8")
                handler_self.send_header("Content-Length", str(len(body)))
                handler_self.end_headers()
                handler_self.wfile.write(body)

            def log_message(self, _format, *_args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class ChatWorker(QThread):
    succeeded = Signal(object, int)
    failed = Signal(str, int, str, int, int)

    def __init__(self, service, user, conversation_id, content=None, complex_task=False,
                 message_id=None, previous_message_id=0):
        super().__init__()
        self.service, self.user = service, user
        self.conversation_id, self.content = conversation_id, content
        self.complex_task, self.message_id = complex_task, message_id
        self.previous_message_id = previous_message_id

    def run(self):
        try:
            if self.message_id is None:
                result = self.service.send(self.user, self.conversation_id, self.content, self.complex_task)
            else:
                result = self.service.resend(self.user, self.message_id, self.complex_task)
            self.succeeded.emit(result, self.conversation_id)
        except (ChatError, AIUnavailable) as exc:
            self.failed.emit(str(exc), self.conversation_id, self.content or "",
                             self.message_id or 0, self.previous_message_id)
        except Exception as exc:
            logger.exception("Falha inesperada no worker do chat (error=%s)", type(exc).__name__)
            self.failed.emit("O assistente está temporariamente indisponível.",
                             self.conversation_id, self.content or "", self.message_id or 0,
                             self.previous_message_id)


class StudyWindow(QMainWindow):
    SESSION_IDLE_SECONDS = 8 * 60 * 60

    def __init__(self, database: Database):
        super().__init__()
        self.database = database
        self.auth = AuthenticationService(database)
        self.tasks = TasksService(database)
        self.focus = FocusSessionsService(database)
        self.notifications = NotificationsService(database)
        self.ai_client = create_ai_client()
        self.mailer = SMTPMailer()
        self.chat = AIChatService(database, self.ai_client, self.auth, self.tasks)
        self.reset_server = ResetLinkServer()
        self.user = None
        self.last_activity = time.monotonic()
        self.active_conversation_id: int | None = None
        self.chat_workers: set[ChatWorker] = set()

        self.setWindowTitle("Estuda+ | Assistente de estudos")
        self.setMinimumSize(1120, 700)
        self.resize(1380, 900)
        self.setStyleSheet(APP_STYLE)
        self.show_auth()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_background)
        self.timer.start(1000)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._check_idle)
        self.idle_timer.start(30_000)
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress):
            self.last_activity = time.monotonic()
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        if any(worker.isRunning() for worker in self.chat_workers):
            QMessageBox.information(self, "Solicitação em andamento", "Aguarde a resposta do assistente antes de fechar o Estuda+.")
            event.ignore()
            return
        self.reset_server.close()
        super().closeEvent(event)

    @staticmethod
    def _label(text: str, role: str | None = None) -> QLabel:
        label = QLabel(text)
        if role:
            label.setProperty("role", role)
            label.style().unpolish(label)
            label.style().polish(label)
        return label

    @staticmethod
    def _card(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        if title:
            label = StudyWindow._label(title, "heading")
            layout.addWidget(label)
        return frame, layout

    @staticmethod
    def _button(text: str, callback=None, variant: str | None = None) -> QPushButton:
        button = QPushButton(text)
        if variant:
            button.setProperty("variant", variant)
        if callback:
            button.clicked.connect(callback)
        return button

    @staticmethod
    def _table(headers: list[str], widths: list[int] | None = None) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        if widths:
            for column, width in enumerate(widths):
                table.setColumnWidth(column, width)
        return table

    def show_auth(self):
        self.user = None
        page = QWidget()
        outer = QHBoxLayout(page)
        outer.setContentsMargins(36, 28, 36, 28)
        outer.setSpacing(24)

        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumWidth(360)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(38, 42, 38, 38)
        hero_layout.setSpacing(18)
        hero_layout.addWidget(self._label("✦   Estuda+", "whiteTitle"))
        hero_layout.addStretch(1)
        hero_layout.addWidget(self._label("Seu próximo\ngrande passo\ncomeça aqui.", "heroTitle"))
        hero_layout.addWidget(self._label("Organize tarefas, encontre foco e avance um pouco todos os dias.", "heroText"))
        hero_card = QFrame()
        hero_card.setObjectName("heroAccent")
        hero_card_layout = QVBoxLayout(hero_card)
        hero_card_layout.setContentsMargins(18, 16, 18, 16)
        hero_card_layout.addWidget(self._label("✦  Planeje com clareza", "whiteTitle"))
        hero_card_layout.addWidget(self._label("Uma rotina simples deixa o estudo mais leve e consistente.", "heroText"))
        hero_layout.addWidget(hero_card)
        hero_layout.addStretch(1)
        outer.addWidget(hero, 5)

        auth_card = QFrame()
        auth_card.setObjectName("authCard")
        auth_layout = QVBoxLayout(auth_card)
        auth_layout.setContentsMargins(40, 36, 40, 30)
        auth_layout.setSpacing(14)
        auth_layout.addWidget(self._label("Bem-vindo de volta", "title"))
        auth_layout.addWidget(self._label("Entre para continuar seu plano de estudos.", "subtitle"))

        tabs = QTabWidget()
        login = QWidget()
        login_form = QVBoxLayout(login)
        login_form.setContentsMargins(10, 22, 10, 12)
        login_form.setSpacing(10)
        login_form.addStretch(1)
        login_form.addWidget(self._label("E-mail", "eyebrow"))
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("voce@exemplo.com")
        login_form.addWidget(self.login_email)
        login_form.addWidget(self._label("Senha", "eyebrow"))
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setPlaceholderText("Sua senha")
        self.login_password.returnPressed.connect(self.login)
        login_form.addWidget(self.login_password)
        login_form.addSpacing(8)
        login_form.addWidget(self._button("Entrar", self.login, "primary"))
        forgot = self._button("Esqueci minha senha", self.forgot_password)
        forgot.setFlat(True)
        login_form.addWidget(forgot)
        login_form.addStretch(1)

        register = QWidget()
        register_form = QVBoxLayout(register)
        register_form.setContentsMargins(10, 22, 10, 12)
        register_form.setSpacing(9)
        register_form.addStretch(1)
        register_form.addWidget(self._label("Nome", "eyebrow"))
        self.register_name = QLineEdit()
        self.register_name.setPlaceholderText("Como podemos chamar você?")
        register_form.addWidget(self.register_name)
        register_form.addWidget(self._label("E-mail", "eyebrow"))
        self.register_email = QLineEdit()
        self.register_email.setPlaceholderText("voce@exemplo.com")
        register_form.addWidget(self.register_email)
        register_form.addWidget(self._label("Senha", "eyebrow"))
        self.register_password = QLineEdit()
        self.register_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_password.setPlaceholderText("Mínimo de 8 caracteres")
        register_form.addWidget(self.register_password)
        register_form.addSpacing(8)
        register_form.addWidget(self._button("Criar conta", self.register, "primary"))
        register_form.addStretch(1)
        tabs.addTab(login, "Entrar")
        tabs.addTab(register, "Criar conta")
        auth_layout.addWidget(tabs, 1)
        auth_layout.addWidget(self._label("Seus dados são armazenados neste computador.", "subtitle"))
        outer.addWidget(auth_card, 4)
        self.setCentralWidget(page)
        self.login_email.setFocus()

    def register(self):
        try:
            self.auth.register(self.register_name.text(), self.register_email.text(), self.register_password.text())
        except AuthenticationError as exc:
            QMessageBox.warning(self, "Não foi possível criar a conta", str(exc))
            return
        QMessageBox.information(self, "Conta criada", "Conta criada. Agora você pode entrar.")

    def login(self):
        try:
            self.user = self.auth.login(self.login_email.text(), self.login_password.text())
        except AuthenticationError:
            QMessageBox.warning(self, "Não foi possível entrar", "E-mail ou senha inválidos.")
            return
        self.last_activity = time.monotonic()
        self.focus.recover()
        self.show_main()

    def forgot_password(self):
        from PySide6.QtWidgets import QInputDialog
        email, accepted = QInputDialog.getText(self, "Recuperar senha", "Informe o e-mail da conta:")
        if not accepted or not email:
            return
        try:
            token = self.auth.create_password_reset(email)
            if token:
                link = f"http://127.0.0.1:{self.reset_server.port}/reset/{token}"
                self.mailer.send(email.strip(), "Recuperação da conta Estuda+", f"Clique no link abaixo para redefinir sua senha. Ele vale por 1 hora e só pode ser usado uma vez.\n\n{link}\n\nMantenha o Estuda+ aberto neste computador ao abrir o link.")
                logger.info("E-mail de recuperação enviado")
        except Exception as exc:
            logger.warning("Não foi possível processar recuperação de conta (error=%s)", type(exc).__name__)
        QMessageBox.information(self, "Recuperação", "Se houver uma conta para esse endereço, enviaremos as instruções. Configure o e-mail para receber o link.")

    def _set_new_password(self, token):
        from PySide6.QtWidgets import QInputDialog
        password, accepted = QInputDialog.getText(self, "Nova senha", "Digite uma nova senha (mínimo 8 caracteres):", QLineEdit.EchoMode.Password)
        if not accepted or not password:
            return
        try:
            self.auth.reset_password(token, password)
        except AuthenticationError as exc:
            QMessageBox.warning(self, "Não foi possível redefinir", str(exc))
            return
        QMessageBox.information(self, "Senha atualizada", "Sua senha foi alterada. Entre novamente.")

    def show_main(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(235)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(16, 24, 16, 18)
        side.setSpacing(8)
        logo_row = QHBoxLayout()
        mark = self._label("✦", None)
        mark.setObjectName("brandMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(40, 40)
        logo_row.addWidget(mark)
        logo_row.addWidget(self._label("Estuda+", "whiteTitle"))
        logo_row.addStretch(1)
        side.addLayout(logo_row)
        side.addSpacing(24)
        side.addWidget(self._label("ESPAÇO DE ESTUDO", "eyebrow"))
        self.nav_buttons = []
        self.stack = QStackedWidget()
        self.page_titles = []
        page_specs = [
            ("⌂", "Visão geral", self._build_dashboard), ("▤", "Tarefas", self._build_tasks),
            ("◷", "Foco", self._build_focus), ("✦", "Assistente", self._build_chat),
            ("◉", "Notificações", self._build_notifications), ("▦", "Histórico", self._build_history),
            ("◎", "Conta", self._build_account),
        ]
        if self.user["role"] == "admin":
            page_specs.append(("⚙", "Administração", self._build_admin))
        for index, (icon, title, builder) in enumerate(page_specs):
            page = QWidget()
            page.setObjectName("page")
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(30, 26, 30, 28)
            page_layout.setSpacing(18)
            builder(page_layout)
            self.stack.addWidget(page)
            self.page_titles.append(title)
            button = QPushButton(f"{icon}    {title}")
            button.setProperty("variant", "nav")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, idx=index: self._set_page(idx))
            self.nav_buttons.append(button)
            side.addWidget(button)
        side.addStretch(1)
        profile = QFrame()
        profile.setObjectName("heroAccent")
        profile_layout = QVBoxLayout(profile)
        profile_layout.setContentsMargins(13, 13, 13, 13)
        profile_name = QLabel(self.user["name"])
        profile_name.setStyleSheet("color:white;font-weight:700")
        profile_layout.addWidget(profile_name)
        email_label = QLabel(self.user["email"])
        email_label.setStyleSheet("color:#C9D9D4;font-size:9pt")
        profile_layout.addWidget(email_label)
        side.addWidget(profile)
        side.addWidget(self._button("Sair da conta", self.logout, "nav"))
        layout.addWidget(self.sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        topbar = QFrame()
        topbar.setObjectName("topbar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(30, 18, 30, 18)
        self.page_heading = self._label("Visão geral", "heading")
        top_layout.addWidget(self.page_heading)
        top_layout.addStretch(1)
        self.header_notifications = self._button("Notificações · 0", lambda: self._set_page(4))
        top_layout.addWidget(self.header_notifications)
        content_layout.addWidget(topbar)
        content_layout.addWidget(self.stack, 1)
        layout.addWidget(content, 1)
        self.setCentralWidget(root)
        self._set_page(0)
        self._refresh_dashboard()
        self._refresh_tasks()
        self._refresh_notifications()
        self._load_conversations()
        self._tick_focus()

    def _set_page(self, index: int):
        if not hasattr(self, "stack"):
            return
        self.stack.setCurrentIndex(index)
        self.page_heading.setText(self.page_titles[index])
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def logout(self):
        self.user = None
        self.active_conversation_id = None
        self.show_auth()

    def _check_idle(self):
        if self.user and time.monotonic() - self.last_activity >= self.SESSION_IDLE_SECONDS:
            QMessageBox.information(self, "Sessão encerrada", "Sua sessão expirou após 8 horas sem atividade. Entre novamente.")
            self.logout()

    def _poll_background(self):
        while True:
            try:
                token = self.reset_server.tokens.get_nowait()
            except queue.Empty:
                break
            self._set_new_password(token)
        if self.user:
            self._tick_focus()
            try:
                if self.tasks.process_due_reminders(self.mailer):
                    self._refresh_notifications()
                    self._refresh_tasks()
            except Exception as exc:
                logger.exception("Falha ao processar lembretes (error=%s)", type(exc).__name__)

    def _build_dashboard(self, layout):
        intro = QVBoxLayout()
        intro.addWidget(self._label(f"Olá, {self.user['name'].split()[0]} 👋", "title"))
        intro.addWidget(self._label("Um passo de cada vez. Veja como seus estudos estão avançando.", "subtitle"))
        layout.addLayout(intro)
        period_row = QHBoxLayout()
        period_row.addStretch(1)
        self.period = QComboBox()
        self.period.addItems(("7 dias", "30 dias", "Todo o período"))
        self.period.setCurrentText("30 dias")
        self.period.currentTextChanged.connect(lambda _value: self._refresh_dashboard())
        period_row.addWidget(QLabel("Período"))
        period_row.addWidget(self.period)
        layout.addLayout(period_row)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.metric_labels = {}
        for key, title, detail in (
            ("completed", "Concluídas", "tarefas finalizadas"),
            ("pending", "Pendentes", "dentro do prazo"),
            ("overdue", "Atrasadas", "pedem atenção"),
            ("focus", "Sessões", "de foco completas"),
            ("time", "Tempo focado", "neste período"),
        ):
            card, card_layout = self._card()
            card_layout.addWidget(self._label(title, "eyebrow"))
            value = self._label("—", "metric")
            card_layout.addWidget(value)
            card_layout.addWidget(self._label(detail, "subtitle"))
            self.metric_labels[key] = value
            cards.addWidget(card, 1)
        layout.addLayout(cards)

        tasks_card, task_layout = self._card("Prioridades da semana")
        task_layout.addWidget(self._label("Tarefas pendentes organizadas pelo prazo mais próximo.", "subtitle"))
        self.dashboard_tasks = self._table(["Tarefa", "Prazo", "Status"], [540, 180, 130])
        task_layout.addWidget(self.dashboard_tasks, 1)
        layout.addWidget(tasks_card, 1)

    def _refresh_dashboard(self):
        if not self.user or not hasattr(self, "metric_labels"):
            return
        all_tasks = self.tasks.list_tasks(self.user["id"], status="Todas")
        now = datetime.now(timezone.utc).isoformat()
        completed = sum(row["status"] == "Concluída" for row in all_tasks)
        overdue = sum(row["status"] == "Pendente" and row["deadline"] < now for row in all_tasks)
        pending = sum(row["status"] == "Pendente" and row["deadline"] >= now for row in all_tasks)
        metrics = self.focus.metrics(self.user["id"], self.period.currentText() if hasattr(self, "period") else "30 dias")
        seconds = metrics["effective_seconds"]
        values = {"completed": str(completed), "pending": str(pending), "overdue": str(overdue),
                  "focus": str(metrics["completed_sessions"]), "time": f"{seconds // 3600}h {(seconds % 3600) // 60}m"}
        for key, value in values.items():
            self.metric_labels[key].setText(value)
        rows = [row for row in all_tasks if row["status"] == "Pendente"][:12]
        self.dashboard_tasks.setRowCount(0)
        for row in rows:
            due = datetime.fromisoformat(row["deadline"]).astimezone().strftime("%d/%m/%Y %H:%M")
            status = "Atrasada" if row["deadline"] < now else "No prazo"
            self._append_row(self.dashboard_tasks, [row["title"], due, status], row["id"])

    @staticmethod
    def _append_row(table, values, record_id=None):
        row = table.rowCount()
        table.insertRow(row)
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if col == 0 and record_id is not None:
                item.setData(Qt.ItemDataRole.UserRole, record_id)
            table.setItem(row, col, item)

    def _build_tasks(self, layout):
        top = QHBoxLayout()
        text = QVBoxLayout()
        text.addWidget(self._label("Planejamento", "title"))
        text.addWidget(self._label("Organize prazos, prioridades e próximas etapas.", "subtitle"))
        top.addLayout(text)
        top.addStretch(1)
        top.addWidget(self._button("＋  Nova tarefa", self._task_dialog, "primary"))
        layout.addLayout(top)

        filters_card, filters = self._card("Filtros")
        filter_row = QHBoxLayout()
        self.filter_status = QComboBox(); self.filter_status.addItems(("Todas", "Pendente", "Concluída", "Atrasada"))
        self.filter_priority = QComboBox(); self.filter_priority.addItems(("Todas", "Baixa", "Média", "Alta"))
        self.filter_from = QLineEdit(); self.filter_from.setPlaceholderText("AAAA-MM-DD")
        self.filter_to = QLineEdit(); self.filter_to.setPlaceholderText("AAAA-MM-DD")
        for label, widget in (("Status", self.filter_status), ("Prioridade", self.filter_priority), ("Prazo de", self.filter_from), ("até", self.filter_to)):
            block = QVBoxLayout(); block.addWidget(self._label(label, "eyebrow")); block.addWidget(widget); filter_row.addLayout(block)
        filter_row.addWidget(self._button("Aplicar", self._refresh_tasks, "primary"))
        filter_row.addWidget(self._button("Limpar", self._clear_filters))
        filters.addLayout(filter_row)
        layout.addWidget(filters_card)

        table_card, table_layout = self._card("Suas tarefas")
        self.task_table = self._table(["Tarefa", "Prazo", "Prioridade", "Status", "Etapas abertas"], [380, 160, 120, 120, 130])
        self.task_table.doubleClicked.connect(self._edit_selected_task)
        table_layout.addWidget(self.task_table, 1)
        actions = QHBoxLayout()
        for label, callback, variant in (
            ("Editar", self._edit_selected_task, None), ("Concluir / reabrir", self._toggle_task, None),
            ("Subtarefas", self._manage_subtasks, None), ("Lembretes", self._manage_reminders, None),
            ("Excluir", self._delete_task, "danger"),
        ):
            actions.addWidget(self._button(label, callback, variant))
        actions.addStretch(1)
        table_layout.addLayout(actions)
        layout.addWidget(table_card, 1)

    def _clear_filters(self):
        self.filter_status.setCurrentText("Todas")
        self.filter_priority.setCurrentText("Todas")
        self.filter_from.clear(); self.filter_to.clear()
        self._refresh_tasks()

    def _refresh_tasks(self):
        if not self.user or not hasattr(self, "task_table"):
            return
        from_text, to_text = self.filter_from.text().strip(), self.filter_to.text().strip()
        try:
            date_from = datetime.strptime(from_text, "%Y-%m-%d").replace(tzinfo=timezone.utc).isoformat() if from_text else None
            date_to = (datetime.strptime(to_text, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1) - timedelta(seconds=1)).isoformat() if to_text else None
            rows = self.tasks.list_tasks(self.user["id"], self.filter_status.currentText(), self.filter_priority.currentText(), date_from, date_to)
        except ValueError:
            QMessageBox.warning(self, "Data inválida", "Informe as datas no formato AAAA-MM-DD.")
            return
        now = datetime.now(timezone.utc).isoformat()
        self.task_table.setRowCount(0)
        for task in rows:
            status = "Atrasada" if task["status"] == "Pendente" and task["deadline"] < now else task["status"]
            due = datetime.fromisoformat(task["deadline"]).astimezone().strftime("%d/%m/%Y %H:%M")
            self._append_row(self.task_table, [task["title"], due, task["priority"], status, task["pending_subtasks"]], task["id"])
        self._refresh_dashboard()
        if hasattr(self, "focus_task"):
            self._refresh_focus_tasks()

    def _selected_task(self):
        row = self.task_table.currentRow() if hasattr(self, "task_table") else -1
        if row < 0 or not self.task_table.item(row, 0):
            return None
        return self.task_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _task_dialog(self, task=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Editar tarefa" if task else "Nova tarefa")
        dialog.setMinimumWidth(480)
        layout = QVBoxLayout(dialog); layout.setContentsMargins(26, 24, 26, 22); layout.setSpacing(15)
        layout.addWidget(self._label("Detalhes da tarefa", "heading"))
        form = QFormLayout(); form.setVerticalSpacing(12)
        title = QLineEdit(); title.setMaxLength(120); title.setPlaceholderText("Ex.: Revisar funções de matemática")
        description = QPlainTextEdit(); description.setMaximumHeight(90); description.setPlaceholderText("Notas opcionais para esta tarefa")
        deadline = QDateTimeEdit(QDateTime.currentDateTime().addDays(1)); deadline.setCalendarPopup(True); deadline.setDisplayFormat("dd/MM/yyyy HH:mm")
        priority = QComboBox(); priority.addItems(("Baixa", "Média", "Alta")); priority.setCurrentText("Média")
        if task:
            title.setText(task["title"]); description.setPlainText(task["description"])
            local_due = datetime.fromisoformat(task["deadline"]).astimezone()
            deadline.setDateTime(QDateTime.fromString(local_due.strftime("%d/%m/%Y %H:%M"), "dd/MM/yyyy HH:mm"))
            priority.setCurrentText(task["priority"])
        form.addRow("Título", title); form.addRow("Descrição", description); form.addRow("Prazo", deadline); form.addRow("Prioridade", priority)
        layout.addLayout(form)
        error = self._label("", None); error.setStyleSheet("color:#B84B54")
        layout.addWidget(error)
        buttons = QHBoxLayout(); buttons.addStretch(1); buttons.addWidget(self._button("Cancelar", dialog.reject)); buttons.addWidget(self._button("Salvar tarefa", lambda: save(), "primary"))
        layout.addLayout(buttons)

        def save():
            try:
                due = datetime.fromisoformat(deadline.dateTime().toString(Qt.DateFormat.ISODate)).astimezone(timezone.utc)
                if task:
                    self.tasks.edit_task(self.user["id"], task["id"], title.text(), due, priority.currentText(), description.toPlainText())
                else:
                    self.tasks.create_task(self.user["id"], title.text(), due, priority.currentText(), description.toPlainText())
            except (ValueError, TaskError) as exc:
                error.setText(str(exc) if isinstance(exc, TaskError) else "Informe um prazo válido.")
                return
            dialog.accept(); self._refresh_tasks()
        title.setFocus()
        dialog.exec()

    def _edit_selected_task(self, *_args):
        task_id = self._selected_task()
        if not task_id:
            QMessageBox.information(self, "Selecione uma tarefa", "Escolha uma tarefa para editar."); return
        try:
            self._task_dialog(self.tasks.get_task(self.user["id"], task_id))
        except TaskError as exc:
            QMessageBox.warning(self, "Tarefa indisponível", str(exc))

    def _toggle_task(self):
        task_id = self._selected_task()
        if not task_id:
            QMessageBox.information(self, "Selecione uma tarefa", "Escolha uma tarefa na lista primeiro."); return
        row = self.tasks.get_task(self.user["id"], task_id)
        try:
            self.tasks.set_completed(self.user["id"], task_id, row["status"] != "Concluída")
        except TaskError as exc:
            QMessageBox.warning(self, "Não foi possível concluir", str(exc))
        self._refresh_tasks()

    def _delete_task(self):
        task_id = self._selected_task()
        if not task_id:
            QMessageBox.information(self, "Selecione uma tarefa", "Escolha uma tarefa na lista primeiro."); return
        answer = QMessageBox.question(self, "Excluir tarefa", "Excluir esta tarefa, subtarefas e lembretes? As sessões de foco concluídas permanecem no histórico.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.tasks.delete_task(self.user["id"], task_id)
        except TaskError as exc:
            QMessageBox.warning(self, "Não foi possível excluir", str(exc))
        self._refresh_tasks()

    def _manage_subtasks(self):
        task_id = self._selected_task()
        if not task_id:
            QMessageBox.information(self, "Selecione uma tarefa", "Escolha uma tarefa na lista primeiro."); return
        task = self.tasks.get_task(self.user["id"], task_id)
        dialog = QDialog(self); dialog.setWindowTitle("Etapas da tarefa"); dialog.resize(640, 480)
        layout = QVBoxLayout(dialog); layout.setContentsMargins(24, 22, 24, 22)
        layout.addWidget(self._label(task["title"], "heading"))
        table = self._table(["Status", "Etapa"], [125, 430]); layout.addWidget(table, 1)
        entry_row = QHBoxLayout(); entry = QLineEdit(); entry.setPlaceholderText("Adicione uma próxima etapa")
        entry_row.addWidget(entry, 1)
        def refresh():
            table.setRowCount(0)
            for subtask in self.tasks.list_subtasks(self.user["id"], task_id):
                self._append_row(table, ["Concluída" if subtask["done"] else "Pendente", subtask["title"]], subtask["id"])
        def add():
            try:
                self.tasks.add_subtask(self.user["id"], task_id, entry.text()); entry.clear(); refresh(); self._refresh_tasks()
            except TaskError as exc:
                QMessageBox.warning(dialog, "Etapa inválida", str(exc))
        entry_row.addWidget(self._button("Adicionar", add, "primary")); layout.addLayout(entry_row)
        def toggle():
            row = table.currentRow()
            if row < 0: return
            subtask_id = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            item = next((sub for sub in self.tasks.list_subtasks(self.user["id"], task_id) if sub["id"] == subtask_id), None)
            if item:
                all_done = self.tasks.set_subtask_done(self.user["id"], subtask_id, not bool(item["done"]))
                if all_done: self.notifications.add(self.user["id"], f"Todas as etapas de {task['title']} foram concluídas.", "Task")
                refresh(); self._refresh_tasks(); self._refresh_notifications()
        layout.addWidget(self._button("Marcar / desmarcar conclusão", toggle))
        refresh(); dialog.exec()

    def _build_focus(self, layout):
        intro = QVBoxLayout()
        intro.addWidget(self._label("Hora de focar", "title"))
        intro.addWidget(self._label("Escolha uma tarefa, ajuste o tempo e avance sem distrações.", "subtitle"))
        layout.addLayout(intro)
        card, card_layout = self._card("Preparar sessão")
        form = QFormLayout(); form.setVerticalSpacing(14)
        self.focus_task = QComboBox()
        self.focus_duration = QSpinBox(); self.focus_duration.setRange(1, 240); self.focus_duration.setValue(25); self.focus_duration.setSuffix(" min")
        form.addRow("Tarefa", self.focus_task); form.addRow("Duração", self.focus_duration)
        card_layout.addLayout(form)
        controls = QHBoxLayout()
        controls.addWidget(self._button("▶  Iniciar", self._start_focus, "primary"))
        controls.addWidget(self._button("Pausar", self._pause_focus))
        controls.addWidget(self._button("Retomar", self._resume_focus))
        controls.addWidget(self._button("Encerrar", self._terminate_focus, "danger"))
        controls.addStretch(1); card_layout.addLayout(controls)
        layout.addWidget(card)

        timer_card = QFrame(); timer_card.setObjectName("hero")
        timer_layout = QVBoxLayout(timer_card); timer_layout.setContentsMargins(36, 30, 36, 30); timer_layout.setSpacing(12)
        timer_layout.addWidget(self._label("SESSÃO ATUAL", "eyebrow"), alignment=Qt.AlignmentFlag.AlignHCenter)
        self.focus_status = self._label("25:00", "whiteTitle")
        self.focus_status.setStyleSheet("color:white;font-size:42pt;font-weight:750")
        timer_layout.addWidget(self.focus_status, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.focus_detail = self._label("Nenhuma sessão ativa · duração padrão de 25 minutos", "heroText")
        timer_layout.addWidget(self.focus_detail, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.focus_progress = QProgressBar(); self.focus_progress.setTextVisible(False); self.focus_progress.setFixedHeight(14)
        self.focus_progress.setStyleSheet("QProgressBar{background:#28574E;border-radius:7px} QProgressBar::chunk{background:#C8E6A0;border-radius:7px}")
        timer_layout.addWidget(self.focus_progress)
        layout.addWidget(timer_card)
        layout.addStretch(1)
        self._refresh_focus_tasks()

    def _refresh_focus_tasks(self):
        if not self.user or not hasattr(self, "focus_task"):
            return
        rows = self.tasks.list_tasks(self.user["id"], status="Pendente")
        current = self.focus_task.currentData()
        self.focus_task.clear()
        for row in rows:
            self.focus_task.addItem(f"{row['title']}  ·  prazo {datetime.fromisoformat(row['deadline']).astimezone().strftime('%d/%m')}", row["id"])
        if current is not None:
            index = self.focus_task.findData(current)
            if index >= 0: self.focus_task.setCurrentIndex(index)

    def _start_focus(self):
        task_id = self.focus_task.currentData()
        if task_id is None:
            QMessageBox.information(self, "Nenhuma tarefa pendente", "Crie ou selecione uma tarefa pendente primeiro."); return
        try:
            session_id = self.focus.start(self.user["id"], int(task_id), self.focus_duration.value())
        except FocusError as exc:
            QMessageBox.warning(self, "Não foi possível iniciar", str(exc)); return
        logger.info("Sessão iniciada na interface (session_id=%s)", session_id)
        self._tick_focus()

    def _pause_focus(self):
        try: self.focus.pause(self.user["id"])
        except FocusError as exc: QMessageBox.information(self, "Sessão de foco", str(exc))
        self._tick_focus()

    def _resume_focus(self):
        try: self.focus.resume(self.user["id"])
        except FocusError as exc: QMessageBox.information(self, "Sessão de foco", str(exc))
        self._tick_focus()

    def _terminate_focus(self):
        try: self.focus.terminate(self.user["id"])
        except FocusError as exc: QMessageBox.information(self, "Sessão de foco", str(exc))
        self._tick_focus(); self._refresh_history(); self._refresh_dashboard()

    def _tick_focus(self):
        if not self.user or not hasattr(self, "focus_status"):
            return
        session = self.focus.tick(self.user["id"])
        if not session:
            self.focus_status.setText("25:00")
            self.focus_detail.setText("Nenhuma sessão ativa · duração padrão de 25 minutos")
            self.focus_progress.setValue(0)
            return
        remaining = max(0, session["duration_seconds"] - session["elapsed_seconds"])
        self.focus_status.setText(f"{remaining // 60:02d}:{remaining % 60:02d}")
        state = "Pausada" if session["status"] == "Paused" else "Em andamento"
        elapsed = session["elapsed_seconds"]
        self.focus_detail.setText(f"{session['task_title']}  ·  {state}  ·  decorrido {elapsed // 60:02d}:{elapsed % 60:02d}")
        self.focus_progress.setValue(min(100, int(100 * elapsed / session["duration_seconds"])))
        if session["status"] == "Completed":
            self._refresh_notifications(); self._refresh_history(); self._refresh_dashboard()

    def _build_chat(self, layout):
        intro = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.addWidget(self._label("Estuda+", "title"))
        title_box.addWidget(self._label("Tire dúvidas e transforme seus estudos em próximos passos.", "subtitle"))
        intro.addLayout(title_box); intro.addStretch(1)
        self.new_conversation_button = self._button("＋  Nova conversa", self._new_conversation, "primary")
        intro.addWidget(self.new_conversation_button)
        layout.addLayout(intro)

        provider_name = "Gemini" if self.ai_client.__class__.__name__ == "GeminiClient" else "OpenAI"
        if getattr(self.ai_client, "available", False):
            connection_text = f"●  {provider_name} configurada"
            connection_role = "chatReady"
        else:
            connection_text = f"○  Configure a chave de API de {provider_name} para conversar"
            connection_role = "chatWarning"
        self.chat_connection = self._label(connection_text, connection_role)
        layout.addWidget(self.chat_connection)

        starters = QHBoxLayout()
        starters.addWidget(self._label("Comece por aqui", "eyebrow"))
        starters.addWidget(self._button("Explicar um assunto", lambda: self._use_chat_prompt("Explique de forma simples este assunto: ")))
        starters.addWidget(self._button("Montar um plano", lambda: self._use_chat_prompt("Ajude-me a montar um plano de estudos para ")))
        starters.addWidget(self._button("Dividir um trabalho", lambda: self._use_chat_prompt("Ajude-me a dividir este trabalho em etapas: ")))
        starters.addStretch(1)
        layout.addLayout(starters)

        convo_card, convo_layout = self._card()
        convo_row = QHBoxLayout(); convo_row.addWidget(self._label("Conversa", "eyebrow"))
        self.conversation_box = QComboBox(); self.conversation_box.currentIndexChanged.connect(self._conversation_selected)
        convo_row.addWidget(self.conversation_box, 1); convo_layout.addLayout(convo_row)
        layout.addWidget(convo_card)

        chat_card, chat_layout = self._card()
        self.chat_log = QTextBrowser(); self.chat_log.setMinimumHeight(300); self.chat_log.setOpenExternalLinks(False)
        chat_layout.addWidget(self.chat_log, 1)
        self.chat_status = self._label("Dica: descreva o que está estudando e onde ficou com dúvida.", "subtitle")
        self.chat_status.setWordWrap(True)
        chat_layout.addWidget(self.chat_status)
        compose = QHBoxLayout()
        self.chat_entry = QLineEdit(); self.chat_entry.setPlaceholderText("Escreva sua dúvida ou o que precisa organizar…")
        self.chat_entry.returnPressed.connect(self._send_chat)
        compose.addWidget(self.chat_entry, 1)
        self.chat_complex = QCheckBox("Gerar etapas")
        self.chat_complex.setToolTip("Peça à IA até cinco etapas que você pode revisar e adicionar como subtarefas.")
        compose.addWidget(self.chat_complex)
        self.chat_send_button = self._button("Enviar", self._send_chat, "primary")
        compose.addWidget(self.chat_send_button); chat_layout.addLayout(compose)
        layout.addWidget(chat_card, 1)

        self.proposals_card, proposal_layout = self._card("Etapas sugeridas pela IA")
        self.suggestion_table = self._table(["Proposta"], [540]); proposal_layout.addWidget(self.suggestion_table)
        proposal_controls = QHBoxLayout()
        self.suggestion_task = QComboBox(); self.suggestion_task.setMinimumWidth(220)
        self.suggestion_title = QLineEdit(); self.suggestion_title.setPlaceholderText("Título editado (opcional)")
        proposal_controls.addWidget(QLabel("Adicionar como subtarefa de")); proposal_controls.addWidget(self.suggestion_task, 1); proposal_controls.addWidget(self.suggestion_title, 1)
        proposal_controls.addWidget(self._button("Aceitar", self._accept_suggestion, "primary")); proposal_controls.addWidget(self._button("Rejeitar", self._reject_suggestion, "danger"))
        proposal_layout.addLayout(proposal_controls); layout.addWidget(self.proposals_card)
        self.proposals_card.hide()

        self.retry_card, retry_layout = self._card()
        retry_row = QHBoxLayout()
        retry_row.addWidget(self._label("Envio com falha", "eyebrow"))
        self.failed_messages = QComboBox(); retry_row.addWidget(self.failed_messages, 1)
        self.retry_button = self._button("Reenviar mensagem", self._resend_failed, "primary")
        retry_row.addWidget(self.retry_button)
        retry_layout.addLayout(retry_row); layout.addWidget(self.retry_card)
        self.retry_card.hide()

    def _use_chat_prompt(self, prompt: str):
        self.chat_entry.setText(prompt)
        self.chat_entry.setFocus()
        self.chat_entry.setCursorPosition(len(prompt))

    def _set_chat_status(self, text: str, role: str = "subtitle"):
        self.chat_status.setText(text)
        self.chat_status.setProperty("role", role)
        self.chat_status.style().unpolish(self.chat_status)
        self.chat_status.style().polish(self.chat_status)

    def _build_chat_html(self, rows):
        chunks = ["<div style='font-family:Segoe UI, sans-serif;color:#172B27'>"]
        if not rows:
            chunks.append("<div style='padding:18px;color:#71817C'>Olá! Conte qual matéria ou atividade você quer começar. Para projetos maiores, marque ‘Dividir em etapas’.</div>")
        for row in rows:
            is_user = row["role"] == "user"
            name = "Você" if is_user else "Estuda+"
            failed = is_user and row["status"] == "Failed"
            bg = "#FFF0F0" if failed else ("#E4F2EC" if is_user else "#F5F7F4")
            align = "right" if is_user else "left"
            label = "Você · envio pendente/falhou — tente novamente" if failed else name
            chunks.append(f"<div style='margin:12px 4px;text-align:{align}'><span style='font-size:10pt;font-weight:700;color:#71817C'>{label}</span><div style='display:inline-block;max-width:78%;margin-top:4px;padding:12px 15px;background:{bg};border-radius:14px;text-align:left;white-space:pre-wrap'>{html.escape(row['content'])}</div></div>")
        chunks.append("</div>")
        return "".join(chunks)

    def _load_conversations(self):
        if not self.user or not hasattr(self, "conversation_box"):
            return
        rows = self.chat.list_conversations(self.user["id"])
        if not rows:
            self.active_conversation_id = self.chat.create_conversation(self.user["id"])
            rows = self.chat.list_conversations(self.user["id"])
        ids = [row["id"] for row in rows]
        if self.active_conversation_id not in ids:
            self.active_conversation_id = ids[0]
        self._conversation_rows = rows
        self.conversation_box.blockSignals(True); self.conversation_box.clear()
        for row in rows:
            self.conversation_box.addItem(f"{row['title']}  ·  #{row['id']}", row["id"])
        index = self.conversation_box.findData(self.active_conversation_id)
        self.conversation_box.setCurrentIndex(index); self.conversation_box.blockSignals(False)
        self._load_messages(); self._load_suggestions()

    def _new_conversation(self):
        if not self.user: return
        self.active_conversation_id = self.chat.create_conversation(self.user["id"])
        self._load_conversations()
        self.chat_entry.setFocus()

    def _conversation_selected(self, index):
        if index < 0 or not hasattr(self, "conversation_box"):
            return
        conversation_id = self.conversation_box.currentData()
        if conversation_id is None: return
        self.active_conversation_id = int(conversation_id)
        self._load_messages(); self._load_suggestions()

    def _load_messages(self):
        if not self.user or not self.active_conversation_id or not hasattr(self, "chat_log"):
            return
        rows = self.chat.messages(self.user["id"], self.active_conversation_id)
        self.chat_log.setHtml(self._build_chat_html(rows))
        self.chat_log.verticalScrollBar().setValue(self.chat_log.verticalScrollBar().maximum())
        failed = [row for row in rows if row["role"] == "user" and row["status"] == "Failed"]
        self._failed_rows = failed
        self.failed_messages.clear()
        for row in failed:
            self.failed_messages.addItem(f"{row['content'][:75]}  ·  #{row['id']}", row["id"])
        self.retry_card.setVisible(bool(failed))

    def _load_suggestions(self):
        if not self.user or not self.active_conversation_id or not hasattr(self, "suggestion_table"):
            return
        rows = self.chat.list_suggestions(self.user["id"], self.active_conversation_id)
        self._suggestion_rows = rows
        self.suggestion_table.setRowCount(0)
        for row in rows:
            self._append_row(self.suggestion_table, [row["title"]], row["id"])
        tasks = self.tasks.list_tasks(self.user["id"], status="Pendente")
        selected = self.suggestion_task.currentData()
        self.suggestion_task.clear()
        for task in tasks:
            self.suggestion_task.addItem(task["title"], task["id"])
        self.proposals_card.setVisible(bool(rows))
        if selected is not None:
            index = self.suggestion_task.findData(selected)
            if index >= 0: self.suggestion_task.setCurrentIndex(index)

    def _send_chat(self):
        content = self.chat_entry.text().strip()
        if not content or not self.active_conversation_id:
            return
        existing = self.chat.messages(self.user["id"], self.active_conversation_id)
        previous_message_id = max((row["id"] for row in existing), default=0)
        self.chat_entry.clear()
        self._start_chat_worker(content=content, previous_message_id=previous_message_id)

    def _start_chat_worker(self, content=None, message_id=None, previous_message_id=0):
        worker = ChatWorker(self.chat, dict(self.user), self.active_conversation_id, content,
                            self.chat_complex.isChecked(), message_id, previous_message_id)
        self.chat_workers.add(worker)
        worker.succeeded.connect(self._chat_succeeded)
        worker.failed.connect(self._chat_failed)
        worker.finished.connect(self._chat_finished)
        self.chat_entry.setEnabled(False)
        self.chat_complex.setEnabled(False)
        self.chat_send_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        self.conversation_box.setEnabled(False)
        self.new_conversation_button.setEnabled(False)
        self._set_chat_status("Enviando sua mensagem…")
        worker.start()

    def _chat_succeeded(self, _result, conversation_id):
        if self.active_conversation_id == conversation_id:
            self._load_messages(); self._load_suggestions()
            self._set_chat_status("Resposta recebida. Pode continuar a conversa.", "chatReady")
        self._refresh_dashboard()

    def _chat_failed(self, message, conversation_id, content, message_id, previous_message_id):
        if self.active_conversation_id != conversation_id:
            return
        self._load_messages()
        rows = self.chat.messages(self.user["id"], conversation_id)
        registered = (any(row["id"] == message_id for row in rows) if message_id else
                      any(row["id"] > previous_message_id and row["role"] == "user"
                          and row["content"] == content for row in rows))
        if content and not registered and not self.chat_entry.text().strip():
            self.chat_entry.setText(content)
            self._set_chat_status(f"A mensagem não foi registrada e voltou para o campo. {message}", "chatError")
        elif registered:
            self._set_chat_status(f"A mensagem ficou salva para reenvio. {message}", "chatError")
        else:
            self._set_chat_status(message, "chatError")

    @Slot()
    def _chat_finished(self):
        worker = self.sender()
        if not isinstance(worker, ChatWorker):
            return
        self.chat_workers.discard(worker)
        self.chat_entry.setEnabled(True)
        self.chat_complex.setEnabled(True)
        self.chat_send_button.setEnabled(True)
        self.retry_button.setEnabled(True)
        self.conversation_box.setEnabled(True)
        self.new_conversation_button.setEnabled(True)
        self.chat_entry.setFocus()

    def _resend_failed(self):
        message_id = self.failed_messages.currentData()
        if message_id is None:
            QMessageBox.information(self, "Sem mensagens com falha", "Não há mensagens para reenviar nesta conversa."); return
        previous_message_id = max((row["id"] for row in self.chat.messages(
            self.user["id"], self.active_conversation_id)), default=0)
        self._start_chat_worker(message_id=int(message_id), previous_message_id=previous_message_id)

    def _accept_suggestion(self):
        row = self.suggestion_table.currentRow()
        task_id = self.suggestion_task.currentData()
        if row < 0 or task_id is None:
            QMessageBox.information(self, "Selecione uma proposta", "Escolha uma proposta e uma tarefa pendente."); return
        suggestion_id = self.suggestion_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        try:
            self.chat.accept_suggestion(self.user["id"], int(suggestion_id), int(task_id), self.suggestion_title.text().strip() or None)
        except (ChatError, TaskError) as exc:
            QMessageBox.warning(self, "Não foi possível adicionar", str(exc)); return
        self.suggestion_title.clear(); self._load_suggestions(); self._refresh_tasks()

    def _reject_suggestion(self):
        row = self.suggestion_table.currentRow()
        if row < 0: return
        suggestion_id = self.suggestion_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        try:
            self.chat.reject_suggestion(self.user["id"], int(suggestion_id))
        except ChatError as exc:
            QMessageBox.warning(self, "Proposta", str(exc))
        self._load_suggestions()

    def _build_notifications(self, layout):
        top = QHBoxLayout()
        title = QVBoxLayout(); title.addWidget(self._label("Central de avisos", "title")); title.addWidget(self._label("Lembretes e atualizações do seu espaço de estudo.", "subtitle"))
        top.addLayout(title); top.addStretch(1); top.addWidget(self._button("Marcar todas como lidas", self._mark_all_read))
        layout.addLayout(top)
        card, card_layout = self._card("Notificações")
        self.notification_table = self._table(["Leitura", "Aviso", "Data"], [130, 600, 180])
        card_layout.addWidget(self.notification_table, 1)
        card_layout.addWidget(self._button("Marcar selecionada como lida", self._mark_notification_read))
        layout.addWidget(card, 1)

    def _refresh_notifications(self):
        if not self.user or not hasattr(self, "notification_table"):
            return
        rows = self.notifications.list_notifications(self.user["id"])
        self.notification_table.setRowCount(0)
        for row in rows:
            status = "Não lida" if not row["read_at"] else "Lida"
            try: date = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).astimezone().strftime("%d/%m/%Y %H:%M")
            except ValueError: date = row["created_at"]
            self._append_row(self.notification_table, [status, row["message"], date], row["id"])
        unread = sum(not row["read_at"] for row in rows)
        self.header_notifications.setText(f"Notificações  ·  {unread}")

    def _mark_notification_read(self):
        row = self.notification_table.currentRow()
        if row < 0: return
        notification_id = self.notification_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.notifications.mark_read(self.user["id"], int(notification_id)); self._refresh_notifications()

    def _mark_all_read(self):
        self.notifications.mark_read(self.user["id"]); self._refresh_notifications()

    def _build_history(self, layout):
        top = QHBoxLayout()
        title = QVBoxLayout(); title.addWidget(self._label("Seu histórico", "title")); title.addWidget(self._label("Acompanhe o que você concluiu e o tempo dedicado.", "subtitle"))
        top.addLayout(title); top.addStretch(1)
        self.history_period = QComboBox(); self.history_period.addItems(("7 dias", "30 dias", "Todo o período")); self.history_period.setCurrentText("30 dias")
        self.history_period.currentTextChanged.connect(lambda _value: self._refresh_history())
        top.addWidget(QLabel("Período")); top.addWidget(self.history_period); layout.addLayout(top)
        task_card, task_layout = self._card("Tarefas")
        self.task_history = self._table(["Tarefa", "Status", "Prazo", "Concluída em"], [380, 140, 190, 190])
        task_layout.addWidget(self.task_history, 1); layout.addWidget(task_card, 1)
        focus_card, focus_layout = self._card("Sessões de foco")
        self.focus_history = self._table(["Tarefa", "Status", "Iniciada em", "Tempo efetivo"], [380, 140, 190, 180])
        focus_layout.addWidget(self.focus_history, 1); layout.addWidget(focus_card, 1)

    def _refresh_history(self):
        if not self.user or not hasattr(self, "task_history"):
            return
        period = self.history_period.currentText() if hasattr(self, "history_period") else "Todo o período"
        date_filter = ""
        if period == "7 dias": date_filter = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        elif period == "30 dias": date_filter = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        with self.database.connection() as db:
            query = "SELECT * FROM tasks WHERE user_id=?"; params = [self.user["id"]]
            if date_filter: query += " AND (completed_at>=? OR status='Pendente')"; params.append(date_filter)
            tasks = db.execute(query + " ORDER BY COALESCE(completed_at,deadline) DESC", params).fetchall()
        self.task_history.setRowCount(0)
        for task in tasks:
            due = datetime.fromisoformat(task["deadline"]).astimezone().strftime("%d/%m/%Y %H:%M")
            completed = datetime.fromisoformat(task["completed_at"]).astimezone().strftime("%d/%m/%Y %H:%M") if task["completed_at"] else "—"
            self._append_row(self.task_history, [task["title"], task["status"], due, completed])
        self.focus_history.setRowCount(0)
        for session in self.focus.history(self.user["id"], period):
            started = datetime.fromisoformat(session["started_at"]).astimezone().strftime("%d/%m/%Y %H:%M")
            seconds = session["effective_seconds"]
            self._append_row(self.focus_history, [session["task_title"], session["status"], started, f"{seconds // 60} min {seconds % 60} s"])

    def _build_account(self, layout):
        layout.addWidget(self._label("Conta e privacidade", "title"))
        profile, profile_layout = self._card("Seu perfil")
        profile_layout.addWidget(self._label(f"{self.user['name']}\n{self.user['email']}\nPerfil: {'Administrador' if self.user['role'] == 'admin' else 'Estudante'}", "subtitle"))
        layout.addWidget(profile)
        privacy, privacy_layout = self._card("Seus dados")
        policy = ("Nome, e-mail, tarefas, mensagens e sessões ficam no banco local deste computador. "
                  "Quando configurado, o texto do chat (com nome e e-mail identificáveis removidos) é enviado ao provedor de IA. "
                  "O e-mail só é enviado para recuperação de conta ou lembretes explicitamente ativados.")
        privacy_layout.addWidget(self._label(policy, "subtitle")); layout.addWidget(privacy)
        layout.addWidget(self._button("Excluir minha conta…", self._delete_account, "danger"), alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)

    def _delete_account(self):
        answer = QMessageBox.question(self, "Excluir conta permanentemente", "Esta ação apagará tarefas, conversas, mensagens, notificações e sessões de foco. Deseja continuar?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.auth.delete_account(self.user["id"], confirmed=True)
        except AuthenticationError as exc:
            QMessageBox.warning(self, "Não foi possível excluir", str(exc)); return
        self.logout(); QMessageBox.information(self, "Conta excluída", "Sua conta e seus dados foram removidos deste computador.")

    def _build_admin(self, layout):
        layout.addWidget(self._label("Configurações do assistente", "title"))
        card, card_layout = self._card("Disponibilidade e limite diário")
        settings = self.auth.get_settings()
        self.ai_enabled_check = QCheckBox("Habilitar o assistente de IA para estudantes")
        self.ai_enabled_check.setChecked(bool(settings["ai_enabled"]))
        card_layout.addWidget(self.ai_enabled_check)
        row = QHBoxLayout(); row.addWidget(QLabel("Máximo de respostas por pessoa por dia"))
        self.ai_limit = QSpinBox(); self.ai_limit.setRange(1, 500); self.ai_limit.setValue(settings["daily_message_limit"]); row.addWidget(self.ai_limit); row.addStretch(1)
        card_layout.addLayout(row); card_layout.addWidget(self._button("Salvar configurações", self._save_admin_settings, "primary"))
        layout.addWidget(card)
        note, note_layout = self._card("Segurança")
        note_layout.addWidget(self._label("Chaves da IA e credenciais de e-mail devem ser configuradas no ambiente, nunca no código ou no banco.", "subtitle"))
        layout.addWidget(note); layout.addStretch(1)

    def _save_admin_settings(self):
        try:
            self.auth.update_ai_settings(self.user["id"], self.ai_enabled_check.isChecked(), self.ai_limit.value())
        except (ValueError, AuthenticationError) as exc:
            QMessageBox.warning(self, "Configuração inválida", str(exc)); return
        QMessageBox.information(self, "Configurações salvas", "Os limites do assistente foram atualizados.")

    def _manage_reminders(self):
        task_id = self._selected_task()
        if not task_id:
            QMessageBox.information(self, "Selecione uma tarefa", "Escolha uma tarefa para configurar lembretes."); return
        task = self.tasks.get_task(self.user["id"], task_id)
        dialog = QDialog(self); dialog.setWindowTitle("Lembretes"); dialog.resize(620, 500)
        layout = QVBoxLayout(dialog); layout.setContentsMargins(24, 22, 24, 22)
        layout.addWidget(self._label(f"Lembretes · {task['title']}", "heading"))
        table = self._table(["Data e hora", "E-mail", "Status"], [210, 100, 160]); layout.addWidget(table, 1)
        layout.addWidget(self._label("Novo lembrete", "eyebrow"))
        when = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600)); when.setCalendarPopup(True); when.setDisplayFormat("dd/MM/yyyy HH:mm")
        layout.addWidget(when)
        email = QCheckBox("Também enviar por e-mail (opcional)")
        layout.addWidget(email)
        def refresh():
            table.setRowCount(0)
            for reminder in self.tasks.list_reminders(self.user["id"], task_id):
                due = datetime.fromisoformat(reminder["scheduled_at"]).astimezone().strftime("%d/%m/%Y %H:%M")
                self._append_row(table, [due, "Sim" if reminder["email_enabled"] else "Não", reminder["status"]])
        def add():
            try:
                due = datetime.fromisoformat(when.dateTime().toString(Qt.DateFormat.ISODate)).astimezone(timezone.utc)
                self.tasks.add_reminder(self.user["id"], task_id, due, email.isChecked())
                refresh()
            except (ValueError, TaskError) as exc:
                QMessageBox.warning(dialog, "Lembrete inválido", str(exc) if isinstance(exc, TaskError) else "Informe uma data válida.")
        layout.addWidget(self._button("Adicionar lembrete", add, "primary"))
        refresh(); dialog.exec()
