"""Consulta e atualização de notificações pessoais do usuário autenticado."""

from estuda.database import Database


class NotificationsService:
    def __init__(self, database: Database):
        self.database = database

    def list_notifications(self, user_id: int, unread_only: bool = False) -> list[dict]:
        query = "SELECT * FROM notifications WHERE user_id=?"
        if unread_only:
            query += " AND read_at IS NULL"
        query += " ORDER BY created_at DESC,id DESC"
        with self.database.connection() as db:
            return [dict(row) for row in db.execute(query, (user_id,)).fetchall()]

    def add(self, user_id: int, message: str, kind: str = "General") -> int:
        with self.database.connection() as db:
            return db.execute("INSERT INTO notifications(user_id,message,kind) VALUES(?,?,?)", (user_id, message[:500], kind[:40])).lastrowid

    def mark_read(self, user_id: int, notification_id: int | None = None) -> int:
        with self.database.connection() as db:
            if notification_id is None:
                cursor = db.execute("UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE user_id=? AND read_at IS NULL", (user_id,))
            else:
                cursor = db.execute("UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE user_id=? AND id=? AND read_at IS NULL", (user_id, notification_id))
            return cursor.rowcount

