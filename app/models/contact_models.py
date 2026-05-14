from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class PartnerContact(Base):
    __tablename__ = "partner_contacts"

    id = Column(Integer, primary_key=True)
    partner_code = Column(String(50), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(255))
    email = Column(String(255))
    phone = Column(String(100))
    specialization = Column(String(255))
    note = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PartnerLink(Base):
    __tablename__ = "partner_links"

    id = Column(Integer, primary_key=True)
    partner_code = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    category = Column(String(100))
    note = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PartnerProduct(Base):
    __tablename__ = "partner_products"

    id = Column(Integer, primary_key=True)
    partner_code = Column(String(50), nullable=False, index=True)
    area = Column(String(255))
    subarea = Column(String(255))
    product_name = Column(String(255), nullable=False)
    note = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
