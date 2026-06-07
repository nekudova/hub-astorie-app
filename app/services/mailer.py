import os
import smtplib
import ssl
import uuid
import html as _html
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, parseaddr
from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy import text


EMAIL_VERSION = "1.6.0d-email-send-rollback-stabilization-safe"
ASTORIE_PETROL = "#003D4C"
ASTORIE_ORANGE = "#FC4C02"
ASTORIE_BG = "#F4F8F9"
ASTORIE_TEXT = "#102A33"


def _getenv(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        val = _getenv(name)
        if val:
            return val
    return default


def _bool_env(name: str, default: bool = True) -> bool:
    raw = _getenv(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "ano", "on", "enabled"}


def _split_emails(value: str) -> List[str]:
    parts: List[str] = []
    for chunk in (value or "").replace(";", ",").split(","):
        email = chunk.strip()
        if email:
            parts.append(email)
    return parts


def _esc(value: Any) -> str:
    return _html.escape(str(value if value is not None else "—"))


def _normalized_from(from_raw: str, user: str) -> str:
    """Accept either plain address or 'Name <mail@domain.cz>'."""
    raw = (from_raw or user or "no-reply@astorieas.cz").strip()
    name, email = parseaddr(raw)
    if email and name:
        return formataddr((name, email))
    return email or raw


def smtp_config_status() -> dict:
    """
    Central SMTP config. Reads Render Environment Variables only.

    Canonical variables:
      EMAIL_ENABLED, SMTP_HOST, SMTP_PORT, SMTP_SECURITY, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_REPLY_TO

    Compatible aliases are kept for older deployments.
    """
    host = _first_env("SMTP_HOST", "SMTP_SERVER", "MAIL_HOST")
    user = _first_env("SMTP_USER", "SMTP_USERNAME", "MAIL_USER")
    password = _first_env("SMTP_PASSWORD", "SMTP_PASS", "MAIL_PASSWORD")
    from_email = _normalized_from(_first_env("SMTP_FROM", "MAIL_FROM", "EMAIL_FROM", default=user or "no-reply@astorieas.cz"), user)
    reply_to = _first_env("SMTP_REPLY_TO", "MAIL_REPLY_TO", default=_getenv("SUPPORT_EMAIL", "backoffice@astorieas.cz"))
    port_raw = _first_env("SMTP_PORT", "MAIL_PORT", default="587")
    try:
        port = int(port_raw)
    except Exception:
        port = 587
    mode = _first_env("SMTP_SECURITY", "SMTP_ENCRYPTION", "MAIL_SECURITY", default="starttls").lower()
    if mode in {"tls", "start_tls", "start-tls"}:
        mode = "starttls"
    if mode in {"ssl_tls", "smtps"}:
        mode = "ssl"
    if mode not in {"starttls", "ssl", "none"}:
        mode = "starttls"
    enabled = _bool_env("EMAIL_ENABLED", True)
    configured = bool(enabled and host and user and password and from_email)
    missing = []
    if not host:
        missing.append("SMTP_HOST")
    if not user:
        missing.append("SMTP_USER")
    if not password:
        missing.append("SMTP_PASSWORD")
    if not from_email:
        missing.append("SMTP_FROM")
    return {
        "version": EMAIL_VERSION,
        "enabled": enabled,
        "configured": configured,
        "host": host,
        "port": port,
        "user": user,
        "from_email": from_email,
        "reply_to": reply_to,
        "security": mode,
        "missing": missing,
    }


def public_smtp_diagnostics() -> dict:
    """Bezpečná diagnostika pro Admin: nevrací heslo, jen stav konfigurace."""
    cfg = smtp_config_status()
    return {
        "version": EMAIL_VERSION,
        "enabled": cfg.get("enabled"),
        "configured": cfg.get("configured"),
        "host": cfg.get("host"),
        "port": cfg.get("port"),
        "security": cfg.get("security"),
        "user": cfg.get("user"),
        "from_email": cfg.get("from_email"),
        "reply_to": cfg.get("reply_to"),
        "missing": cfg.get("missing", []),
        "password_present": bool(_first_env("SMTP_PASSWORD", "SMTP_PASS", "MAIL_PASSWORD")),
    }


def ensure_email_tables(db) -> None:
    """Additive-only email logging. No destructive DB operation."""
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
    # Additive compatibility columns for professional audit. Existing rows remain untouched.
    for stmt in [
        "ALTER TABLE email_logs ADD COLUMN IF NOT EXISTS template_key VARCHAR(120) NOT NULL DEFAULT ''",
        "ALTER TABLE email_logs ADD COLUMN IF NOT EXISTS provider VARCHAR(120) NOT NULL DEFAULT ''",
        "ALTER TABLE email_logs ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE email_logs ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ",
    ]:
        try:
            db.execute(text(stmt))
        except Exception:
            db.rollback()
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON email_logs (created_at DESC)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_email_logs_entity ON email_logs (entity_type, entity_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs (status)"))
    db.commit()


def log_email(db, *, event_type: str, entity_type: str, entity_id: str, to_email: str, subject: str, status: str, error: str = "", created_by_email: str = "", template_key: str = "") -> None:
    try:
        ensure_email_tables(db)
        cfg = smtp_config_status()
        db.execute(text("""
            INSERT INTO email_logs
              (id, event_type, entity_type, entity_id, recipient_email, subject, status, error, smtp_host, created_by_email, template_key, provider, last_attempt_at)
            VALUES
              (:id, :event_type, :entity_type, :entity_id, :recipient_email, :subject, :status, :error, :smtp_host, :created_by_email, :template_key, :provider, NOW())
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
            "template_key": template_key or "",
            "provider": "smtp",
        })
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def _button(url: str, label: str) -> str:
    if not url:
        return ""
    return f'''
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:22px 0 8px 0">
        <tr><td bgcolor="{ASTORIE_ORANGE}" style="border-radius:12px">
          <a href="{_esc(url)}" style="display:inline-block;padding:13px 20px;font-family:Arial,sans-serif;font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:12px">{_esc(label)}</a>
        </td></tr>
      </table>
    '''


def _rows(rows: List[Tuple[str, Any]]) -> str:
    out = []
    for label, value in rows:
        out.append(f'''
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #E6EEF1;color:#607382;font-size:13px;width:36%;vertical-align:top"><b>{_esc(label)}</b></td>
          <td style="padding:10px 12px;border-bottom:1px solid #E6EEF1;color:{ASTORIE_TEXT};font-size:14px;vertical-align:top">{_esc(value) if value not in [None, ''] else '—'}</td>
        </tr>''')
    return '<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="width:100%;border-collapse:collapse;margin:14px 0;background:#ffffff;border:1px solid #E6EEF1;border-radius:12px;overflow:hidden">' + ''.join(out) + '</table>'


def _html_shell(title: str, body_html: str, *, preheader: str = "", badge: str = "HUB ASTORIE") -> str:
    safe_title = _esc(title)
    safe_preheader = _esc(preheader or title)
    safe_badge = _esc(badge)
    return f"""<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
</head>
<body style="margin:0;padding:0;background:{ASTORIE_BG};font-family:Arial,Helvetica,sans-serif;color:{ASTORIE_TEXT};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{safe_preheader}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:{ASTORIE_BG};padding:24px 10px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:720px;background:#ffffff;border:1px solid #DCE8EA;border-radius:22px;overflow:hidden;box-shadow:0 16px 38px rgba(0,61,76,.08);">
        <tr>
          <td style="padding:22px 26px;background:{ASTORIE_PETROL};color:#ffffff;">
            <div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#BFE5E8;font-weight:700;">{safe_badge}</div>
            <div style="font-size:24px;line-height:1.25;font-weight:800;margin-top:8px;">{safe_title}</div>
          </td>
        </tr>
        <tr><td style="padding:26px;">
          {body_html}
          <div style="height:1px;background:#E6EEF1;margin:26px 0 18px"></div>
          <p style="margin:0 0 4px 0;color:{ASTORIE_TEXT};font-size:14px;line-height:1.55;">S pozdravem</p>
          <p style="margin:0;color:{ASTORIE_PETROL};font-size:15px;font-weight:800;">ASTORIE a.s.</p>
          <p style="margin:10px 0 0;color:#6C7F8C;font-size:12px;line-height:1.45;">Tento e-mail byl odeslán automaticky z interní aplikace HUB ASTORIE. V případě technických potíží kontaktujte backoffice.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _plain_footer(body: str) -> str:
    if "ASTORIE" in (body or "")[-80:]:
        return body
    return (body or "") + "\n\nS pozdravem\nASTORIE a.s."


def email_template(kind: str, **data) -> Tuple[str, str, str]:
    """Professional centralized templates. Returns (subject, plain_text, html)."""
    app_url = data.get("app_url") or _getenv("APP_BASE_URL", "https://hub-astorie-app.onrender.com")

    if kind == "system_test":
        subject = "Test e-mailu – HUB ASTORIE"
        body = "Dobrý den,\n\ntoto je testovací e-mail z aplikace HUB ASTORIE. Pokud Vám přišel, SMTP napojení funguje.\n\nASTORIE a.s."
        html = _html_shell("Test e-mailu – HUB ASTORIE", """
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">Dobrý den,</p>
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">toto je testovací e-mail z aplikace <b>HUB ASTORIE</b>.</p>
          <p style="font-size:15px;line-height:1.6;margin:0;">Pokud Vám přišel, SMTP napojení funguje.</p>
        """, preheader="SMTP napojení HUB ASTORIE funguje.")
        return subject, body, html

    if kind == "new_user":
        subject = "Přístup do HUB ASTORIE"
        body = _plain_footer(
            "Dobrý den,\n\n"
            "byl Vám vytvořen přístup do interní aplikace HUB ASTORIE.\n\n"
            f"Jméno: {data.get('name','—')}\n"
            f"E-mail / přihlášení: {data.get('email','—')}\n"
            f"Dočasné heslo: {data.get('password','—')}\n\n"
            "Po prvním přihlášení si heslo změňte."
        )
        html = _html_shell("Přístup do HUB ASTORIE", f"""
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">Dobrý den,</p>
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">byl Vám vytvořen přístup do interní aplikace <b>HUB ASTORIE</b>.</p>
          {_rows([('Jméno', data.get('name','—')), ('Přihlášení', data.get('email','—')), ('Dočasné heslo', data.get('password','—'))])}
          {_button(app_url + '/hub', 'Otevřít HUB ASTORIE')}
          <p style="font-size:13px;color:#607382;line-height:1.5;margin:16px 0 0 0;">Po prvním přihlášení si heslo změňte.</p>
        """, preheader="Byl Vám vytvořen přístup do HUB ASTORIE.")
        return subject, body, html

    if kind == "password_reset":
        subject = "Reset hesla do HUB ASTORIE"
        body = _plain_footer(
            "Dobrý den,\n\n"
            "bylo Vám resetováno heslo do interní aplikace HUB ASTORIE.\n\n"
            f"E-mail / přihlášení: {data.get('email','—')}\n"
            f"Nové dočasné heslo: {data.get('password','—')}\n\n"
            "Po přihlášení si heslo změňte."
        )
        html = _html_shell("Reset hesla do HUB ASTORIE", f"""
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">Dobrý den,</p>
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">bylo Vám resetováno heslo do interní aplikace <b>HUB ASTORIE</b>.</p>
          {_rows([('Přihlášení', data.get('email','—')), ('Nové dočasné heslo', data.get('password','—'))])}
          {_button(app_url + '/hub', 'Přejít do HUBu')}
          <p style="font-size:13px;color:#607382;line-height:1.5;margin:16px 0 0 0;">Po přihlášení si heslo změňte.</p>
        """, preheader="Bylo Vám resetováno heslo do HUB ASTORIE.")
        return subject, body, html

    if kind == "tip_new_specialist":
        subject = "Nový TIP v HUB ASTORIE"
        body = _plain_footer(
            "Dobrý den,\n\nbyl Vám předán nový TIP.\n\n"
            f"Poradce: {data.get('adviser_name','—')} ({data.get('adviser_email','—')})\n"
            f"Klient: {data.get('client_name','—')}\n"
            f"Kontakt na klienta: {data.get('client_phone','—')}\n"
            f"Identifikace: {data.get('client_identifier','—')}\n"
            f"Oblast: {data.get('section_label','—')}\n"
            f"Podsekce: {data.get('subsection_label','—')}\n"
            f"Smlouva č.: {data.get('policy_no','—')}\n"
            f"Odhad potenciálu / objemu: {data.get('potential_amount','—')}\n\n"
            f"Popis případu:\n{data.get('adviser_note','—')}\n\n"
            "Prosíme o převzetí a další zpracování v aplikaci HUB ASTORIE."
        )
        html = _html_shell("Nový TIP k převzetí", f"""
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">Dobrý den,</p>
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">v aplikaci HUB ASTORIE Vám byl předán nový TIP ke zpracování.</p>
          {_rows([
            ('Poradce', f"{data.get('adviser_name','—')} ({data.get('adviser_email','—')})"),
            ('Klient', data.get('client_name','—')),
            ('Kontakt na klienta', data.get('client_phone','—')),
            ('Identifikace', data.get('client_identifier','—')),
            ('Oblast', data.get('section_label','—')),
            ('Podsekce', data.get('subsection_label','—')),
            ('Smlouva č.', data.get('policy_no','—')),
            ('Potenciál / objem', data.get('potential_amount','—')),
          ])}
          <div style="background:#F4F8F9;border-left:5px solid {ASTORIE_ORANGE};border-radius:12px;padding:14px 16px;margin-top:16px;">
            <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#607382;font-weight:700;margin-bottom:6px;">Popis případu</div>
            <div style="font-size:14px;line-height:1.55;color:{ASTORIE_TEXT};white-space:pre-wrap;">{_esc(data.get('adviser_note','—'))}</div>
          </div>
          {_button(app_url + '/hub/specialist-tips', 'Otevřít TIPy k vyřízení')}
        """, preheader="Byl Vám předán nový TIP v HUB ASTORIE.")
        return subject, body, html

    if kind == "tip_new_adviser":
        subject = "Potvrzení odeslání TIPu – HUB ASTORIE"
        body = _plain_footer(
            "Dobrý den,\n\nváš TIP byl úspěšně uložen a předán vybranému specialistovi.\n\n"
            f"Specialista: {data.get('specialist_name','—')}\n"
            f"Klient: {data.get('client_name','—')}\n"
            f"Oblast: {data.get('section_label','—')}\n"
            f"Podsekce: {data.get('subsection_label','—')}\n"
            "Stav: Nový\n\nDalší průběh uvidíte v sekci Moje TIPy."
        )
        html = _html_shell("TIP byl úspěšně odeslán", f"""
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">Dobrý den,</p>
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">váš TIP byl úspěšně uložen a předán vybranému specialistovi.</p>
          {_rows([
            ('Specialista', data.get('specialist_name','—')),
            ('Klient', data.get('client_name','—')),
            ('Oblast', data.get('section_label','—')),
            ('Podsekce', data.get('subsection_label','—')),
            ('Stav', 'Nový'),
          ])}
          {_button(app_url + '/hub/my-tips', 'Sledovat v Moje TIPy')}
        """, preheader="Váš TIP byl uložen a předán specialistovi.")
        return subject, body, html

    if kind == "partner_request_bo":
        subject = data.get("subject") or "Nový požadavek na partnera – HUB ASTORIE"
        body_text = data.get("body") or ""
        html = _html_shell(subject, f"""
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">Dobrý den,</p>
          <p style="font-size:15px;line-height:1.6;margin:0 0 14px 0;">v HUB ASTORIE byl vložen nový požadavek v oblasti partnerů.</p>
          <div style="background:#F4F8F9;border-left:5px solid {ASTORIE_ORANGE};border-radius:12px;padding:14px 16px;margin-top:16px;white-space:pre-wrap;font-size:14px;line-height:1.55;">{_esc(body_text)}</div>
          {_button(app_url + '/admin/partner-requests', 'Otevřít administraci požadavků')}
        """, preheader="Nový požadavek na partnera v HUB ASTORIE.")
        return subject, _plain_footer(body_text), html

    if kind == "generic_notice":
        subject = data.get("subject") or "HUB ASTORIE"
        body_text = data.get("body") or ""
        html = _html_shell(subject, f"""
          <div style="font-size:15px;line-height:1.6;white-space:pre-wrap;">{_esc(body_text)}</div>
        """, preheader=subject)
        return subject, _plain_footer(body_text), html

    subject = data.get("subject") or f"HUB ASTORIE – {kind}"
    body = data.get("body", "")
    html = data.get("html") or _html_shell(subject, f"<div style='font-size:15px;line-height:1.6;white-space:pre-wrap'>{_esc(body)}</div>")
    return subject, _plain_footer(body), html


def send_email(db, to_email: str, subject: str, text_body: str, *, html_body: Optional[str] = None, event_type: str = "system", entity_type: str = "", entity_id: str = "", created_by_email: str = "", template_key: str = "") -> Tuple[bool, str]:
    recipients = _split_emails(to_email)
    subject = subject or ""
    text_body = text_body or ""
    if not recipients:
        err = "Chybí e-mail příjemce."
        log_email(db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, to_email=to_email, subject=subject, status="error", error=err, created_by_email=created_by_email, template_key=template_key)
        return False, err

    cfg = smtp_config_status()
    if not cfg.get("enabled", True):
        err = "Odesílání e-mailů je vypnuté proměnnou EMAIL_ENABLED."
        log_email(db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, to_email=", ".join(recipients), subject=subject, status="disabled", error=err, created_by_email=created_by_email, template_key=template_key)
        return False, err
    if not cfg["configured"]:
        err = "SMTP není nakonfigurováno. Chybí: " + ", ".join(cfg.get("missing") or [])
        log_email(db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, to_email=", ".join(recipients), subject=subject, status="not_configured", error=err, created_by_email=created_by_email, template_key=template_key)
        return False, err

    try:
        if html_body:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))
        else:
            msg = MIMEText(text_body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = cfg["from_email"]
        msg["To"] = ", ".join(recipients)
        if cfg.get("reply_to"):
            msg["Reply-To"] = cfg["reply_to"]
        msg["X-ASTORIE-HUB"] = EMAIL_VERSION

        if cfg["security"] == "ssl":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=30, context=context) as server:
                server.login(cfg["user"], _first_env("SMTP_PASSWORD", "SMTP_PASS", "MAIL_PASSWORD"))
                server.sendmail(parseaddr(cfg["from_email"])[1] or cfg["from_email"], recipients, msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
                server.ehlo()
                if cfg["security"] != "none":
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                server.login(cfg["user"], _first_env("SMTP_PASSWORD", "SMTP_PASS", "MAIL_PASSWORD"))
                server.sendmail(parseaddr(cfg["from_email"])[1] or cfg["from_email"], recipients, msg.as_string())

        log_email(db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, to_email=", ".join(recipients), subject=subject, status="sent", created_by_email=created_by_email, template_key=template_key)
        return True, ""
    except Exception as exc:
        err = f"{exc.__class__.__name__}: {str(exc)}"
        try:
            print(f"SMTP_SEND_ERROR | version={EMAIL_VERSION} host={cfg.get('host')} port={cfg.get('port')} security={cfg.get('security')} user={cfg.get('user')} from={cfg.get('from_email')} to={', '.join(recipients)} template={template_key} | {err}", flush=True)
        except Exception:
            pass
        log_email(db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, to_email=", ".join(recipients), subject=subject, status="error", error=err, created_by_email=created_by_email, template_key=template_key)
        return False, err


def send_template_email(db, to_email: str, template_key: str, *, data: Optional[Dict[str, Any]] = None, event_type: str = "system", entity_type: str = "", entity_id: str = "", created_by_email: str = "") -> Tuple[bool, str]:
    """Safe template sender. Supports both old 2-value and new 3-value templates."""
    try:
        tpl = email_template(template_key, **(data or {}))
        if isinstance(tpl, (list, tuple)) and len(tpl) >= 3:
            subject, body, html = tpl[0], tpl[1], tpl[2]
        elif isinstance(tpl, (list, tuple)) and len(tpl) == 2:
            subject, body = tpl
            html = None
        else:
            subject = f"HUB ASTORIE – {template_key}"
            body = str(tpl or "")
            html = None
    except Exception as exc:
        subject = f"HUB ASTORIE – {template_key}"
        body = f"Dobrý den,\n\ne-mail byl vytvořen systémem HUB ASTORIE.\n\nPoznámka šablony: {exc}\n\nASTORIE a.s."
        html = None
    return send_email(
        db,
        to_email,
        subject,
        body,
        html_body=html,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        created_by_email=created_by_email,
        template_key=template_key,
    )
