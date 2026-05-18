import os
import smtplib
import ssl
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple

from sqlalchemy import text


EMAIL_VERSION = "1.4.8-email-core-safe"


def _getenv(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def smtp_config_status() -> dict:
    host = _getenv("SMTP_HOST")
    user = _getenv("SMTP_USER")
    password = _getenv("SMTP_PASSWORD")
    from_email = _getenv("SMTP_FROM", user or "no-reply@astorieas.cz")
    port_raw = _getenv("SMTP_PORT", "587")
    try:
        port = int(port_raw)
    except Exception:
        port = 587
    mode = _getenv("SMTP_SECURITY", "starttls").lower()  # starttls | ssl | none
    configured = bool(host and user and password and from_email)
    return {
        "configured": configured,
        "host": host,
        "port": port,
        "user": user,
        "from_email": from_email,
        "security": mode,
        "missing": [k for k, v in {
            "SMTP_HOST": host,
            "SMTP_USER": user,
            "SMTP_PASSWORD": password,
            "SMTP_FROM": from_email,
        }.items() if not v],
    }


def ensure_email_tables(db) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id VARCHAR(80) PRIMARY KEY,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            event_type VARCHAR(120) NOT NULL DEFAULT '',
            entity_type VARCHAR(120) NOT NULL DEFAULT '',
            entity_id VARCHAR(120) NOT NULL DEFAULT '',
            recipient_email VARCHAR(255) NOT NULL DEFAULT '',
            subject TEXT NOT NULL DEFAULT '',
            status VARCHAR(40) NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            smtp_host VARCHAR(255) NOT NULL DEFAULT '',
            created_by_email VARCHAR(255) NOT NULL DEFAULT ''
        )
    """))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON email_logs (created_at DESC)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_email_logs_entity ON email_logs (entity_type, entity_id)"))
    db.commit()


def log_email(db, *, event_type: str, entity_type: str, entity_id: str, to_email: str, subject: str, status: str, error: str = "", created_by_email: str = "") -> None:
    try:
        ensure_email_tables(db)
        cfg = smtp_config_status()
        db.execute(text("""
            INSERT INTO email_logs
              (id, event_type, entity_type, entity_id, recipient_email, subject, status, error, smtp_host, created_by_email)
            VALUES
              (:id, :event_type, :entity_type, :entity_id, :recipient_email, :subject, :status, :error, :smtp_host, :created_by_email)
        """), {
            "id": str(uuid.uuid4()),
            "event_type": event_type or "",
            "entity_type": entity_type or "",
            "entity_id": entity_id or "",
            "recipient_email": to_email or "",
            "subject": subject or "",
            "status": status or "",
            "error": error or "",
            "smtp_host": cfg.get("host", ""),
            "created_by_email": created_by_email or "",
        })
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def send_email(db, to_email: str, subject: str, text_body: str, *, html_body: Optional[str] = None, event_type: str = "system", entity_type: str = "", entity_id: str = "", created_by_email: str = "") -> Tuple[bool, str]:
    to_email = (to_email or "").strip()
    subject = subject or ""
    text_body = text_body or ""
    if not to_email:
        err = "Chybí e-mail příjemce."
        log_email(db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, to_email=to_email, subject=subject, status="error", error=err, created_by_email=created_by_email)
        return False, err

    cfg = smtp_config_status()
    if not cfg["configured"]:
        err = "SMTP není nakonfigurováno. Chybí: " + ", ".join(cfg.get("missing") or [])
        log_email(db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, to_email=to_email, subject=subject, status="not_configured", error=err, created_by_email=created_by_email)
        return False, err

    try:
        msg = MIMEMultipart("alternative") if html_body else MIMEText(text_body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = cfg["from_email"]
        msg["To"] = to_email
        if html_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        if cfg["security"] == "ssl":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=25, context=context) as server:
                server.login(cfg["user"], _getenv("SMTP_PASSWORD"))
                server.sendmail(cfg["from_email"], [to_email], msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=25) as server:
                if cfg["security"] != "none":
                    server.starttls(context=ssl.create_default_context())
                server.login(cfg["user"], _getenv("SMTP_PASSWORD"))
                server.sendmail(cfg["from_email"], [to_email], msg.as_string())

        log_email(db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, to_email=to_email, subject=subject, status="sent", created_by_email=created_by_email)
        return True, ""
    except Exception as exc:
        err = str(exc)
        log_email(db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, to_email=to_email, subject=subject, status="error", error=err, created_by_email=created_by_email)
        return False, err


def email_template(kind: str, **data) -> Tuple[str, str]:
    company = "ASTORIE a.s."
    if kind == "new_user":
        subject = "Přístup do HUB ASTORIE"
        body = (
            "Dobrý den,\n\n"
            "byl Vám vytvořen přístup do interní aplikace HUB ASTORIE.\n\n"
            f"Jméno: {data.get('name','—')}\n"
            f"E-mail / přihlášení: {data.get('email','—')}\n"
            f"Dočasné heslo: {data.get('password','—')}\n\n"
            "Po prvním přihlášení si heslo změňte.\n\n"
            "S pozdravem\nASTORIE a.s."
        )
        return subject, body
    if kind == "password_reset":
        subject = "Reset hesla do HUB ASTORIE"
        body = (
            "Dobrý den,\n\n"
            "bylo Vám resetováno heslo do interní aplikace HUB ASTORIE.\n\n"
            f"E-mail / přihlášení: {data.get('email','—')}\n"
            f"Nové dočasné heslo: {data.get('password','—')}\n\n"
            "Po přihlášení si heslo změňte.\n\n"
            "S pozdravem\nASTORIE a.s."
        )
        return subject, body
    return f"HUB ASTORIE – {kind}", data.get("body", "")
