"""Serviço de sessões Pomodoro com tempos calculados a partir de timestamps."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from estuda.database import Database

logger = logging.getLogger(__name__)


class FocusError(ValueError):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def effective_seconds(session: dict, now: datetime | None = None) -> int:
    start = datetime.fromisoformat(session["started_at"])
    end = datetime.fromisoformat(session["ended_at"]) if session.get("ended_at") else (now or now_utc())
    elapsed = int((end - start).total_seconds()) - int(session.get("paused_seconds", 0))
    if session.get("paused_at"):
        elapsed -= int((end - datetime.fromisoformat(session["paused_at"])).total_seconds())
    return max(0, elapsed)


class FocusSessionsService:
    def __init__(self, database: Database):
        self.database = database

    def start(self, user_id: int, task_id: int, duration_minutes: int = 25) -> int:
        if not 1 <= int(duration_minutes) <= 240:
            raise FocusError("A duração deve estar entre 1 e 240 minutos.")
        with self.database.connection() as db:
            active = db.execute("SELECT id FROM focus_sessions WHERE user_id=? AND status IN ('Running','Paused')", (user_id,)).fetchone()
            if active:
                raise FocusError("Você já tem uma sessão de foco ativa.")
            task = db.execute("SELECT title FROM tasks WHERE id=? AND user_id=? AND status='Pendente'", (task_id, user_id)).fetchone()
            if not task:
                raise FocusError("Selecione uma tarefa sua que ainda esteja pendente.")
            session_id = db.execute("INSERT INTO focus_sessions(user_id,task_id,task_title,started_at,duration_seconds) VALUES(?,?,?,?,?)",
                                    (user_id, task_id, task["title"], now_utc().isoformat(), int(duration_minutes) * 60)).lastrowid
        logger.info("Sessão de foco iniciada (session_id=%s user_id=%s)", session_id, user_id)
        return session_id

    def active(self, user_id: int) -> dict | None:
        with self.database.connection() as db:
            row = db.execute("SELECT * FROM focus_sessions WHERE user_id=? AND status IN ('Running','Paused') ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        return dict(row) if row else None

    def pause(self, user_id: int) -> None:
        with self.database.connection() as db:
            cursor = db.execute("UPDATE focus_sessions SET status='Paused',paused_at=? WHERE user_id=? AND status='Running'",
                                (now_utc().isoformat(), user_id))
            if not cursor.rowcount:
                raise FocusError("Não há sessão em andamento para pausar.")

    def resume(self, user_id: int) -> None:
        now = now_utc()
        with self.database.connection() as db:
            row = db.execute("SELECT * FROM focus_sessions WHERE user_id=? AND status='Paused' ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
            if not row:
                raise FocusError("Não há sessão pausada para retomar.")
            paused = int((now - datetime.fromisoformat(row["paused_at"])).total_seconds())
            db.execute("UPDATE focus_sessions SET status='Running',paused_seconds=paused_seconds+?,paused_at=NULL WHERE id=?",
                       (max(paused, 0), row["id"]))

    def terminate(self, user_id: int) -> None:
        now = now_utc()
        with self.database.connection() as db:
            row = db.execute("SELECT * FROM focus_sessions WHERE user_id=? AND status IN ('Running','Paused') ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
            if not row:
                raise FocusError("Não há sessão ativa para encerrar.")
            snapshot = dict(row)
            if row["status"] == "Paused" and row["paused_at"]:
                snapshot["paused_seconds"] += max(0, int((now - datetime.fromisoformat(row["paused_at"])).total_seconds()))
            elapsed = max(0, int((now - datetime.fromisoformat(row["started_at"])).total_seconds()) - snapshot["paused_seconds"])
            db.execute("UPDATE focus_sessions SET ended_at=?,paused_seconds=?,paused_at=NULL,status='Terminated' WHERE id=?",
                       (now.isoformat(), snapshot["paused_seconds"], row["id"]))
        logger.info("Sessão de foco encerrada (session_id=%s user_id=%s effective_seconds=%s)", row["id"], user_id, elapsed)

    def tick(self, user_id: int) -> dict | None:
        """Atualiza término pelo timestamp e retorna estado para a interface."""
        session = self.active(user_id)
        if not session:
            return None
        elapsed = effective_seconds(session)
        if session["status"] == "Running" and elapsed >= session["duration_seconds"]:
            now = now_utc().isoformat()
            with self.database.connection() as db:
                db.execute("UPDATE focus_sessions SET status='Completed',ended_at=? WHERE id=? AND status='Running'", (now, session["id"]))
                db.execute("INSERT INTO notifications(user_id,message,kind) VALUES(?,?,?)",
                           (user_id, f"Sessão de foco concluída: {session['task_title']}", "Focus"))
            logger.info("Sessão de foco concluída (session_id=%s user_id=%s)", session["id"], user_id)
            session["status"] = "Completed"
            session["ended_at"] = now
            elapsed = session["duration_seconds"]
        session["elapsed_seconds"] = min(elapsed, session["duration_seconds"])
        return session

    def recover(self) -> None:
        """Ao iniciar, completa sessões cuja duração venceu enquanto o app estava fechado."""
        with self.database.connection() as db:
            sessions = [dict(row) for row in db.execute("SELECT * FROM focus_sessions WHERE status='Running'").fetchall()]
        for session in sessions:
            if effective_seconds(session) >= session["duration_seconds"]:
                ended = (datetime.fromisoformat(session["started_at"]) + timedelta(seconds=session["duration_seconds"] + session["paused_seconds"])).isoformat()
                with self.database.connection() as db:
                    cursor = db.execute("UPDATE focus_sessions SET status='Completed',ended_at=? WHERE id=? AND status='Running'", (ended, session["id"]))
                    if cursor.rowcount:
                        db.execute("INSERT INTO notifications(user_id,message,kind) VALUES(?,?,?)",
                                   (session["user_id"], f"Sessão de foco concluída: {session['task_title']}", "Focus"))

    def history(self, user_id: int, period: str = "30 dias") -> list[dict]:
        clauses, params = ["user_id=?"], [user_id]
        if period == "7 dias":
            clauses.append("started_at>=?")
            params.append((now_utc() - timedelta(days=7)).isoformat())
        elif period == "30 dias":
            clauses.append("started_at>=?")
            params.append((now_utc() - timedelta(days=30)).isoformat())
        with self.database.connection() as db:
            rows = db.execute("SELECT * FROM focus_sessions WHERE " + " AND ".join(clauses) + " ORDER BY started_at DESC", params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["effective_seconds"] = effective_seconds(item, datetime.fromisoformat(item["ended_at"]) if item["ended_at"] else None)
            result.append(item)
        return result

    def metrics(self, user_id: int, period: str = "30 dias") -> dict:
        sessions = self.history(user_id, period)
        finished = [item for item in sessions if item["status"] in ("Completed", "Terminated")]
        return {"completed_sessions": sum(item["status"] == "Completed" for item in sessions),
                "effective_seconds": sum(item["effective_seconds"] for item in finished)}

