from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.core_models import AppSetting, Role, User, Section, Subsection, Partner
from app.services.passwords import hash_password


def ensure_schema_compatibility(db: Session) -> None:
    # Bezpečné doplnění sloupců, pokud databáze vznikla ze starší ZIP verze.
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(120) DEFAULT 'IF' NOT NULL",
        "ALTER TABLE subsections ADD COLUMN IF NOT EXISTS section_code VARCHAR(80)",
        "UPDATE subsections SET section_code = subsection_code WHERE section_code IS NULL",
    ]
    for sql in statements:
        try:
            db.execute(text(sql))
            db.commit()
        except Exception:
            db.rollback()


def write_audit(db: Session, action: str, entity_type: str, new_value: dict | None = None, user_email: str = "system") -> None:
    try:
        from app.models.core_models import AuditLog
        db.add(AuditLog(user_email=user_email, action=action, entity_type=entity_type, new_value=new_value or {}))
        db.commit()
    except Exception:
        db.rollback()


def seed_initial_data(db: Session) -> None:
    ensure_schema_compatibility(db)

    roles = [
        ("ADMIN", "Administrátor", "Plná správa systému"),
        ("BO", "Backoffice", "Správa dat a provozu"),
        ("IF", "Poradce", "Zadávání a sledování TIPů"),
        ("SPECIALISTA", "Specialista", "Zpracování přidělených TIPů"),
        ("VEDENI", "Vedení", "Manažerské přehledy"),
    ]

    for code, name, description in roles:
        if not db.query(Role).filter(Role.code == code).first():
            db.add(Role(code=code, name=name, description=description, is_system=True))

    settings_rows = [
        ("APP_NAME", settings.app_name, "Název aplikace"),
        ("BRAND_COLOR_PRIMARY", settings.brand_primary, "Primární barva ASTORIE"),
        ("BRAND_COLOR_SECONDARY", settings.brand_secondary, "Sekundární barva ASTORIE"),
        ("BRAND_COLOR_ORANGE", settings.brand_orange, "Oranžová ASTORIE"),
    ]

    for key, value, description in settings_rows:
        if not db.query(AppSetting).filter(AppSetting.key == key).first():
            db.add(AppSetting(key=key, value=value, description=description))

    if not db.query(User).filter(User.email == "admin@astorie.local").first():
        db.add(User(
            advisor_id="ADMIN",
            name="Technický administrátor",
            email="admin@astorie.local",
            phone="",
            role="ADMIN",
            password_hash=hash_password("ChangeMe2026!"),
            is_active=True,
            must_change_password=True,
        ))

    # Jemné demo položky pro první admin UI, pokud DB zatím nemá žádná data.
    if db.query(Section).count() == 0:
        demo_sections = [
            ("FLOTILY", "Flotily", "🚗", 10),
            ("MAJETEK", "Majetek", "🏡", 20),
            ("ZIVOT", "Život", "❤️", 30),
            ("PENZE", "Penze", "💼", 40),
            ("UVERY", "Úvěry", "🏦", 50),
        ]
        for code, name, icon, order in demo_sections:
            db.add(Section(section_code=code, name=name, icon=icon, sort_order=order, is_active=True))

    if db.query(Subsection).count() == 0:
        demo_subsections = [
            ("FLOTILY_FIREMNI", "FLOTILY", "Firemní flotily", 10),
            ("AUTODOPRAVCI", "FLOTILY", "Autodopravci", 20),
            ("DPS", "PENZE", "Doplňkové penzijní spoření", 10),
        ]
        for code, section_code, name, order in demo_subsections:
            db.add(Subsection(subsection_code=code, section_code=section_code, name=name, sort_order=order, is_active=True))

    if db.query(Partner).count() == 0:
        demo_partners = [
            ("KOOP", "Kooperativa pojišťovna, a.s.", "Importováno jako vzorová položka."),
            ("ALLIANZ", "Allianz pojišťovna, a.s.", "Importováno jako vzorová položka."),
            ("CPP", "Česká podnikatelská pojišťovna, a.s.", "Importováno jako vzorová položka."),
        ]
        for code, name, note in demo_partners:
            db.add(Partner(partner_code=code, name=name, note=note, is_active=True))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
