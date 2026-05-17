from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin-api"])

TABLES = ["users", "roles", "app_settings", "sections", "subsections", "partners", "partner_contacts", "partner_links", "partner_products", "tips", "commission_rates", "audit_log"]


def safe_count_table(db: Session, table_name: str):
    exists = db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": f"public.{table_name}"}).scalar()
    if not exists:
        return {"exists": False, "count": 0, "error": None}
    try:
        count = db.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
        return {"exists": True, "count": int(count or 0), "error": None}
    except Exception as exc:
        return {"exists": True, "count": None, "error": str(exc)}


@router.get("/summary")
def admin_summary(db: Session = Depends(get_db)):
    return {
        "ok": True,
        "version": "1.1.8-partners-restore-visual-plus-grouping",
        "message": "Admin Core + Visible Sections Fix běží.",
        "counts": {table: safe_count_table(db, table) for table in TABLES},
    }
