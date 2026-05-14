from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core_models import AuditLog, Partner, Section, Subsection, User
from app.services.passwords import hash_password

router = APIRouter(tags=["admin-ui"])


def render(request: Request, template_name: str, context: dict):
    templates = request.app.state.templates
    base_context = {
        "request": request,
        "app_name": "HUB",
        "version": "v0.3.0",
        "admin_name": "Admin ASTORIE",
        "admin_email": "nekudova@astorieas.cz",
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context)


def audit(db: Session, action: str, entity_type: str, payload: dict):
    try:
        db.add(AuditLog(user_email="admin@astorie.local", action=action, entity_type=entity_type, new_value=payload))
        db.commit()
    except Exception:
        db.rollback()


@router.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse(url="/admin", status_code=302)


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    counts = {
        "users": db.query(User).count(),
        "sections": db.query(Section).count(),
        "subsections": db.query(Subsection).count(),
        "partners": db.query(Partner).count(),
        "audit": db.query(AuditLog).count(),
    }
    latest_audit = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(8).all()
    return render(request, "dashboard.html", {"active": "dashboard", "counts": counts, "latest_audit": latest_audit})


@router.get("/admin/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return render(request, "users.html", {"active": "users", "users": users})


@router.post("/admin/users")
def create_user(
    advisor_id: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    role: str = Form("IF"),
    password: str = Form("1234"),
    db: Session = Depends(get_db),
):
    user = User(
        advisor_id=advisor_id.strip(),
        name=name.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        role=role.strip().upper(),
        password_hash=hash_password(password),
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    audit(db, "CREATE", "users", {"advisor_id": advisor_id, "email": email, "role": role})
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/admin/users/{user_id}/toggle")
def toggle_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_active = not user.is_active
        db.commit()
        audit(db, "TOGGLE_ACTIVE", "users", {"id": user_id, "is_active": user.is_active})
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/admin/sections", response_class=HTMLResponse)
def sections_page(request: Request, db: Session = Depends(get_db)):
    sections = db.query(Section).order_by(Section.sort_order.asc(), Section.name.asc()).all()
    subsections = db.query(Subsection).order_by(Subsection.section_code.asc(), Subsection.sort_order.asc()).all()
    return render(request, "sections.html", {"active": "sections", "sections": sections, "subsections": subsections})


@router.post("/admin/sections")
def create_section(
    section_code: str = Form(...),
    name: str = Form(...),
    icon: str = Form(""),
    sort_order: int = Form(0),
    db: Session = Depends(get_db),
):
    row = Section(section_code=section_code.strip().upper(), name=name.strip(), icon=icon.strip(), sort_order=sort_order, is_active=True)
    db.add(row)
    db.commit()
    audit(db, "CREATE", "sections", {"section_code": section_code, "name": name})
    return RedirectResponse(url="/admin/sections", status_code=303)


@router.post("/admin/subsections")
def create_subsection(
    subsection_code: str = Form(...),
    section_code: str = Form(...),
    name: str = Form(...),
    sort_order: int = Form(0),
    db: Session = Depends(get_db),
):
    row = Subsection(
        subsection_code=subsection_code.strip().upper(),
        section_code=section_code.strip().upper(),
        name=name.strip(),
        sort_order=sort_order,
        is_active=True,
    )
    db.add(row)
    db.commit()
    audit(db, "CREATE", "subsections", {"subsection_code": subsection_code, "section_code": section_code, "name": name})
    return RedirectResponse(url="/admin/sections", status_code=303)


@router.get("/admin/partners", response_class=HTMLResponse)
def partners_page(request: Request, db: Session = Depends(get_db)):
    partners = db.query(Partner).order_by(Partner.name.asc()).all()
    return render(request, "partners.html", {"active": "partners", "partners": partners})


@router.post("/admin/partners")
def create_partner(
    partner_code: str = Form(...),
    name: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    row = Partner(partner_code=partner_code.strip().upper(), name=name.strip(), note=note.strip(), is_active=True)
    db.add(row)
    db.commit()
    audit(db, "CREATE", "partners", {"partner_code": partner_code, "name": name})
    return RedirectResponse(url="/admin/partners", status_code=303)


@router.get("/admin/audit", response_class=HTMLResponse)
def audit_page(request: Request, db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return render(request, "audit.html", {"active": "audit", "rows": rows})
