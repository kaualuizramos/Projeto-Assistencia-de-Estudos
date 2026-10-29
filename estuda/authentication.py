"""Serviço de autenticação, sessões locais e gestão de contas."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from estuda.database import Database

logger = logging.getLogger(__name__)


class AuthenticationError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso_now() -> str:
    return utc_now().isoformat()


class AuthenticationService:
    MAX_ATTEMPTS = 5
    LOCK_MINUTES = 15

    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _password_hash(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
        salt = salt or os.urandom(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)
        return salt, digest

    def register(self, name: str, email: str, password: str) -> int:
        name, email = name.strip(), email.strip().casefold()
        if not name or len(name) > 100 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise AuthenticationError("Informe nome e endereço de e-mail válidos.")
        if len(email) > 254:
            raise AuthenticationError("O endereço de e-mail é muito longo.")
        if len(password) < 8 or len(password) > 1024:
            raise AuthenticationError("A senha deve conter entre 8 e 1024 caracteres.")
        salt, digest = self._password_hash(password)
        admin_email = os.getenv("ESTUDA_ADMIN_EMAIL", "").strip().casefold()
        role = "admin" if admin_email and email == admin_email else "student"
        try:
            with self.database.connection() as db:
                cursor = db.execute(
                    "INSERT INTO users(name,email,salt,password_hash,password_algorithm,role) VALUES(?,?,?,?,?,?)",
                    (name, email, salt, digest, "scrypt", role),
                )
                user_id = cursor.lastrowid
        except Exception as exc:
            if "UNIQUE constraint failed: users.email" in str(exc):
                raise AuthenticationError("Este e-mail já está cadastrado.") from exc
            raise
        logger.info("Conta criada (id=%s)", user_id)
        return user_id

    def login(self, email: str, password: str) -> dict:
        email = email.strip().casefold()[:254]
        now = utc_now()
        invalid = False
        result = None
        with self.database.connection() as db:
            attempts = db.execute("SELECT * FROM login_attempts WHERE email=?", (email,)).fetchone()
            if attempts and attempts["locked_until"] and datetime.fromisoformat(attempts["locked_until"]) > now:
                raise AuthenticationError("E-mail ou senha inválidos.")
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            valid = False
            if user:
                if user["password_algorithm"] == "pbkdf2_sha256":
                    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), user["salt"], 240_000)
                else:
                    _, candidate = self._password_hash(password, user["salt"])
                valid = hmac.compare_digest(candidate, user["password_hash"])
            if not valid:
                if attempts and now - datetime.fromisoformat(attempts["window_started"]) <= timedelta(minutes=self.LOCK_MINUTES):
                    count = attempts["attempts"] + 1
                    lock_until = (now + timedelta(minutes=self.LOCK_MINUTES)).isoformat() if count >= self.MAX_ATTEMPTS else None
                    db.execute("UPDATE login_attempts SET attempts=?,locked_until=? WHERE email=?", (count, lock_until, email))
                else:
                    count = 1
                    db.execute("INSERT OR REPLACE INTO login_attempts(email,attempts,window_started,locked_until) VALUES(?,?,?,NULL)", (email, count, now.isoformat()))
                logger.warning("Falha de autenticação registrada")
                invalid = True
            else:
                db.execute("DELETE FROM login_attempts WHERE email=?", (email,))
                if user["failed_attempts"] or user["locked_until"]:
                    db.execute("UPDATE users SET failed_attempts=0,locked_until=NULL WHERE id=?", (user["id"],))
                if user["password_algorithm"] == "pbkdf2_sha256":
                    salt, digest = self._password_hash(password)
                    db.execute("UPDATE users SET salt=?,password_hash=?,password_algorithm='scrypt' WHERE id=?", (salt, digest, user["id"]))
                    logger.info("Algoritmo de senha legado atualizado (user_id=%s)", user["id"])
                result = dict(user)
        if invalid:
            raise AuthenticationError("E-mail ou senha inválidos.")
        result.pop("password_hash", None)
        result.pop("salt", None)
        return result

    def create_password_reset(self, email: str) -> str | None:
        email = email.strip().casefold()
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires = (utc_now() + timedelta(hours=1)).isoformat()
        with self.database.connection() as db:
            user = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if not user:
                return None
            db.execute("UPDATE password_resets SET used_at=? WHERE user_id=? AND used_at IS NULL", (iso_now(), user["id"]))
            db.execute("INSERT INTO password_resets(user_id,token_hash,expires_at) VALUES(?,?,?)", (user["id"], token_hash, expires))
        return token

    def reset_password(self, token: str, new_password: str) -> None:
        if len(new_password) < 8 or len(new_password) > 1024:
            raise AuthenticationError("A senha deve conter entre 8 e 1024 caracteres.")
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.database.connection() as db:
            reset = db.execute("SELECT * FROM password_resets WHERE token_hash=? AND used_at IS NULL", (token_hash,)).fetchone()
            if not reset or datetime.fromisoformat(reset["expires_at"]) <= utc_now():
                raise AuthenticationError("Link de recuperação inválido ou expirado.")
            salt, digest = self._password_hash(new_password)
            db.execute("UPDATE users SET salt=?,password_hash=?,password_algorithm='scrypt' WHERE id=?", (salt, digest, reset["user_id"]))
            db.execute("UPDATE password_resets SET used_at=? WHERE id=?", (iso_now(), reset["id"]))
            db.execute("DELETE FROM login_attempts WHERE email=(SELECT email FROM users WHERE id=?)", (reset["user_id"],))
        logger.info("Senha redefinida (user_id=%s)", reset["user_id"])

    def delete_account(self, user_id: int, confirmed: bool) -> None:
        if not confirmed:
            raise AuthenticationError("A exclusão da conta precisa ser confirmada.")
        with self.database.connection() as db:
            cursor = db.execute("DELETE FROM users WHERE id=?", (user_id,))
            if cursor.rowcount != 1:
                raise AuthenticationError("Conta não encontrada.")
        logger.info("Conta excluída (user_id=%s)", user_id)

    def get_settings(self) -> dict:
        with self.database.connection() as db:
            return dict(db.execute("SELECT ai_enabled,daily_message_limit FROM app_settings WHERE id=1").fetchone())

    def update_ai_settings(self, user_id: int, enabled: bool, daily_limit: int) -> None:
        if not 1 <= int(daily_limit) <= 500:
            raise AuthenticationError("O limite diário deve estar entre 1 e 500 mensagens.")
        with self.database.connection() as db:
            user = db.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
            if not user or user["role"] != "admin":
                raise AuthenticationError("Apenas administradores podem alterar as configurações do assistente.")
            db.execute("UPDATE app_settings SET ai_enabled=?,daily_message_limit=? WHERE id=1", (int(enabled), int(daily_limit)))
        logger.info("Configuração de IA atualizada por admin (user_id=%s)", user_id)

