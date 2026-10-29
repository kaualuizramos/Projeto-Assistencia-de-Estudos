"""Regras e persistência de tarefas, subtarefas e lembretes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from estuda.database import Database

logger = logging.getLogger(__name__)


class TaskError(ValueError):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def dt_value(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class TasksService:
    PRIORITIES = {"Baixa", "Média", "Alta"}

    def __init__(self, database: Database):
        self.database = database

    def _validate(self, title: str, deadline: str | datetime, description: str, priority: str, now=None) -> tuple[str, str, str, str]:
        errors = []
        title = title.strip()
        description = description.strip()
        if not title:
            errors.append("Título obrigatório.")
        elif len(title) > 120:
            errors.append("O título pode ter até 120 caracteres.")
        if len(description) > 1000:
            errors.append("A descrição pode ter até 1000 caracteres.")
        if priority not in self.PRIORITIES:
            errors.append("Prioridade inválida.")
        try:
            due = dt_value(deadline).astimezone(timezone.utc)
            current = dt_value(now or now_utc()).astimezone(timezone.utc)
            if due <= current:
                errors.append("O prazo deve estar no futuro.")
        except (TypeError, ValueError):
            errors.append("Informe um prazo válido com data e hora.")
            due = None
        if errors:
            raise TaskError("\n".join(errors))
        return title, description, due.isoformat(), priority

    def create_task(self, user_id: int, title: str, deadline: str | datetime,
                    priority: str = "Média", description: str = "", now=None) -> int:
        title, description, due, priority = self._validate(title, deadline, description, priority, now)
        with self.database.connection() as db:
            task_id = db.execute(
                "INSERT INTO tasks(user_id,title,description,deadline,priority) VALUES(?,?,?,?,?)",
                (user_id, title, description, due, priority),
            ).lastrowid
        logger.info("Tarefa persistida (task_id=%s user_id=%s)", task_id, user_id)
        return task_id

    def edit_task(self, user_id: int, task_id: int, title: str, deadline: str | datetime,
                  priority: str = "Média", description: str = "", now=None) -> None:
        title, description, due, priority = self._validate(title, deadline, description, priority, now)
        with self.database.connection() as db:
            cursor = db.execute("UPDATE tasks SET title=?,description=?,deadline=?,priority=? WHERE id=? AND user_id=?",
                                (title, description, due, priority, task_id, user_id))
            if cursor.rowcount != 1:
                raise TaskError("Tarefa não encontrada.")
        logger.info("Tarefa editada (task_id=%s user_id=%s)", task_id, user_id)

    def list_tasks(self, user_id: int, status: str = "Todas", priority: str = "Todas",
                   deadline_from: str | None = None, deadline_to: str | None = None,
                   now=None) -> list[dict]:
        current = (now or now_utc()).isoformat()
        clauses, params = ["t.user_id=?"], [user_id]
        if status == "Atrasada":
            clauses.append("t.status='Pendente' AND t.deadline<?")
            params.append(current)
        elif status in ("Pendente", "Concluída"):
            clauses.append("t.status=?")
            params.append(status)
        if priority in self.PRIORITIES:
            clauses.append("t.priority=?")
            params.append(priority)
        if deadline_from:
            clauses.append("t.deadline>=?")
            params.append(deadline_from)
        if deadline_to:
            clauses.append("t.deadline<=?")
            params.append(deadline_to)
        query = "SELECT t.*, (SELECT COUNT(*) FROM subtasks s WHERE s.task_id=t.id AND s.done=0) AS pending_subtasks FROM tasks t WHERE " + " AND ".join(clauses) + " ORDER BY t.status='Concluída',t.deadline"
        with self.database.connection() as db:
            return [dict(row) for row in db.execute(query, params).fetchall()]

    def get_task(self, user_id: int, task_id: int) -> dict:
        with self.database.connection() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)).fetchone()
        if not row:
            raise TaskError("Tarefa não encontrada.")
        return dict(row)

    def delete_task(self, user_id: int, task_id: int) -> None:
        with self.database.connection() as db:
            task = db.execute("SELECT id FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)).fetchone()
            if not task:
                raise TaskError("Tarefa não encontrada.")
            active = db.execute("SELECT COUNT(*) FROM focus_sessions WHERE task_id=? AND status IN ('Running','Paused')", (task_id,)).fetchone()[0]
            if active:
                raise TaskError("Não é possível excluir a tarefa enquanto uma sessão de foco estiver ativa.")
            db.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
        logger.info("Tarefa removida (task_id=%s user_id=%s)", task_id, user_id)

    def set_completed(self, user_id: int, task_id: int, completed: bool) -> None:
        with self.database.connection() as db:
            task = db.execute("SELECT id,status FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)).fetchone()
            if not task:
                raise TaskError("Tarefa não encontrada.")
            if completed:
                pending = db.execute("SELECT COUNT(*) FROM subtasks WHERE task_id=? AND done=0", (task_id,)).fetchone()[0]
                if pending:
                    raise TaskError(f"Ainda restam {pending} subtarefa(s) pendente(s).")
                db.execute("UPDATE tasks SET status='Concluída',completed_at=? WHERE id=? AND user_id=?", (now_utc().isoformat(), task_id, user_id))
                db.execute("UPDATE reminders SET status='Cancelled',retry_at=NULL WHERE task_id=? AND status='Scheduled'", (task_id,))
            else:
                db.execute("UPDATE tasks SET status='Pendente',completed_at=NULL WHERE id=? AND user_id=?", (task_id, user_id))
        logger.info("Status da tarefa alterado (task_id=%s user_id=%s completed=%s)", task_id, user_id, completed)

    def add_subtask(self, user_id: int, task_id: int, title: str) -> int:
        title = title.strip()
        if not title or len(title) > 120:
            raise TaskError("A subtarefa precisa de um título de até 120 caracteres.")
        with self.database.connection() as db:
            task = db.execute("SELECT id FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)).fetchone()
            if not task:
                raise TaskError("Tarefa não encontrada.")
            cursor = db.execute("INSERT INTO subtasks(task_id,title) VALUES(?,?)", (task_id, title))
            return cursor.lastrowid

    def list_subtasks(self, user_id: int, task_id: int) -> list[dict]:
        with self.database.connection() as db:
            task = db.execute("SELECT id FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)).fetchone()
            if not task:
                raise TaskError("Tarefa não encontrada.")
            return [dict(row) for row in db.execute("SELECT * FROM subtasks WHERE task_id=? ORDER BY id", (task_id,)).fetchall()]

    def set_subtask_done(self, user_id: int, subtask_id: int, done: bool) -> bool:
        with self.database.connection() as db:
            item = db.execute("SELECT s.*,t.user_id,t.title AS task_title FROM subtasks s JOIN tasks t ON t.id=s.task_id WHERE s.id=? AND t.user_id=?", (subtask_id, user_id)).fetchone()
            if not item:
                raise TaskError("Subtarefa não encontrada.")
            db.execute("UPDATE subtasks SET done=? WHERE id=?", (int(done), subtask_id))
            pending = db.execute("SELECT COUNT(*) FROM subtasks WHERE task_id=? AND done=0", (item["task_id"],)).fetchone()[0]
            return bool(done and pending == 0)

    def add_reminder(self, user_id: int, task_id: int, scheduled_at: str | datetime,
                     email_enabled: bool = False, now=None) -> int:
        when = dt_value(scheduled_at)
        current = now or now_utc()
        with self.database.connection() as db:
            task = db.execute("SELECT deadline,status FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)).fetchone()
            if not task:
                raise TaskError("Tarefa não encontrada.")
            if task["status"] != "Pendente":
                raise TaskError("Lembretes só podem ser criados para tarefas pendentes.")
            if when <= current or when >= dt_value(task["deadline"]):
                raise TaskError("O lembrete deve ocorrer depois de agora e antes do prazo da tarefa.")
            cursor = db.execute("INSERT INTO reminders(user_id,task_id,scheduled_at,email_enabled) VALUES(?,?,?,?)",
                                (user_id, task_id, when.isoformat(), int(email_enabled)))
            return cursor.lastrowid

    def list_reminders(self, user_id: int, task_id: int) -> list[dict]:
        with self.database.connection() as db:
            return [dict(row) for row in db.execute("SELECT r.*,t.title AS task_title FROM reminders r JOIN tasks t ON t.id=r.task_id WHERE r.user_id=? AND r.task_id=? ORDER BY r.scheduled_at", (user_id, task_id)).fetchall()]

    def process_due_reminders(self, mailer, now=None) -> int:
        current = now or now_utc()
        current_text = current.isoformat()
        with self.database.connection() as db:
            due = db.execute("""SELECT r.*,t.title AS task_title,u.email FROM reminders r
                JOIN tasks t ON t.id=r.task_id JOIN users u ON u.id=r.user_id
                WHERE (r.status='Scheduled' AND r.scheduled_at<=?)
                   OR (r.status='Sent' AND r.retry_at IS NOT NULL AND r.retry_at<=? AND r.email_attempts<4)""",
                (current_text, current_text)).fetchall()
        processed = 0
        for reminder in due:
            is_first = reminder["status"] == "Scheduled"
            if is_first:
                with self.database.connection() as db:
                    cursor = db.execute("UPDATE reminders SET status='Sent' WHERE id=? AND status='Scheduled'", (reminder["id"],))
                    if not cursor.rowcount:
                        continue
                    db.execute("INSERT INTO notifications(user_id,message,kind) VALUES(?,?,?)", (reminder["user_id"], f"Lembrete: {reminder['task_title']}", "Reminder"))
            if reminder["email_enabled"] and reminder["email_attempts"] < 4:
                try:
                    mailer.send(reminder["email"], f"Lembrete de estudo: {reminder['task_title']}", f"Você tem uma tarefa de estudo: {reminder['task_title']}.")
                except Exception as exc:
                    attempts = reminder["email_attempts"] + 1
                    retry_at = (current + timedelta(minutes=5)).isoformat() if attempts < 4 else None
                    with self.database.connection() as db:
                        db.execute("UPDATE reminders SET email_attempts=?,retry_at=?,last_error=? WHERE id=?",
                                   (attempts, retry_at, type(exc).__name__, reminder["id"]))
                    logger.warning("Falha no envio de lembrete (reminder_id=%s; tentativa=%s)", reminder["id"], attempts)
                else:
                    with self.database.connection() as db:
                        db.execute("UPDATE reminders SET email_attempts=email_attempts+1,retry_at=NULL,last_error=NULL WHERE id=?", (reminder["id"],))
            processed += 1
        return processed

