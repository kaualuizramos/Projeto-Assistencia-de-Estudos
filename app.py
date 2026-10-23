"""Protótipo demonstrativo de assistência de estudos. Execute com: python app.py"""

import hashlib
import hmac
import os
import re
import sqlite3
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assistente_estudos.db")
BG = "#f4f6fb"
INK = "#172033"
MUTED = "#667085"
ACCENT = "#5146e5"


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize():
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                deadline TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Média',
                status TEXT NOT NULL DEFAULT 'Pendente'
            );
            CREATE TABLE IF NOT EXISTS subtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)


def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240_000)
    return salt, digest


class StudyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Estuda+ | Assistente de estudos")
        self.geometry("1040x720")
        self.minsize(900, 620)
        self.configure(bg=BG)
        self.user = None
        self.selected_task_id = None
        self.setup_style()
        self.show_auth()

    def setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background="white")
        style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 23, "bold"), foreground=INK)
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground=MUTED)
        style.configure("CardTitle.TLabel", background="white", font=("Segoe UI", 13, "bold"), foreground=INK)
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure("Accent.TButton", background=ACCENT, foreground="white", borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#4035c7")])
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=32, background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#eef0f8")

    def label(self, parent, text, style=None, **kwargs):
        return ttk.Label(parent, text=text, style=style or "TLabel", **kwargs)

    def show_auth(self):
        for child in self.winfo_children():
            child.destroy()
        wrapper = ttk.Frame(self, padding=34)
        wrapper.pack(expand=True)
        self.label(wrapper, "Estuda+", "Title.TLabel").pack(anchor="w")
        self.label(wrapper, "Organize seus estudos e peça ajuda para começar.", "Subtitle.TLabel").pack(anchor="w", pady=(3, 20))
        card = ttk.Frame(wrapper, style="Card.TFrame", padding=24)
        card.pack(fill="both", expand=True)
        tabs = ttk.Notebook(card)
        tabs.pack(fill="both", expand=True)
        login = ttk.Frame(tabs, style="Card.TFrame", padding=18)
        register = ttk.Frame(tabs, style="Card.TFrame", padding=18)
        tabs.add(login, text="Entrar")
        tabs.add(register, text="Criar conta")
        self.login_email = self.field(login, "E-mail")
        self.login_password = self.field(login, "Senha", show="•")
        ttk.Button(login, text="Entrar", style="Accent.TButton", command=self.login).pack(fill="x", pady=(14, 0))
        self.register_name = self.field(register, "Seu nome")
        self.register_email = self.field(register, "E-mail")
        self.register_password = self.field(register, "Senha (mínimo 8 caracteres)", show="•")
        ttk.Button(register, text="Criar conta", style="Accent.TButton", command=self.register).pack(fill="x", pady=(14, 0))

    def field(self, parent, caption, show=None):
        group = ttk.Frame(parent, style="Card.TFrame")
        group.pack(fill="x", pady=6)
        self.label(group, caption).pack(anchor="w", pady=(0, 4))
        entry = ttk.Entry(group, show=show, font=("Segoe UI", 11))
        entry.pack(fill="x", ipady=6)
        return entry

    def register(self):
        name, email, password = self.register_name.get().strip(), self.register_email.get().strip().lower(), self.register_password.get()
        if not name or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            messagebox.showerror("Confira os dados", "Informe seu nome e um e-mail válido.")
            return
        if len(password) < 8:
            messagebox.showerror("Senha curta", "A senha deve ter pelo menos 8 caracteres.")
            return
        salt, digest = hash_password(password)
        try:
            with connect() as db:
                db.execute("INSERT INTO users(name,email,salt,password_hash) VALUES(?,?,?,?)", (name, email, salt, digest))
            messagebox.showinfo("Conta criada", "Agora você já pode entrar.")
        except sqlite3.IntegrityError:
            messagebox.showerror("E-mail já cadastrado", "Este e-mail já está em uso.")

    def login(self):
        email, password = self.login_email.get().strip().lower(), self.login_password.get()
        with connect() as db:
            row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if row:
            _, digest = hash_password(password, row["salt"])
            if hmac.compare_digest(digest, row["password_hash"]):
                self.user = row
                self.show_dashboard()
                return
        messagebox.showerror("Não foi possível entrar", "E-mail ou senha inválidos.")

    def show_dashboard(self):
        for child in self.winfo_children():
            child.destroy()
        header = ttk.Frame(self, padding=(24, 18))
        header.pack(fill="x")
        self.label(header, "Estuda+", "Title.TLabel").pack(side="left")
        self.label(header, f"Olá, {self.user['name']}", "Subtitle.TLabel").pack(side="left", padx=20, pady=(8, 0))
        ttk.Button(header, text="Sair", command=self.logout).pack(side="right")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=22, pady=(0, 22))
        self.tasks_page = ttk.Frame(self.tabs, padding=20)
        self.chat_page = ttk.Frame(self.tabs, padding=20)
        self.tabs.add(self.tasks_page, text="  Minhas tarefas  ")
        self.tabs.add(self.chat_page, text="  Assistente de estudos  ")
        self.build_tasks()
        self.build_chat()

    def logout(self):
        self.user = None
        self.show_auth()

    def build_tasks(self):
        top = ttk.Frame(self.tasks_page)
        top.pack(fill="x")
        self.label(top, "Suas tarefas", "Title.TLabel").pack(side="left")
        ttk.Button(top, text="+ Nova tarefa", style="Accent.TButton", command=self.new_task).pack(side="right")
        self.task_summary = self.label(self.tasks_page, "", "Subtitle.TLabel")
        self.task_summary.pack(anchor="w", pady=(8, 14))
        columns = ("title", "deadline", "priority", "status")
        self.task_tree = ttk.Treeview(self.tasks_page, columns=columns, show="headings", selectmode="browse")
        for col, caption, width in [("title", "Tarefa", 340), ("deadline", "Prazo", 170), ("priority", "Prioridade", 120), ("status", "Status", 120)]:
            self.task_tree.heading(col, text=caption)
            self.task_tree.column(col, width=width, anchor="w")
        self.task_tree.pack(fill="both", expand=True)
        self.task_tree.bind("<<TreeviewSelect>>", self.on_task_select)
        buttons = ttk.Frame(self.tasks_page)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Concluir / reabrir", command=self.toggle_task).pack(side="left")
        ttk.Button(buttons, text="Excluir", command=self.delete_task).pack(side="left", padx=8)
        ttk.Button(buttons, text="Ver subtarefas", command=self.manage_subtasks).pack(side="left")
        self.refresh_tasks()

    def refresh_tasks(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with connect() as db:
            rows = db.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY status='Concluída', deadline", (self.user["id"],)).fetchall()
        pending = 0
        for row in rows:
            status = "Atrasada" if row["status"] == "Pendente" and row["deadline"] < now else row["status"]
            pending += status != "Concluída"
            deadline = datetime.strptime(row["deadline"], "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
            self.task_tree.insert("", "end", iid=str(row["id"]), values=(row["title"], deadline, row["priority"], status))
        self.task_summary.config(text=f"{len(rows)} tarefa(s) · {pending} em aberto")

    def new_task(self):
        dialog = tk.Toplevel(self)
        dialog.title("Nova tarefa")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="both", expand=True)
        title = self.field(form, "Título (obrigatório)")
        desc = self.field(form, "Descrição (opcional)")
        deadline = self.field(form, "Prazo (DD/MM/AAAA HH:MM)")
        deadline.insert(0, (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M"))
        self.label(form, "Prioridade").pack(anchor="w", pady=(6, 4))
        priority = ttk.Combobox(form, values=("Baixa", "Média", "Alta"), state="readonly")
        priority.set("Média")
        priority.pack(fill="x", ipady=4)
        def save():
            name = title.get().strip()
            if not name or len(name) > 120:
                messagebox.showerror("Título inválido", "Informe um título com até 120 caracteres.", parent=dialog)
                return
            try:
                due = datetime.strptime(deadline.get().strip(), "%d/%m/%Y %H:%M")
            except ValueError:
                messagebox.showerror("Prazo inválido", "Use o formato DD/MM/AAAA HH:MM.", parent=dialog)
                return
            if due <= datetime.now():
                messagebox.showerror("Prazo inválido", "O prazo deve estar no futuro.", parent=dialog)
                return
            with connect() as db:
                db.execute("INSERT INTO tasks(user_id,title,description,deadline,priority) VALUES(?,?,?,?,?)",
                           (self.user["id"], name, desc.get().strip()[:1000], due.strftime("%Y-%m-%d %H:%M"), priority.get()))
            dialog.destroy()
            self.refresh_tasks()
        ttk.Button(form, text="Salvar tarefa", style="Accent.TButton", command=save).pack(fill="x", pady=(16, 0))
        title.focus_set()

    def selected_task(self):
        selection = self.task_tree.selection()
        return int(selection[0]) if selection else None

    def on_task_select(self, _event=None):
        self.selected_task_id = self.selected_task()

    def toggle_task(self):
        task_id = self.selected_task()
        if not task_id:
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma tarefa na lista primeiro.")
            return
        with connect() as db:
            row = db.execute("SELECT status FROM tasks WHERE id=? AND user_id=?", (task_id, self.user["id"])).fetchone()
            if not row:
                return
            new_status = "Pendente" if row["status"] == "Concluída" else "Concluída"
            if new_status == "Concluída":
                remaining = db.execute("SELECT COUNT(*) FROM subtasks WHERE task_id=? AND done=0", (task_id,)).fetchone()[0]
                if remaining:
                    messagebox.showerror("Ainda há etapas pendentes", f"Conclua as {remaining} subtarefa(s) antes de finalizar esta tarefa.")
                    return
            db.execute("UPDATE tasks SET status=? WHERE id=? AND user_id=?", (new_status, task_id, self.user["id"]))
        self.refresh_tasks()

    def delete_task(self):
        task_id = self.selected_task()
        if not task_id:
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma tarefa na lista primeiro.")
            return
        if messagebox.askyesno("Excluir tarefa", "Excluir esta tarefa e suas subtarefas?"):
            with connect() as db:
                db.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, self.user["id"]))
            self.refresh_tasks()

    def manage_subtasks(self):
        task_id = self.selected_task()
        if not task_id:
            messagebox.showinfo("Selecione uma tarefa", "Escolha uma tarefa na lista primeiro.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Subtarefas")
        dialog.configure(bg=BG)
        dialog.geometry("460x400")
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        with connect() as db:
            task = db.execute("SELECT title FROM tasks WHERE id=? AND user_id=?", (task_id, self.user["id"])).fetchone()
        self.label(frame, task["title"], "CardTitle.TLabel").pack(anchor="w", pady=(0, 12))
        listbox = tk.Listbox(frame, font=("Segoe UI", 10), height=12, borderwidth=0, highlightthickness=0)
        listbox.pack(fill="both", expand=True)
        def refresh():
            listbox.delete(0, "end")
            with connect() as db:
                items = db.execute("SELECT * FROM subtasks WHERE task_id=? ORDER BY id", (task_id,)).fetchall()
            for item in items:
                listbox.insert("end", ("✓ " if item["done"] else "○ ") + item["title"])
        def add():
            value = entry.get().strip()
            if value:
                with connect() as db:
                    db.execute("INSERT INTO subtasks(task_id,title) VALUES(?,?)", (task_id, value[:120]))
                entry.delete(0, "end")
                refresh()
        def toggle():
            pick = listbox.curselection()
            if not pick:
                return
            with connect() as db:
                items = db.execute("SELECT id,done FROM subtasks WHERE task_id=? ORDER BY id", (task_id,)).fetchall()
                item = items[pick[0]]
                db.execute("UPDATE subtasks SET done=? WHERE id=?", (0 if item["done"] else 1, item["id"]))
                remaining = db.execute("SELECT COUNT(*) FROM subtasks WHERE task_id=? AND done=0", (task_id,)).fetchone()[0]
                if remaining == 0 and items:
                    self.chat_add_message("assistant", "Boa! Todas as subtarefas desta tarefa foram concluídas.")
            refresh()
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(10, 0))
        entry = ttk.Entry(row)
        entry.pack(side="left", fill="x", expand=True, ipady=5)
        ttk.Button(row, text="Adicionar", command=add).pack(side="left", padx=(6, 0))
        ttk.Button(frame, text="Marcar / desmarcar conclusão", command=toggle).pack(anchor="w", pady=(8, 0))
        refresh()

    def build_chat(self):
        self.label(self.chat_page, "Assistente de estudos", "Title.TLabel").pack(anchor="w")
        self.label(self.chat_page, "Protótipo: respostas demonstrativas, sem conexão com um serviço externo de IA.", "Subtitle.TLabel").pack(anchor="w", pady=(4, 12))
        self.chat_log = tk.Text(self.chat_page, height=20, wrap="word", state="disabled", font=("Segoe UI", 10), bg="white", relief="flat", padx=14, pady=12)
        self.chat_log.pack(fill="both", expand=True)
        self.chat_log.tag_configure("user", foreground=ACCENT, spacing1=8, font=("Segoe UI", 10, "bold"))
        self.chat_log.tag_configure("assistant", foreground=INK, spacing1=8)
        row = ttk.Frame(self.chat_page)
        row.pack(fill="x", pady=(12, 0))
        self.chat_entry = ttk.Entry(row, font=("Segoe UI", 11))
        self.chat_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.chat_entry.bind("<Return>", lambda _event: self.send_chat())
        ttk.Button(row, text="Enviar", style="Accent.TButton", command=self.send_chat).pack(side="left", padx=(8, 0))
        self.load_chat()

    def chat_add_message(self, role, text):
        with connect() as db:
            db.execute("INSERT INTO messages(user_id,role,content) VALUES(?,?,?)", (self.user["id"], role, text))
        self.load_chat()

    def load_chat(self):
        with connect() as db:
            rows = db.execute("SELECT role,content FROM messages WHERE user_id=? ORDER BY id", (self.user["id"],)).fetchall()
        self.chat_log.config(state="normal")
        self.chat_log.delete("1.0", "end")
        if not rows:
            self.chat_log.insert("end", "Assistente\n", "assistant")
            self.chat_log.insert("end", "Oi! Posso ajudar você a dar o primeiro passo. Experimente: ‘Tenho que estudar biologia’ ou ‘Me ajuda a dividir meu trabalho’.\n\n", "assistant")
        for row in rows:
            who = "Você" if row["role"] == "user" else "Assistente"
            self.chat_log.insert("end", who + "\n", row["role"])
            self.chat_log.insert("end", row["content"] + "\n\n", row["role"])
        self.chat_log.config(state="disabled")
        self.chat_log.see("end")

    def send_chat(self):
        message = self.chat_entry.get().strip()
        if not message:
            return
        self.chat_entry.delete(0, "end")
        with connect() as db:
            db.execute("INSERT INTO messages(user_id,role,content) VALUES(?,?,?)", (self.user["id"], "user", message))
        answer = self.demo_answer(message)
        with connect() as db:
            db.execute("INSERT INTO messages(user_id,role,content) VALUES(?,?,?)", (self.user["id"], "assistant", answer))
        self.load_chat()

    @staticmethod
    def demo_answer(message):
        text = message.casefold()
        if any(word in text for word in ("dividir", "complex", "trabalho", "projeto", "apresentação")):
            return ("Podemos dividir em etapas pequenas. Sugestão: 1) entender o tema; 2) pesquisar fontes; "
                    "3) organizar os tópicos; 4) preparar uma primeira versão; 5) revisar. "
                    "Abra ‘Minhas tarefas’ e use ‘Ver subtarefas’ para registrar seu plano.")
        if any(word in text for word in ("começar", "começo", "procrastin", "difícil", "não sei")):
            return "Escolha uma ação que leve só 10 minutos: abra o material, leia uma página e anote uma dúvida. Qual matéria você quer começar?"
        if any(word in text for word in ("biologia", "matemática", "história", "física", "química", "estudar")):
            return "Vamos por partes: defina um tópico, estude por 25 minutos e depois tente explicar o que entendeu sem consultar o material. Quer transformar isso em uma tarefa?"
        return "Entendi. Para avançar, escreva o próximo passo mais simples que você consegue fazer em 10 minutos. Posso ajudar a transformar uma atividade grande em etapas menores."


if __name__ == "__main__":
    initialize()
    StudyApp().mainloop()
