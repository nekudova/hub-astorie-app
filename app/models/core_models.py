import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(120), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advisor_id = Column(String(80), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(80), nullable=True)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class Section(Base):
    __tablename__ = "sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_code = Column(String(80), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    icon = Column(String(80), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class Subsection(Base):
    __tablename__ = "subsections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subsection_code = Column(String(80), unique=True, nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.id"), nullable=False)
    name = Column(String(255), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class Partner(Base):
    __tablename__ = "partners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_code = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    note = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class Tip(Base):
    __tablename__ = "tips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    adviser_original_id = Column(String(80), nullable=True)
    adviser_name = Column(String(255), nullable=True)
    adviser_email = Column(String(255), nullable=True)

    specialist_name = Column(String(255), nullable=True)
    specialist_email = Column(String(255), nullable=True)

    client_name = Column(String(255), nullable=False)
    client_phone = Column(String(100), nullable=True)
    client_identifier = Column(String(100), nullable=True)

    potential_amount = Column(Numeric(14, 2), nullable=True)
    adviser_note = Column(Text, nullable=True)

    status = Column(String(50), default="Nový", nullable=False)
    policy_no = Column(String(150), nullable=True)
    final_volume = Column(Numeric(14, 2), nullable=True)
    specialist_feedback = Column(Text, nullable=True)


class CommissionRate(Base):
    __tablename__ = "commission_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_code = Column(String(80), nullable=True)
    subsection_code = Column(String(80), nullable=True)
    partner_name = Column(String(255), nullable=False)
    base_type = Column(String(150), nullable=True)
    product_type = Column(String(255), nullable=True)
    rate_percent = Column(Numeric(8, 4), nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    user_email = Column(String(255), nullable=True)
    action = Column(String(120), nullable=False)
    entity_type = Column(String(120), nullable=False)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
