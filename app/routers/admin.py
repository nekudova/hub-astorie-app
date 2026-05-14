from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.core_models import User, Role, Section, Subsection, Partner, Tip, CommissionRate, AuditLog

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/summary")
def admin_summary(db: Session = Depends(get_db)):
    return {
        "ok": True,
        "version": "0.2.4-clean",
        "counts": {
            "users": db.query(User).count(),
            "roles": db.query(Role).count(),
            "sections": db.query(Section).count(),
            "subsections": db.query(Subsection).count(),
            "partners": db.query(Partner).count(),
            "tips": db.query(Tip).count(),
            "commission_rates": db.query(CommissionRate).count(),
            "audit_log": db.query(AuditLog).count(),
        },
    }
