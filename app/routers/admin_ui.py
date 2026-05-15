from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.audit_helper import safe_audit, model_snapshot
from app.core.database import get_db
from app.models.core_models import AuditLog, Partner, Section, Subsection, User
from app.models.contact_models import PartnerContact, PartnerLink, PartnerProduct
from app.services.passwords import hash_password
from app.services.importer import IMPORT_HANDLERS
from app.services.ares import fetch_ares_subject

router = APIRouter(tags=["admin-ui"])


def render(request: Request, template_name: str, context: dict):
    templates = request.app.state.templates
    base_context = {
        "request": request,
        "app_name": "HUB",
        "version": "v0.5.2",
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
def partners_page(
    request: Request,
    q: str = "",
    status: str = "",
    segment: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(Partner)

    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            (Partner.partner_code.ilike(like)) |
            (Partner.name.ilike(like)) |
            (Partner.ico.ilike(like)) |
            (Partner.data_box.ilike(like)) |
            (Partner.registry_email.ilike(like)) |
            (Partner.city.ilike(like)) |
            (Partner.address_full.ilike(like))
        )

    if status:
        query = query.filter(Partner.partner_status == status)

    if segment == "vip":
        query = query.filter(Partner.is_vip == True)
    elif segment == "fleet":
        query = query.filter(Partner.segment_fleet == True)
    elif segment == "retail":
        query = query.filter(Partner.segment_retail == True)
    elif segment == "life":
        query = query.filter(Partner.segment_life == True)
    elif segment == "business":
        query = query.filter(Partner.segment_business == True)
    elif segment == "missing_contact":
        query = query.outerjoin(PartnerContact, PartnerContact.partner_code == Partner.partner_code).filter(PartnerContact.id == None)

    partners = query.order_by(Partner.name).limit(1000).all()

    return render(request, "partners.html", {
        "active": "partners",
        "partners": partners,
        "q": q,
        "status": status,
        "segment": segment,
    })


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


@router.get("/api/ares/subject")
def api_ares_subject(ico: str):
    return JSONResponse(fetch_ares_subject(ico))


@router.post("/admin/partners/create-extended")
def create_partner_extended(
    request: Request,
    partner_code: str = Form(...),
    name: str = Form(...),
    ico: str = Form(""),
    dic: str = Form(""),
    data_box: str = Form(""),
    registry_email: str = Form(""),
    street: str = Form(""),
    city: str = Form(""),
    zip_code: str = Form(""),
    address_full: str = Form(""),
    legal_form: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    code = partner_code.upper().strip()
    existing = db.query(Partner).filter(Partner.partner_code == code).first()
    if existing:
        existing.name = name
        existing.ico = ico
        existing.dic = dic
        existing.data_box = data_box
        existing.registry_email = registry_email
        existing.street = street
        existing.city = city
        existing.zip_code = zip_code
        existing.address_full = address_full
        existing.legal_form = legal_form
        existing.note = note
        existing.is_active = True
    else:
        db.add(Partner(
            partner_code=code,
            name=name,
            ico=ico,
            dic=dic,
            data_box=data_box,
            registry_email=registry_email,
            street=street,
            city=city,
            zip_code=zip_code,
            address_full=address_full,
            legal_form=legal_form,
            note=note,
            is_active=True,
        ))
    db.commit()
    return RedirectResponse("/admin/partners", status_code=303)


@router.post("/admin/partners/{partner_code}/ares-refresh")
def refresh_partner_from_ares(partner_code: str, db: Session = Depends(get_db)):
    partner = db.query(Partner).filter(Partner.partner_code == partner_code.upper()).first()
    if not partner or not partner.ico:
        return RedirectResponse(f"/admin/partners/{partner_code.upper()}", status_code=303)

    data = fetch_ares_subject(partner.ico)
    if data.get("ok"):
        partner.name = data.get("name") or partner.name
        partner.dic = data.get("dic") or partner.dic
        partner.data_box = data.get("data_box") or partner.data_box
        partner.street = data.get("street") or partner.street
        partner.city = data.get("city") or partner.city
        partner.zip_code = data.get("zip_code") or partner.zip_code
        partner.address_full = data.get("address_full") or partner.address_full
        partner.legal_form = data.get("legal_form") or partner.legal_form
        partner.source = "ARES"
        db.commit()

    return RedirectResponse(f"/admin/partners/{partner_code.upper()}", status_code=303)


@router.post("/admin/partners/{partner_code}/duplicate-partner")
def duplicate_partner(partner_code: str, db: Session = Depends(get_db)):
    src = db.query(Partner).filter(Partner.partner_code == partner_code.upper()).first()
    if not src:
        return RedirectResponse("/admin/partners", status_code=303)

    base_code = (src.partner_code + "_COPY")[:40]
    code = base_code
    counter = 1
    while db.query(Partner).filter(Partner.partner_code == code).first():
        counter += 1
        code = f"{base_code}_{counter}"[:50]

    db.add(Partner(
        partner_code=code,
        name=(src.name or "") + " – kopie",
        ico=src.ico,
        dic=src.dic,
        data_box=src.data_box,
        registry_email=src.registry_email,
        street=src.street,
        city=src.city,
        zip_code=src.zip_code,
        address_full=src.address_full,
        legal_form=src.legal_form,
        source=src.source,
        note=src.note,
        partner_status=getattr(src, "partner_status", "aktivní"),
        cooperation_status=getattr(src, "cooperation_status", ""),
        is_vip=getattr(src, "is_vip", False),
        segment_fleet=getattr(src, "segment_fleet", False),
        segment_retail=getattr(src, "segment_retail", False),
        segment_life=getattr(src, "segment_life", False),
        segment_business=getattr(src, "segment_business", False),
        onboarding_done=getattr(src, "onboarding_done", False),
        contract_valid=getattr(src, "contract_valid", False),
        last_audit_note=getattr(src, "last_audit_note", ""),
        is_active=True,
    ))
    db.commit()
    return RedirectResponse("/admin/partners", status_code=303)


@router.post("/admin/partners/{partner_code}/update")
def update_partner(
    partner_code: str,
    request: Request,
    name: str = Form(...),
    ico: str = Form(""),
    dic: str = Form(""),
    data_box: str = Form(""),
    registry_email: str = Form(""),
    street: str = Form(""),
    city: str = Form(""),
    zip_code: str = Form(""),
    address_full: str = Form(""),
    legal_form: str = Form(""),
    note: str = Form(""),
    partner_status: str = Form("aktivní"),
    cooperation_status: str = Form(""),
    is_vip: str = Form(""),
    segment_fleet: str = Form(""),
    segment_retail: str = Form(""),
    segment_life: str = Form(""),
    segment_business: str = Form(""),
    onboarding_done: str = Form(""),
    contract_valid: str = Form(""),
    last_audit_note: str = Form(""),
    is_active: str = Form(""),
    db: Session = Depends(get_db),
):
    partner = db.query(Partner).filter(Partner.partner_code == partner_code.upper()).first()
    if not partner:
        return RedirectResponse("/admin/partners", status_code=303)

    old_snapshot = model_snapshot(partner, [
        "name", "ico", "dic", "data_box", "registry_email", "street", "city", "zip_code",
        "address_full", "legal_form", "note", "is_active"
    ])

    partner.name = name
    partner.ico = ico
    partner.dic = dic
    partner.data_box = data_box
    partner.registry_email = registry_email
    partner.street = street
    partner.city = city
    partner.zip_code = zip_code
    partner.address_full = address_full
    partner.legal_form = legal_form
    partner.note = note
    partner.partner_status = partner_status
    partner.cooperation_status = cooperation_status
    partner.is_vip = bool(is_vip)
    partner.segment_fleet = bool(segment_fleet)
    partner.segment_retail = bool(segment_retail)
    partner.segment_life = bool(segment_life)
    partner.segment_business = bool(segment_business)
    partner.onboarding_done = bool(onboarding_done)
    partner.contract_valid = bool(contract_valid)
    partner.last_audit_note = last_audit_note
    partner.is_active = bool(is_active)
    new_snapshot = model_snapshot(partner, [
        "name", "ico", "dic", "data_box", "registry_email", "street", "city", "zip_code",
        "address_full", "legal_form", "note", "is_active"
    ])
    db.commit()
    safe_audit(db, "admin@astorie.local", "UPDATE", "partner", partner.partner_code, old_snapshot, new_snapshot, "Úprava partnera")

    return RedirectResponse(f"/admin/partners/{partner.partner_code}", status_code=303)


@router.get("/api/partners/{partner_code}/registry")
def api_partner_registry(partner_code: str, db: Session = Depends(get_db)):
    partner = db.query(Partner).filter(Partner.partner_code == partner_code.upper()).first()
    if not partner:
        return JSONResponse({"ok": False, "error": "Partner nebyl nalezen."}, status_code=404)

    return {
        "ok": True,
        "partner": {
            "partner_code": partner.partner_code,
            "name": partner.name,
            "ico": partner.ico,
            "dic": partner.dic,
            "data_box": partner.data_box,
            "registry_email": partner.registry_email,
            "street": partner.street,
            "city": partner.city,
            "zip_code": partner.zip_code,
            "address_full": partner.address_full,
            "legal_form": partner.legal_form,
            "note": partner.note,
            "is_active": partner.is_active,
            "partner_status": getattr(partner, "partner_status", "aktivní"),
            "cooperation_status": getattr(partner, "cooperation_status", ""),
            "is_vip": getattr(partner, "is_vip", False),
            "segment_fleet": getattr(partner, "segment_fleet", False),
            "segment_retail": getattr(partner, "segment_retail", False),
            "segment_life": getattr(partner, "segment_life", False),
            "segment_business": getattr(partner, "segment_business", False),
        }
    }


@router.post("/admin/contacts/{item_id}/update")
def update_contact(
    item_id: int,
    partner_code: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    specialization: str = Form(""),
    contact_type: str = Form(""),
    territory: str = Form(""),
    is_vip: str = Form(""),
    note: str = Form(""),
    is_active: str = Form(""),
    db: Session = Depends(get_db),
):
    item = db.query(PartnerContact).filter(PartnerContact.id == item_id).first()
    if item:
        item.partner_code = partner_code.upper().strip()
        item.full_name = full_name
        item.role = role
        item.email = email
        item.phone = phone
        item.specialization = specialization
        item.contact_type = contact_type
        item.territory = territory
        item.is_vip = bool(is_vip)
        item.is_top = bool(is_vip)
        item.note = note
        item.is_active = bool(is_active)
        db.commit()
        return RedirectResponse(f"/admin/partners/{item.partner_code}", status_code=303)
    return RedirectResponse("/admin/contacts", status_code=303)


@router.post("/admin/contacts/{item_id}/toggle")
def toggle_contact(item_id: int, db: Session = Depends(get_db)):
    item = db.query(PartnerContact).filter(PartnerContact.id == item_id).first()
    if item:
        item.is_active = not item.is_active
        partner_code = item.partner_code
        db.commit()
        return RedirectResponse(f"/admin/partners/{partner_code}", status_code=303)
    return RedirectResponse("/admin/contacts", status_code=303)


@router.post("/admin/links/{item_id}/update")
def update_link(
    item_id: int,
    partner_code: str = Form(...),
    title: str = Form(...),
    url: str = Form(...),
    category: str = Form(""),
    note: str = Form(""),
    is_active: str = Form(""),
    db: Session = Depends(get_db),
):
    item = db.query(PartnerLink).filter(PartnerLink.id == item_id).first()
    if item:
        item.partner_code = partner_code.upper().strip()
        item.title = title
        item.url = url
        item.category = category
        item.note = note
        item.is_active = bool(is_active)
        db.commit()
        return RedirectResponse(f"/admin/partners/{item.partner_code}", status_code=303)
    return RedirectResponse("/admin/links", status_code=303)


@router.post("/admin/links/{item_id}/toggle")
def toggle_link(item_id: int, db: Session = Depends(get_db)):
    item = db.query(PartnerLink).filter(PartnerLink.id == item_id).first()
    if item:
        item.is_active = not item.is_active
        partner_code = item.partner_code
        db.commit()
        return RedirectResponse(f"/admin/partners/{partner_code}", status_code=303)
    return RedirectResponse("/admin/links", status_code=303)


@router.post("/admin/products/{item_id}/update")
def update_product(
    item_id: int,
    partner_code: str = Form(...),
    area: str = Form(""),
    subarea: str = Form(""),
    product_name: str = Form(...),
    note: str = Form(""),
    is_active: str = Form(""),
    db: Session = Depends(get_db),
):
    item = db.query(PartnerProduct).filter(PartnerProduct.id == item_id).first()
    if item:
        item.partner_code = partner_code.upper().strip()
        item.area = area
        item.subarea = subarea
        item.product_name = product_name
        item.note = note
        item.is_active = bool(is_active)
        db.commit()
        return RedirectResponse(f"/admin/partners/{item.partner_code}", status_code=303)
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/admin/products/{item_id}/toggle")
def toggle_product(item_id: int, db: Session = Depends(get_db)):
    item = db.query(PartnerProduct).filter(PartnerProduct.id == item_id).first()
    if item:
        item.is_active = not item.is_active
        partner_code = item.partner_code
        db.commit()
        return RedirectResponse(f"/admin/partners/{partner_code}", status_code=303)
    return RedirectResponse("/admin/products", status_code=303)


@router.get("/api/partners/search")
def api_partner_search(q: str = "", limit: int = 20, db: Session = Depends(get_db)):
    text = (q or "").strip()
    query = db.query(Partner).filter(Partner.is_active == True)

    if text:
        like = f"%{text.lower()}%"
        query = query.filter(
            (Partner.partner_code.ilike(like)) |
            (Partner.name.ilike(like)) |
            (Partner.ico.ilike(like)) |
            (Partner.data_box.ilike(like)) |
            (Partner.registry_email.ilike(like)) |
            (Partner.city.ilike(like))
        )

    items = query.order_by(Partner.name).limit(max(1, min(limit, 50))).all()

    return {
        "ok": True,
        "items": [
            {
                "partner_code": p.partner_code,
                "label": f"{p.partner_code} – {p.name}",
                "name": p.name,
                "ico": p.ico,
                "data_box": p.data_box,
                "email": p.registry_email,
                "city": p.city,
            }
            for p in items
        ],
    }


@router.get("/api/partners/{partner_code}/form-source")
def api_partner_form_source(partner_code: str, db: Session = Depends(get_db)):
    partner = db.query(Partner).filter(Partner.partner_code == partner_code.upper()).first()
    if not partner:
        return JSONResponse({"ok": False, "error": "Partner nebyl nalezen."}, status_code=404)

    top_contacts = (
        db.query(PartnerContact)
        .filter(PartnerContact.partner_code == partner.partner_code)
        .filter(PartnerContact.is_active == True)
        .order_by(PartnerContact.is_top.desc(), PartnerContact.is_vip.desc(), PartnerContact.full_name)
        .limit(10)
        .all()
    )

    links = (
        db.query(PartnerLink)
        .filter(PartnerLink.partner_code == partner.partner_code)
        .filter(PartnerLink.is_active == True)
        .order_by(PartnerLink.category, PartnerLink.title)
        .limit(20)
        .all()
    )

    products = (
        db.query(PartnerProduct)
        .filter(PartnerProduct.partner_code == partner.partner_code)
        .filter(PartnerProduct.is_active == True)
        .order_by(PartnerProduct.area, PartnerProduct.subarea, PartnerProduct.product_name)
        .limit(50)
        .all()
    )

    return {
        "ok": True,
        "partner": {
            "partner_code": partner.partner_code,
            "name": partner.name,
            "ico": partner.ico,
            "dic": partner.dic,
            "data_box": partner.data_box,
            "registry_email": partner.registry_email,
            "street": partner.street,
            "city": partner.city,
            "zip_code": partner.zip_code,
            "address_full": partner.address_full,
            "legal_form": partner.legal_form,
            "is_active": partner.is_active,
            "partner_status": getattr(partner, "partner_status", "aktivní"),
            "cooperation_status": getattr(partner, "cooperation_status", ""),
            "is_vip": getattr(partner, "is_vip", False),
            "segment_fleet": getattr(partner, "segment_fleet", False),
            "segment_retail": getattr(partner, "segment_retail", False),
            "segment_life": getattr(partner, "segment_life", False),
            "segment_business": getattr(partner, "segment_business", False),
        },
        "form_prefill": {
            "insurer_name": partner.name,
            "insurer_ico": partner.ico,
            "insurer_data_box": partner.data_box,
            "insurer_email": partner.registry_email,
            "insurer_address": partner.address_full or " ".join([x for x in [partner.street, partner.zip_code, partner.city] if x]),
        },
        "contacts": [
            {
                "full_name": c.full_name,
                "role": c.role,
                "contact_type": c.contact_type,
                "territory": c.territory,
                "email": c.email,
                "phone": c.phone,
                "is_top": c.is_top or c.is_vip,
            }
            for c in top_contacts
        ],
        "links": [
            {
                "title": l.title,
                "url": l.url,
                "category": l.category,
            }
            for l in links
        ],
        "products": [
            {
                "area": p.area,
                "subarea": p.subarea,
                "product_name": p.product_name,
            }
            for p in products
        ],
    }


@router.get("/admin/form-bridge", response_class=HTMLResponse)
def form_bridge_page(request: Request):
    return render(request, "form_bridge.html", {"active": "form_bridge"})


@router.get("/admin/terminations", response_class=HTMLResponse)
def terminations_page(request: Request, partner_code: str = "", db: Session = Depends(get_db)):
    partner = db.query(Partner).filter(Partner.partner_code == partner_code.upper()).first() if partner_code else None
    return render(request, "terminations.html", {
        "active": "terminations",
        "partner": partner,
        "partner_code": partner_code.upper() if partner_code else "",
    })


@router.post("/admin/terminations/preview", response_class=HTMLResponse)
def termination_preview(
    request: Request,
    partner_code: str = Form(""),
    termination_type: str = Form("A"),
    client_name: str = Form(""),
    client_identifier: str = Form(""),
    client_address: str = Form(""),
    policy_no: str = Form(""),
    insurance_type: str = Form(""),
    insured_subject: str = Form(""),
    bank_account: str = Form(""),
    extra_date: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    partner = db.query(Partner).filter(Partner.partner_code == partner_code.upper()).first() if partner_code else None

    reason_map = {
        "A": "ke konci pojistného období",
        "B": "ve lhůtě do 2 měsíců od uzavření smlouvy",
        "C": "po oznámení pojistné události",
        "D": "z důvodu nesouhlasu se změnou výše pojistného",
        "E": "z důvodu zániku pojistného zájmu – prodej předmětu pojištění",
        "F": "z důvodu vyřazení vozidla z evidence / odcizení",
    }

    insurer_name = partner.name if partner else ""
    insurer_address = partner.address_full if partner else ""
    insurer_data_box = partner.data_box if partner else ""
    insurer_email = partner.registry_email if partner else ""

    lines = [
        "VÝPOVĚĎ POJISTNÉ SMLOUVY",
        "",
        f"Adresát: {insurer_name}",
    ]
    if insurer_address:
        lines.append(f"Adresa: {insurer_address}")
    if insurer_data_box:
        lines.append(f"Datová schránka: {insurer_data_box}")
    if insurer_email:
        lines.append(f"E-mail: {insurer_email}")

    lines += [
        "",
        f"Pojistník: {client_name}",
    ]
    if client_identifier:
        lines.append(f"Identifikace: {client_identifier}")
    if client_address:
        lines.append(f"Adresa pojistníka: {client_address}")

    lines += [
        "",
        f"Tímto vypovídám pojistnou smlouvu č. {policy_no}.",
        f"Výpověď podávám {reason_map.get(termination_type, reason_map['A'])}.",
    ]

    if extra_date:
        lines.append(f"Rozhodné datum: {extra_date}")
    if insurance_type:
        lines.append(f"Druh pojištění: {insurance_type}")
    if insured_subject:
        lines.append(f"Identifikace předmětu pojištění: {insured_subject}")

    lines += [
        "",
        "Žádám o potvrzení přijetí této výpovědi.",
    ]
    if bank_account:
        lines.append(f"Případný přeplatek pojistného žádám zaslat na bankovní účet: {bank_account}.")
    else:
        lines.append("Případný přeplatek pojistného žádám zaslat na adresu pojistníka.")
    if note:
        lines += ["", f"Poznámka: {note}"]

    return render(request, "termination_preview.html", {
        "active": "terminations",
        "partner": partner,
        "partner_code": partner_code.upper() if partner_code else "",
        "preview_text": "\\n".join(lines),
    })


@router.get("/admin/modules", response_class=HTMLResponse)
def modules_page(request: Request, focus: str = '', db: Session = Depends(get_db)):
    modules = [
        {
            "group": "TIP HUB",
            "items": [
                {"name": "Nový TIP", "status": "připraveno", "desc": "Budoucí migrace zadání TIPu z uživatelského HUBu.", "url": "/admin/modules"},
                {"name": "Moje TIPy", "status": "připraveno", "desc": "Budoucí přehled odeslaných a přidělených TIPů.", "url": "/admin/modules"},
                {"name": "Specialisté", "status": "připraveno", "desc": "Správa specialistů, dostupnosti a routingu.", "url": "/admin/modules"},
                {"name": "Statistiky & soutěž", "status": "připraveno", "desc": "Budoucí manažerský žebříček a vyhodnocení TIPů.", "url": "/admin/modules"},
            ],
        },
        {
            "group": "ČÍSELNÍKY",
            "items": [
                {"name": "Poradci / uživatelé", "status": "funkční", "desc": "Základní správa uživatelů.", "url": "/admin/advisors"},
                {"name": "Sekce / podsekce", "status": "funkční", "desc": "Základní struktura oblastí.", "url": "/admin/sections"},
                {"name": "Partneři", "status": "funkční", "desc": "Centrální partner registry s ARES.", "url": "/admin/partners"},
                {"name": "Kontakty", "status": "funkční", "desc": "Kontakty partnerů.", "url": "/admin/contacts"},
                {"name": "Odkazy", "status": "funkční", "desc": "Odkazy partnerů.", "url": "/admin/links"},
                {"name": "Produkty", "status": "funkční", "desc": "Produkty partnerů.", "url": "/admin/products"},
            ],
        },
        {
            "group": "DOKUMENTY",
            "items": [
                {"name": "Výpovědi", "status": "funkční základ", "desc": "Modul výpovědí s napojením na partnera.", "url": "/admin/terminations"},
                {"name": "Formuláře", "status": "připraveno", "desc": "Budoucí generování dalších dokumentů.", "url": "/admin/form-bridge"},
                {"name": "Napojení formulářů", "status": "funkční", "desc": "API bridge pro přebírání dat partnera.", "url": "/admin/form-bridge"},
            ],
        },
        {
            "group": "SYSTÉM",
            "items": [
                {"name": "Import dat", "status": "funkční", "desc": "Import ze stávajících CSV/Sheets zdrojů.", "url": "/admin/import"},
                {"name": "Audit", "status": "funkční", "desc": "Záznam změn a provozních událostí.", "url": "/admin/audit"},
                {"name": "Health", "status": "funkční", "desc": "Kontrola běhu služby.", "url": "/health"},
                {"name": "API dokumentace", "status": "funkční", "desc": "OpenAPI dokumentace.", "url": "/docs"},
            ],
        },
    ]

    return render(request, "modules.html", {
        "active": "modules",
        "modules": modules,
        "focus": focus,
    })


@router.post("/admin/partners/registry-upgrade")
def partner_registry_upgrade(db: Session = Depends(get_db)):
    statements = [
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS partner_status VARCHAR(80) DEFAULT 'aktivní' NOT NULL",
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS cooperation_status VARCHAR(120) DEFAULT '' NOT NULL",
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS is_vip BOOLEAN DEFAULT FALSE NOT NULL",
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS segment_fleet BOOLEAN DEFAULT FALSE NOT NULL",
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS segment_retail BOOLEAN DEFAULT FALSE NOT NULL",
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS segment_life BOOLEAN DEFAULT FALSE NOT NULL",
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS segment_business BOOLEAN DEFAULT FALSE NOT NULL",
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS onboarding_done BOOLEAN DEFAULT FALSE NOT NULL",
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS contract_valid BOOLEAN DEFAULT FALSE NOT NULL",
        "ALTER TABLE partners ADD COLUMN IF NOT EXISTS last_audit_note TEXT DEFAULT '' NOT NULL",
    ]
    for sql in statements:
        db.execute(text(sql))
    db.commit()
    return RedirectResponse("/admin/partners", status_code=303)


@router.post("/admin/audit-history/upgrade")
def audit_history_upgrade(db: Session = Depends(get_db)):
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
    db.commit()
    return RedirectResponse("/admin/audit-history", status_code=303)


@router.get("/admin/audit-history", response_class=HTMLResponse)
def audit_history_page(
    request: Request,
    q: str = "",
    entity: str = "",
    action: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
):
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
    db.commit()

    sql = "SELECT * FROM audit_history WHERE 1=1"
    params = {}

    if q:
        sql += " AND (lower(user_email) LIKE :q OR lower(entity_id) LIKE :q OR lower(note) LIKE :q OR lower(new_data) LIKE :q OR lower(old_data) LIKE :q)"
        params["q"] = f"%{q.lower()}%"

    if entity:
        sql += " AND entity = :entity"
        params["entity"] = entity

    if action:
        sql += " AND action = :action"
        params["action"] = action

    sql += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = max(1, min(limit, 1000))

    rows = db.execute(text(sql), params).mappings().all()

    return render(request, "audit_history.html", {
        "active": "audit_history",
        "rows": rows,
        "q": q,
        "entity": entity,
        "action": action,
        "limit": limit,
    })


@router.get("/admin/partners/{partner_code}/history", response_class=HTMLResponse)
def partner_history_page(request: Request, partner_code: str, db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT * FROM audit_history
            WHERE entity_id = :partner_code OR lower(new_data) LIKE :like OR lower(old_data) LIKE :like
            ORDER BY created_at DESC
            LIMIT 300
        """),
        {"partner_code": partner_code.upper(), "like": f"%{partner_code.lower()}%"}
    ).mappings().all()

    partner = db.query(Partner).filter(Partner.partner_code == partner_code.upper()).first()

    return render(request, "partner_history.html", {
        "active": "partners",
        "partner": partner,
        "partner_code": partner_code.upper(),
        "rows": rows,
    })
