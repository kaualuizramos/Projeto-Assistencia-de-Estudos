"""Interface desktop Tkinter que apresenta os cinco serviços do domínio."""

from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tkinter import messagebox, simpledialog, ttk
import tkinter as tk
from urllib.parse import unquote

from estuda.ai_chat import AIChatService, ChatError
from estuda.authentication import AuthenticationError, AuthenticationService
from estuda.database import Database
from estuda.focus_sessions import FocusError, FocusSessionsService
from estuda.integrations.ai import AIUnavailable, OpenAIResponsesClient
from estuda.integrations.email import SMTPMailer
from estuda.notifications import NotificationsService
from estuda.tasks import TaskError, TasksService

logger = logging.getLogger(__name__)
BG = "#f3f5fa"
INK = "#1c2435"
MUTED = "#647087"
ACCENT = "#5146e5"
WHITE = "#ffffff"


class ResetLinkServer:
    """Callback local: o link de recuperação abre uma caixa da aplicação desktop."""

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
                body = b"<!doctype html><meta charset='utf-8'><title>Estuda+</title><p>Volte ao aplicativo Estuda+ para criar sua nova senha.</p>"
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
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class StudyWindow(tk.Tk):
    SESSION_IDLE_SECONDS = 8 * 60 * 60

    def __init__(self, database: Database):
        super().__init__()
        self.database = database
        self.auth = AuthenticationService(database)
        self.tasks = TasksService(database)
        self.focus = FocusSessionsService(database)
        self.notifications = NotificationsService(database)
        self.ai_client = OpenAIResponsesClient()
        self.mailer = SMTPMailer()
        self.chat = AIChatService(database, self.ai_client, self.auth, self.tasks)
        self.reset_server = ResetLinkServer()
        self.user = None
        self.last_activity = time.monotonic()
        self.worker_queue: queue.Queue = queue.Queue()
        self.selected_task_id: int | None = None
        self.active_conversation_id: int | None = None
        self.task_filter_status = None
        self.title("Estuda+ | Assistente de estudos")
        self.geometry("1180x790")
        self.minsize(760, 620)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.bind_all("<KeyPress>", self._activity, add="+")
        self.bind_all("<Button>", self._activity, add="+")
        self._setup_style()
        self.show_auth()
        self.after(1000, self._poll_background)
        self.after(30_000, self._check_idle)

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=WHITE)
        style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=INK, font=("Segoe UI", 21, "bold"))
        style.configure("Section.TLabel", background=WHITE, foreground=INK, font=("Segoe UI", 13, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7))
        style.configure("Accent.TButton", background=ACCENT, foreground=WHITE, borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#4035c7")])
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=30, background=WHITE, fieldbackground=WHITE)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e9ebf5")
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(11, 8))

    @staticmethod
    def _label(parent, text, style="TLabel", **kwargs):
        return ttk.Label(parent, text=text, style=style, **kwargs)

    def _activity(self, _event=None):
        self.last_activity = time.monotonic()

    def close_app(self):
        self.reset_server.close()
        self.destroy()

    def _check_idle(self):
        if self.user and time.monotonic() - self.last_activity >= self.SESSION_IDLE_SECONDS:
            messagebox.showinfo("Sessão encerrada", "Sua sessão expirou após 8 horas sem atividade. Entre novamente.")
            self.logout(show_message=False)
        self.after(30_000, self._check_idle)

    def _poll_background(self):
        while True:
            try:
                kind, data = self.worker_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "chat_success" and self.user:
                self._load_messages()
                self._load_suggestions()
                self._refresh_dashboard()
            elif kind == "chat_error" and self.user:
                self._load_messages()
                messagebox.showerror("Assistente indisponível", str(data))
            elif kind == "reset_token":
                self._set_new_password(data)
            elif kind == "chat_finished" and self.user and hasattr(self, "chat_send_button"):
                self.chat_send_button.config(state="normal")
        if self.user:
            self._tick_focus()
            try:
                processed = self.tasks.process_due_reminders(self.mailer)
                if processed:
                    self._refresh_notifications()
                    self._refresh_tasks()
            except Exception as exc:
                logger.exception("Falha ao processar lembretes (error=%s)", type(exc).__name__)
        self.after(1000, self._poll_background)

    def show_auth(self):
        for child in self.winfo_children():
            if child is not getattr(self, "_background_after", None):
                child.destroy()
        page = ttk.Frame(self, padding=32)
        page.place(relx=.5, rely=.5, anchor="center", width=470, relheight=.82)
        self._label(page, "Estuda+", "Title.TLabel").pack(anchor="w")
        self._label(page, "Planeje seus estudos e acompanhe seu progresso.", "Muted.TLabel").pack(anchor="w", pady=(2, 18))
        card = ttk.Frame(page, style="Card.TFrame", padding=22)
        card.pack(fill="both", expand=True)
        notebook = ttk.Notebook(card)
        notebook.pack(fill="both", expand=True)
        login_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)
        register_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)
        notebook.add(login_tab, text="Entrar")
        notebook.add(register_tab, text="Criar conta")
        self.login_email = self._field(login_tab, "E-mail")
        self.login_password = self._field(login_tab, "Senha", show="•")
        ttk.Button(login_tab, text="Entrar", style="Accent.TButton", command=self.login).pack(fill="x", pady=(12, 7))
        ttk.Button(login_tab, text="Esqueci minha senha", command=self.forgot_password).pack(fill="x")
        self.register_name = self._field(register_tab, "Nome")
        self.register_email = self._field(register_tab, "E-mail")
        self.register_password = self._field(register_tab, "Senha (mínimo 8 caracteres)", show="•")
        ttk.Button(register_tab, text="Criar conta", style="Accent.TButton", command=self.register).pack(fill="x", pady=(12, 0))
        self._label(page, "Seus dados ficam neste computador. O chat envia apenas o contexto necessário ao provedor de IA configurado.", "Muted.TLabel", wraplength=410, justify="left").pack(anchor="w", pady=(12, 0))

    def _field(self, parent, caption, show=None):
        group = ttk.Frame(parent, style="Card.TFrame")
        group.pack(fill="x", pady=6)
        ttk.Label(group, text=caption, background=WHITE, foreground=INK).pack(anchor="w", pady=(0, 4))
        entry = ttk.Entry(group, show=show, font=("Segoe UI", 11))
        entry.pack(fill="x", ipady=6)
        return entry

    def register(self):
        try:
            self.auth.register(self.register_name.get(), self.register_email.get(), self.register_password.get())
        except AuthenticationError as exc:
            messagebox.showerror("Não foi possível criar a conta", str(exc))
            return
        messagebox.showinfo("Conta criada", "Conta criada. Agora você pode entrar.")

    def login(self):
        try:
            self.user = self.auth.login(self.login_email.get(), self.login_password.get())
        except AuthenticationError:
            messagebox.showerror("Não foi possível entrar", "E-mail ou senha inválidos.")
            return
        self.last_activity = time.monotonic()
        self.focus.recover()
        self.show_main()

    def forgot_password(self):
        email = simpledialog.askstring("Recuperar senha", "Informe o e-mail da conta:", parent=self)
        if not email:
            return
        try:
            token = self.auth.create_password_reset(email)
            if token:
                link = f"http://127.0.0.1:{self.reset_server.port}/reset/{token}"
                self.mailer.send(email.strip(), "Recuperação da conta Estuda+", f"Clique no link abaixo para redefinir sua senha. Ele vale por 1 hora e só pode ser usado uma vez.\n\n{link}\n\nMantenha o Estuda+ aberto neste computador ao abrir o link.")
                logger.info("E-mail de recuperação enviado")
        except Exception as exc:
            logger.warning("Não foi possível processar recuperação de conta (error=%s)", type(exc).__name__)
        messagebox.showinfo("Recuperação", "Se houver uma conta para esse endereço, enviaremos as instruções de recuperação. Configure o envio de e-mail para receber o link.")

    def _set_new_password(self, token):
        password = simpledialog.askstring("Nova senha", "Digite uma nova senha com pelo menos 8 caracteres:", show="•", parent=self)
        if not password:
            return
        try:
            self.auth.reset_password(token, password)
        except AuthenticationError as exc:
            messagebox.showerror("Não foi possível redefinir", str(exc))
            return
        messagebox.showinfo("Senha atualizada", "Sua senha foi alterada. Entre novamente.")

    def logout(self, show_message=True):
        self.user = None
        self.active_conversation_id = None
        self.show_auth()
        if show_message:
            messagebox.showinfo("Sessão encerrada", "Você saiu da sua conta.")

    def show_main(self):
        for child in self.winfo_children():
            child.destroy()
        header = ttk.Frame(self, padding=(18, 13))
        header.pack(fill="x")
        self._label(header, "Estuda+", "Title.TLabel").pack(side="left")
        self._label(header, f"Olá, {self.user['name']}", "Muted.TLabel").pack(side="left", padx=16, pady=(7, 0))
        unread = len(self.notifications.list_notifications(self.user["id"], unread_only=True))
        self.header_notifications = ttk.Button(header, text=f"Notificações ({unread})", command=lambda: self.tabs.select(self.notifications_page))
        self.header_notifications.pack(side="right", padx=(8, 0))
        ttk.Button(header, text="Sair", command=self.logout).pack(side="right")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.dashboard_page = ttk.Frame(self.tabs, padding=16)
        self.tasks_page = ttk.Frame(self.tabs, padding=16)
        self.focus_page = ttk.Frame(self.tabs, padding=16)
        self.chat_page = ttk.Frame(self.tabs, padding=16)
        self.notifications_page = ttk.Frame(self.tabs, padding=16)
        self.history_page = ttk.Frame(self.tabs, padding=16)
        self.account_page = ttk.Frame(self.tabs, padding=16)
        for page, title in ((self.dashboard_page, "Visão geral"), (self.tasks_page, "Tarefas"), (self.focus_page, "Foco"),
                            (self.chat_page, "Assistente"), (self.notifications_page, "Notificações"),
                            (self.history_page, "Histórico"), (self.account_page, "Conta")):
            self.tabs.add(page, text=title)
        if self.user["role"] == "admin":
            self.admin_page = ttk.Frame(self.tabs, padding=16)
            self.tabs.add(self.admin_page, text="Administração")
        self._build_dashboard()
        self._build_tasks()
        self._build_focus()
        self._build_chat()
        self._build_notifications()
        self._build_history()
        self._build_account()
        if self.user["role"] == "admin":
            self._build_admin()
        self._refresh_dashboard()
        self._refresh_tasks()
        self._refresh_notifications()
        self._load_conversations()
        self._tick_focus()

    def _build_dashboard(self):
        top = ttk.Frame(self.dashboard_page)
        top.pack(fill="x")
        self._label(top, "Seu progresso", "Title.TLabel").pack(side="left")
        self.period = ttk.Combobox(top, values=("7 dias", "30 dias", "Todo o período"), state="readonly", width=18)
        self.period.set("30 dias")
        self.period.pack(side="right")
        self.period.bind("<<ComboboxSelected>>", lambda _e: self._refresh_dashboard())
        cards = ttk.Frame(self.dashboard_page)
        cards.pack(fill="x", pady=18)
        self.metric_labels = {}
        for key, title in (("completed", "Concluídas"), ("pending", "Pendentes"), ("overdue", "Atrasadas"), ("focus", "Sessões concluídas"), ("time", "Tempo focado")):
            card = ttk.Frame(cards, style="Card.TFrame", padding=15)
            card.pack(side="left", fill="both", expand=True, padx=(0, 8))
            ttk.Label(card, text=title, background=WHITE, foreground=MUTED).pack(anchor="w")
            value = ttk.Label(card, text="—", background=WHITE, foreground=INK, font=("Segoe UI", 18, "bold"))
            value.pack(anchor="w", pady=(5, 0))
            self.metric_labels[key] = value
        self._label(self.dashboard_page, "Tarefas que precisam de atenção", "Section.TLabel").pack(anchor="w", pady=(8, 10))
        self.dashboard_tasks = ttk.Treeview(self.dashboard_page, columns=("title", "deadline", "status"), show="headings", height=10)
        for column, title, width in (("title", "Tarefa", 450), ("deadline", "Prazo", 180), ("status", "Status", 130)):
            self.dashboard_tasks.heading(column, text=title)
            self.dashboard_tasks.column(column, width=width, anchor="w")
        self.dashboard_tasks.pack(fill="both", expand=True)

    def _refresh_dashboard(self):
        if not self.user or not hasattr(self, "metric_labels"):
            return
        all_tasks = self.tasks.list_tasks(self.user["id"], status="Todas")
        completed = sum(row["status"] == "Concluída" for row in all_tasks)
        overdue = sum(row["status"] == "Pendente" and row["deadline"] < datetime.now(timezone.utc).isoformat() for row in all_tasks)
        pending = sum(row["status"] == "Pendente" and row["deadline"] >= datetime.now(timezone.utc).isoformat() for row in all_tasks)
        metrics = self.focus.metrics(self.user["id"], self.period.get() if hasattr(self, "period") else "30 dias")
        seconds = metrics["effective_seconds"]
        self.metric_labels["completed"].config(text=str(completed))
        self.metric_labels["pending"].config(text=str(pending))
        self.metric_labels["overdue"].config(text=str(overdue))
        self.metric_labels["focus"].config(text=str(metrics["completed_sessions"]))
        self.metric_labels["time"].config(text=f"{seconds // 3600}h {(seconds % 3600) // 60}min")
        for item in self.dashboard_tasks.get_children():
            self.dashboard_tasks.delete(item)
        for row in all_tasks:
            if row["status"] == "Pendente":
                status = "Atrasada" if row["deadline"] < datetime.now(timezone.utc).isoformat() else "Pendente"
                due = datetime.fromisoformat(row["deadline"]).astimezone().strftime("%d/%m/%Y %H:%M")
                self.dashboard_tasks.insert("", "end", iid=f"d{row['id']}", values=(row["title"], due, status))

    def _build_tasks(self):
        toolbar = ttk.Frame(self.tasks_page)
        toolbar.pack(fill="x")
        self._label(toolbar, "Gerencie prazos e etapas", "Title.TLabel").pack(side="left")
        ttk.Button(toolbar, text="+ Nova tarefa", style="Accent.TButton", command=lambda: self._task_dialog()).pack(side="right")
        filters = ttk.Frame(self.tasks_page)
        filters.pack(fill="x", pady=10)
        self.filter_status = ttk.Combobox(filters, values=("Todas", "Pendente", "Concluída", "Atrasada"), state="readonly", width=14)
        self.filter_status.set("Todas")
        self.filter_priority = ttk.Combobox(filters, values=("Todas", "Baixa", "Média", "Alta"), state="readonly", width=12)
        self.filter_priority.set("Todas")
        self.filter_from = ttk.Entry(filters, width=13)
        self.filter_to = ttk.Entry(filters, width=13)
        for caption, widget in (("Status", self.filter_status), ("Prioridade", self.filter_priority), ("Prazo de", self.filter_from), ("até", self.filter_to)):
            ttk.Label(filters, text=caption).pack(side="left", padx=(0, 5))
            widget.pack(side="left", padx=(0, 12), ipady=3)
        ttk.Button(filters, text="Filtrar", command=self._refresh_tasks).pack(side="left")
        ttk.Button(filters, text="Limpar", command=self._clear_filters).pack(side="left", padx=5)
        self._label(self.tasks_page, "Datas de prazo: AAAA-MM-DD", "Muted.TLabel").pack(anchor="w", pady=(0, 7))
        columns = ("title", "deadline", "priority", "status", "subtasks")
        self.task_tree = ttk.Treeview(self.tasks_page, columns=columns, show="headings", selectmode="browse")
        for col, caption, width in (("title", "Tarefa", 340), ("deadline", "Prazo", 170), ("priority", "Prioridade", 110), ("status", "Status", 110), ("subtasks", "Etapas pendentes", 125)):
            self.task_tree.heading(col, text=caption)
            self.task_tree.column(col, width=width, anchor="w")
        self.task_tree.pack(fill="both", expand=True)
        self.task_tree.bind("<<TreeviewSelect>>", self._task_selected)
        buttons = ttk.Frame(self.tasks_page)
        buttons.pack(fill="x", pady=(10, 0))
        for label, callback in (("Editar", self._edit_selected_task), ("Concluir / reabrir", self._toggle_task),
                                ("Subtarefas", self._manage_subtasks), ("Lembretes", self._manage_reminders),
                                ("Excluir", self._delete_task)):
            ttk.Button(buttons, text=label, command=callback).pack(side="left", padx=(0, 7))

    def _clear_filters(self):
        self.filter_status.set("Todas")
        self.filter_priority.set("Todas")
        self.filter_from.delete(0, "end")
        self.filter_to.delete(0, "end")
        self._refresh_tasks()

    def _refresh_tasks(self):
        if not self.user or not hasattr(self, "task_tree"):
            return
        date_from = self.filter_from.get().strip() if hasattr(self, "filter_from") else ""
        date_to = self.filter_to.get().strip() if hasattr(self, "filter_to") else ""
        try:
            if date_from:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc).isoformat()
            if date_to:
                date_to = (datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1) - timedelta(seconds=1)).isoformat()
            rows = self.tasks.list_tasks(self.user["id"], self.filter_status.get(), self.filter_priority.get(), date_from or None, date_to or None)
        except ValueError:
            messagebox.showerror("Data inválida", "Informe as datas no formato AAAA-MM-DD.")
            return
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        for row in rows:
            status = "Atrasada" if row["status"] == "Pendente" and row["deadline"] < datetime.now(timezone.utc).isoformat() else row["status"]
            due = datetime.fromisoformat(row["deadline"]).astimezone().strftime("%d/%m/%Y %H:%M")
            self.task_tree.insert("", "end", iid=str(row["id"]), values=(row["title"], due, row["priority"], status, row["pending_subtasks"]))
        self._refresh_dashboard()
        if hasattr(self, "focus_task"):
            self._refresh_focus_tasks()

    def _task_selected(self, _event=None):
        selection = self.task_tree.selection()
        self.selected_task_id = int(selection[0]) if selection else None

    def _selected_task(self):
        selection = self.task_tree.selection()
        return int(selection[0]) if selection else None

    def _task_dialog(self, task=None):
        dialog = tk.Toplevel(self)
        dialog.title("Editar tarefa" if task else "Nova tarefa")
        dialog.transient(self)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)
        title = self._field(frame, "Título (obrigatório; até 120 caracteres)")
        description = self._field(frame, "Descrição (opcional; até 1000 caracteres)")
        deadline = self._field(frame, "Prazo (DD/MM/AAAA HH:MM)")
        priority = ttk.Combobox(frame, values=("Baixa", "Média", "Alta"), state="readonly")
        priority.set("Média")
        ttk.Label(frame, text="Prioridade").pack(anchor="w", pady=(7, 4))
        priority.pack(fill="x", ipady=4)
        if task:
            title.insert(0, task["title"])
            description.insert(0, task["description"])
            deadline.insert(0, datetime.fromisoformat(task["deadline"]).astimezone().strftime("%d/%m/%Y %H:%M"))
            priority.set(task["priority"])
        else:
            deadline.insert(0, (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y %H:%M"))
        error = ttk.Label(frame, text="", foreground="#b42318", wraplength=420)
        error.pack(anchor="w", pady=(8, 0))
        def save():
            try:
                due = datetime.strptime(deadline.get().strip(), "%d/%m/%Y %H:%M").astimezone().astimezone(timezone.utc)
                if task:
                    self.tasks.edit_task(self.user["id"], task["id"], title.get(), due, priority.get(), description.get())
                else:
                    self.tasks.create_task(self.user["id"], title.get(), due, priority.get(), description.get())
            except (ValueError, TaskError) as exc:
                error.config(text=str(exc) if isinstance(exc, TaskError) else "Use o formato DD/MM/AAAA HH:MM para o prazo.")
                return
            dialog.destroy()
            self._refresh_tasks()
        ttk.Button(frame, text="Salvar tarefa", style="Accent.TButton", command=save).pack(fill="x", pady=(14, 0))
        title.focus_set()

    def _edit_selected_task(self):
        task_id = self._selected_task()
        if not task_id:
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma tarefa para editar.")
            return
        try:
            self._task_dialog(self.tasks.get_task(self.user["id"], task_id))
        except TaskError as exc:
            messagebox.showerror("Tarefa indisponível", str(exc))

    def _toggle_task(self):
        task_id = self._selected_task()
        if not task_id:
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma tarefa na lista primeiro.")
            return
        row = self.tasks.get_task(self.user["id"], task_id)
        try:
            self.tasks.set_completed(self.user["id"], task_id, row["status"] != "Concluída")
        except TaskError as exc:
            messagebox.showerror("Não foi possível concluir", str(exc))
        self._refresh_tasks()

    def _delete_task(self):
        task_id = self._selected_task()
        if not task_id:
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma tarefa na lista primeiro.")
            return
        if messagebox.askyesno("Excluir tarefa", "Excluir esta tarefa, subtarefas e lembretes? As sessões de foco concluídas permanecem no histórico."):
            try:
                self.tasks.delete_task(self.user["id"], task_id)
            except TaskError as exc:
                messagebox.showerror("Não foi possível excluir", str(exc))
            self._refresh_tasks()

    def _manage_subtasks(self):
        task_id = self._selected_task()
        if not task_id:
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma tarefa na lista primeiro.")
            return
        task = self.tasks.get_task(self.user["id"], task_id)
        dialog = tk.Toplevel(self)
        dialog.title("Subtarefas")
        dialog.geometry("560x460")
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        self._label(frame, task["title"], "Title.TLabel").pack(anchor="w", pady=(0, 10))
        tree = ttk.Treeview(frame, columns=("done", "title"), show="headings", selectmode="browse")
        tree.heading("done", text="Status")
        tree.heading("title", text="Subtarefa")
        tree.column("done", width=95)
        tree.column("title", width=380)
        tree.pack(fill="both", expand=True)
        def refresh():
            for item in tree.get_children(): tree.delete(item)
            for item in self.tasks.list_subtasks(self.user["id"], task_id):
                tree.insert("", "end", iid=str(item["id"]), values=("Concluída" if item["done"] else "Pendente", item["title"]))
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(10, 0))
        entry = ttk.Entry(row)
        entry.pack(side="left", fill="x", expand=True, ipady=5)
        def add():
            try:
                self.tasks.add_subtask(self.user["id"], task_id, entry.get())
                entry.delete(0, "end")
                refresh()
                self._refresh_tasks()
            except TaskError as exc:
                messagebox.showerror("Subtarefa inválida", str(exc), parent=dialog)
        ttk.Button(row, text="Adicionar", command=add).pack(side="left", padx=(7, 0))
        def toggle():
            selected = tree.selection()
            if not selected: return
            item = next((x for x in self.tasks.list_subtasks(self.user["id"], task_id) if x["id"] == int(selected[0])), None)
            if item:
                all_done = self.tasks.set_subtask_done(self.user["id"], item["id"], not bool(item["done"]))
                if all_done:
                    self.notifications.add(self.user["id"], f"Todas as subtarefas de {task['title']} foram concluídas.", "Task")
                refresh()
                self._refresh_tasks()
                self._refresh_notifications()
        ttk.Button(frame, text="Marcar / desmarcar conclusão", command=toggle).pack(anchor="w", pady=(8, 0))
        refresh()

    def _manage_reminders(self):
        task_id = self._selected_task()
        if not task_id:
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma tarefa para configurar lembretes.")
            return
        task = self.tasks.get_task(self.user["id"], task_id)
        dialog = tk.Toplevel(self)
        dialog.title("Lembretes")
        dialog.geometry("580x450")
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        self._label(frame, f"Lembretes · {task['title']}", "Title.TLabel").pack(anchor="w", pady=(0, 10))
        tree = ttk.Treeview(frame, columns=("when", "email", "status"), show="headings")
        for col, caption, width in (("when", "Data e hora", 190), ("email", "E-mail", 100), ("status", "Status", 120)):
            tree.heading(col, text=caption); tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        def refresh():
            for item in tree.get_children(): tree.delete(item)
            for reminder in self.tasks.list_reminders(self.user["id"], task_id):
                when = datetime.fromisoformat(reminder["scheduled_at"]).astimezone().strftime("%d/%m/%Y %H:%M")
                tree.insert("", "end", values=(when, "Sim" if reminder["email_enabled"] else "Não", reminder["status"]))
        self._label(frame, "Novo lembrete (DD/MM/AAAA HH:MM)", "Muted.TLabel").pack(anchor="w", pady=(12, 4))
        when = ttk.Entry(frame)
        when.pack(fill="x", ipady=4)
        email_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Também enviar por e-mail (desativado por padrão)", variable=email_enabled).pack(anchor="w", pady=6)
        def add():
            try:
                local_dt = datetime.strptime(when.get().strip(), "%d/%m/%Y %H:%M").astimezone().astimezone(timezone.utc)
                self.tasks.add_reminder(self.user["id"], task_id, local_dt, email_enabled.get())
                when.delete(0, "end"); refresh()
            except (ValueError, TaskError) as exc:
                messagebox.showerror("Lembrete inválido", str(exc) if isinstance(exc, TaskError) else "Data no formato DD/MM/AAAA HH:MM.", parent=dialog)
        ttk.Button(frame, text="Adicionar lembrete", style="Accent.TButton", command=add).pack(anchor="w", pady=(5, 0))
        refresh()

    def _build_focus(self):
        self._label(self.focus_page, "Sessão de foco", "Title.TLabel").pack(anchor="w")
        self._label(self.focus_page, "Escolha uma tarefa pendente e concentre-se em uma etapa por vez.", "Muted.TLabel").pack(anchor="w", pady=(3, 18))
        form = ttk.Frame(self.focus_page, style="Card.TFrame", padding=18)
        form.pack(fill="x")
        ttk.Label(form, text="Tarefa", background=WHITE).grid(row=0, column=0, sticky="w")
        self.focus_task = ttk.Combobox(form, state="readonly", width=58)
        self.focus_task.grid(row=1, column=0, sticky="ew", padx=(0, 15), pady=(5, 12))
        ttk.Label(form, text="Duração (minutos)", background=WHITE).grid(row=0, column=1, sticky="w")
        self.focus_duration = tk.Spinbox(form, from_=1, to=240, width=8)
        self.focus_duration.delete(0, "end"); self.focus_duration.insert(0, "25")
        self.focus_duration.grid(row=1, column=1, sticky="w", pady=(5, 12))
        form.columnconfigure(0, weight=1)
        buttons = ttk.Frame(form, style="Card.TFrame")
        buttons.grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Button(buttons, text="Iniciar", style="Accent.TButton", command=self._start_focus).pack(side="left", padx=(0, 7))
        ttk.Button(buttons, text="Pausar", command=self._pause_focus).pack(side="left", padx=7)
        ttk.Button(buttons, text="Retomar", command=self._resume_focus).pack(side="left", padx=7)
        ttk.Button(buttons, text="Encerrar", command=self._terminate_focus).pack(side="left", padx=7)
        self.focus_status = ttk.Label(self.focus_page, text="Nenhuma sessão ativa", font=("Segoe UI", 19, "bold"))
        self.focus_status.pack(anchor="center", pady=(45, 10))
        self.focus_progress = ttk.Progressbar(self.focus_page, mode="determinate", maximum=100)
        self.focus_progress.pack(fill="x", padx=40)
        self.focus_detail = ttk.Label(self.focus_page, text="", style="Muted.TLabel")
        self.focus_detail.pack(anchor="center", pady=8)
        self._refresh_focus_tasks()

    def _refresh_focus_tasks(self):
        if not hasattr(self, "focus_task"):
            return
        rows = self.tasks.list_tasks(self.user["id"], status="Pendente")
        self._focus_rows = rows
        self.focus_task["values"] = [f"{row['id']} · {row['title']}" for row in rows]
        if rows and not self.focus_task.get():
            self.focus_task.current(0)

    def _start_focus(self):
        selection = self.focus_task.get()
        if not selection:
            messagebox.showinfo("Selecione uma tarefa", "Crie ou selecione uma tarefa pendente primeiro.")
            return
        try:
            task_id = int(selection.split(" · ", 1)[0])
            session_id = self.focus.start(self.user["id"], task_id, int(self.focus_duration.get()))
            self._refresh_history()
        except (ValueError, FocusError) as exc:
            messagebox.showerror("Não foi possível iniciar", str(exc))
            return
        logger.info("Sessão iniciada na interface (session_id=%s)", session_id)
        self._tick_focus()

    def _pause_focus(self):
        try:
            self.focus.pause(self.user["id"])
        except FocusError as exc:
            messagebox.showinfo("Sessão de foco", str(exc))
        self._tick_focus()

    def _resume_focus(self):
        try:
            self.focus.resume(self.user["id"])
        except FocusError as exc:
            messagebox.showinfo("Sessão de foco", str(exc))
        self._tick_focus()

    def _terminate_focus(self):
        try:
            self.focus.terminate(self.user["id"])
        except FocusError as exc:
            messagebox.showinfo("Sessão de foco", str(exc))
        self._tick_focus()
        self._refresh_history()
        self._refresh_dashboard()

    def _tick_focus(self):
        if not self.user or not hasattr(self, "focus_status"):
            return
        session = self.focus.tick(self.user["id"])
        if not session:
            self.focus_status.config(text="Nenhuma sessão ativa")
            self.focus_detail.config(text="Duração padrão: 25 minutos")
            self.focus_progress["value"] = 0
            return
        seconds = session["elapsed_seconds"]
        remaining = max(0, session["duration_seconds"] - seconds)
        self.focus_status.config(text=f"{remaining // 60:02d}:{remaining % 60:02d} · {session['status']}")
        self.focus_detail.config(text=f"{session['task_title']} · decorrido {seconds // 60:02d}:{seconds % 60:02d}")
        self.focus_progress["value"] = min(100, 100 * seconds / session["duration_seconds"])
        if session["status"] == "Completed":
            self._refresh_notifications()
            self._refresh_history()
            self._refresh_dashboard()

    def _build_chat(self):
        top = ttk.Frame(self.chat_page)
        top.pack(fill="x")
        self._label(top, "Assistente de estudos", "Title.TLabel").pack(side="left")
        ttk.Button(top, text="+ Nova conversa", command=self._new_conversation).pack(side="right")
        self._label(self.chat_page, "A conversa usa um provedor de IA externo quando OPENAI_API_KEY está configurada.", "Muted.TLabel").pack(anchor="w", pady=(3, 8))
        selector = ttk.Frame(self.chat_page)
        selector.pack(fill="x", pady=(0, 8))
        ttk.Label(selector, text="Conversa").pack(side="left", padx=(0, 6))
        self.conversation_box = ttk.Combobox(selector, state="readonly", width=54)
        self.conversation_box.pack(side="left", fill="x", expand=True)
        self.conversation_box.bind("<<ComboboxSelected>>", self._conversation_selected)
        self.chat_log = tk.Text(self.chat_page, wrap="word", state="disabled", font=("Segoe UI", 10), bg=WHITE, relief="flat", padx=14, pady=12)
        self.chat_log.pack(fill="both", expand=True)
        self.chat_log.tag_configure("user", foreground=ACCENT, spacing1=8, font=("Segoe UI", 10, "bold"))
        self.chat_log.tag_configure("assistant", foreground=INK, spacing1=8)
        self.chat_log.tag_configure("failed", foreground="#b42318", spacing1=8)
        compose = ttk.Frame(self.chat_page)
        compose.pack(fill="x", pady=(10, 0))
        self.chat_entry = ttk.Entry(compose, font=("Segoe UI", 11))
        self.chat_entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.chat_entry.bind("<Return>", lambda _event: self._send_chat())
        self.chat_complex = tk.BooleanVar(value=False)
        ttk.Checkbutton(compose, text="Sugerir subtarefas", variable=self.chat_complex).pack(side="left", padx=8)
        self.chat_send_button = ttk.Button(compose, text="Enviar", style="Accent.TButton", command=self._send_chat)
        self.chat_send_button.pack(side="left")
        suggestion_frame = ttk.LabelFrame(self.chat_page, text="Propostas de subtarefa · aceite para adicionar")
        suggestion_frame.pack(fill="x", pady=(10, 0))
        self.suggestion_tree = ttk.Treeview(suggestion_frame, columns=("title",), show="headings", height=3, selectmode="browse")
        self.suggestion_tree.heading("title", text="Proposta")
        self.suggestion_tree.column("title", width=500, anchor="w")
        self.suggestion_tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        controls = ttk.Frame(suggestion_frame)
        controls.pack(side="left", fill="y", padx=7)
        self.suggestion_task = ttk.Combobox(controls, state="readonly", width=27)
        self.suggestion_task.pack(fill="x", pady=(5, 6))
        self.suggestion_title = ttk.Entry(controls, width=30)
        self.suggestion_title.pack(fill="x", pady=(0, 6))
        ttk.Button(controls, text="Aceitar / editar título", command=self._accept_suggestion).pack(fill="x", pady=2)
        ttk.Button(controls, text="Rejeitar proposta", command=self._reject_suggestion).pack(fill="x", pady=2)
        failures = ttk.Frame(self.chat_page)
        failures.pack(fill="x", pady=(8, 0))
        ttk.Label(failures, text="Mensagens com falha").pack(side="left")
        self.failed_messages = ttk.Combobox(failures, state="readonly", width=68)
        self.failed_messages.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(failures, text="Reenviar", command=self._resend_failed).pack(side="left")

    def _load_conversations(self):
        rows = self.chat.list_conversations(self.user["id"])
        if not rows:
            conversation_id = self.chat.create_conversation(self.user["id"])
            rows = self.chat.list_conversations(self.user["id"])
            self.active_conversation_id = conversation_id
        elif self.active_conversation_id not in {row["id"] for row in rows}:
            self.active_conversation_id = rows[0]["id"]
        self._conversation_rows = rows
        self.conversation_box["values"] = [f"{row['id']} · {row['title']}" for row in rows]
        current = next((f"{row['id']} · {row['title']}" for row in rows if row["id"] == self.active_conversation_id), "")
        self.conversation_box.set(current)
        self._load_messages()
        self._load_suggestions()

    def _new_conversation(self):
        self.active_conversation_id = self.chat.create_conversation(self.user["id"])
        self._load_conversations()

    def _conversation_selected(self, _event=None):
        try:
            self.active_conversation_id = int(self.conversation_box.get().split(" · ", 1)[0])
        except ValueError:
            return
        self._load_messages()
        self._load_suggestions()

    def _load_messages(self):
        if not self.user or not self.active_conversation_id or not hasattr(self, "chat_log"):
            return
        rows = self.chat.messages(self.user["id"], self.active_conversation_id)
        self.chat_log.config(state="normal")
        self.chat_log.delete("1.0", "end")
        if not rows:
            self.chat_log.insert("end", "Assistente\n", "assistant")
            self.chat_log.insert("end", "Olá! Conte qual matéria ou atividade você quer começar. Também pode marcar ‘Sugerir subtarefas’ para dividir uma tarefa complexa.\n\n", "assistant")
        for row in rows:
            if row["role"] == "user":
                who = "Você"
                tag = "failed" if row["status"] == "Failed" else "user"
                suffix = " · falhou, você pode reenviar" if row["status"] == "Failed" else ""
            else:
                who, tag, suffix = "Assistente", "assistant", ""
            self.chat_log.insert("end", who + suffix + "\n", tag)
            self.chat_log.insert("end", row["content"] + "\n\n", tag)
        self.chat_log.config(state="disabled")
        self.chat_log.see("end")
        failed = [row for row in rows if row["role"] == "user" and row["status"] == "Failed"]
        self._failed_rows = failed
        self.failed_messages["values"] = [f"{row['id']} · {row['content'][:65]}" for row in failed]
        self.failed_messages.set(f"{failed[-1]['id']} · {failed[-1]['content'][:65]}" if failed else "")

    def _load_suggestions(self):
        if not self.user or not self.active_conversation_id or not hasattr(self, "suggestion_tree"):
            return
        for item in self.suggestion_tree.get_children(): self.suggestion_tree.delete(item)
        suggestions = self.chat.list_suggestions(self.user["id"], self.active_conversation_id)
        self._suggestion_rows = suggestions
        for row in suggestions:
            self.suggestion_tree.insert("", "end", iid=str(row["id"]), values=(row["title"],))
        tasks = self.tasks.list_tasks(self.user["id"], status="Pendente")
        self._suggestion_task_rows = tasks
        self.suggestion_task["values"] = [f"{row['id']} · {row['title']}" for row in tasks]
        if tasks and not self.suggestion_task.get():
            self.suggestion_task.current(0)

    def _send_chat(self):
        content = self.chat_entry.get().strip()
        if not content or not self.active_conversation_id:
            return
        self.chat_entry.delete(0, "end")
        self.chat_send_button.config(state="disabled")
        self.chat_log.config(state="normal")
        self.chat_log.insert("end", "Você\n" + content + "\n\n", "user")
        self.chat_log.insert("end", "Assistente\nRespondendo…\n\n", "assistant")
        self.chat_log.config(state="disabled")
        args = (dict(self.user), self.active_conversation_id, content, self.chat_complex.get())
        threading.Thread(target=self._chat_worker, args=args, daemon=True).start()

    def _chat_worker(self, user, conversation_id, content, complex_task):
        try:
            result = self.chat.send(user, conversation_id, content, complex_task)
            self.worker_queue.put(("chat_success", result))
        except (ChatError, AIUnavailable) as exc:
            self.worker_queue.put(("chat_error", str(exc)))
        finally:
            self.worker_queue.put(("chat_finished", None))

    def _resend_failed(self):
        if not self.failed_messages.get():
            messagebox.showinfo("Sem mensagens com falha", "Não há mensagem para reenviar nesta conversa.")
            return
        try:
            message_id = int(self.failed_messages.get().split(" · ", 1)[0])
        except ValueError:
            return
        threading.Thread(target=self._resend_worker, args=(dict(self.user), message_id), daemon=True).start()

    def _resend_worker(self, user, message_id):
        try:
            self.chat.resend(user, message_id, self.chat_complex.get())
            self.worker_queue.put(("chat_success", None))
        except (ChatError, AIUnavailable) as exc:
            self.worker_queue.put(("chat_error", str(exc)))

    def _accept_suggestion(self):
        selected = self.suggestion_tree.selection()
        target = self.suggestion_task.get()
        if not selected or not target:
            messagebox.showinfo("Escolha a proposta e a tarefa", "Selecione uma proposta e uma tarefa pendente.")
            return
        suggestion_id, task_id = int(selected[0]), int(target.split(" · ", 1)[0])
        title = self.suggestion_title.get().strip() or None
        try:
            self.chat.accept_suggestion(self.user["id"], suggestion_id, task_id, title)
        except (ChatError, TaskError) as exc:
            messagebox.showerror("Não foi possível adicionar", str(exc))
            return
        self.suggestion_title.delete(0, "end")
        self._load_suggestions(); self._refresh_tasks()

    def _reject_suggestion(self):
        selected = self.suggestion_tree.selection()
        if not selected:
            return
        try:
            self.chat.reject_suggestion(self.user["id"], int(selected[0]))
        except ChatError as exc:
            messagebox.showerror("Proposta", str(exc))
        self._load_suggestions()

    def _build_notifications(self):
        toolbar = ttk.Frame(self.notifications_page)
        toolbar.pack(fill="x")
        self._label(toolbar, "Notificações", "Title.TLabel").pack(side="left")
        ttk.Button(toolbar, text="Marcar todas como lidas", command=self._mark_all_read).pack(side="right")
        self.notification_tree = ttk.Treeview(self.notifications_page, columns=("status", "message", "date"), show="headings")
        for col, title, width in (("status", "Leitura", 110), ("message", "Aviso", 560), ("date", "Data", 180)):
            self.notification_tree.heading(col, text=title); self.notification_tree.column(col, width=width, anchor="w")
        self.notification_tree.pack(fill="both", expand=True, pady=12)
        ttk.Button(self.notifications_page, text="Marcar selecionada como lida", command=self._mark_notification_read).pack(anchor="w")

    def _refresh_notifications(self):
        if not self.user or not hasattr(self, "notification_tree"):
            return
        for item in self.notification_tree.get_children(): self.notification_tree.delete(item)
        rows = self.notifications.list_notifications(self.user["id"])
        for row in rows:
            status = "Não lida" if not row["read_at"] else "Lida"
            try: date = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).astimezone().strftime("%d/%m/%Y %H:%M")
            except ValueError: date = row["created_at"]
            self.notification_tree.insert("", "end", iid=str(row["id"]), values=(status, row["message"], date))
        unread = sum(not row["read_at"] for row in rows)
        if hasattr(self, "header_notifications"):
            self.header_notifications.config(text=f"Notificações ({unread})")

    def _mark_notification_read(self):
        selection = self.notification_tree.selection()
        if selection:
            self.notifications.mark_read(self.user["id"], int(selection[0]))
            self._refresh_notifications()

    def _mark_all_read(self):
        self.notifications.mark_read(self.user["id"])
        self._refresh_notifications()

    def _build_history(self):
        top = ttk.Frame(self.history_page)
        top.pack(fill="x")
        self._label(top, "Histórico de atividade", "Title.TLabel").pack(side="left")
        self.history_period = ttk.Combobox(top, values=("7 dias", "30 dias", "Todo o período"), state="readonly", width=18)
        self.history_period.set("30 dias")
        self.history_period.pack(side="right")
        self.history_period.bind("<<ComboboxSelected>>", lambda _e: self._refresh_history())
        self._label(self.history_page, "Tarefas", "Section.TLabel").pack(anchor="w", pady=(14, 6))
        self.task_history = ttk.Treeview(self.history_page, columns=("title", "status", "deadline", "completed"), show="headings", height=8)
        for col, caption, width in (("title", "Tarefa", 330), ("status", "Status", 120), ("deadline", "Prazo", 160), ("completed", "Concluída em", 170)):
            self.task_history.heading(col, text=caption); self.task_history.column(col, width=width, anchor="w")
        self.task_history.pack(fill="both", expand=True)
        self._label(self.history_page, "Sessões de foco", "Section.TLabel").pack(anchor="w", pady=(14, 6))
        self.focus_history = ttk.Treeview(self.history_page, columns=("task", "status", "start", "duration"), show="headings", height=7)
        for col, caption, width in (("task", "Tarefa", 330), ("status", "Status", 120), ("start", "Iniciada em", 180), ("duration", "Tempo efetivo", 140)):
            self.focus_history.heading(col, text=caption); self.focus_history.column(col, width=width, anchor="w")
        self.focus_history.pack(fill="both", expand=True)
        self._refresh_history()

    def _refresh_history(self):
        if not self.user or not hasattr(self, "task_history"):
            return
        for item in self.task_history.get_children(): self.task_history.delete(item)
        period = self.history_period.get() if hasattr(self, "history_period") else "Todo o período"
        date_filter = ""
        if period == "7 dias": date_filter = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        elif period == "30 dias": date_filter = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        with self.database.connection() as db:
            query = "SELECT * FROM tasks WHERE user_id=?"
            params = [self.user["id"]]
            if date_filter:
                query += " AND (completed_at>=? OR status='Pendente')"; params.append(date_filter)
            tasks = db.execute(query + " ORDER BY COALESCE(completed_at,deadline) DESC", params).fetchall()
        for task in tasks:
            due = datetime.fromisoformat(task["deadline"]).astimezone().strftime("%d/%m/%Y %H:%M")
            completed = datetime.fromisoformat(task["completed_at"]).astimezone().strftime("%d/%m/%Y %H:%M") if task["completed_at"] else "—"
            self.task_history.insert("", "end", values=(task["title"], task["status"], due, completed))
        for item in self.focus_history.get_children(): self.focus_history.delete(item)
        for session in self.focus.history(self.user["id"], period):
            start = datetime.fromisoformat(session["started_at"]).astimezone().strftime("%d/%m/%Y %H:%M")
            secs = session["effective_seconds"]
            self.focus_history.insert("", "end", values=(session["task_title"], session["status"], start, f"{secs // 60} min {secs % 60} s"))

    def _build_account(self):
        self._label(self.account_page, "Conta e privacidade", "Title.TLabel").pack(anchor="w", pady=(0, 12))
        self._label(self.account_page, f"Nome: {self.user['name']}\nE-mail: {self.user['email']}\nPerfil: {'Administrador' if self.user['role'] == 'admin' else 'Estudante'}", "Muted.TLabel", justify="left").pack(anchor="w")
        policy = ("Este aplicativo guarda nome, e-mail, tarefas, mensagens e sessões no banco local deste computador. "
                  "Quando configurado, o texto da conversa (com nome e e-mail identificáveis removidos) é enviado ao provedor de IA; "
                  "o envio de e-mail só ocorre para recuperação e lembretes explicitamente marcados. A exclusão da conta apaga seus dados locais.")
        ttk.Label(self.account_page, text=policy, wraplength=760, justify="left").pack(anchor="w", pady=20)
        ttk.Button(self.account_page, text="Excluir minha conta…", command=self._delete_account).pack(anchor="w")

    def _delete_account(self):
        if not messagebox.askyesno("Excluir conta permanentemente", "Esta ação apagará permanentemente suas tarefas, conversas, mensagens, notificações e sessões de foco. Deseja continuar?"):
            return
        try:
            self.auth.delete_account(self.user["id"], confirmed=True)
        except AuthenticationError as exc:
            messagebox.showerror("Não foi possível excluir", str(exc))
            return
        self.user = None
        self.show_auth()
        messagebox.showinfo("Conta excluída", "Sua conta e seus dados foram removidos deste computador.")

    def _build_admin(self):
        self._label(self.admin_page, "Configurações do assistente", "Title.TLabel").pack(anchor="w", pady=(0, 12))
        settings = self.auth.get_settings()
        self.ai_enabled_var = tk.BooleanVar(value=bool(settings["ai_enabled"]))
        ttk.Checkbutton(self.admin_page, text="Habilitar o assistente de IA para estudantes", variable=self.ai_enabled_var).pack(anchor="w", pady=6)
        row = ttk.Frame(self.admin_page)
        row.pack(anchor="w", pady=8)
        ttk.Label(row, text="Máximo de respostas do assistente por usuário por dia").pack(side="left", padx=(0, 10))
        self.ai_limit = tk.Spinbox(row, from_=1, to=500, width=7)
        self.ai_limit.delete(0, "end"); self.ai_limit.insert(0, str(settings["daily_message_limit"]))
        self.ai_limit.pack(side="left")
        ttk.Button(self.admin_page, text="Salvar configurações", style="Accent.TButton", command=self._save_admin_settings).pack(anchor="w", pady=10)
        self._label(self.admin_page, "Credenciais de IA e e-mail são configuradas no ambiente, nunca salvas no código ou no banco.", "Muted.TLabel", wraplength=720).pack(anchor="w", pady=6)

    def _save_admin_settings(self):
        try:
            self.auth.update_ai_settings(self.user["id"], self.ai_enabled_var.get(), int(self.ai_limit.get()))
        except (ValueError, AuthenticationError) as exc:
            messagebox.showerror("Configuração inválida", str(exc))
            return
        messagebox.showinfo("Configurações salvas", "Os limites do assistente foram atualizados.")



