from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core_models import AuditLog, Partner, Section, Subsection, User
from app.models.contact_models import PartnerContact, PartnerLink, PartnerProduct
from app.services.passwords import hash_password
from app.services.importer import IMPORT_HANDLERS

router = APIRouter(tags=["admin-ui"])


def render(request: Request, template_name: str, context: dict):
    templates = request.app.state.templates
    base_context = {
        "request": request,
        "app_name": "HUB",
        "version": "v0.3.6",
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
@router.get("/admin/", response_class=HTMLResponse)
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


@router.get("/admin/import", response_class=HTMLResponse)
def import_page(request: Request):
    return render(request, "import.html", {"active": "import", "result": None})


@router.post("/admin/import", response_class=HTMLResponse)
async def import_csv(
    request: Request,
    entity: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    handler = IMPORT_HANDLERS.get(entity)
    if not handler:
        return render(request, "import.html", {
            "active": "import",
            "result": {"ok": False, "entity": entity, "errors": ["Neznámý typ importu."]},
        })

    raw = await file.read()
    try:
        result = handler(db, raw).as_dict()
    except Exception as exc:
        result = {"ok": False, "entity": entity, "errors": [str(exc)]}

    return render(request, "import.html", {"active": "import", "result": result})


@router.get("/admin/contacts", response_class=HTMLResponse)
def contacts_page(request: Request, q: str = "", partner: str = "", db: Session = Depends(get_db)):
    query = db.query(PartnerContact)
    if partner:
        query = query.filter(PartnerContact.partner_code == partner.upper())
    if q:
        like = f"%{q}%"
        query = query.filter(
            (PartnerContact.full_name.ilike(like)) |
            (PartnerContact.role.ilike(like)) |
            (PartnerContact.email.ilike(like)) |
            (PartnerContact.phone.ilike(like)) |
            (PartnerContact.specialization.ilike(like)) |
            (PartnerContact.territory.ilike(like)) |
            (PartnerContact.contact_type.ilike(like)) |
            (PartnerContact.partner_code.ilike(like))
        )
    contacts = query.order_by(PartnerContact.partner_code, PartnerContact.full_name).limit(500).all()
    partners = db.query(Partner).order_by(Partner.name).all()
    return render(request, "contacts.html", {"active": "contacts", "contacts": contacts, "partners": partners, "q": q, "partner": partner})


@router.post("/admin/contacts/create")
def create_contact(request: Request, partner_code: str = Form(...), full_name: str = Form(...), role: str = Form(""), email: str = Form(""), phone: str = Form(""), specialization: str = Form(""), contact_type: str = Form(""), territory: str = Form(""), is_vip: str = Form(""), note: str = Form(""), db: Session = Depends(get_db)):
    db.add(PartnerContact(partner_code=partner_code.upper().strip(), full_name=full_name, role=role, email=email, phone=phone, specialization=specialization, contact_type=contact_type, territory=territory, is_vip=bool(is_vip), is_top=bool(is_vip), note=note, is_active=True))
    db.commit()
    return RedirectResponse("/admin/contacts", status_code=303)


@router.post("/admin/contacts/{item_id}/duplicate")
def duplicate_contact(item_id: int, db: Session = Depends(get_db)):
    item = db.query(PartnerContact).filter(PartnerContact.id == item_id).first()
    if item:
        db.add(PartnerContact(partner_code=item.partner_code, full_name=item.full_name + " – kopie", role=item.role, email=item.email, phone=item.phone, specialization=item.specialization, contact_type=item.contact_type, territory=item.territory, is_vip=item.is_vip, is_top=item.is_top, note=item.note, is_active=item.is_active))
        db.commit()
    return RedirectResponse("/admin/contacts", status_code=303)


@router.get("/admin/links", response_class=HTMLResponse)
def links_page(request: Request, q: str = "", partner: str = "", db: Session = Depends(get_db)):
    query = db.query(PartnerLink)
    if partner:
        query = query.filter(PartnerLink.partner_code == partner.upper())
    if q:
        like = f"%{q}%"
        query = query.filter((PartnerLink.title.ilike(like)) | (PartnerLink.url.ilike(like)) | (PartnerLink.category.ilike(like)) | (PartnerLink.note.ilike(like)) | (PartnerLink.partner_code.ilike(like)))
    links = query.order_by(PartnerLink.partner_code, PartnerLink.title).limit(500).all()
    partners = db.query(Partner).order_by(Partner.name).all()
    return render(request, "links.html", {"active": "links", "links": links, "partners": partners, "q": q, "partner": partner})


@router.post("/admin/links/create")
def create_link(request: Request, partner_code: str = Form(...), title: str = Form(...), url: str = Form(...), category: str = Form(""), note: str = Form(""), db: Session = Depends(get_db)):
    db.add(PartnerLink(partner_code=partner_code.upper().strip(), title=title, url=url, category=category, note=note, is_active=True))
    db.commit()
    return RedirectResponse("/admin/links", status_code=303)


@router.post("/admin/links/{item_id}/duplicate")
def duplicate_link(item_id: int, db: Session = Depends(get_db)):
    item = db.query(PartnerLink).filter(PartnerLink.id == item_id).first()
    if item:
        db.add(PartnerLink(partner_code=item.partner_code, title=item.title + " – kopie", url=item.url, category=item.category, note=item.note, is_active=item.is_active))
        db.commit()
    return RedirectResponse("/admin/links", status_code=303)


@router.get("/admin/products", response_class=HTMLResponse)
def products_page(request: Request, q: str = "", partner: str = "", db: Session = Depends(get_db)):
    query = db.query(PartnerProduct)
    if partner:
        query = query.filter(PartnerProduct.partner_code == partner.upper())
    if q:
        like = f"%{q}%"
        query = query.filter((PartnerProduct.partner_code.ilike(like)) | (PartnerProduct.area.ilike(like)) | (PartnerProduct.subarea.ilike(like)) | (PartnerProduct.product_name.ilike(like)) | (PartnerProduct.note.ilike(like)))
    products = query.order_by(PartnerProduct.partner_code, PartnerProduct.area, PartnerProduct.product_name).limit(500).all()
    partners = db.query(Partner).order_by(Partner.name).all()
    return render(request, "products.html", {"active": "products", "products": products, "partners": partners, "q": q, "partner": partner})


@router.post("/admin/products/create")
def create_product(request: Request, partner_code: str = Form(...), area: str = Form(""), subarea: str = Form(""), product_name: str = Form(...), note: str = Form(""), db: Session = Depends(get_db)):
    db.add(PartnerProduct(partner_code=partner_code.upper().strip(), area=area, subarea=subarea, product_name=product_name, note=note, is_active=True))
    db.commit()
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/admin/products/{item_id}/duplicate")
def duplicate_product(item_id: int, db: Session = Depends(get_db)):
    item = db.query(PartnerProduct).filter(PartnerProduct.id == item_id).first()
    if item:
        db.add(PartnerProduct(partner_code=item.partner_code, area=item.area, subarea=item.subarea, product_name=item.product_name + " – kopie", note=item.note, is_active=item.is_active))
        db.commit()
    return RedirectResponse("/admin/products", status_code=303)


@router.get("/admin/partners/{partner_code}", response_class=HTMLResponse)
def partner_detail(request: Request, partner_code: str, db: Session = Depends(get_db)):
    partner = db.query(Partner).filter(Partner.partner_code == partner_code.upper()).first()
    contacts = db.query(PartnerContact).filter(PartnerContact.partner_code == partner_code.upper()).order_by(PartnerContact.full_name).all()
    links = db.query(PartnerLink).filter(PartnerLink.partner_code == partner_code.upper()).order_by(PartnerLink.title).all()
    products = db.query(PartnerProduct).filter(PartnerProduct.partner_code == partner_code.upper()).order_by(PartnerProduct.area, PartnerProduct.product_name).all()
    return render(request, "partner_detail.html", {"active": "partners", "partner": partner, "partner_code": partner_code.upper(), "contacts": contacts, "links": links, "products": products})
