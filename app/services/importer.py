import csv
import io
from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

from app.models.core_models import Partner, Section, Subsection, User, AuditLog
from app.services.passwords import hash_password


def norm_key(value: str) -> str:
    value = (value or "").strip().lower()
    replace_map = {
        "á": "a", "č": "c", "ď": "d", "é": "e", "ě": "e", "í": "i",
        "ň": "n", "ó": "o", "ř": "r", "š": "s", "ť": "t", "ú": "u",
        "ů": "u", "ý": "y", "ž": "z",
    }
    for old, new in replace_map.items():
        value = value.replace(old, new)
    for ch in [" ", "-", ".", "/", "\\", "(", ")", "[", "]"]:
        value = value.replace(ch, "_")
    while "__" in value:
        value = value.replace("__", "_")
    return value.strip("_")


def pick(row: dict, *names: str, default: str = "") -> str:
    for name in names:
        key = norm_key(name)
        if key in row and row[key] not in (None, ""):
            return str(row[key]).strip()
    return default


def is_yes(value: str) -> bool:
    return str(value or "").strip().lower() in {"ano", "a", "true", "1", "yes", "aktivni", "aktivní"}


def parse_csv_bytes(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8-sig", errors="replace")

    # Detekce oddělovače: český export často používá středník.
    sample = text[:4000]
    delimiter = ";"
    if sample.count(",") > sample.count(";"):
        delimiter = ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = []
    for src_row in reader:
        normalized = {norm_key(k): (v or "").strip() for k, v in (src_row or {}).items()}
        if any(normalized.values()):
            rows.append(normalized)
    return rows


@dataclass
class ImportResult:
    ok: bool
    entity: str
    total_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] | None = None

    def as_dict(self):
        return {
            "ok": self.ok,
            "entity": self.entity,
            "total_rows": self.total_rows,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors or [],
        }


def write_import_audit(db: Session, entity: str, result: ImportResult) -> None:
    try:
        db.add(AuditLog(
            user_email="admin@astorie.local",
            action="IMPORT",
            entity_type=entity,
            new_value=result.as_dict(),
        ))
        db.commit()
    except Exception:
        db.rollback()


def import_users(db: Session, raw: bytes) -> ImportResult:
    rows = parse_csv_bytes(raw)
    result = ImportResult(ok=True, entity="users", total_rows=len(rows), errors=[])

    for idx, row in enumerate(rows, start=2):
        try:
            advisor_id = pick(row, "ID_poradce", "ID", "Poradce_ID", "id_poradce")
            email = pick(row, "Email", "E-mail", "Mail")
            name = pick(row, "Jmeno", "Jméno", "Name", "Poradce")
            phone = pick(row, "Telefon", "Tel", "Phone")
            role = pick(row, "Role", "Funkce", default="IF").upper()
            password = pick(row, "Heslo", "PIN", "Password", default="1234")
            active_raw = pick(row, "Aktivni", "Aktivní", "Active", default="ANO")

            if not advisor_id or not email or not name:
                result.skipped += 1
                result.errors.append(f"Řádek {idx}: chybí ID, e-mail nebo jméno.")
                continue

            existing = db.query(User).filter(User.advisor_id == advisor_id).first()
            if not existing:
                existing = db.query(User).filter(User.email == email.lower()).first()

            if existing:
                existing.name = name
                existing.email = email.lower()
                existing.phone = phone
                existing.role = role or "IF"
                existing.is_active = is_yes(active_raw)
                result.updated += 1
            else:
                db.add(User(
                    advisor_id=advisor_id,
                    name=name,
                    email=email.lower(),
                    phone=phone,
                    role=role or "IF",
                    password_hash=hash_password(password),
                    is_active=is_yes(active_raw),
                    must_change_password=True,
                ))
                result.created += 1
        except Exception as exc:
            result.skipped += 1
            result.errors.append(f"Řádek {idx}: {exc}")

    db.commit()
    write_import_audit(db, "users", result)
    return result


def import_sections(db: Session, raw: bytes) -> ImportResult:
    rows = parse_csv_bytes(raw)
    result = ImportResult(ok=True, entity="sections", total_rows=len(rows), errors=[])

    for idx, row in enumerate(rows, start=2):
        try:
            code = pick(row, "Sekce_ID", "ID", "Kod", "Kód", "section_code", "sekce")
            name = pick(row, "Nazev", "Název", "Name", "Sekce_nazev", "Sekce název")
            icon = pick(row, "Ikona", "Icon")
            order_raw = pick(row, "Poradi", "Pořadí", "Sort", "sort_order", default="0")
            active_raw = pick(row, "Aktivni", "Aktivní", default="ANO")

            if not code or not name:
                result.skipped += 1
                result.errors.append(f"Řádek {idx}: chybí kód nebo název sekce.")
                continue

            item = db.query(Section).filter(Section.section_code == code.upper()).first()
            if item:
                item.name = name
                item.icon = icon
                item.sort_order = int(order_raw or 0)
                item.is_active = is_yes(active_raw)
                result.updated += 1
            else:
                db.add(Section(
                    section_code=code.upper(),
                    name=name,
                    icon=icon,
                    sort_order=int(order_raw or 0),
                    is_active=is_yes(active_raw),
                ))
                result.created += 1
        except Exception as exc:
            result.skipped += 1
            result.errors.append(f"Řádek {idx}: {exc}")

    db.commit()
    write_import_audit(db, "sections", result)
    return result


def import_subsections(db: Session, raw: bytes) -> ImportResult:
    rows = parse_csv_bytes(raw)
    result = ImportResult(ok=True, entity="subsections", total_rows=len(rows), errors=[])

    for idx, row in enumerate(rows, start=2):
        try:
            code = pick(row, "Podsekce_ID", "ID", "Kod", "Kód", "subsection_code", "podsekce")
            section_code = pick(row, "Sekce_ID", "Sekce", "section_code")
            name = pick(row, "Nazev", "Název", "Name", "Podsekce_nazev", "Podsekce název")
            order_raw = pick(row, "Poradi", "Pořadí", "Sort", "sort_order", default="0")
            active_raw = pick(row, "Aktivni", "Aktivní", default="ANO")

            if not code or not section_code or not name:
                result.skipped += 1
                result.errors.append(f"Řádek {idx}: chybí kód podsekce, sekce nebo název.")
                continue

            item = db.query(Subsection).filter(Subsection.subsection_code == code.upper()).first()
            if item:
                item.section_code = section_code.upper()
                item.name = name
                item.sort_order = int(order_raw or 0)
                item.is_active = is_yes(active_raw)
                result.updated += 1
            else:
                db.add(Subsection(
                    subsection_code=code.upper(),
                    section_code=section_code.upper(),
                    name=name,
                    sort_order=int(order_raw or 0),
                    is_active=is_yes(active_raw),
                ))
                result.created += 1
        except Exception as exc:
            result.skipped += 1
            result.errors.append(f"Řádek {idx}: {exc}")

    db.commit()
    write_import_audit(db, "subsections", result)
    return result


def import_partners(db: Session, raw: bytes) -> ImportResult:
    rows = parse_csv_bytes(raw)
    result = ImportResult(ok=True, entity="partners", total_rows=len(rows), errors=[])

    for idx, row in enumerate(rows, start=2):
        try:
            code = pick(row, "Partner_ID", "ID", "Kod", "Kód", "partner_code")
            name = pick(row, "Nazev", "Název", "Name", "Partner", "Partner_nazev")
            note = pick(row, "Poznamka", "Poznámka", "Note")
            active_raw = pick(row, "Aktivni", "Aktivní", "Active", default="ANO")

            if not code or not name:
                result.skipped += 1
                result.errors.append(f"Řádek {idx}: chybí ID partnera nebo název.")
                continue

            item = db.query(Partner).filter(Partner.partner_code == code.upper()).first()
            if item:
                item.name = name
                item.note = note
                item.is_active = is_yes(active_raw)
                result.updated += 1
            else:
                db.add(Partner(
                    partner_code=code.upper(),
                    name=name,
                    note=note,
                    is_active=is_yes(active_raw),
                ))
                result.created += 1
        except Exception as exc:
            result.skipped += 1
            result.errors.append(f"Řádek {idx}: {exc}")

    db.commit()
    write_import_audit(db, "partners", result)
    return result


IMPORT_HANDLERS: dict[str, Callable[[Session, bytes], ImportResult]] = {
    "users": import_users,
    "sections": import_sections,
    "subsections": import_subsections,
    "partners": import_partners,
}
