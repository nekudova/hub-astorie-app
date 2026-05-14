from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.models.core_models import AppSetting, Role, User
from app.services.passwords import hash_password


def seed_initial_data(db: Session) -> None:
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
            password_hash=hash_password("ChangeMe2026!"),
            is_active=True,
            must_change_password=True,
        ))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
