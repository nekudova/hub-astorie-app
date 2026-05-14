from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.core_models import User, Role, Section, Subsection, Partner, Tip, CommissionRate, AuditLog

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/summary")
def admin_summary(db: Session = Depends(get_db)):
    return {
        "ok": True,
        "version": "0.2.0",
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

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.created_at.desc()).limit(200).all()
    return {
        "ok": True,
        "users": [
            {
                "id": str(u.id),
                "advisor_id": u.advisor_id,
                "name": u.name,
                "email": u.email,
                "phone": u.phone,
                "is_active": u.is_active,
                "must_change_password": u.must_change_password,
            } for u in rows
        ],
    }
