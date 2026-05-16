import json
import re
from io import BytesIO
from datetime import datetime
import io
import csv
from decimal import Decimal
import uuid
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
        "version": "v0.9.8",
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
    try:
        ensure_visible_hub_sections_(db)
    except Exception:
        pass
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
def api_partner_search(q: str = "", limit: int = 15, db: Session = Depends(get_db)):
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

    items = query.order_by(Partner.name).limit(max(1, min(limit, 25))).all()

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
    limit: int = 150,
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



@router.get("/admin/advisors", response_class=HTMLResponse)
def advisors_page(
    request: Request,
    q: str = "",
    role: str = "",
    active: str = "",
    db: Session = Depends(get_db),
):
    # Bezpečný upgrade tabulky users – sekce Poradci nesmí spadnout kvůli chybějícím sloupcům.
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS advisor_id VARCHAR(80)"))
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255)"))
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(80)"))
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(120) DEFAULT 'IF' NOT NULL"))
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL"))
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE NOT NULL"))
    db.commit()

    sql = """
      SELECT
        id,
        COALESCE(advisor_id, '') AS advisor_id,
        COALESCE(name, '') AS name,
        COALESCE(email, '') AS email,
        COALESCE(phone, '') AS phone,
        COALESCE(role, '') AS role,
        COALESCE(is_active, TRUE) AS is_active,
        COALESCE(must_change_password, FALSE) AS must_change_password
      FROM users
      WHERE 1=1
    """
    params = {}

    if q:
        sql += """
          AND (
            lower(COALESCE(advisor_id, '')) LIKE :q OR
            lower(COALESCE(name, '')) LIKE :q OR
            lower(COALESCE(email, '')) LIKE :q OR
            lower(COALESCE(phone, '')) LIKE :q
          )
        """
        params["q"] = f"%{q.lower()}%"

    if role:
        sql += " AND COALESCE(role, '') = :role"
        params["role"] = role

    if active == "1":
        sql += " AND COALESCE(is_active, TRUE) = TRUE"
    elif active == "0":
        sql += " AND COALESCE(is_active, TRUE) = FALSE"

    sql += " ORDER BY name, advisor_id LIMIT 1000"

    advisors = db.execute(text(sql), params).mappings().all()

    return render(request, "advisors.html", {
        "active": "advisors",
        "advisors": advisors,
        "q": q,
        "role": role,
        "active_filter": active,
    })


@router.post("/admin/advisors/create")
def advisor_create(
    advisor_id: str = Form(""),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    role: str = Form("IF"),
    password: str = Form("1234"),
    is_active: str = Form(""),
    db: Session = Depends(get_db),
):
    # Heslo ukládáme přes existující hash helper, pokud je dostupný.
    try:
        password_hash = hash_password(password)
    except Exception:
        password_hash = password

    db.execute(text("""
      INSERT INTO users
        (advisor_id, name, email, phone, role, password_hash, is_active, must_change_password)
      VALUES
        (:advisor_id, :name, :email, :phone, :role, :password_hash, :is_active, TRUE)
    """), {
        "advisor_id": advisor_id,
        "name": name,
        "email": email.lower().strip(),
        "phone": phone,
        "role": role,
        "password_hash": password_hash,
        "is_active": bool(is_active),
    })
    db.commit()

    safe_audit(db, "admin@astorie.local", "CREATE", "advisor", advisor_id or email, {}, {
        "advisor_id": advisor_id, "name": name, "email": email, "role": role, "is_active": bool(is_active)
    }, "Založení poradce / uživatele")

    return RedirectResponse("/admin/advisors", status_code=303)


@router.post("/admin/advisors/{user_id}/update")
def advisor_update(
    user_id: int,
    advisor_id: str = Form(""),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    role: str = Form("IF"),
    is_active: str = Form(""),
    must_change_password: str = Form(""),
    db: Session = Depends(get_db),
):
    old = db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id}).mappings().first()

    db.execute(text("""
      UPDATE users
      SET advisor_id = :advisor_id,
          name = :name,
          email = :email,
          phone = :phone,
          role = :role,
          is_active = :is_active,
          must_change_password = :must_change_password
      WHERE id = :id
    """), {
        "id": user_id,
        "advisor_id": advisor_id,
        "name": name,
        "email": email.lower().strip(),
        "phone": phone,
        "role": role,
        "is_active": bool(is_active),
        "must_change_password": bool(must_change_password),
    })
    db.commit()

    safe_audit(db, "admin@astorie.local", "UPDATE", "advisor", str(user_id), dict(old or {}), {
        "advisor_id": advisor_id, "name": name, "email": email, "role": role,
        "is_active": bool(is_active), "must_change_password": bool(must_change_password)
    }, "Úprava poradce / uživatele")

    return RedirectResponse("/admin/advisors", status_code=303)


@router.post("/admin/advisors/{user_id}/toggle")
def advisor_toggle(user_id: int, db: Session = Depends(get_db)):
    old = db.execute(text("SELECT id, is_active, email, advisor_id FROM users WHERE id = :id"), {"id": user_id}).mappings().first()
    if old:
        new_active = not bool(old["is_active"])
        db.execute(text("UPDATE users SET is_active = :is_active WHERE id = :id"), {"id": user_id, "is_active": new_active})
        db.commit()
        safe_audit(db, "admin@astorie.local", "TOGGLE", "advisor", str(user_id), dict(old), {"is_active": new_active}, "Zapnutí/vypnutí poradce")
    return RedirectResponse("/admin/advisors", status_code=303)


@router.post("/admin/advisors/{user_id}/reset-password")
def advisor_reset_password(
    user_id: int,
    password: str = Form("1234"),
    db: Session = Depends(get_db),
):
    try:
        password_hash = hash_password(password)
    except Exception:
        password_hash = password

    db.execute(text("""
      UPDATE users
      SET password_hash = :password_hash,
          must_change_password = TRUE
      WHERE id = :id
    """), {"id": user_id, "password_hash": password_hash})
    db.commit()

    safe_audit(db, "admin@astorie.local", "UPDATE", "advisor", str(user_id), {}, {"password_reset": True}, "Reset hesla poradce")
    return RedirectResponse("/admin/advisors", status_code=303)




def ensure_specialists_table_(db: Session):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS specialists (
            id SERIAL PRIMARY KEY,
            advisor_id TEXT NOT NULL DEFAULT '',
            specialist_name TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            section_code TEXT NOT NULL DEFAULT '',
            subsection_code TEXT NOT NULL DEFAULT '',
            role_description TEXT NOT NULL DEFAULT '',
            region TEXT NOT NULL DEFAULT '',
            if_share TEXT NOT NULL DEFAULT '',
            ps_share TEXT NOT NULL DEFAULT '',
            available BOOLEAN NOT NULL DEFAULT TRUE,
            unavailable_reason TEXT NOT NULL DEFAULT '',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            note TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """))
    db.commit()


@router.get("/admin/specialists", response_class=HTMLResponse)
def specialists_page(
    request: Request,
    q: str = "",
    section: str = "",
    available: str = "",
    db: Session = Depends(get_db),
):
    ensure_specialists_table_(db)
    sql = "SELECT * FROM specialists WHERE 1=1"
    params = {}

    if q:
        sql += """
          AND (
            lower(specialist_name) LIKE :q OR
            lower(email) LIKE :q OR
            lower(phone) LIKE :q OR
            lower(advisor_id) LIKE :q OR
            lower(region) LIKE :q OR
            lower(role_description) LIKE :q
          )
        """
        params["q"] = f"%{q.lower()}%"

    if section:
        sql += " AND section_code = :section"
        params["section"] = section

    if available == "1":
        sql += " AND available = TRUE AND is_active = TRUE"
    elif available == "0":
        sql += " AND (available = FALSE OR is_active = FALSE)"

    sql += " ORDER BY specialist_name, section_code, subsection_code LIMIT 1000"
    rows = db.execute(text(sql), params).mappings().all()

    ensure_taxonomy_tables_(db)
    sections = db.execute(text("""
        SELECT section_code AS code, section_name AS name
        FROM hub_sections
        WHERE is_active = TRUE
        ORDER BY sort_order, section_name
    """)).mappings().all()
    subsections = db.execute(text("""
        SELECT subsection_code AS code, subsection_name AS name, section_code
        FROM hub_subsections
        WHERE is_active = TRUE
        ORDER BY sort_order, subsection_name
    """)).mappings().all()

    return render(request, "specialists.html", {
        "active": "specialists",
        "specialists": rows,
        "sections": sections,
        "subsections": subsections,
        "q": q,
        "section": section,
        "available_filter": available,
    })


@router.post("/admin/specialists/create")
def specialist_create(
    advisor_id: str = Form(""),
    specialist_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    section_code: str = Form(""),
    subsection_code: str = Form(""),
    role_description: str = Form(""),
    region: str = Form(""),
    if_share: str = Form(""),
    ps_share: str = Form(""),
    available: str = Form(""),
    is_active: str = Form(""),
    unavailable_reason: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_specialists_table_(db)
    db.execute(text("""
        INSERT INTO specialists
        (advisor_id, specialist_name, email, phone, section_code, subsection_code, role_description, region,
         if_share, ps_share, available, unavailable_reason, is_active, note)
        VALUES
        (:advisor_id, :specialist_name, :email, :phone, :section_code, :subsection_code, :role_description, :region,
         :if_share, :ps_share, :available, :unavailable_reason, :is_active, :note)
    """), {
        "advisor_id": advisor_id,
        "specialist_name": specialist_name,
        "email": email.lower().strip(),
        "phone": phone,
        "section_code": section_code.upper().strip(),
        "subsection_code": subsection_code.upper().strip(),
        "role_description": role_description,
        "region": region,
        "if_share": if_share,
        "ps_share": ps_share,
        "available": bool(available),
        "unavailable_reason": unavailable_reason,
        "is_active": bool(is_active),
        "note": note,
    })
    db.commit()
    try:
        safe_audit(db, "admin@astorie.local", "CREATE", "specialist", specialist_name, {}, {
            "advisor_id": advisor_id, "name": specialist_name, "email": email,
            "section": section_code, "subsection": subsection_code
        }, "Založení specialisty")
    except Exception:
        pass
    return RedirectResponse("/admin/specialists", status_code=303)


@router.post("/admin/specialists/{item_id}/update")
def specialist_update(
    item_id: int,
    advisor_id: str = Form(""),
    specialist_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    section_code: str = Form(""),
    subsection_code: str = Form(""),
    role_description: str = Form(""),
    region: str = Form(""),
    if_share: str = Form(""),
    ps_share: str = Form(""),
    available: str = Form(""),
    is_active: str = Form(""),
    unavailable_reason: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_specialists_table_(db)
    old = db.execute(text("SELECT * FROM specialists WHERE id = :id"), {"id": item_id}).mappings().first()
    db.execute(text("""
        UPDATE specialists SET
          advisor_id = :advisor_id,
          specialist_name = :specialist_name,
          email = :email,
          phone = :phone,
          section_code = :section_code,
          subsection_code = :subsection_code,
          role_description = :role_description,
          region = :region,
          if_share = :if_share,
          ps_share = :ps_share,
          available = :available,
          unavailable_reason = :unavailable_reason,
          is_active = :is_active,
          note = :note
        WHERE id = :id
    """), {
        "id": item_id,
        "advisor_id": advisor_id,
        "specialist_name": specialist_name,
        "email": email.lower().strip(),
        "phone": phone,
        "section_code": section_code.upper().strip(),
        "subsection_code": subsection_code.upper().strip(),
        "role_description": role_description,
        "region": region,
        "if_share": if_share,
        "ps_share": ps_share,
        "available": bool(available),
        "unavailable_reason": unavailable_reason,
        "is_active": bool(is_active),
        "note": note,
    })
    db.commit()
    try:
        safe_audit(db, "admin@astorie.local", "UPDATE", "specialist", str(item_id), dict(old or {}), {
            "advisor_id": advisor_id, "name": specialist_name, "email": email,
            "section": section_code, "subsection": subsection_code,
            "available": bool(available), "is_active": bool(is_active)
        }, "Úprava specialisty")
    except Exception:
        pass
    return RedirectResponse("/admin/specialists", status_code=303)


@router.post("/admin/specialists/{item_id}/toggle")
def specialist_toggle(item_id: int, db: Session = Depends(get_db)):
    ensure_specialists_table_(db)
    old = db.execute(text("SELECT * FROM specialists WHERE id = :id"), {"id": item_id}).mappings().first()
    if old:
        new_active = not bool(old["is_active"])
        db.execute(text("UPDATE specialists SET is_active = :is_active WHERE id = :id"), {"id": item_id, "is_active": new_active})
        db.commit()
        try:
            safe_audit(db, "admin@astorie.local", "TOGGLE", "specialist", str(item_id), dict(old), {"is_active": new_active}, "Zapnutí/vypnutí specialisty")
        except Exception:
            pass
    return RedirectResponse("/admin/specialists", status_code=303)


@router.get("/api/specialists/search")
def api_specialists_search(section: str = "", subsection: str = "", q: str = "", db: Session = Depends(get_db)):
    ensure_specialists_table_(db)
    sql = "SELECT * FROM specialists WHERE is_active = TRUE AND available = TRUE"
    params = {}

    if section:
        sql += " AND section_code = :section"
        params["section"] = section.upper()

    if subsection:
        sql += " AND (subsection_code = :subsection OR COALESCE(subsection_code, '') = '')"
        params["subsection"] = subsection.upper()

    if q:
        sql += """
          AND (
            lower(specialist_name) LIKE :q OR
            lower(email) LIKE :q OR
            lower(region) LIKE :q OR
            lower(role_description) LIKE :q
          )
        """
        params["q"] = f"%{q.lower()}%"

    sql += " ORDER BY specialist_name LIMIT 50"
    rows = db.execute(text(sql), params).mappings().all()

    return {
        "ok": True,
        "items": [
            {
                "id": r["id"],
                "advisor_id": r["advisor_id"],
                "name": r["specialist_name"],
                "email": r["email"],
                "phone": r["phone"],
                "section_code": r["section_code"],
                "subsection_code": r["subsection_code"],
                "role_description": r["role_description"],
                "region": r["region"],
                "if_share": r["if_share"],
                "ps_share": r["ps_share"],
            }
            for r in rows
        ],
    }





def ensure_taxonomy_tables_(db: Session):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS hub_sections (
            id SERIAL PRIMARY KEY,
            section_code TEXT UNIQUE NOT NULL,
            section_name TEXT NOT NULL DEFAULT '',
            icon TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 100,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            note TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS hub_subsections (
            id SERIAL PRIMARY KEY,
            subsection_code TEXT UNIQUE NOT NULL,
            section_code TEXT NOT NULL DEFAULT '',
            subsection_name TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 100,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            note TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """))
    db.commit()


@router.get("/admin/subsections")
def admin_subsections_compat():
    return RedirectResponse("/admin/sections", status_code=303)


@router.get("/admin/sections", response_class=HTMLResponse)
def sections_page(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
):
    ensure_visible_hub_sections_(db)

    sql = "SELECT * FROM hub_sections WHERE 1=1"
    params = {}
    if q:
        sql += " AND (lower(section_code) LIKE :q OR lower(section_name) LIKE :q OR lower(note) LIKE :q)"
        params["q"] = f"%{q.lower()}%"
    sql += " ORDER BY sort_order, section_name"

    sections = db.execute(text(sql), params).mappings().all()
    subsections = db.execute(text("""
        SELECT s.*, h.section_name
        FROM hub_subsections s
        LEFT JOIN hub_sections h ON h.section_code = s.section_code
        ORDER BY h.sort_order, s.sort_order, s.subsection_name
    """)).mappings().all()

    return render(request, "sections.html", {
        "active": "sections",
        "sections": sections,
        "subsections": subsections,
        "q": q,
    })


@router.post("/admin/sections/create")
def section_create(
    section_code: str = Form(...),
    section_name: str = Form(...),
    icon: str = Form(""),
    image_url: str = Form(""),
    sort_order: int = Form(100),
    is_active: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_taxonomy_tables_(db)
    db.execute(text("""
        INSERT INTO hub_sections
          (section_code, section_name, icon, image_url, sort_order, is_active, note)
        VALUES
          (:section_code, :section_name, :icon, :image_url, :sort_order, :is_active, :note)
        ON CONFLICT (section_code) DO UPDATE SET
          section_name = EXCLUDED.section_name,
          icon = EXCLUDED.icon,
          image_url = EXCLUDED.image_url,
          sort_order = EXCLUDED.sort_order,
          is_active = EXCLUDED.is_active,
          note = EXCLUDED.note
    """), {
        "section_code": section_code.upper().strip(),
        "section_name": section_name,
        "icon": icon,
        "image_url": image_url,
        "sort_order": sort_order,
        "is_active": bool(is_active),
        "note": note,
    })
    db.commit()
    try:
        safe_audit(db, "admin@astorie.local", "UPSERT", "section", section_code.upper().strip(), {}, {
            "section_code": section_code.upper().strip(), "section_name": section_name
        }, "Založení/úprava sekce")
    except Exception:
        pass
    return RedirectResponse("/admin/sections", status_code=303)


@router.post("/admin/subsections/create")
def subsection_create(
    section_code: str = Form(...),
    subsection_code: str = Form(...),
    subsection_name: str = Form(...),
    sort_order: int = Form(100),
    is_active: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_taxonomy_tables_(db)
    db.execute(text("""
        INSERT INTO hub_subsections
          (section_code, subsection_code, subsection_name, sort_order, is_active, note)
        VALUES
          (:section_code, :subsection_code, :subsection_name, :sort_order, :is_active, :note)
        ON CONFLICT (subsection_code) DO UPDATE SET
          section_code = EXCLUDED.section_code,
          subsection_name = EXCLUDED.subsection_name,
          sort_order = EXCLUDED.sort_order,
          is_active = EXCLUDED.is_active,
          note = EXCLUDED.note
    """), {
        "section_code": section_code.upper().strip(),
        "subsection_code": subsection_code.upper().strip(),
        "subsection_name": subsection_name,
        "sort_order": sort_order,
        "is_active": bool(is_active),
        "note": note,
    })
    db.commit()
    try:
        safe_audit(db, "admin@astorie.local", "UPSERT", "subsection", subsection_code.upper().strip(), {}, {
            "section_code": section_code.upper().strip(),
            "subsection_code": subsection_code.upper().strip(),
            "subsection_name": subsection_name
        }, "Založení/úprava podsekce")
    except Exception:
        pass
    return RedirectResponse("/admin/sections", status_code=303)


@router.get("/api/taxonomy/sections")
def api_taxonomy_sections(db: Session = Depends(get_db)):
    ensure_taxonomy_tables_(db)
    rows = db.execute(text("""
        SELECT section_code, section_name, icon, image_url
        FROM hub_sections
        WHERE is_active = TRUE
        ORDER BY sort_order, section_name
    """)).mappings().all()
    return {"ok": True, "items": [dict(r) for r in rows]}


@router.get("/api/taxonomy/subsections")
def api_taxonomy_subsections(section_code: str = "", db: Session = Depends(get_db)):
    ensure_taxonomy_tables_(db)
    sql = """
        SELECT subsection_code, subsection_name, section_code
        FROM hub_subsections
        WHERE is_active = TRUE
    """
    params = {}
    if section_code:
        sql += " AND section_code = :section_code"
        params["section_code"] = section_code.upper()
    sql += " ORDER BY sort_order, subsection_name"
    rows = db.execute(text(sql), params).mappings().all()
    return {"ok": True, "items": [dict(r) for r in rows]}


@router.get("/admin/my-specialist-profile-old", response_class=HTMLResponse)
def my_specialist_profile(request: Request, db: Session = Depends(get_db)):
    ensure_specialists_table_(db)
    # Dočasně používáme admin e-mail; po ostrém loginu se nahradí session uživatelem.
    email = "nekudova@astorieas.cz"
    rows = db.execute(text("""
        SELECT * FROM specialists
        WHERE lower(email) = :email
        ORDER BY specialist_name, section_code, subsection_code
    """), {"email": email}).mappings().all()

    return render(request, "my_specialist_profile.html", {
        "active": "my_specialist_profile",
        "rows": rows,
        "email": email,
    })


@router.post("/admin/my-specialist-profile-old/{item_id}/availability")
def my_specialist_availability(
    item_id: int,
    available: str = Form(""),
    unavailable_reason: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_specialists_table_(db)
    old = db.execute(text("SELECT * FROM specialists WHERE id = :id"), {"id": item_id}).mappings().first()
    db.execute(text("""
        UPDATE specialists
        SET available = :available,
            unavailable_reason = :unavailable_reason
        WHERE id = :id
    """), {
        "id": item_id,
        "available": bool(available),
        "unavailable_reason": unavailable_reason,
    })
    db.commit()
    try:
        safe_audit(db, "admin@astorie.local", "UPDATE", "specialist_availability", str(item_id), dict(old or {}), {
            "available": bool(available), "unavailable_reason": unavailable_reason
        }, "Specialista upravil vlastní dostupnost")
    except Exception:
        pass
    return RedirectResponse("/admin/my-specialist-profile-old", status_code=303)


@router.get("/api/routing/specialists")
def api_routing_specialists(section_code: str = "", subsection_code: str = "", db: Session = Depends(get_db)):
    ensure_specialists_table_(db)
    ensure_taxonomy_tables_(db)

    sql = """
        SELECT *
        FROM specialists
        WHERE is_active = TRUE
          AND available = TRUE
    """
    params = {}

    if section_code:
        sql += " AND section_code = :section_code"
        params["section_code"] = section_code.upper()

    if subsection_code:
        sql += " AND (subsection_code = :subsection_code OR COALESCE(subsection_code, '') = '')"
        params["subsection_code"] = subsection_code.upper()

    sql += " ORDER BY specialist_name LIMIT 50"
    rows = db.execute(text(sql), params).mappings().all()

    return {
        "ok": True,
        "routing": {
            "section_code": section_code.upper() if section_code else "",
            "subsection_code": subsection_code.upper() if subsection_code else "",
            "count": len(rows),
        },
        "specialists": [
            {
                "id": r["id"],
                "name": r["specialist_name"],
                "email": r["email"],
                "phone": r["phone"],
                "region": r["region"],
                "section_code": r["section_code"],
                "subsection_code": r["subsection_code"],
                "if_share": r["if_share"],
                "ps_share": r["ps_share"],
            }
            for r in rows
        ],
    }




# -------------------------------------------------------------------
# v0.9.8 Specialist Profile & Sections Fix
# -------------------------------------------------------------------

def seed_default_hub_taxonomy_(db: Session):
    ensure_taxonomy_tables_(db)

    defaults_sections = [
        ("FLOTILY", "Flotily", "🚗", 10),
        ("MAJETEK", "Majetek", "🏡", 20),
        ("ZIVOT", "Život", "❤️", 30),
        ("PODNIKATELE", "Podnikatelé", "🏢", 40),
        ("PENZE", "Penze", "💼", 50),
        ("UVERY", "Úvěry", "🏦", 60),
        ("OBNOVA", "Obnova", "♻️", 70),
        ("INVESTICE", "Investice", "📈", 80),
        ("ZLATO", "Zlato", "💰", 90),
        ("ZVIRE", "Zvíře", "🐕", 100),
    ]

    defaults_subsections = [
        ("FLOTILY", "FLOTILY_FIREMNI", "Firemní flotily", 10),
        ("FLOTILY", "AUTODOPRAVCI", "Autodopravci", 20),
        ("MAJETEK", "DOMACNOSTI", "Domácnosti", 10),
        ("MAJETEK", "NEMOVITOSTI", "Nemovitosti", 20),
        ("ZIVOT", "ZIVOTNI_POJISTENI", "Životní pojištění", 10),
        ("PODNIKATELE", "PODNIKATELSKA_RIZIKA", "Podnikatelská rizika", 10),
        ("PENZE", "DPS", "Doplňkové penzijní spoření", 10),
        ("UVERY", "HYPOTEKY", "Hypotéky", 10),
        ("OBNOVA", "RETENCE", "Obnova / retence", 10),
        ("INVESTICE", "INVESTICE_OBECNE", "Investice", 10),
        ("ZLATO", "INVESTICNI_ZLATO", "Investiční zlato", 10),
        ("ZVIRE", "POJISTENI_ZVIRAT", "Pojištění zvířat", 10),
    ]

    for code, name, icon, order in defaults_sections:
        db.execute(text("""
            INSERT INTO hub_sections (section_code, section_name, icon, sort_order, is_active)
            VALUES (:code, :name, :icon, :sort_order, TRUE)
            ON CONFLICT (section_code) DO NOTHING
        """), {"code": code, "name": name, "icon": icon, "sort_order": order})

    for section_code, sub_code, sub_name, order in defaults_subsections:
        db.execute(text("""
            INSERT INTO hub_subsections (section_code, subsection_code, subsection_name, sort_order, is_active)
            VALUES (:section_code, :sub_code, :sub_name, :sort_order, TRUE)
            ON CONFLICT (subsection_code) DO NOTHING
        """), {
            "section_code": section_code,
            "sub_code": sub_code,
            "sub_name": sub_name,
            "sort_order": order,
        })

    db.commit()


@router.post("/admin/sections/seed-defaults")
def sections_seed_defaults(db: Session = Depends(get_db)):
    seed_default_hub_taxonomy_(db)
    try:
        safe_audit(db, "admin@astorie.local", "UPSERT", "taxonomy", "defaults", {}, {"seed": "default_hub_taxonomy"}, "Doplnění výchozích sekcí a podsekcí")
    except Exception:
        pass
    return RedirectResponse("/admin/sections", status_code=303)


@router.get("/admin/my-specialist-profile", response_class=HTMLResponse)
def my_specialist_profile_v071(request: Request, db: Session = Depends(get_db)):
    ensure_specialists_table_(db)
    seed_default_hub_taxonomy_(db)

    current_user = {
        "advisor_id": "501",
        "name": "Nekudová Dagmar",
        "email": "nekudova@astorieas.cz",
        "phone": "737 233 888",
    }

    rows = db.execute(text("""
        SELECT s.*,
               hs.section_name,
               hss.subsection_name
        FROM specialists s
        LEFT JOIN hub_sections hs ON hs.section_code = s.section_code
        LEFT JOIN hub_subsections hss ON hss.subsection_code = s.subsection_code
        WHERE lower(s.email) = :email
        ORDER BY s.specialist_name, hs.sort_order, hss.sort_order, s.section_code, s.subsection_code
    """), {"email": current_user["email"].lower()}).mappings().all()

    sections = db.execute(text("""
        SELECT section_code, section_name, icon
        FROM hub_sections
        WHERE is_active = TRUE
        ORDER BY sort_order, section_name
    """)).mappings().all()

    subsections = db.execute(text("""
        SELECT subsection_code, subsection_name, section_code
        FROM hub_subsections
        WHERE is_active = TRUE
        ORDER BY section_code, sort_order, subsection_name
    """)).mappings().all()

    return render(request, "my_specialist_profile.html", {
        "active": "my_specialist_profile",
        "rows": rows,
        "sections": sections,
        "subsections": subsections,
        "current_user": current_user,
        "email": current_user["email"],
    })


@router.post("/admin/my-specialist-profile/add-specialization")
def my_specialist_add_specialization_v071(
    section_code: str = Form(...),
    subsection_code: str = Form(""),
    role_description: str = Form(""),
    region: str = Form("ČR"),
    if_share: str = Form(""),
    ps_share: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_specialists_table_(db)
    seed_default_hub_taxonomy_(db)

    current_user = {
        "advisor_id": "501",
        "name": "Nekudová Dagmar",
        "email": "nekudova@astorieas.cz",
        "phone": "737 233 888",
    }

    db.execute(text("""
        INSERT INTO specialists
        (advisor_id, specialist_name, email, phone, section_code, subsection_code,
         role_description, region, if_share, ps_share, available, is_active, note)
        VALUES
        (:advisor_id, :name, :email, :phone, :section_code, :subsection_code,
         :role_description, :region, :if_share, :ps_share, TRUE, TRUE, 'Založeno z profilu specialisty')
    """), {
        "advisor_id": current_user["advisor_id"],
        "name": current_user["name"],
        "email": current_user["email"].lower(),
        "phone": current_user["phone"],
        "section_code": section_code.upper().strip(),
        "subsection_code": subsection_code.upper().strip(),
        "role_description": role_description,
        "region": region,
        "if_share": if_share,
        "ps_share": ps_share,
    })
    db.commit()

    try:
        safe_audit(db, current_user["email"], "CREATE", "specialist_profile", current_user["email"], {}, {
            "section_code": section_code,
            "subsection_code": subsection_code,
            "role_description": role_description,
        }, "Specialista si přidal odbornost do profilu")
    except Exception:
        pass

    return RedirectResponse("/admin/my-specialist-profile", status_code=303)


@router.post("/admin/my-specialist-profile/{item_id}/availability")
def my_specialist_availability_v071(
    item_id: int,
    available: str = Form(""),
    unavailable_reason: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_specialists_table_(db)
    old = db.execute(text("SELECT * FROM specialists WHERE id = :id"), {"id": item_id}).mappings().first()
    db.execute(text("""
        UPDATE specialists
        SET available = :available,
            unavailable_reason = :unavailable_reason
        WHERE id = :id
    """), {
        "id": item_id,
        "available": bool(available),
        "unavailable_reason": unavailable_reason,
    })
    db.commit()
    try:
        safe_audit(db, "admin@astorie.local", "UPDATE", "specialist_availability", str(item_id), dict(old or {}), {
            "available": bool(available), "unavailable_reason": unavailable_reason
        }, "Specialista upravil vlastní dostupnost")
    except Exception:
        pass
    return RedirectResponse("/admin/my-specialist-profile", status_code=303)





# -------------------------------------------------------------------
# v0.9.8 Visible Sections Fix
# -------------------------------------------------------------------

def ensure_visible_hub_sections_(db: Session):
    """
    Zajistí, že poradenská část HUBu vždy uvidí základní sekce.
    Nedestruktivní: nic nemaže a existující sekce nepřepisuje.
    """
    try:
        seed_default_hub_taxonomy_(db)
    except NameError:
        ensure_taxonomy_tables_(db)
        defaults_sections = [
            ("FLOTILY", "Flotily", "🚗", 10),
            ("MAJETEK", "Majetek", "🏡", 20),
            ("ZIVOT", "Život", "❤️", 30),
            ("PODNIKATELE", "Podnikatelé", "🏢", 40),
            ("PENZE", "Penze", "💼", 50),
            ("UVERY", "Úvěry", "🏦", 60),
            ("OBNOVA", "Obnova", "♻️", 70),
            ("INVESTICE", "Investice", "📈", 80),
            ("ZLATO", "Zlato", "💰", 90),
            ("ZVIRE", "Zvíře", "🐕", 100),
        ]
        defaults_subsections = [
            ("FLOTILY", "FLOTILY_FIREMNI", "Firemní flotily", 10),
            ("FLOTILY", "AUTODOPRAVCI", "Autodopravci", 20),
            ("MAJETEK", "DOMACNOSTI", "Domácnosti", 10),
            ("MAJETEK", "NEMOVITOSTI", "Nemovitosti", 20),
            ("ZIVOT", "ZIVOTNI_POJISTENI", "Životní pojištění", 10),
            ("PODNIKATELE", "PODNIKATELSKA_RIZIKA", "Podnikatelská rizika", 10),
            ("PENZE", "DPS", "Doplňkové penzijní spoření", 10),
            ("UVERY", "HYPOTEKY", "Hypotéky", 10),
            ("OBNOVA", "RETENCE", "Obnova / retence", 10),
            ("INVESTICE", "INVESTICE_OBECNE", "Investice", 10),
            ("ZLATO", "INVESTICNI_ZLATO", "Investiční zlato", 10),
            ("ZVIRE", "POJISTENI_ZVIRAT", "Pojištění zvířat", 10),
        ]
        for code, name, icon, order in defaults_sections:
            db.execute(text("""
                INSERT INTO hub_sections (section_code, section_name, icon, sort_order, is_active)
                VALUES (:code, :name, :icon, :sort_order, TRUE)
                ON CONFLICT (section_code) DO NOTHING
            """), {"code": code, "name": name, "icon": icon, "sort_order": order})
        for section_code, sub_code, sub_name, order in defaults_subsections:
            db.execute(text("""
                INSERT INTO hub_subsections (section_code, subsection_code, subsection_name, sort_order, is_active)
                VALUES (:section_code, :sub_code, :sub_name, :sort_order, TRUE)
                ON CONFLICT (subsection_code) DO NOTHING
            """), {"section_code": section_code, "sub_code": sub_code, "sub_name": sub_name, "sort_order": order})
        db.commit()


@router.get("/api/taxonomy/visible-sections")
def api_visible_sections_v072(db: Session = Depends(get_db)):
    ensure_visible_hub_sections_(db)
    sections = db.execute(text("""
        SELECT section_code, section_name, icon, image_url
        FROM hub_sections
        WHERE is_active = TRUE
        ORDER BY sort_order, section_name
    """)).mappings().all()
    subsections = db.execute(text("""
        SELECT subsection_code, subsection_name, section_code
        FROM hub_subsections
        WHERE is_active = TRUE
        ORDER BY section_code, sort_order, subsection_name
    """)).mappings().all()
    return {
        "ok": True,
        "version": "0.9.8-import-timestamps-fix",
        "sections": [dict(s) for s in sections],
        "subsections": [dict(s) for s in subsections],
    }


@router.post("/admin/sections/force-visible-defaults")
def sections_force_visible_defaults_v072(db: Session = Depends(get_db)):
    ensure_visible_hub_sections_(db)
    return RedirectResponse("/admin/sections", status_code=303)







def ensure_user_hub_tables_v082_(db: Session):
    """
    v0.9.8 – bezpečné tabulky pro TIPy.
    Nedestruktivní: tabulku vytvoří nebo doplní chybějící sloupce.
    """
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS tips (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            adviser_original_id TEXT NOT NULL DEFAULT '',
            adviser_name TEXT NOT NULL DEFAULT '',
            adviser_email TEXT NOT NULL DEFAULT '',
            specialist_name TEXT NOT NULL DEFAULT '',
            specialist_email TEXT NOT NULL DEFAULT '',
            client_name TEXT NOT NULL DEFAULT '',
            client_phone TEXT NOT NULL DEFAULT '',
            client_identifier TEXT NOT NULL DEFAULT '',
            potential_amount NUMERIC(14,2),
            adviser_note TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Nový',
            policy_no TEXT NOT NULL DEFAULT '',
            final_volume NUMERIC(14,2),
            specialist_feedback TEXT NOT NULL DEFAULT ''
        )
    """))

    # Bezpečné doplnění sloupců pro případy, kdy už tabulka existuje ze starší verze.
    alters = [
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS adviser_original_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS adviser_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS adviser_email TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS specialist_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS specialist_email TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS client_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS client_phone TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS client_identifier TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS potential_amount NUMERIC(14,2)",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS adviser_note TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'Nový'",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS policy_no TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS final_volume NUMERIC(14,2)",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS specialist_feedback TEXT NOT NULL DEFAULT ''",
    ]
    for stmt in alters:
        db.execute(text(stmt))

    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tips_adviser ON tips (adviser_original_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tips_status ON tips (status)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tips_created ON tips (created_at DESC)"))
    db.commit()


@router.get("/api/tips/status")
def api_tips_status_v082(db: Session = Depends(get_db)):
    try:
        ensure_user_hub_tables_v082_(db)
        count = db.execute(text("SELECT COUNT(*) FROM tips")).scalar()
        latest = db.execute(text("SELECT created_at, client_name, status FROM tips ORDER BY created_at DESC LIMIT 5")).mappings().all()
        return {
            "ok": True,
            "version": "0.9.8-import-timestamps-fix",
            "count": count,
            "latest": [dict(r) for r in latest],
        }
    except Exception as e:
        return {"ok": False, "version": "0.9.8-import-timestamps-fix", "error": str(e)}




# -------------------------------------------------------------------
# v0.9.8 Adviser HUB routes fix
# -------------------------------------------------------------------

def hub_user_context_v083_():
    return {
        "advisor_id": "501",
        "name": "Nekudová Dagmar",
        "email": "nekudova@astorieas.cz",
        "phone": "737 233 888",
        "role": "IF",
    }


def hub_render_v083_(request: Request, template_name: str, context: dict):
    base = {
        "request": request,
        "app_name": "HUB ASTORIE",
        "version": "0.9.8-import-timestamps-fix",
        "user": hub_user_context_v083_(),
    }
    base.update(context)
    return request.app.state.templates.TemplateResponse(template_name, base)


def ensure_hub_taxonomy_v083_(db: Session):
    try:
        ensure_visible_hub_sections_(db)
    except Exception:
        try:
            seed_default_hub_taxonomy_(db)
        except Exception:
            pass


@router.get("/hub")
def hub_home_v083():
    return RedirectResponse("/hub/new-tip", status_code=302)


@router.get("/hub/new-tip-old-v085", response_class=HTMLResponse)
def hub_new_tip_v083(request: Request, db: Session = Depends(get_db)):
    ensure_user_hub_tables_v082_(db)
    ensure_hub_taxonomy_v083_(db)

    sections = db.execute(text("""
        SELECT section_code, section_name, icon
        FROM hub_sections
        WHERE is_active = TRUE
        ORDER BY sort_order, section_name
    """)).mappings().all()

    subsections = db.execute(text("""
        SELECT subsection_code, subsection_name, section_code
        FROM hub_subsections
        WHERE is_active = TRUE
        ORDER BY section_code, sort_order, subsection_name
    """)).mappings().all()

    try:
        ensure_specialists_table_(db)
        specialists = db.execute(text("""
            SELECT *
            FROM specialists
            WHERE is_active = TRUE
              AND available = TRUE
            ORDER BY specialist_name, section_code, subsection_code
            LIMIT 200
        """)).mappings().all()
    except Exception:
        specialists = []

    return hub_render_v083_(request, "hub_new_tip.html", {
        "active": "new_tip",
        "sections": sections,
        "subsections": subsections,
        "specialists": specialists,
    })


@router.post("/hub/tips/create-old-v085")
def hub_create_tip_v083(
    section_code: str = Form(""),
    subsection_code: str = Form(""),
    specialist_email: str = Form(""),
    specialist_name: str = Form(""),
    client_name: str = Form(...),
    client_phone: str = Form(""),
    client_identifier: str = Form(""),
    potential_amount: str = Form(""),
    adviser_note: str = Form(""),
    policy_no: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_user_hub_tables_v082_(db)
    user = hub_user_context_v083_()

    amount = None
    if potential_amount:
        try:
            amount = Decimal(str(potential_amount).replace(" ", "").replace("Kč", "").replace(",", "."))
        except Exception:
            amount = None

    tip_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO tips
          (id, adviser_original_id, adviser_name, adviser_email, specialist_name, specialist_email,
           client_name, client_phone, client_identifier, potential_amount, adviser_note, status, policy_no)
        VALUES
          (:id, :advisor_id, :advisor_name, :advisor_email, :specialist_name, :specialist_email,
           :client_name, :client_phone, :client_identifier, :potential_amount, :adviser_note, 'Nový', :policy_no)
    """), {
        "id": tip_id,
        "advisor_id": user["advisor_id"],
        "advisor_name": user["name"],
        "advisor_email": user["email"],
        "specialist_name": specialist_name,
        "specialist_email": specialist_email,
        "client_name": client_name,
        "client_phone": client_phone,
        "client_identifier": client_identifier,
        "potential_amount": amount,
        "adviser_note": f"[Sekce: {section_code}; Podsekce: {subsection_code}]\n{adviser_note}",
        "policy_no": policy_no,
    })
    db.commit()
    return RedirectResponse("/hub/my-tips?created=1", status_code=303)


@router.get("/hub/my-tips-old-v085", response_class=HTMLResponse)
def hub_my_tips_v083(
    request: Request,
    q: str = "",
    status: str = "",
    created: str = "",
    db: Session = Depends(get_db),
):
    ensure_user_hub_tables_v082_(db)
    user = hub_user_context_v083_()

    sql = """
        SELECT *
        FROM tips
        WHERE COALESCE(adviser_original_id, '') = :advisor_id
    """
    params = {"advisor_id": user["advisor_id"]}

    if q:
        sql += """
          AND (
            lower(COALESCE(client_name, '')) LIKE :q OR
            lower(COALESCE(client_identifier, '')) LIKE :q OR
            lower(COALESCE(specialist_name, '')) LIKE :q OR
            lower(COALESCE(policy_no, '')) LIKE :q OR
            lower(COALESCE(adviser_note, '')) LIKE :q
          )
        """
        params["q"] = f"%{q.lower()}%"

    if status:
        sql += " AND status = :status"
        params["status"] = status

    sql += " ORDER BY created_at DESC LIMIT 300"
    rows = db.execute(text(sql), params).mappings().all()

    stats = db.execute(text("""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status ILIKE 'sjednáno') AS won,
          COUNT(*) FILTER (WHERE status ILIKE 'storno') AS lost,
          COUNT(*) FILTER (WHERE status NOT ILIKE 'sjednáno' AND status NOT ILIKE 'storno') AS open
        FROM tips
        WHERE COALESCE(adviser_original_id, '') = :advisor_id
    """), {"advisor_id": user["advisor_id"]}).mappings().first()

    return hub_render_v083_(request, "hub_my_tips.html", {
        "active": "my_tips",
        "rows": rows,
        "stats": stats,
        "q": q,
        "status": status,
        "created": created,
    })


@router.get("/hub/calculators-old-v083", response_class=HTMLResponse)
def hub_calculators_v083(request: Request, db: Session = Depends(get_db)):
    return hub_render_v083_(request, "hub_calculators.html", {"active": "calculators", "links": [], "rates": [], "q": ""})


@router.get("/hub/partners-old-v083", response_class=HTMLResponse)
def hub_partners_v083(request: Request, q: str = "", selected: str = "", tab: str = "contacts", db: Session = Depends(get_db)):
    return hub_render_v083_(request, "hub_partners.html", {
        "active": "partners", "partners": [], "partner": None,
        "contacts": [], "links": [], "products": [], "q": q, "selected": selected, "tab": tab
    })


@router.get("/hub/contacts-old-v083", response_class=HTMLResponse)
def hub_contacts_v083(request: Request, q: str = "", db: Session = Depends(get_db)):
    return hub_render_v083_(request, "hub_contacts.html", {"active": "contacts", "rows": [], "q": q})


@router.get("/hub/forms-old-v083", response_class=HTMLResponse)
def hub_forms_v083(request: Request, db: Session = Depends(get_db)):
    return hub_render_v083_(request, "hub_forms.html", {"active": "forms", "partners": []})


@router.get("/hub/stats-old-v083", response_class=HTMLResponse)
def hub_stats_v083(request: Request, db: Session = Depends(get_db)):
    ensure_user_hub_tables_v082_(db)
    user = hub_user_context_v083_()
    stats = db.execute(text("""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status ILIKE 'sjednáno') AS won,
          COUNT(*) FILTER (WHERE status ILIKE 'storno') AS lost,
          COUNT(*) FILTER (WHERE status NOT ILIKE 'sjednáno' AND status NOT ILIKE 'storno') AS open,
          COALESCE(SUM(final_volume), 0) AS final_volume,
          COALESCE(SUM(potential_amount), 0) AS potential_amount
        FROM tips
        WHERE adviser_original_id = :advisor_id
    """), {"advisor_id": user["advisor_id"]}).mappings().first()

    return hub_render_v083_(request, "hub_stats.html", {"active": "stats", "stats": stats, "by_specialist": []})


@router.get("/hub/help-old-v083", response_class=HTMLResponse)
def hub_help_v083(request: Request):
    return hub_render_v083_(request, "hub_help.html", {"active": "help"})





# -------------------------------------------------------------------
# v0.9.8 HUB Data Bridge – propojení uživatelského HUBu na admin data
# -------------------------------------------------------------------

def table_exists_v084_(db: Session, table_name: str) -> bool:
    try:
        return bool(db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = :table_name
            )
        """), {"table_name": table_name}).scalar())
    except Exception:
        return False


def column_exists_v084_(db: Session, table_name: str, column_name: str) -> bool:
    try:
        return bool(db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                  AND column_name = :column_name
            )
        """), {"table_name": table_name, "column_name": column_name}).scalar())
    except Exception:
        return False


def fetch_all_safe_v084_(db: Session, sql: str, params: dict | None = None):
    try:
        return db.execute(text(sql), params or {}).mappings().all()
    except Exception:
        return []


def fetch_one_safe_v084_(db: Session, sql: str, params: dict | None = None):
    try:
        return db.execute(text(sql), params or {}).mappings().first()
    except Exception:
        return None


@router.get("/hub/partners", response_class=HTMLResponse)
def hub_partners_v084(
    request: Request,
    q: str = "",
    selected: str = "",
    tab: str = "contacts",
    db: Session = Depends(get_db),
):
    # Partner data z admin číselníku – uživatelský HUB už neukazuje placeholder.
    partners = []
    partner = None
    contacts = []
    links = []
    products = []

    if table_exists_v084_(db, "partners"):
        where = "WHERE COALESCE(is_active, TRUE) = TRUE"
        params = {}
        if q:
            where += """
              AND (
                lower(COALESCE(partner_code, '')) LIKE :q OR
                lower(COALESCE(name, '')) LIKE :q OR
                lower(COALESCE(ico, '')) LIKE :q OR
                lower(COALESCE(data_box, '')) LIKE :q OR
                lower(COALESCE(registry_email, '')) LIKE :q OR
                lower(COALESCE(city, '')) LIKE :q
              )
            """
            params["q"] = f"%{q.lower()}%"

        partners = fetch_all_safe_v084_(db, f"""
            SELECT *
            FROM partners
            {where}
            ORDER BY name
            LIMIT 500
        """, params)

        if not selected and partners:
            selected = partners[0]["partner_code"]

        if selected:
            partner = fetch_one_safe_v084_(db, """
                SELECT *
                FROM partners
                WHERE upper(partner_code) = upper(:code)
                LIMIT 1
            """, {"code": selected})

    if selected and table_exists_v084_(db, "partner_contacts"):
        contacts = fetch_all_safe_v084_(db, """
            SELECT *
            FROM partner_contacts
            WHERE upper(partner_code) = upper(:code)
              AND COALESCE(is_active, TRUE) = TRUE
            ORDER BY COALESCE(is_vip, FALSE) DESC, COALESCE(is_top, FALSE) DESC, full_name
            LIMIT 300
        """, {"code": selected})

    if selected and table_exists_v084_(db, "partner_links"):
        links = fetch_all_safe_v084_(db, """
            SELECT *
            FROM partner_links
            WHERE upper(partner_code) = upper(:code)
              AND COALESCE(is_active, TRUE) = TRUE
            ORDER BY category, title
            LIMIT 300
        """, {"code": selected})

    if selected and table_exists_v084_(db, "partner_products"):
        products = fetch_all_safe_v084_(db, """
            SELECT *
            FROM partner_products
            WHERE upper(partner_code) = upper(:code)
              AND COALESCE(is_active, TRUE) = TRUE
            ORDER BY area, subarea, product_name
            LIMIT 300
        """, {"code": selected})

    return hub_render_v083_(request, "hub_partners.html", {
        "active": "partners",
        "partners": partners,
        "partner": partner,
        "contacts": contacts,
        "links": links,
        "products": products,
        "q": q,
        "selected": selected or "",
        "tab": tab,
    })


@router.get("/hub/contacts", response_class=HTMLResponse)
def hub_contacts_v084(request: Request, q: str = "", db: Session = Depends(get_db)):
    rows = []
    if table_exists_v084_(db, "partner_contacts"):
        params = {}
        where = "WHERE COALESCE(c.is_active, TRUE) = TRUE"
        if q:
            where += """
              AND (
                lower(COALESCE(c.full_name, '')) LIKE :q OR
                lower(COALESCE(c.email, '')) LIKE :q OR
                lower(COALESCE(c.phone, '')) LIKE :q OR
                lower(COALESCE(c.role, '')) LIKE :q OR
                lower(COALESCE(c.territory, '')) LIKE :q OR
                lower(COALESCE(p.name, '')) LIKE :q
              )
            """
            params["q"] = f"%{q.lower()}%"

        rows = fetch_all_safe_v084_(db, f"""
            SELECT c.*, p.name AS partner_name
            FROM partner_contacts c
            LEFT JOIN partners p ON p.partner_code = c.partner_code
            {where}
            ORDER BY COALESCE(c.is_vip, FALSE) DESC, p.name, c.full_name
            LIMIT 500
        """, params)

    return hub_render_v083_(request, "hub_contacts.html", {
        "active": "contacts",
        "rows": rows,
        "q": q,
    })


@router.get("/hub/calculators", response_class=HTMLResponse)
def hub_calculators_v084(request: Request, q: str = "", db: Session = Depends(get_db)):
    links = []
    rates = []

    if table_exists_v084_(db, "partner_links"):
        params = {}
        where = """
            WHERE COALESCE(l.is_active, TRUE) = TRUE
              AND (
                lower(COALESCE(l.category, '')) LIKE '%kalk%'
                OR lower(COALESCE(l.title, '')) LIKE '%kalk%'
                OR lower(COALESCE(l.note, '')) LIKE '%kalk%'
                OR lower(COALESCE(l.url, '')) LIKE '%kalk%'
              )
        """
        if q:
            where += """
              AND (
                lower(COALESCE(l.title, '')) LIKE :q OR
                lower(COALESCE(p.name, '')) LIKE :q OR
                lower(COALESCE(l.category, '')) LIKE :q OR
                lower(COALESCE(l.url, '')) LIKE :q
              )
            """
            params["q"] = f"%{q.lower()}%"

        links = fetch_all_safe_v084_(db, f"""
            SELECT l.*, p.name AS partner_name
            FROM partner_links l
            LEFT JOIN partners p ON p.partner_code = l.partner_code
            {where}
            ORDER BY COALESCE(p.name, ''), l.title
            LIMIT 300
        """, params)

    if table_exists_v084_(db, "commission_rates"):
        rates = fetch_all_safe_v084_(db, """
            SELECT *
            FROM commission_rates
            WHERE COALESCE(is_active, TRUE) = TRUE
            ORDER BY partner_name, section_code, subsection_code
            LIMIT 300
        """)

    return hub_render_v083_(request, "hub_calculators.html", {
        "active": "calculators",
        "links": links,
        "rates": rates,
        "q": q,
    })


@router.get("/hub/forms-old-v086", response_class=HTMLResponse)
def hub_forms_v084(request: Request, q: str = "", db: Session = Depends(get_db)):
    partners = []
    if table_exists_v084_(db, "partners"):
        params = {}
        where = "WHERE COALESCE(is_active, TRUE) = TRUE"
        if q:
            where += """
              AND (
                lower(COALESCE(name, '')) LIKE :q OR
                lower(COALESCE(partner_code, '')) LIKE :q OR
                lower(COALESCE(ico, '')) LIKE :q
              )
            """
            params["q"] = f"%{q.lower()}%"

        partners = fetch_all_safe_v084_(db, f"""
            SELECT partner_code, name, ico, data_box, registry_email, address_full, street, city, zip_code
            FROM partners
            {where}
            ORDER BY name
            LIMIT 500
        """, params)

    return hub_render_v083_(request, "hub_forms.html", {
        "active": "forms",
        "partners": partners,
        "q": q,
    })


@router.get("/hub/help", response_class=HTMLResponse)
def hub_help_v084(request: Request, q: str = "", db: Session = Depends(get_db)):
    # V této fázi použijeme FAQ/odkazy z partnerů jako první datový základ nápovědy.
    faqs = []
    links = []

    if table_exists_v084_(db, "partner_links"):
        params = {}
        where = "WHERE COALESCE(is_active, TRUE) = TRUE"
        if q:
            where += """
              AND (
                lower(COALESCE(title, '')) LIKE :q OR
                lower(COALESCE(note, '')) LIKE :q OR
                lower(COALESCE(category, '')) LIKE :q
              )
            """
            params["q"] = f"%{q.lower()}%"

        links = fetch_all_safe_v084_(db, f"""
            SELECT *
            FROM partner_links
            {where}
            ORDER BY category, title
            LIMIT 200
        """, params)

    return hub_render_v083_(request, "hub_help.html", {
        "active": "help",
        "q": q,
        "faqs": faqs,
        "links": links,
    })


@router.get("/api/hub/data-status")
def api_hub_data_status_v084(db: Session = Depends(get_db)):
    tables = ["partners", "partner_contacts", "partner_links", "partner_products", "hub_sections", "hub_subsections", "specialists", "tips"]
    result = {}
    for t in tables:
        exists = table_exists_v084_(db, t)
        count = None
        error = None
        if exists:
            try:
                count = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            except Exception as e:
                error = str(e)
        result[t] = {"exists": exists, "count": count, "error": error}

    return {
        "ok": True,
        "version": "0.9.8-import-timestamps-fix",
        "tables": result,
    }




# -------------------------------------------------------------------
# v0.9.8 TIP Admin Data Flow – sekce/podsekce/specialisté z adminu do poradce
# -------------------------------------------------------------------

def ensure_tips_columns_v085_(db: Session):
    ensure_user_hub_tables_v082_(db)
    alters = [
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS section_code TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS subsection_code TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS section_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS subsection_name TEXT NOT NULL DEFAULT ''",
    ]
    for stmt in alters:
        db.execute(text(stmt))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tips_section ON tips (section_code)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tips_subsection ON tips (subsection_code)"))
    db.commit()


def get_hub_taxonomy_v085_(db: Session):
    ensure_hub_taxonomy_v083_(db)
    sections = fetch_all_safe_v084_(db, """
        SELECT section_code, section_name, icon, COALESCE(image_url, '') AS image_url, sort_order
        FROM hub_sections
        WHERE COALESCE(is_active, TRUE) = TRUE
        ORDER BY sort_order, section_name
    """)
    subsections = fetch_all_safe_v084_(db, """
        SELECT subsection_code, subsection_name, section_code, sort_order
        FROM hub_subsections
        WHERE COALESCE(is_active, TRUE) = TRUE
        ORDER BY section_code, sort_order, subsection_name
    """)
    return sections, subsections


def get_specialists_for_hub_v085_(db: Session):
    try:
        ensure_specialists_table_(db)
    except Exception:
        return []
    return fetch_all_safe_v084_(db, """
        SELECT s.*,
               COALESCE(hs.section_name, s.section_code) AS section_name,
               COALESCE(hss.subsection_name, s.subsection_code) AS subsection_name
        FROM specialists s
        LEFT JOIN hub_sections hs ON hs.section_code = s.section_code
        LEFT JOIN hub_subsections hss ON hss.subsection_code = s.subsection_code
        WHERE COALESCE(s.is_active, TRUE) = TRUE
          AND COALESCE(s.available, TRUE) = TRUE
        ORDER BY hs.sort_order, hss.sort_order, s.specialist_name
        LIMIT 500
    """)


@router.get("/hub/new-tip", response_class=HTMLResponse)
def hub_new_tip_v085(request: Request, db: Session = Depends(get_db)):
    ensure_tips_columns_v085_(db)
    sections, subsections = get_hub_taxonomy_v085_(db)
    specialists = get_specialists_for_hub_v085_(db)
    return hub_render_v083_(request, "hub_new_tip.html", {
        "active": "new_tip",
        "sections": sections,
        "subsections": subsections,
        "specialists": specialists,
    })


@router.post("/hub/tips/create")
def hub_create_tip_v085(
    section_code: str = Form(""),
    subsection_code: str = Form(""),
    specialist_email: str = Form(""),
    specialist_name: str = Form(""),
    client_name: str = Form(...),
    client_phone: str = Form(""),
    client_identifier: str = Form(""),
    potential_amount: str = Form(""),
    adviser_note: str = Form(""),
    policy_no: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_tips_columns_v085_(db)
    user = hub_user_context_v083_()

    section = fetch_one_safe_v084_(db, """
        SELECT section_code, section_name
        FROM hub_sections
        WHERE upper(section_code) = upper(:code)
        LIMIT 1
    """, {"code": section_code})

    subsection = fetch_one_safe_v084_(db, """
        SELECT subsection_code, subsection_name
        FROM hub_subsections
        WHERE upper(subsection_code) = upper(:code)
        LIMIT 1
    """, {"code": subsection_code})

    amount = None
    if potential_amount:
        try:
            amount = Decimal(str(potential_amount).replace(" ", "").replace("Kč", "").replace(",", "."))
        except Exception:
            amount = None

    if not specialist_name and specialist_email:
        spec = fetch_one_safe_v084_(db, """
            SELECT specialist_name
            FROM specialists
            WHERE lower(email) = lower(:email)
            LIMIT 1
        """, {"email": specialist_email})
        if spec:
            specialist_name = spec["specialist_name"]

    tip_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO tips
          (id, adviser_original_id, adviser_name, adviser_email,
           section_code, subsection_code, section_name, subsection_name,
           specialist_name, specialist_email,
           client_name, client_phone, client_identifier, potential_amount,
           adviser_note, status, policy_no)
        VALUES
          (:id, :advisor_id, :advisor_name, :advisor_email,
           :section_code, :subsection_code, :section_name, :subsection_name,
           :specialist_name, :specialist_email,
           :client_name, :client_phone, :client_identifier, :potential_amount,
           :adviser_note, 'Nový', :policy_no)
    """), {
        "id": tip_id,
        "advisor_id": user["advisor_id"],
        "advisor_name": user["name"],
        "advisor_email": user["email"],
        "section_code": section_code,
        "subsection_code": subsection_code,
        "section_name": section["section_name"] if section else section_code,
        "subsection_name": subsection["subsection_name"] if subsection else subsection_code,
        "specialist_name": specialist_name,
        "specialist_email": specialist_email,
        "client_name": client_name,
        "client_phone": client_phone,
        "client_identifier": client_identifier,
        "potential_amount": amount,
        "adviser_note": adviser_note,
        "policy_no": policy_no,
    })
    db.commit()
    try:
        safe_audit(db, user["email"], "CREATE", "tips", tip_id, {}, {
            "client_name": client_name,
            "section_code": section_code,
            "subsection_code": subsection_code,
            "specialist_email": specialist_email,
        }, "Poradce založil nový TIP")
    except Exception:
        pass
    return RedirectResponse("/hub/my-tips?created=1", status_code=303)


@router.get("/hub/my-tips-old-v091", response_class=HTMLResponse)
def hub_my_tips_v085(
    request: Request,
    q: str = "",
    status: str = "",
    section: str = "",
    created: str = "",
    db: Session = Depends(get_db),
):
    ensure_tips_columns_v085_(db)
    user = hub_user_context_v083_()
    sections, _ = get_hub_taxonomy_v085_(db)

    sql = """
        SELECT *
        FROM tips
        WHERE COALESCE(adviser_original_id, '') = :advisor_id
    """
    params = {"advisor_id": user["advisor_id"]}

    if q:
        sql += """
          AND (
            lower(COALESCE(client_name, '')) LIKE :q OR
            lower(COALESCE(client_identifier, '')) LIKE :q OR
            lower(COALESCE(specialist_name, '')) LIKE :q OR
            lower(COALESCE(policy_no, '')) LIKE :q OR
            lower(COALESCE(adviser_note, '')) LIKE :q OR
            lower(COALESCE(section_name, '')) LIKE :q OR
            lower(COALESCE(subsection_name, '')) LIKE :q
          )
        """
        params["q"] = f"%{q.lower()}%"

    if status:
        sql += " AND status = :status"
        params["status"] = status
    if section:
        sql += " AND upper(section_code) = upper(:section)"
        params["section"] = section

    sql += " ORDER BY created_at DESC LIMIT 300"
    rows = db.execute(text(sql), params).mappings().all()

    stats = db.execute(text("""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status ILIKE 'sjednáno') AS won,
          COUNT(*) FILTER (WHERE status ILIKE 'storno') AS lost,
          COUNT(*) FILTER (WHERE status NOT ILIKE 'sjednáno' AND status NOT ILIKE 'storno') AS open
        FROM tips
        WHERE COALESCE(adviser_original_id, '') = :advisor_id
    """), {"advisor_id": user["advisor_id"]}).mappings().first()

    return hub_render_v083_(request, "hub_my_tips.html", {
        "active": "my_tips",
        "rows": rows,
        "stats": stats,
        "sections": sections,
        "q": q,
        "status": status,
        "section": section,
        "created": created,
    })


@router.get("/api/hub/taxonomy-status")
def api_hub_taxonomy_status_v085(db: Session = Depends(get_db)):
    sections, subsections = get_hub_taxonomy_v085_(db)
    specialists = get_specialists_for_hub_v085_(db)
    return {
        "ok": True,
        "version": "0.9.8-import-timestamps-fix",
        "sections_count": len(sections),
        "subsections_count": len(subsections),
        "specialists_count": len(specialists),
        "sections": [dict(s) for s in sections],
        "subsections": [dict(s) for s in subsections],
    }



# -------------------------------------------------------------------
# v0.9.8 Partner autocomplete & Forms data source
# -------------------------------------------------------------------

@router.get("/api/hub/partners/search")
def api_hub_partners_search_v086(q: str = "", limit: int = 20, db: Session = Depends(get_db)):
    """Našeptávač partnerů pro uživatelskou část HUBu."""
    if not table_exists_v084_(db, "partners"):
        return {"ok": True, "version": "0.9.8-import-timestamps-fix", "items": []}

    q_clean = (q or "").strip().lower()
    params = {"limit": max(1, min(limit, 50))}
    where = "WHERE COALESCE(is_active, TRUE) = TRUE"

    if q_clean:
        where += """
          AND (
            lower(COALESCE(partner_code, '')) LIKE :q OR
            lower(COALESCE(name, '')) LIKE :q OR
            lower(COALESCE(ico, '')) LIKE :q OR
            lower(COALESCE(data_box, '')) LIKE :q OR
            lower(COALESCE(registry_email, '')) LIKE :q OR
            lower(COALESCE(city, '')) LIKE :q
          )
        """
        params["q"] = f"%{q_clean}%"

    rows = fetch_all_safe_v084_(db, f"""
        SELECT partner_code, name, ico, data_box, registry_email, address_full, street, city, zip_code, status
        FROM partners
        {where}
        ORDER BY
          CASE WHEN lower(COALESCE(partner_code, '')) = :exact THEN 0 ELSE 1 END,
          name
        LIMIT :limit
    """, {**params, "exact": q_clean})

    return {
        "ok": True,
        "version": "0.9.8-import-timestamps-fix",
        "items": [dict(r) for r in rows],
    }


@router.get("/api/hub/partners/{partner_code}/form-source")
def api_hub_partner_form_source_v086(partner_code: str, db: Session = Depends(get_db)):
    """Kompletní zdrojová data partnera pro výpovědi a formuláře."""
    if not table_exists_v084_(db, "partners"):
        return {"ok": False, "version": "0.9.8-import-timestamps-fix", "error": "Tabulka partners neexistuje."}

    partner = fetch_one_safe_v084_(db, """
        SELECT *
        FROM partners
        WHERE upper(partner_code) = upper(:code)
        LIMIT 1
    """, {"code": partner_code})

    if not partner:
        return {"ok": False, "version": "0.9.8-import-timestamps-fix", "error": "Partner nenalezen."}

    contacts = []
    links = []
    products = []

    if table_exists_v084_(db, "partner_contacts"):
        contacts = fetch_all_safe_v084_(db, """
            SELECT *
            FROM partner_contacts
            WHERE upper(partner_code) = upper(:code)
              AND COALESCE(is_active, TRUE) = TRUE
            ORDER BY COALESCE(is_vip, FALSE) DESC, COALESCE(is_top, FALSE) DESC, full_name
            LIMIT 100
        """, {"code": partner_code})

    if table_exists_v084_(db, "partner_links"):
        links = fetch_all_safe_v084_(db, """
            SELECT *
            FROM partner_links
            WHERE upper(partner_code) = upper(:code)
              AND COALESCE(is_active, TRUE) = TRUE
            ORDER BY category, title
            LIMIT 100
        """, {"code": partner_code})

    if table_exists_v084_(db, "partner_products"):
        products = fetch_all_safe_v084_(db, """
            SELECT *
            FROM partner_products
            WHERE upper(partner_code) = upper(:code)
              AND COALESCE(is_active, TRUE) = TRUE
            ORDER BY area, subarea, product_name
            LIMIT 100
        """, {"code": partner_code})

    return {
        "ok": True,
        "version": "0.9.8-import-timestamps-fix",
        "partner": dict(partner),
        "contacts": [dict(c) for c in contacts],
        "links": [dict(l) for l in links],
        "products": [dict(p) for p in products],
    }


@router.get("/api/hub/partners/{partner_code}/summary")
def api_hub_partner_summary_v086(partner_code: str, db: Session = Depends(get_db)):
    """Rychlý souhrn partnera pro detail v HUBu."""
    data = api_hub_partner_form_source_v086(partner_code, db)
    if not data.get("ok"):
        return data
    return {
        "ok": True,
        "version": "0.9.8-import-timestamps-fix",
        "partner": data["partner"],
        "counts": {
            "contacts": len(data["contacts"]),
            "links": len(data["links"]),
            "products": len(data["products"]),
        },
    }



@router.get("/hub/forms", response_class=HTMLResponse)
def hub_forms_v086(request: Request, q: str = "", selected: str = "", db: Session = Depends(get_db)):
    partners = []
    partner = None

    if table_exists_v084_(db, "partners"):
        params = {}
        where = "WHERE COALESCE(is_active, TRUE) = TRUE"
        if q:
            where += """
              AND (
                lower(COALESCE(name, '')) LIKE :q OR
                lower(COALESCE(partner_code, '')) LIKE :q OR
                lower(COALESCE(ico, '')) LIKE :q OR
                lower(COALESCE(data_box, '')) LIKE :q OR
                lower(COALESCE(registry_email, '')) LIKE :q
              )
            """
            params["q"] = f"%{q.lower()}%"

        partners = fetch_all_safe_v084_(db, f"""
            SELECT partner_code, name, ico, data_box, registry_email, address_full, street, city, zip_code
            FROM partners
            {where}
            ORDER BY name
            LIMIT 200
        """, params)

        if selected:
            partner = fetch_one_safe_v084_(db, """
                SELECT partner_code, name, ico, data_box, registry_email, address_full, street, city, zip_code
                FROM partners
                WHERE upper(partner_code) = upper(:code)
                LIMIT 1
            """, {"code": selected})

    return hub_render_v083_(request, "hub_forms.html", {
        "active": "forms",
        "partners": partners,
        "partner": partner,
        "q": q,
        "selected": selected,
    })





# -------------------------------------------------------------------
# v0.9.8 Operational TIP Workflow
# Import dat + BO centrální evidence + specialista pracovní fronta
# -------------------------------------------------------------------

def current_bo_user_v090_():
    return {
        "name": "Admin ASTORIE",
        "email": "nekudova@astorieas.cz",
        "role": "BO",
    }


def ensure_tip_workflow_v090_(db: Session):
    ensure_tips_columns_v085_(db)

    alters = [
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS bo_note TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS specialist_internal_note TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS adviser_last_message TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS final_report TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS last_update_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS imported_source TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS imported_original_id TEXT NOT NULL DEFAULT ''",
    ]
    for stmt in alters:
        db.execute(text(stmt))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS tip_updates (
            id TEXT PRIMARY KEY,
            tip_id TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            author_name TEXT NOT NULL DEFAULT '',
            author_email TEXT NOT NULL DEFAULT '',
            author_role TEXT NOT NULL DEFAULT '',
            update_type TEXT NOT NULL DEFAULT '',
            old_status TEXT NOT NULL DEFAULT '',
            new_status TEXT NOT NULL DEFAULT '',
            message_to_adviser TEXT NOT NULL DEFAULT '',
            internal_note TEXT NOT NULL DEFAULT '',
            final_report TEXT NOT NULL DEFAULT ''
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS import_jobs (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            source_name TEXT NOT NULL DEFAULT '',
            rows_total INTEGER NOT NULL DEFAULT 0,
            rows_imported INTEGER NOT NULL DEFAULT 0,
            rows_skipped INTEGER NOT NULL DEFAULT 0,
            error_log TEXT NOT NULL DEFAULT '',
            created_by TEXT NOT NULL DEFAULT ''
        )
    """))

    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tips_specialist_email ON tips (specialist_email)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tips_status_all ON tips (status)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tips_last_update ON tips (last_update_at DESC)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tip_updates_tip ON tip_updates (tip_id, created_at DESC)"))
    db.commit()


def normalize_tip_status_v090_(status: str) -> str:
    s = (status or "").strip().lower()
    if not s:
        return "Nový"
    if s in ["novy", "nový", "new", "zadáno", "zadano"]:
        return "Nový"
    if s in ["v reseni", "v řešení", "reseni", "řešení", "pracuje se", "rozpracováno"]:
        return "V řešení"
    if s in ["sjednano", "sjednáno", "hotovo", "uzavreno", "uzavřeno", "vyřízeno"]:
        return "Sjednáno"
    if s in ["storno", "zruseno", "zrušeno", "nezajem", "nezájem", "nevyšlo"]:
        return "Storno"
    if s in ["archiv", "archivováno", "archivovano"]:
        return "Archiv"
    return status.strip()


def find_header_v090_(row: dict, candidates: list[str]) -> str:
    normalized = {str(k).strip().lower(): k for k in row.keys()}
    for c in candidates:
        key = c.strip().lower()
        if key in normalized:
            return normalized[key]
    return ""


def get_row_value_v090_(row: dict, candidates: list[str], default: str = ""):
    key = find_header_v090_(row, candidates)
    if not key:
        return default
    return (row.get(key) or default)


@router.get("/admin/tips", response_class=HTMLResponse)
def admin_all_tips_v090(
    request: Request,
    q: str = "",
    status: str = "",
    specialist: str = "",
    adviser: str = "",
    archive: str = "",
    db: Session = Depends(get_db),
):
    ensure_tip_workflow_v090_(db)

    sql = """
        SELECT *
        FROM tips
        WHERE 1=1
    """
    params = {}

    if q:
        sql += """
          AND (
            lower(COALESCE(client_name, '')) LIKE :q OR
            lower(COALESCE(client_identifier, '')) LIKE :q OR
            lower(COALESCE(adviser_name, '')) LIKE :q OR
            lower(COALESCE(adviser_email, '')) LIKE :q OR
            lower(COALESCE(specialist_name, '')) LIKE :q OR
            lower(COALESCE(specialist_email, '')) LIKE :q OR
            lower(COALESCE(policy_no, '')) LIKE :q OR
            lower(COALESCE(section_name, '')) LIKE :q OR
            lower(COALESCE(subsection_name, '')) LIKE :q
          )
        """
        params["q"] = f"%{q.lower()}%"

    if status:
        sql += " AND status = :status"
        params["status"] = status

    if specialist:
        sql += " AND lower(COALESCE(specialist_email, '')) LIKE :specialist"
        params["specialist"] = f"%{specialist.lower()}%"

    if adviser:
        sql += " AND lower(COALESCE(adviser_email, '')) LIKE :adviser"
        params["adviser"] = f"%{adviser.lower()}%"

    if archive != "1":
        sql += " AND COALESCE(status, '') <> 'Archiv'"

    sql += " ORDER BY last_update_at DESC, created_at DESC LIMIT 800"

    rows = db.execute(text(sql), params).mappings().all()

    stats = db.execute(text("""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status = 'Nový') AS new_count,
          COUNT(*) FILTER (WHERE status = 'V řešení') AS progress_count,
          COUNT(*) FILTER (WHERE status = 'Sjednáno') AS won_count,
          COUNT(*) FILTER (WHERE status = 'Storno') AS lost_count,
          COUNT(*) FILTER (WHERE status = 'Archiv') AS archive_count
        FROM tips
    """)).mappings().first()

    return request.app.state.templates.TemplateResponse("admin_tips.html", {
        "request": request,
        "active": "admin_tips",
        "rows": rows,
        "stats": stats,
        "q": q,
        "status": status,
        "specialist": specialist,
        "adviser": adviser,
        "archive": archive,
        "version": "0.9.8-import-timestamps-fix",
    })


@router.get("/admin/tips/{tip_id}", response_class=HTMLResponse)
def admin_tip_detail_v090(request: Request, tip_id: str, db: Session = Depends(get_db)):
    ensure_tip_workflow_v090_(db)
    tip = fetch_one_safe_v084_(db, "SELECT * FROM tips WHERE id = :id", {"id": tip_id})
    updates = fetch_all_safe_v084_(db, """
        SELECT *
        FROM tip_updates
        WHERE tip_id = :id
        ORDER BY created_at DESC
    """, {"id": tip_id})

    return request.app.state.templates.TemplateResponse("admin_tip_detail.html", {
        "request": request,
        "active": "admin_tips",
        "tip": tip,
        "updates": updates,
        "version": "0.9.8-import-timestamps-fix",
    })


@router.post("/admin/tips/{tip_id}/bo-update")
def admin_tip_bo_update_v090(
    tip_id: str,
    status: str = Form(""),
    bo_note: str = Form(""),
    message_to_adviser: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_tip_workflow_v090_(db)
    user = current_bo_user_v090_()
    old = fetch_one_safe_v084_(db, "SELECT * FROM tips WHERE id = :id", {"id": tip_id})
    old_status = old["status"] if old else ""

    new_status = normalize_tip_status_v090_(status or old_status)
    closed_sql = ", closed_at = now()" if new_status in ["Sjednáno", "Storno"] else ""
    archived_sql = ", archived_at = now()" if new_status == "Archiv" else ""

    db.execute(text(f"""
        UPDATE tips
        SET status = :status,
            bo_note = :bo_note,
            adviser_last_message = :message_to_adviser,
            last_update_at = now()
            {closed_sql}
            {archived_sql}
        WHERE id = :id
    """), {
        "id": tip_id,
        "status": new_status,
        "bo_note": bo_note,
        "message_to_adviser": message_to_adviser,
    })

    db.execute(text("""
        INSERT INTO tip_updates
        (id, tip_id, author_name, author_email, author_role, update_type,
         old_status, new_status, message_to_adviser, internal_note)
        VALUES
        (:id, :tip_id, :author_name, :author_email, :author_role, 'BO_UPDATE',
         :old_status, :new_status, :message_to_adviser, :internal_note)
    """), {
        "id": str(uuid.uuid4()),
        "tip_id": tip_id,
        "author_name": user["name"],
        "author_email": user["email"],
        "author_role": user["role"],
        "old_status": old_status,
        "new_status": new_status,
        "message_to_adviser": message_to_adviser,
        "internal_note": bo_note,
    })
    db.commit()
    return RedirectResponse(f"/admin/tips/{tip_id}", status_code=303)


@router.get("/hub/specialist-tips", response_class=HTMLResponse)
def hub_specialist_tips_v090(
    request: Request,
    q: str = "",
    status: str = "",
    archive: str = "",
    db: Session = Depends(get_db),
):
    ensure_tip_workflow_v090_(db)
    user = hub_user_context_v083_()
    email = (user.get("email") or "").lower()

    sql = """
        SELECT *
        FROM tips
        WHERE lower(COALESCE(specialist_email, '')) = :email
    """
    params = {"email": email}

    if q:
        sql += """
          AND (
            lower(COALESCE(client_name, '')) LIKE :q OR
            lower(COALESCE(adviser_name, '')) LIKE :q OR
            lower(COALESCE(policy_no, '')) LIKE :q OR
            lower(COALESCE(section_name, '')) LIKE :q OR
            lower(COALESCE(subsection_name, '')) LIKE :q
          )
        """
        params["q"] = f"%{q.lower()}%"

    if status:
        sql += " AND status = :status"
        params["status"] = status

    if archive != "1":
        sql += " AND COALESCE(status, '') <> 'Archiv'"

    sql += " ORDER BY last_update_at DESC, created_at DESC LIMIT 300"
    rows = db.execute(text(sql), params).mappings().all()

    stats = db.execute(text("""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status = 'Nový') AS new_count,
          COUNT(*) FILTER (WHERE status = 'V řešení') AS progress_count,
          COUNT(*) FILTER (WHERE status = 'Sjednáno') AS won_count,
          COUNT(*) FILTER (WHERE status = 'Storno') AS lost_count,
          COUNT(*) FILTER (WHERE status = 'Archiv') AS archive_count
        FROM tips
        WHERE lower(COALESCE(specialist_email, '')) = :email
    """), {"email": email}).mappings().first()

    return hub_render_v083_(request, "hub_specialist_tips.html", {
        "active": "specialist_tips",
        "rows": rows,
        "stats": stats,
        "q": q,
        "status": status,
        "archive": archive,
    })


@router.get("/hub/specialist-tips/{tip_id}", response_class=HTMLResponse)
def hub_specialist_tip_detail_v090(request: Request, tip_id: str, db: Session = Depends(get_db)):
    ensure_tip_workflow_v090_(db)
    user = hub_user_context_v083_()
    tip = fetch_one_safe_v084_(db, """
        SELECT *
        FROM tips
        WHERE id = :id
          AND lower(COALESCE(specialist_email, '')) = lower(:email)
        LIMIT 1
    """, {"id": tip_id, "email": user["email"]})

    updates = fetch_all_safe_v084_(db, """
        SELECT *
        FROM tip_updates
        WHERE tip_id = :id
        ORDER BY created_at DESC
    """, {"id": tip_id})

    return hub_render_v083_(request, "hub_specialist_tip_detail.html", {
        "active": "specialist_tips",
        "tip": tip,
        "updates": updates,
    })


@router.post("/hub/specialist-tips/{tip_id}/update")
def hub_specialist_tip_update_v090(
    tip_id: str,
    status: str = Form("V řešení"),
    message_to_adviser: str = Form(""),
    internal_note: str = Form(""),
    final_report: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_tip_workflow_v090_(db)
    user = hub_user_context_v083_()
    old = fetch_one_safe_v084_(db, """
        SELECT *
        FROM tips
        WHERE id = :id
          AND lower(COALESCE(specialist_email, '')) = lower(:email)
        LIMIT 1
    """, {"id": tip_id, "email": user["email"]})

    if not old:
        return RedirectResponse("/hub/specialist-tips", status_code=303)

    old_status = old["status"]
    new_status = normalize_tip_status_v090_(status)
    closed_sql = ", closed_at = now()" if new_status in ["Sjednáno", "Storno"] else ""

    db.execute(text(f"""
        UPDATE tips
        SET status = :status,
            adviser_last_message = :message_to_adviser,
            specialist_internal_note = :internal_note,
            final_report = :final_report,
            last_update_at = now()
            {closed_sql}
        WHERE id = :id
    """), {
        "id": tip_id,
        "status": new_status,
        "message_to_adviser": message_to_adviser,
        "internal_note": internal_note,
        "final_report": final_report,
    })

    db.execute(text("""
        INSERT INTO tip_updates
        (id, tip_id, author_name, author_email, author_role, update_type,
         old_status, new_status, message_to_adviser, internal_note, final_report)
        VALUES
        (:id, :tip_id, :author_name, :author_email, 'SPECIALIST', 'SPECIALIST_UPDATE',
         :old_status, :new_status, :message_to_adviser, :internal_note, :final_report)
    """), {
        "id": str(uuid.uuid4()),
        "tip_id": tip_id,
        "author_name": user["name"],
        "author_email": user["email"],
        "old_status": old_status,
        "new_status": new_status,
        "message_to_adviser": message_to_adviser,
        "internal_note": internal_note,
        "final_report": final_report,
    })

    db.commit()
    return RedirectResponse(f"/hub/specialist-tips/{tip_id}", status_code=303)


@router.get("/admin/import/legacy-tips", response_class=HTMLResponse)
def admin_import_legacy_tips_page_v090(request: Request, db: Session = Depends(get_db)):
    ensure_tip_workflow_v090_(db)
    jobs = fetch_all_safe_v084_(db, """
        SELECT *
        FROM import_jobs
        ORDER BY created_at DESC
        LIMIT 20
    """)
    return request.app.state.templates.TemplateResponse("admin_import_legacy_tips.html", {
        "request": request,
        "active": "import",
        "jobs": jobs,
        "version": "0.9.8-import-timestamps-fix",
    })


@router.post("/admin/import/legacy-tips")
async def admin_import_legacy_tips_v090(
    file: UploadFile = File(...),
    source_name: str = Form("Stávající HUB ASTORIE"),
    db: Session = Depends(get_db),
):
    ensure_tip_workflow_v090_(db)
    user = current_bo_user_v090_()
    job_id = str(uuid.uuid4())
    rows_total = rows_imported = rows_skipped = 0
    errors = []

    content = await file.read()
    text_content = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text_content), delimiter=";")
    if not reader.fieldnames or len(reader.fieldnames) <= 1:
        reader = csv.DictReader(io.StringIO(text_content), delimiter=",")

    for row in reader:
        rows_total += 1
        try:
            original_id = str(get_row_value_v090_(row, ["id", "tip_id", "ID", "Číslo", "Cislo"], "")).strip()
            client_name = str(get_row_value_v090_(row, ["client_name", "Klient", "Jméno klienta", "Jmeno klienta", "Název klienta"], "")).strip()
            adviser_name = str(get_row_value_v090_(row, ["adviser_name", "Poradce", "Tipař", "Tipar", "IF"], "")).strip()
            adviser_email = str(get_row_value_v090_(row, ["adviser_email", "E-mail poradce", "Email poradce", "E-mail IF"], "")).strip()
            specialist_name = str(get_row_value_v090_(row, ["specialist_name", "Specialista", "PS"], "")).strip()
            specialist_email = str(get_row_value_v090_(row, ["specialist_email", "E-mail specialista", "Email specialista", "E-mail PS"], "")).strip()
            status = normalize_tip_status_v090_(str(get_row_value_v090_(row, ["status", "Stav"], "Nový")).strip())
            section_name = str(get_row_value_v090_(row, ["section_name", "Sekce", "Oblast"], "")).strip()
            subsection_name = str(get_row_value_v090_(row, ["subsection_name", "Podsekce", "Podoblast"], "")).strip()
            policy_no = str(get_row_value_v090_(row, ["policy_no", "Smlouva", "Číslo smlouvy", "Cislo smlouvy"], "")).strip()
            note = str(get_row_value_v090_(row, ["adviser_note", "Poznámka", "Poznamka", "Popis"], "")).strip()
            potential_raw = str(get_row_value_v090_(row, ["potential_amount", "Potenciál", "Potencial", "Objem"], "")).strip()

            if not client_name and not adviser_name and not specialist_name:
                rows_skipped += 1
                continue

            amount = None
            if potential_raw:
                try:
                    amount = Decimal(potential_raw.replace(" ", "").replace("Kč", "").replace(",", "."))
                except Exception:
                    amount = None

            db.execute(text("""
                INSERT INTO tips
                (id, adviser_original_id, adviser_name, adviser_email,
                 specialist_name, specialist_email, client_name, potential_amount,
                 adviser_note, status, policy_no, section_name, subsection_name,
                 imported_source, imported_original_id, last_update_at)
                VALUES
                (:id, :adviser_original_id, :adviser_name, :adviser_email,
                 :specialist_name, :specialist_email, :client_name, :potential_amount,
                 :adviser_note, :status, :policy_no, :section_name, :subsection_name,
                 :imported_source, :imported_original_id, now())
            """), {
                "id": str(uuid.uuid4()),
                "adviser_original_id": str(get_row_value_v090_(row, ["advisor_id", "ID poradce", "ID"], "")),
                "adviser_name": adviser_name,
                "adviser_email": adviser_email,
                "specialist_name": specialist_name,
                "specialist_email": specialist_email,
                "client_name": client_name,
                "potential_amount": amount,
                "adviser_note": note,
                "status": status,
                "policy_no": policy_no,
                "section_name": section_name,
                "subsection_name": subsection_name,
                "imported_source": source_name,
                "imported_original_id": original_id,
            })
            rows_imported += 1
        except Exception as e:
            rows_skipped += 1
            errors.append(f"Řádek {rows_total}: {str(e)}")

    db.execute(text("""
        INSERT INTO import_jobs
        (id, source_name, rows_total, rows_imported, rows_skipped, error_log, created_by)
        VALUES
        (:id, :source_name, :rows_total, :rows_imported, :rows_skipped, :error_log, :created_by)
    """), {
        "id": job_id,
        "source_name": source_name,
        "rows_total": rows_total,
        "rows_imported": rows_imported,
        "rows_skipped": rows_skipped,
        "error_log": "\n".join(errors[:100]),
        "created_by": user["email"],
    })
    db.commit()

    return RedirectResponse("/admin/import/legacy-tips", status_code=303)


@router.get("/api/tips/central-status")
def api_tips_central_status_v090(db: Session = Depends(get_db)):
    ensure_tip_workflow_v090_(db)
    stats = db.execute(text("""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status = 'Nový') AS new_count,
          COUNT(*) FILTER (WHERE status = 'V řešení') AS progress_count,
          COUNT(*) FILTER (WHERE status = 'Sjednáno') AS won_count,
          COUNT(*) FILTER (WHERE status = 'Storno') AS lost_count,
          COUNT(*) FILTER (WHERE status = 'Archiv') AS archive_count
        FROM tips
    """)).mappings().first()
    return {
        "ok": True,
        "version": "0.9.8-import-timestamps-fix",
        "stats": dict(stats or {}),
    }





# -------------------------------------------------------------------
# v0.9.8 Unified TIP Inbox – jedna obrazovka jako ve stávající aplikaci
# -------------------------------------------------------------------

@router.get("/hub/my-tips", response_class=HTMLResponse)
def hub_my_tips_unified_v091(
    request: Request,
    tab: str = "sent",
    q: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    ensure_tip_workflow_v090_(db)
    user = hub_user_context_v083_()
    adviser_id = user.get("advisor_id") or ""
    email = (user.get("email") or "").lower()

    base_where = "1=1"
    params = {}

    if tab == "work":
        base_where = "lower(COALESCE(specialist_email, '')) = :email AND COALESCE(status, '') NOT IN ('Sjednáno','Storno','Archiv')"
        params["email"] = email
    elif tab == "archive":
        base_where = """
          (
            COALESCE(adviser_original_id, '') = :adviser_id
            OR lower(COALESCE(adviser_email, '')) = :email
            OR lower(COALESCE(specialist_email, '')) = :email
          )
          AND COALESCE(status, '') IN ('Sjednáno','Storno','Archiv')
        """
        params["adviser_id"] = adviser_id
        params["email"] = email
    else:
        tab = "sent"
        base_where = """
          (
            COALESCE(adviser_original_id, '') = :adviser_id
            OR lower(COALESCE(adviser_email, '')) = :email
          )
          AND COALESCE(status, '') <> 'Archiv'
        """
        params["adviser_id"] = adviser_id
        params["email"] = email

    sql = f"SELECT * FROM tips WHERE {base_where}"

    if q:
        sql += """
          AND (
            lower(COALESCE(client_name, '')) LIKE :q OR
            lower(COALESCE(client_identifier, '')) LIKE :q OR
            lower(COALESCE(adviser_name, '')) LIKE :q OR
            lower(COALESCE(specialist_name, '')) LIKE :q OR
            lower(COALESCE(policy_no, '')) LIKE :q OR
            lower(COALESCE(section_name, '')) LIKE :q OR
            lower(COALESCE(subsection_name, '')) LIKE :q OR
            lower(COALESCE(adviser_note, '')) LIKE :q
          )
        """
        params["q"] = f"%{q.lower()}%"

    if status:
        sql += " AND status = :status"
        params["status"] = status

    sql += " ORDER BY last_update_at DESC, created_at DESC LIMIT 500"
    rows = db.execute(text(sql), params).mappings().all()

    stats = db.execute(text("""
        SELECT
          COUNT(*) FILTER (
            WHERE (COALESCE(adviser_original_id, '') = :adviser_id OR lower(COALESCE(adviser_email, '')) = :email)
              AND COALESCE(status, '') <> 'Archiv'
          ) AS sent_count,
          COUNT(*) FILTER (
            WHERE lower(COALESCE(specialist_email, '')) = :email
              AND COALESCE(status, '') NOT IN ('Sjednáno','Storno','Archiv')
          ) AS work_count,
          COUNT(*) FILTER (
            WHERE (
              COALESCE(adviser_original_id, '') = :adviser_id
              OR lower(COALESCE(adviser_email, '')) = :email
              OR lower(COALESCE(specialist_email, '')) = :email
            )
            AND COALESCE(status, '') IN ('Sjednáno','Storno','Archiv')
          ) AS archive_count,
          COUNT(*) FILTER (WHERE status = 'Sjednáno') AS won_count,
          COUNT(*) FILTER (WHERE status = 'Storno') AS lost_count
        FROM tips
    """), {"adviser_id": adviser_id, "email": email}).mappings().first()

    return hub_render_v083_(request, "hub_my_tips_unified.html", {
        "active": "my_tips",
        "tab": tab,
        "rows": rows,
        "stats": stats,
        "q": q,
        "status": status,
    })


@router.get("/hub/tips/{tip_id}", response_class=HTMLResponse)
def hub_tip_detail_unified_v091(request: Request, tip_id: str, db: Session = Depends(get_db)):
    ensure_tip_workflow_v090_(db)
    user = hub_user_context_v083_()
    email = (user.get("email") or "").lower()
    adviser_id = user.get("advisor_id") or ""

    tip = fetch_one_safe_v084_(db, """
        SELECT *
        FROM tips
        WHERE id = :id
          AND (
            COALESCE(adviser_original_id, '') = :adviser_id
            OR lower(COALESCE(adviser_email, '')) = :email
            OR lower(COALESCE(specialist_email, '')) = :email
          )
        LIMIT 1
    """, {"id": tip_id, "email": email, "adviser_id": adviser_id})

    updates = fetch_all_safe_v084_(db, """
        SELECT *
        FROM tip_updates
        WHERE tip_id = :id
        ORDER BY created_at DESC
    """, {"id": tip_id})

    return hub_render_v083_(request, "hub_tip_detail_unified.html", {
        "active": "my_tips",
        "tip": tip,
        "updates": updates,
        "is_specialist": bool(tip and (tip.get("specialist_email") or "").lower() == email),
    })


@router.post("/hub/tips/{tip_id}/specialist-update")
def hub_tip_unified_specialist_update_v091(
    tip_id: str,
    status: str = Form("V řešení"),
    message_to_adviser: str = Form(""),
    internal_note: str = Form(""),
    final_report: str = Form(""),
    db: Session = Depends(get_db),
):
    return hub_specialist_tip_update_v090(
        tip_id=tip_id,
        status=status,
        message_to_adviser=message_to_adviser,
        internal_note=internal_note,
        final_report=final_report,
        db=db,
    )





# -------------------------------------------------------------------
# v0.9.8 XLSX importer – import přímo ze staženého Google Sheetu
# -------------------------------------------------------------------

def xlsx_cell_to_str_v093_(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    # Excel často vrací číselné ID jako float 501.0; v aplikaci musí být 501.
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value).strip()
    if isinstance(value, int):
        return str(value)
    text_value = str(value).strip()
    if re.fullmatch(r"\d+\.0", text_value):
        return text_value[:-2]
    return text_value


def xlsx_bool_v093_(value):
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"ano", "a", "true", "1", "yes", "aktivni", "aktivní"}


def xlsx_num_v093_(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", ".").replace(" ", "")))
    except Exception:
        return default


def xlsx_decimal_v093_(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace("Kč", "").replace(",-", "").replace(" ", "").replace(",", "."))
    except Exception:
        return None


def xlsx_norm_header_v093_(value):
    value = str(value or "").strip().lower()
    repl = {
        "á": "a", "č": "c", "ď": "d", "é": "e", "ě": "e", "í": "i",
        "ň": "n", "ó": "o", "ř": "r", "š": "s", "ť": "t", "ú": "u",
        "ů": "u", "ý": "y", "ž": "z",
    }
    for a, b in repl.items():
        value = value.replace(a, b)
    for ch in [" ", "-", ".", "/", "\\", "(", ")", "[", "]", ":", ";"]:
        value = value.replace(ch, "_")
    while "__" in value:
        value = value.replace("__", "_")
    return value.strip("_")


def xlsx_rows_v093_(wb, sheet_name):
    if sheet_name not in wb.sheetnames:
        return []
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [xlsx_norm_header_v093_(h) for h in rows[0]]
    out = []
    for row in rows[1:]:
        item = {}
        empty = True
        for i, h in enumerate(headers):
            if not h:
                continue
            val = row[i] if i < len(row) else None
            if val not in (None, ""):
                empty = False
            item[h] = val
        if not empty:
            out.append(item)
    return out


def xlsx_pick_v093_(row, *keys, default=""):
    for key in keys:
        k = xlsx_norm_header_v093_(key)
        if k in row and row[k] not in (None, ""):
            return row[k]
    return default


def xlsx_upsert_v093_(db, table, conflict_col, data, update_existing=False):
    """
    Bezpečný UPSERT pro XLSX import.
    v0.9.8: u UUID tabulek doplňuje id ručně, protože starší PostgreSQL tabulky
    nemají vždy serverový DEFAULT pro id a raw SQL nepoužije SQLAlchemy default.
    """
    uuid_tables = {
        "users",
        "roles",
        "app_settings",
        "sections",
        "subsections",
        "partners",
        "tips",
        "commission_rates",
        "audit_log",
    }

    data = dict(data or {})
    if table in uuid_tables and "id" not in data:
        data["id"] = str(uuid.uuid4())

    # v0.9.8: produkční tabulky mohou mít NOT NULL created_at/updated_at bez DB defaultu.
    # Proto timestampy doplňujeme přímo do importních dat.
    timestamp_tables = {
        "users",
        "sections",
        "subsections",
        "hub_sections",
        "hub_subsections",
        "specialists",
        "partners",
        "partner_contacts",
        "partner_links",
        "partner_products",
        "tips",
        "commission_rates",
        "audit_log",
    }
    if table in timestamp_tables:
        if "created_at" not in data:
            data["created_at"] = datetime.utcnow()
        if "updated_at" not in data:
            data["updated_at"] = datetime.utcnow()

    columns = list(data.keys())
    params = {k: data[k] for k in columns}
    col_sql = ", ".join(columns)
    val_sql = ", ".join([f":{c}" for c in columns])

    if update_existing:
        # Nikdy neaktualizujeme primární klíč id ani konfliktní sloupec.
        set_cols = [c for c in columns if c not in {conflict_col, "id"}]
        set_sql = ", ".join([f"{c}=EXCLUDED.{c}" for c in set_cols]) or f"{conflict_col}=EXCLUDED.{conflict_col}"
        sql = f"""
            INSERT INTO {table} ({col_sql})
            VALUES ({val_sql})
            ON CONFLICT ({conflict_col}) DO UPDATE SET {set_sql}
        """
    else:
        sql = f"""
            INSERT INTO {table} ({col_sql})
            VALUES ({val_sql})
            ON CONFLICT ({conflict_col}) DO NOTHING
        """

    try:
        res = db.execute(text(sql), params)
        return res.rowcount or 0
    except Exception:
        db.rollback()
        raise


def ensure_xlsx_import_structures_v093_(db):
    ensure_tip_workflow_v090_(db)
    ensure_visible_hub_sections_(db)
    ensure_specialists_table_(db)

    # Starší DB mohou mít užší tabulky. Tady je pouze bezpečné rozšíření.
    db.execute(text("ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS risks TEXT NOT NULL DEFAULT ''"))
    db.execute(text("ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS client_type TEXT NOT NULL DEFAULT ''"))
    db.execute(text("ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS keywords TEXT NOT NULL DEFAULT ''"))
    db.execute(text("ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100"))
    db.execute(text("ALTER TABLE partner_links ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT ''"))
    db.execute(text("ALTER TABLE partner_contacts ADD COLUMN IF NOT EXISTS original_note TEXT NOT NULL DEFAULT ''"))
    db.execute(text("ALTER TABLE commission_rates ADD COLUMN IF NOT EXISTS business_type TEXT NOT NULL DEFAULT ''"))
    db.execute(text("ALTER TABLE commission_rates ADD COLUMN IF NOT EXISTS area TEXT NOT NULL DEFAULT ''"))
    db.commit()


def import_hub_xlsx_data_v093_(db, wb, update_existing=False):
    try:
        repair_users_timestamps_v098_(db)
    except Exception:
        pass
    ensure_xlsx_import_structures_v093_(db)

    result = {
        "users": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "sections": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "subsections": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "specialists": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "partners": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "contacts": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "links": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "products": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "commission_rates": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "terminations_partners": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "tips": {"created": 0, "updated_or_skipped": 0, "rows": 0},
        "errors": [],
    }

    # Poradci -> users
    for row in xlsx_rows_v093_(wb, "Poradci"):
        result["users"]["rows"] += 1
        try:
            advisor_id = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID_poradce"))
            email = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Email")).lower()
            name = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Jmeno"))
            if not advisor_id or not email or not name:
                continue
            data = {
                "advisor_id": advisor_id,
                "name": name,
                "email": email,
                "phone": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Telefon")),
                "role": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Role", default="IF")) or "IF",
                "password_hash": hash_password(xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Heslo", default="1234")) or "1234"),
                "is_active": xlsx_bool_v093_(xlsx_pick_v093_(row, "Aktivni", default="ANO")),
                "must_change_password": True,
            }
            created = xlsx_upsert_v093_(db, "users", "advisor_id", data, update_existing)
            result["users"]["created"] += created
            result["users"]["updated_or_skipped"] += 0 if created else 1
        except Exception as exc:
            result["errors"].append(f"Poradci: {exc}")

    # Sekce -> hub_sections + sections
    for row in xlsx_rows_v093_(wb, "Sekce"):
        result["sections"]["rows"] += 1
        try:
            code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID_sekce")).upper()
            name = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Nazev sekce", "Název sekce"))
            if not code or not name:
                continue
            data_hub = {
                "section_code": code,
                "section_name": name,
                "icon": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Ikona")),
                "sort_order": xlsx_num_v093_(xlsx_pick_v093_(row, "Poradi", "Pořadí"), 100),
                "is_active": xlsx_bool_v093_(xlsx_pick_v093_(row, "Aktivni", "Aktivní", default="ANO")),
                "note": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Popis")),
            }
            created = xlsx_upsert_v093_(db, "hub_sections", "section_code", data_hub, update_existing)
            result["sections"]["created"] += created
            result["sections"]["updated_or_skipped"] += 0 if created else 1

            data_core = {
                "section_code": code,
                "name": name,
                "icon": data_hub["icon"],
                "sort_order": data_hub["sort_order"],
                "is_active": data_hub["is_active"],
            }
            xlsx_upsert_v093_(db, "sections", "section_code", data_core, update_existing)
        except Exception as exc:
            result["errors"].append(f"Sekce: {exc}")

    # Podsekce -> hub_subsections + subsections
    for row in xlsx_rows_v093_(wb, "Podsekce"):
        result["subsections"]["rows"] += 1
        try:
            code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID_podsekce")).upper()
            section_code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Sekce_ID")).upper()
            name = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Nazev podsekce", "Název podsekce"))
            if not code or not section_code or not name:
                continue
            data_hub = {
                "subsection_code": code,
                "section_code": section_code,
                "subsection_name": name,
                "sort_order": xlsx_num_v093_(xlsx_pick_v093_(row, "Poradi", "Pořadí"), 100),
                "is_active": xlsx_bool_v093_(xlsx_pick_v093_(row, "Aktivni", "Aktivní", default="ANO")),
                "note": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Popis")),
            }
            created = xlsx_upsert_v093_(db, "hub_subsections", "subsection_code", data_hub, update_existing)
            result["subsections"]["created"] += created
            result["subsections"]["updated_or_skipped"] += 0 if created else 1

            data_core = {
                "subsection_code": code,
                "section_code": section_code,
                "name": name,
                "sort_order": data_hub["sort_order"],
                "is_active": data_hub["is_active"],
            }
            xlsx_upsert_v093_(db, "subsections", "subsection_code", data_core, update_existing)
        except Exception as exc:
            result["errors"].append(f"Podsekce: {exc}")

    # Specialisté
    # v0.9.8: index se nevytváří uvnitř importu. Připravuje se bezpečně před importem.
    for row in xlsx_rows_v093_(wb, "Specialisté"):
        result["specialists"]["rows"] += 1
        try:
            advisor_id = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID_poradce"))
            section_code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID_sekce")).upper()
            subsection_code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID_podsekce")).upper()
            email = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Email")).lower()
            name = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Jmeno", "Jméno"))
            if not advisor_id or not section_code or not email or not name:
                continue

            data = {
                "advisor_id": advisor_id,
                "specialist_name": name,
                "email": email,
                "phone": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Telefon")),
                "section_code": section_code,
                "subsection_code": subsection_code,
                "role_description": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Role")),
                "region": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Region")),
                "if_share": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "IF_podil", "IF podíl")),
                "ps_share": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "PS_podil", "PS podíl")),
                "available": xlsx_bool_v093_(xlsx_pick_v093_(row, "Dostupny", "Dostupný", "Aktivni", default="ANO")),
                "unavailable_reason": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Duvod nedostupnosti", "Důvod nedostupnosti")),
                "is_active": xlsx_bool_v093_(xlsx_pick_v093_(row, "Aktivni", "Aktivní", default="ANO")),
                "note": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Poznamka", "Poznámka")),
            }
            cols = list(data.keys())
            params = data
            sql = f"""
                INSERT INTO specialists ({", ".join(cols)})
                VALUES ({", ".join([":" + c for c in cols])})
                ON CONFLICT (advisor_id, section_code, subsection_code, email)
                DO {"UPDATE SET " + ", ".join([c + "=EXCLUDED." + c for c in cols if c not in ["advisor_id","section_code","subsection_code","email"]]) if update_existing else "NOTHING"}
            """
            created = db.execute(text(sql), params).rowcount or 0
            result["specialists"]["created"] += created
            result["specialists"]["updated_or_skipped"] += 0 if created else 1
        except Exception as exc:
            result["errors"].append(f"Specialisté: {exc}")

    # Import_Partners + Vypovedi_Pojistovny
    for sheet_name in ["Import_Partners", "Vypovedi_Pojistovny"]:
        for row in xlsx_rows_v093_(wb, sheet_name):
            result["partners" if sheet_name == "Import_Partners" else "terminations_partners"]["rows"] += 1
            try:
                code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Partner_ID")).upper()
                name = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Nazev", "Název"))
                if not code or not name:
                    continue
                data = {
                    "partner_code": code,
                    "name": name,
                    "address_full": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Adresa")),
                    "registry_email": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Email_podatelna", "Email", "E-mail")),
                    "data_box": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Datova_schranka", "Datová schránka")),
                    "note": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Poznamka", "Poznámka")),
                    "source": "xlsx_import",
                    "is_active": xlsx_bool_v093_(xlsx_pick_v093_(row, "Aktivni", "Aktivní", default="ANO")),
                }
                created = xlsx_upsert_v093_(db, "partners", "partner_code", data, update_existing)
                key = "partners" if sheet_name == "Import_Partners" else "terminations_partners"
                result[key]["created"] += created
                result[key]["updated_or_skipped"] += 0 if created else 1
            except Exception as exc:
                result["errors"].append(f"{sheet_name}: {exc}")

    # Kontakty
    for row in xlsx_rows_v093_(wb, "Import_Partner_Contacts"):
        result["contacts"]["rows"] += 1
        try:
            code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Partner_ID")).upper()
            name = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Jmeno", "Jméno"))
            role = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Role"))
            if not code or (not name and not role):
                continue
            db.execute(text("""
                INSERT INTO partner_contacts
                (partner_code, full_name, role, phone, email, specialization, territory, is_top, is_vip, note, original_note, is_active)
                VALUES
                (:partner_code, :full_name, :role, :phone, :email, :specialization, :territory, :is_top, :is_vip, :note, :original_note, TRUE)
            """), {
                "partner_code": code,
                "full_name": name or role,
                "role": role,
                "phone": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Telefon")),
                "email": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Email")),
                "specialization": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Specikace", "Specifikace")),
                "territory": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Region")),
                "is_top": xlsx_bool_v093_(xlsx_pick_v093_(row, "TOP")),
                "is_vip": xlsx_bool_v093_(xlsx_pick_v093_(row, "VIP")),
                "note": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Poznamka", "Poznámka")),
                "original_note": "Import_Partner_Contacts",
            })
            result["contacts"]["created"] += 1
        except Exception as exc:
            result["contacts"]["updated_or_skipped"] += 1
            result["errors"].append(f"Kontakty: {exc}")

    # Odkazy partnerů + online kalkulačky + odkazy ASTORIE
    for sheet_name, is_global in [("Import_Partner_Links", False), ("Import_Online kalkulacky_Links", False), ("Import_Astorie_Links", True)]:
        for row in xlsx_rows_v093_(wb, sheet_name):
            result["links"]["rows"] += 1
            try:
                code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Partner_ID", default="ASTORIE")).upper()
                title = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Nazev", "Název"))
                url = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "URL"))
                if is_global and not code:
                    code = "ASTORIE"
                if not code or not title or not url:
                    continue
                db.execute(text("""
                    INSERT INTO partner_links
                    (partner_code, title, url, category, note, visibility, is_active)
                    VALUES
                    (:partner_code, :title, :url, :category, :note, :visibility, TRUE)
                """), {
                    "partner_code": code,
                    "title": title,
                    "url": url,
                    "category": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Typ", "Kategorie")),
                    "note": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Poznamka", "Poznámka")),
                    "visibility": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Viditelnost")),
                })
                result["links"]["created"] += 1
            except Exception as exc:
                result["links"]["updated_or_skipped"] += 1
                result["errors"].append(f"{sheet_name}: {exc}")

    # Produkty
    for row in xlsx_rows_v093_(wb, "Import_Products"):
        result["products"]["rows"] += 1
        try:
            code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Partner_ID")).upper()
            product = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Produkt"))
            if not code or not product:
                continue
            db.execute(text("""
                INSERT INTO partner_products
                (partner_code, area, subarea, product_name, note, risks, client_type, keywords, priority, is_active)
                VALUES
                (:partner_code, :area, :subarea, :product_name, :note, :risks, :client_type, :keywords, :priority, :is_active)
            """), {
                "partner_code": code,
                "area": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Oblast")),
                "subarea": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Podoblast")),
                "product_name": product,
                "note": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Poznamka", "Poznámka")),
                "risks": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Rizika")),
                "client_type": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Typ_klienta")),
                "keywords": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Klicova_slova")),
                "priority": xlsx_num_v093_(xlsx_pick_v093_(row, "Priorita"), 100),
                "is_active": xlsx_bool_v093_(xlsx_pick_v093_(row, "Aktivni", "Aktivní", default="ANO")),
            })
            result["products"]["created"] += 1
        except Exception as exc:
            result["products"]["updated_or_skipped"] += 1
            result["errors"].append(f"Produkty: {exc}")

    # Provize
    for row in xlsx_rows_v093_(wb, "Provize_TIPHub"):
        result["commission_rates"]["rows"] += 1
        try:
            section_code = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID_sekce")).upper()
            partner = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Partner"))
            if not section_code or not partner:
                continue
            db.execute(text("""
                INSERT INTO commission_rates
                (id, section_code, subsection_code, partner_name, base_type, product_type, rate_percent, priority, is_active, business_type, area)
                VALUES
                (:id, :section_code, :subsection_code, :partner_name, :base_type, :product_type, :rate_percent, :priority, TRUE, :business_type, :area)
            """), {
                "id": str(uuid.uuid4()),
                "section_code": section_code,
                "subsection_code": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID_podsekce")).upper(),
                "partner_name": partner,
                "base_type": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Typ_pojistneho")),
                "product_type": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Typ_obchodu")),
                "rate_percent": xlsx_decimal_v093_(xlsx_pick_v093_(row, "Sazba_provize_%")),
                "priority": xlsx_num_v093_(xlsx_pick_v093_(row, "Priorita"), 100),
                "business_type": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Druh obchodu")),
                "area": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Oblast")),
            })
            result["commission_rates"]["created"] += 1
        except Exception as exc:
            result["commission_rates"]["updated_or_skipped"] += 1
            result["errors"].append(f"Provize_TIPHub: {exc}")

    # TIPy
    for row in xlsx_rows_v093_(wb, "Tipy"):
        result["tips"]["rows"] += 1
        try:
            client = xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Jmeno Klienta", "Jméno Klienta"))
            if not client:
                continue
            tip_id = str(uuid.uuid4())
            db.execute(text("""
                INSERT INTO tips
                (id, adviser_original_id, adviser_name, adviser_email,
                 specialist_name, specialist_email, client_name, client_phone, client_identifier,
                 potential_amount, adviser_note, status, policy_no, final_volume, specialist_feedback,
                 section_code, subsection_code, section_name, subsection_name,
                 imported_source, imported_original_id, adviser_last_message, final_report, last_update_at)
                VALUES
                (:id, :adviser_original_id, :adviser_name, :adviser_email,
                 :specialist_name, :specialist_email, :client_name, :client_phone, :client_identifier,
                 :potential_amount, :adviser_note, :status, :policy_no, :final_volume, :specialist_feedback,
                 :section_code, :subsection_code, :section_name, :subsection_name,
                 'xlsx_Aktivni_29032026_ASTORIE_HUB', :imported_original_id, :adviser_last_message, :final_report, now())
            """), {
                "id": tip_id,
                "adviser_original_id": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID Poradce")),
                "adviser_name": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Jmeno Poradce", "Jméno Poradce")),
                "adviser_email": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Email Poradce")).lower(),
                "specialist_name": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Jmeno Specialisty", "Jméno Specialisty")),
                "specialist_email": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Email Specialisty")).lower(),
                "client_name": client,
                "client_phone": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Kontakt Klienta")),
                "client_identifier": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Identifikace RČ IČO Datum nar", "Identifikace (RČ/IČO/Datum nar.)")),
                "potential_amount": xlsx_decimal_v093_(xlsx_pick_v093_(row, "Potencial", "Potenciál")),
                "adviser_note": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Poznamka", "Poznámka")),
                "status": normalize_tip_status_v090_(xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Stav", default="Nový"))),
                "policy_no": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Cislo smlouvy", "Číslo smlouvy")),
                "final_volume": xlsx_decimal_v093_(xlsx_pick_v093_(row, "Vyse obchodu", "Výše obchodu")),
                "specialist_feedback": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Vyjadreni specialisty", "Vyjádření specialisty")),
                "section_code": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID Sekce")).upper(),
                "subsection_code": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "ID Podsekce")).upper(),
                "section_name": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Nazev Sekce", "Název Sekce")),
                "subsection_name": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Nazev Podsekce", "Název Podsekce")),
                "imported_original_id": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Datum vytvoření", "Datum vytvoreni")),
                "adviser_last_message": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Vyjadreni specialisty", "Vyjádření specialisty")),
                "final_report": xlsx_cell_to_str_v093_(xlsx_pick_v093_(row, "Vyjadreni specialisty", "Vyjádření specialisty")),
            })
            result["tips"]["created"] += 1
        except Exception as exc:
            result["tips"]["updated_or_skipped"] += 1
            result["errors"].append(f"Tipy: {exc}")

    db.commit()
    return result


@router.get("/admin/import/hub-xlsx", response_class=HTMLResponse)
def admin_import_hub_xlsx_page_v093(request: Request):
    return render(request, "admin_import_hub_xlsx.html", {
        "active": "import",
        "result": None,
        "version": "0.9.8-import-timestamps-fix",
    })


@router.post("/admin/import/hub-xlsx", response_class=HTMLResponse)
async def admin_import_hub_xlsx_v093(
    request: Request,
    file: UploadFile = File(...),
    update_existing: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        from openpyxl import load_workbook
    except Exception as exc:
        return render(request, "admin_import_hub_xlsx.html", {
            "active": "import",
            "result": {"ok": False, "errors": [f"Chybí knihovna openpyxl: {exc}"]},
            "version": "0.9.8-import-timestamps-fix",
        })

    raw = await file.read()
    try:
        wb = load_workbook(BytesIO(raw), data_only=True, read_only=True)
        result = import_hub_xlsx_data_v093_(db, wb, update_existing=(update_existing == "1"))
        result["ok"] = len(result.get("errors", [])) == 0
        result["mode"] = "update_existing" if update_existing == "1" else "safe_insert_only"
    except Exception as exc:
        result = {"ok": False, "errors": [str(exc)]}

    return render(request, "admin_import_hub_xlsx.html", {
        "active": "import",
        "result": result,
        "version": "0.9.8-import-timestamps-fix",
    })


@router.get("/api/import/hub-xlsx/expected-sheets")
def api_import_hub_xlsx_expected_sheets_v093():
    return {
        "ok": True,
        "version": "0.9.8-import-timestamps-fix",
        "mode_default": "safe_insert_only",
        "sheets": [
            "Poradci",
            "Sekce",
            "Podsekce",
            "Specialisté",
            "Import_Partners",
            "Vypovedi_Pojistovny",
            "Import_Partner_Contacts",
            "Import_Partner_Links",
            "Import_Online kalkulacky_Links",
            "Import_Astorie_Links",
            "Import_Products",
            "Provize_TIPHub",
            "Tipy",
        ],
        "note": "Importer nemění původní Google Sheet. Načítá XLSX do nové databáze aplikace.",
    }



# -------------------------------------------------------------------
# v0.9.8 import hardening endpoints
# - chybějící /api/admin/summary
# - aliasy pro import route
# - JSON upload endpoint
# - bezpečné počty tabulek
# -------------------------------------------------------------------

def safe_count_table_v094_(db: Session, table_name: str):
    try:
        exists = db.execute(text("""
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema = 'public'
                AND table_name = :table_name
            )
        """), {"table_name": table_name}).scalar()
        if not exists:
            return {"exists": False, "count": 0, "error": None}
        count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        return {"exists": True, "count": int(count or 0), "error": None}
    except Exception as exc:
        return {"exists": False, "count": 0, "error": str(exc)}


@router.get("/api/admin/summary")
def api_admin_summary_v094(db: Session = Depends(get_db)):
    """
    Stabilní kontrolní endpoint pro BO a testování migrace.
    Vrací počty hlavních tabulek, aby bylo po importu jasně vidět, zda data přibyla.
    """
    # vytvoří/rozšíří struktury, ale nemaže data
    try:
        ensure_xlsx_import_structures_v093_(db)
    except Exception:
        try:
            ensure_tip_workflow_v090_(db)
        except Exception:
            pass

    tables = [
        "users",
        "roles",
        "app_settings",
        "sections",
        "subsections",
        "hub_sections",
        "hub_subsections",
        "specialists",
        "partners",
        "partner_contacts",
        "partner_links",
        "partner_products",
        "commission_rates",
        "tips",
        "tip_updates",
        "import_jobs",
        "audit_log",
    ]
    return {
        "ok": True,
        "version": "0.9.8-import-timestamps-fix",
        "message": "Admin summary endpoint běží. Počty jsou čtené bezpečně přes PostgreSQL.",
        "counts": {t: safe_count_table_v094_(db, t) for t in tables},
    }


@router.get("/api/import/hub-xlsx/status")
def api_import_hub_xlsx_status_v094(db: Session = Depends(get_db)):
    """
    Zatím synchronní import: endpoint vrací poslední stav podle import_jobs.
    Plnohodnotný async progress bude další krok, až bude ověřen základní import.
    """
    try:
        ensure_tip_workflow_v090_(db)
        last_job = fetch_one_safe_v084_(db, """
            SELECT *
            FROM import_jobs
            ORDER BY created_at DESC
            LIMIT 1
        """)
        return {
            "ok": True,
            "version": "0.9.8-import-timestamps-fix",
            "running": False,
            "last_job": dict(last_job) if last_job else None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "version": "0.9.8-import-timestamps-fix",
            "running": False,
            "error": str(exc),
        }


@router.post("/api/import/hub-xlsx")
async def api_import_hub_xlsx_upload_v094(
    file: UploadFile = File(...),
    update_existing: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    JSON varianta importu pro budoucí AJAX/frontend.
    Používá stejný importní engine jako HTML stránka.
    """
    try:
        from openpyxl import load_workbook
        raw = await file.read()
        wb = load_workbook(BytesIO(raw), data_only=True, read_only=True)
        result = import_hub_xlsx_data_v093_(db, wb, update_existing=(update_existing == "1"))
        result["ok"] = len(result.get("errors", [])) == 0
        result["mode"] = "update_existing" if update_existing == "1" else "safe_insert_only"
        result["version"] = "0.9.8-import-timestamps-fix"
        return result
    except Exception as exc:
        return {
            "ok": False,
            "version": "0.9.8-import-timestamps-fix",
            "errors": [str(exc)],
        }


# Alias, kdyby někde frontend / uživatel použil jiný název.
@router.get("/admin/import/hub-xlsx/")
def admin_import_hub_xlsx_slash_alias_v094(request: Request):
    return RedirectResponse("/admin/import/hub-xlsx", status_code=307)


@router.post("/admin/import/hub-xlsx/")
async def admin_import_hub_xlsx_post_slash_alias_v094(
    request: Request,
    file: UploadFile = File(...),
    update_existing: str = Form(""),
    db: Session = Depends(get_db),
):
    return await admin_import_hub_xlsx_v093(
        request=request,
        file=file,
        update_existing=update_existing,
        db=db,
    )


@router.get("/admin/import/xlsx")
def admin_import_xlsx_short_alias_v094():
    return RedirectResponse("/admin/import/hub-xlsx", status_code=307)


@router.get("/api/import/hub-xlsx/summary")
def api_import_hub_xlsx_summary_alias_v094(db: Session = Depends(get_db)):
    return api_admin_summary_v094(db=db)





# -------------------------------------------------------------------
# v0.9.8 import transaction fix
# Oprava: current transaction is aborted před CREATE UNIQUE INDEX
# -------------------------------------------------------------------

def ensure_specialists_table_columns_v095_(db):
    """
    Starší DB může mít tabulku specialists založenou s jinou strukturou.
    Importér potřebuje tyto sloupce. Každý ALTER je chráněný rollbackem,
    aby jedna chyba neshodila celou transakci.
    """
    try:
        ensure_specialists_table_(db)
        db.commit()
    except Exception:
        db.rollback()

    statements = [
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS advisor_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS specialist_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS email TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS phone TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS section_code TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS subsection_code TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS role_description TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS region TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS if_share TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS ps_share TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS available BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS unavailable_reason TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS note TEXT NOT NULL DEFAULT ''",
    ]

    for stmt in statements:
        try:
            db.execute(text(stmt))
            db.commit()
        except Exception:
            db.rollback()

    try:
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_specialists_import_key
            ON specialists (advisor_id, section_code, subsection_code, email)
        """))
        db.commit()
    except Exception:
        db.rollback()


def ensure_xlsx_import_structures_v095_(db):
    """
    Robustní verze přípravy struktur pro XLSX import.
    Každý blok se commituje/rollbackuje samostatně, aby PostgreSQL nezůstal
    ve stavu InFailedSqlTransaction.
    """
    for fn in [ensure_tip_workflow_v090_, ensure_visible_hub_sections_, ensure_specialists_table_columns_v095_]:
        try:
            fn(db)
            db.commit()
        except Exception:
            db.rollback()

    statements = [
        "ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS risks TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS client_type TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS keywords TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100",
        "ALTER TABLE partner_links ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE partner_contacts ADD COLUMN IF NOT EXISTS original_note TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE commission_rates ADD COLUMN IF NOT EXISTS business_type TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE commission_rates ADD COLUMN IF NOT EXISTS area TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS final_volume NUMERIC",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS specialist_feedback TEXT NOT NULL DEFAULT ''",
    ]
    for stmt in statements:
        try:
            db.execute(text(stmt))
            db.commit()
        except Exception:
            db.rollback()


# Přesměrování původní funkce na robustní verzi.
ensure_xlsx_import_structures_v093_ = ensure_xlsx_import_structures_v095_





# -------------------------------------------------------------------
# v0.9.8 import index fix
# Definitivní oprava: odstranění inline CREATE UNIQUE INDEX z importní transakce
# a bezpečné čištění transakce před vlastním importem.
# -------------------------------------------------------------------

def db_safe_exec_v096_(db: Session, sql: str, params: dict | None = None):
    try:
        db.rollback()
    except Exception:
        pass
    try:
        db.execute(text(sql), params or {})
        db.commit()
        return True, None
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        return False, str(exc)


def ensure_specialists_import_schema_v096_(db: Session):
    """
    Tato funkce nesmí shodit import. Každý SQL příkaz běží odděleně.
    """
    try:
        ensure_specialists_table_(db)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    stmts = [
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS advisor_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS specialist_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS email TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS phone TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS section_code TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS subsection_code TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS role_description TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS region TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS if_share TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS ps_share TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS available BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS unavailable_reason TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE specialists ADD COLUMN IF NOT EXISTS note TEXT NOT NULL DEFAULT ''",
    ]

    errors = []
    for stmt in stmts:
        ok, err = db_safe_exec_v096_(db, stmt)
        if err:
            errors.append(err)

    # Index je užitečný, ale nesmí zablokovat import. Pokud nejde vytvořit, import pokračuje bez něj.
    ok, err = db_safe_exec_v096_(db, """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_specialists_import_key
        ON specialists (advisor_id, section_code, subsection_code, email)
    """)
    if err:
        errors.append("Index specialists přeskočen: " + err)

    try:
        db.rollback()
    except Exception:
        pass
    return errors


def ensure_xlsx_import_structures_v096_(db: Session):
    errors = []

    for fn in [ensure_tip_workflow_v090_, ensure_visible_hub_sections_]:
        try:
            db.rollback()
        except Exception:
            pass
        try:
            fn(db)
            db.commit()
        except Exception as exc:
            errors.append(str(exc))
            try:
                db.rollback()
            except Exception:
                pass

    errors.extend(ensure_specialists_import_schema_v096_(db))

    stmts = [
        "ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS risks TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS client_type TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS keywords TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE partner_products ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100",
        "ALTER TABLE partner_links ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE partner_contacts ADD COLUMN IF NOT EXISTS original_note TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE commission_rates ADD COLUMN IF NOT EXISTS business_type TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE commission_rates ADD COLUMN IF NOT EXISTS area TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS final_volume NUMERIC",
        "ALTER TABLE tips ADD COLUMN IF NOT EXISTS specialist_feedback TEXT NOT NULL DEFAULT ''",
    ]
    for stmt in stmts:
        ok, err = db_safe_exec_v096_(db, stmt)
        if err:
            errors.append(err)

    try:
        db.rollback()
    except Exception:
        pass
    return errors


_original_import_hub_xlsx_data_v093_v096 = import_hub_xlsx_data_v093_

def import_hub_xlsx_data_v096_(db, wb, update_existing=False):
    prep_errors = ensure_xlsx_import_structures_v096_(db)
    try:
        db.rollback()
    except Exception:
        pass

    result = _original_import_hub_xlsx_data_v093_v096(db, wb, update_existing=update_existing)

    # Nepovažovat přeskočený index za fatální chybu importu.
    non_fatal = []
    fatal = []
    for e in prep_errors:
        if "Index specialists přeskočen" in str(e):
            non_fatal.append(e)
        else:
            fatal.append(e)

    if non_fatal:
        result.setdefault("warnings", []).extend(non_fatal)
    if fatal:
        result.setdefault("errors", []).extend(fatal)
    return result


# Přesměrování všech importů na opravený engine.
import_hub_xlsx_data_v093_ = import_hub_xlsx_data_v096_
ensure_xlsx_import_structures_v093_ = ensure_xlsx_import_structures_v096_

@router.get("/api/import/hub-xlsx/repair-schema")
def api_import_repair_schema_v096(db: Session = Depends(get_db)):
    errors = ensure_xlsx_import_structures_v096_(db)
    return {
        "ok": len(errors) == 0,
        "version": "0.9.8-import-timestamps-fix",
        "message": "Importní struktury byly zkontrolovány a opraveny. Původní Google Sheet se nemění.",
        "errors": errors,
    }





# -------------------------------------------------------------------
# v0.9.8 import user id fix
# Oprava: users.id nemá serverový default a raw SQL insert bez id padal.
# -------------------------------------------------------------------

def repair_uuid_defaults_v097_(db: Session):
    """
    Doplní serverový DEFAULT gen_random_uuid() pro UUID id sloupce.
    Je to pojistka; import zároveň posílá id explicitně.
    """
    errors = []
    try:
        db.rollback()
    except Exception:
        pass

    db_safe_exec_v096_(db, "CREATE EXTENSION IF NOT EXISTS pgcrypto")
    for table in ["users", "roles", "app_settings", "sections", "subsections", "partners", "tips", "commission_rates", "audit_log"]:
        ok, err = db_safe_exec_v096_(db, f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT gen_random_uuid()")
        if err:
            errors.append(f"{table}.id default: {err}")
    try:
        db.rollback()
    except Exception:
        pass
    return errors


_previous_ensure_xlsx_import_structures_v093_v097 = ensure_xlsx_import_structures_v093_

def ensure_xlsx_import_structures_v097_(db: Session):
    errors = []
    try:
        repair_uuid_defaults_v097_(db)
    except Exception as exc:
        errors.append(str(exc))
    try:
        rv = _previous_ensure_xlsx_import_structures_v093_v097(db)
        if isinstance(rv, list):
            errors.extend(rv)
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        errors.append(str(exc))
    return errors


ensure_xlsx_import_structures_v093_ = ensure_xlsx_import_structures_v097_

@router.get("/api/import/hub-xlsx/repair-users")
def api_import_repair_users_v097(db: Session = Depends(get_db)):
    errors = repair_uuid_defaults_v097_(db)
    return {
        "ok": len(errors) == 0,
        "version": "0.9.8-import-timestamps-fix",
        "message": "Opraveny UUID defaulty pro users a další hlavní tabulky. Import zároveň posílá id explicitně.",
        "errors": errors,
    }




# -------------------------------------------------------------------
# v0.9.8 import timestamps fix
# Oprava: users.created_at / users.updated_at NOT NULL při importu poradců
# -------------------------------------------------------------------

def repair_users_timestamps_v098_(db: Session):
    errors = []
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
        "UPDATE users SET created_at = NOW() WHERE created_at IS NULL",
        "UPDATE users SET updated_at = NOW() WHERE updated_at IS NULL",
        "ALTER TABLE users ALTER COLUMN created_at SET DEFAULT NOW()",
        "ALTER TABLE users ALTER COLUMN updated_at SET DEFAULT NOW()",
    ]
    for stmt in statements:
        try:
            db.rollback()
        except Exception:
            pass
        try:
            db.execute(text(stmt))
            db.commit()
        except Exception as exc:
            errors.append(str(exc))
            try:
                db.rollback()
            except Exception:
                pass
    return errors


@router.get("/api/import/hub-xlsx/repair-users-timestamps")
def api_import_repair_users_timestamps_v098(db: Session = Depends(get_db)):
    errors = repair_users_timestamps_v098_(db)
    return {
        "ok": len(errors) == 0,
        "version": "0.9.8-import-timestamps-fix",
        "message": "Opraveny created_at/updated_at defaulty pro users. Import poradců nyní posílá timestampy explicitně.",
        "errors": errors,
    }

