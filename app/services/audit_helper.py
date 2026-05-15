from datetime import datetime, timezone
import json

from sqlalchemy import text


def safe_audit(db, user_email: str, action: str, entity: str, entity_id: str = "", old_data=None, new_data=None, note: str = ""):
    """Safe audit writer. Never breaks the business action if audit fails."""
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_history (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                user_email TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL DEFAULT '',
                entity TEXT NOT NULL DEFAULT '',
                entity_id TEXT NOT NULL DEFAULT '',
                old_data TEXT NOT NULL DEFAULT '',
                new_data TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT ''
            )
        """))
        db.execute(
            text("""
                INSERT INTO audit_history
                (created_at, user_email, action, entity, entity_id, old_data, new_data, note)
                VALUES
                (:created_at, :user_email, :action, :entity, :entity_id, :old_data, :new_data, :note)
            """),
            {
                "created_at": datetime.now(timezone.utc),
                "user_email": user_email or "admin@astorie.local",
                "action": action or "",
                "entity": entity or "",
                "entity_id": str(entity_id or ""),
                "old_data": json.dumps(old_data or {}, ensure_ascii=False, default=str),
                "new_data": json.dumps(new_data or {}, ensure_ascii=False, default=str),
                "note": note or "",
            },
        )
        db.commit()
    except Exception:
        db.rollback()


def model_snapshot(obj, fields):
    data = {}
    for f in fields:
        data[f] = getattr(obj, f, None)
    return data
