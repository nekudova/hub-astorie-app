import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(120), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class Role(Base):
    __tablename__ = "roles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    is_system = Column(Boolean, default=False, nullable=False)


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advisor_id = Column(String(80), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(80))
    role = Column(String(120), default="IF", nullable=False)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class Section(Base):
    __tablename__ = "sections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_code = Column(String(80), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    icon = Column(String(80))
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class Subsection(Base):
    __tablename__ = "subsections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subsection_code = Column(String(80), unique=True, nullable=False)
    section_code = Column(String(80), nullable=False)
    name = Column(String(255), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class Partner(Base):
    __tablename__ = "partners"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_code = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    ico = Column(String(20), index=True)
    dic = Column(String(30))
    data_box = Column(String(50))
    registry_email = Column(String(255))
    street = Column(String(255))
    city = Column(String(120))
    zip_code = Column(String(20))
    address_full = Column(Text)
    legal_form = Column(String(255))
    source = Column(String(80), default="manual")
    note = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)


class Tip(Base):
    __tablename__ = "tips"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    adviser_original_id = Column(String(80))
    adviser_name = Column(String(255))
    adviser_email = Column(String(255))
    specialist_name = Column(String(255))
    specialist_email = Column(String(255))
    client_name = Column(String(255), nullable=False)
    client_phone = Column(String(100))
    client_identifier = Column(String(100))
    potential_amount = Column(Numeric(14, 2))
    adviser_note = Column(Text)
    status = Column(String(50), default="Nový", nullable=False)
    policy_no = Column(String(150))
    final_volume = Column(Numeric(14, 2))
    specialist_feedback = Column(Text)


class CommissionRate(Base):
    __tablename__ = "commission_rates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_code = Column(String(80))
    subsection_code = Column(String(80))
    partner_name = Column(String(255), nullable=False)
    base_type = Column(String(150))
    product_type = Column(String(255))
    rate_percent = Column(Numeric(8, 4))
    priority = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    user_email = Column(String(255))
    action = Column(String(120), nullable=False)
    entity_type = Column(String(120), nullable=False)
    old_value = Column(JSONB)
    new_value = Column(JSONB)
