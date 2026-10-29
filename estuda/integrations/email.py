"""Transporte SMTP configurado pelo ambiente, isolado do domínio."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


class EmailUnavailable(RuntimeError):
    pass


class SMTPMailer:
    def __init__(self, environ=None):
        env = environ if environ is not None else os.environ
        self.host = env.get("ESTUDA_SMTP_HOST", "").strip()
        self.port = int(env.get("ESTUDA_SMTP_PORT", "587"))
        self.username = env.get("ESTUDA_SMTP_USER", "")
        self.password = env.get("ESTUDA_SMTP_PASSWORD", "")
        self.sender = env.get("ESTUDA_SMTP_FROM", self.username).strip()
        self.use_ssl = env.get("ESTUDA_SMTP_SSL", "false").casefold() == "true"

    @property
    def available(self) -> bool:
        return bool(self.host and self.sender)

    def send(self, recipient: str, subject: str, body: str) -> None:
        if not self.available:
            raise EmailUnavailable("SMTP não configurado.")
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        if self.use_ssl:
            client = smtplib.SMTP_SSL(self.host, self.port, timeout=15, context=ssl.create_default_context())
        else:
            client = smtplib.SMTP(self.host, self.port, timeout=15)
        with client:
            if not self.use_ssl:
                client.starttls(context=ssl.create_default_context())
            if self.username:
                client.login(self.username, self.password)
            client.send_message(message)

