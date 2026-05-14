import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

class AppSetting(Base):
    __tablename__ = "app_settings"
    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    advisor_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class Section(Base):
    __tablename__ = "sections"
    id: Mapped[uuid.UUID] = uuid_pk()
    section_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(80))
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class Subsection(Base):
    __tablename__ = "subsections"
    id: Mapped[uuid.UUID] = uuid_pk()
    subsection_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    section_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sections.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class Partner(Base):
    __tablename__ = "partners"
    id: Mapped[uuid.UUID] = uuid_pk()
    partner_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class Tip(Base):
    __tablename__ = "tips"
    id: Mapped[uuid.UUID] = uuid_pk()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    adviser_original_id: Mapped[str | None] = mapped_column(String(80))
    adviser_name: Mapped[str | None] = mapped_column(String(255))
    adviser_email: Mapped[str | None] = mapped_column(String(255))
    specialist_name: Mapped[str | None] = mapped_column(String(255))
    specialist_email: Mapped[str | None] = mapped_column(String(255))
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_phone: Mapped[str | None] = mapped_column(String(100))
    client_identifier: Mapped[str | None] = mapped_column(String(100))
    potential_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    adviser_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="Nový", nullable=False)
    policy_no: Mapped[str | None] = mapped_column(String(150))
    final_volume: Mapped[float | None] = mapped_column(Numeric(14, 2))
    specialist_feedback: Mapped[str | None] = mapped_column(Text)

class CommissionRate(Base):
    __tablename__ = "commission_rates"
    id: Mapped[uuid.UUID] = uuid_pk()
    section_code: Mapped[str | None] = mapped_column(String(80))
    subsection_code: Mapped[str | None] = mapped_column(String(80))
    partner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_type: Mapped[str | None] = mapped_column(String(150))
    product_type: Mapped[str | None] = mapped_column(String(255))
    rate_percent: Mapped[float | None] = mapped_column(Numeric(8, 4))
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[uuid.UUID] = uuid_pk()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    user_email: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)
