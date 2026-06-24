import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    company_name = Column(String, nullable=True)
    gst_in = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    invoices = relationship("Invoice", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("GSTReport", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_number = Column(String, index=True, nullable=True)
    invoice_date = Column(String, nullable=True)
    po_number = Column(String, nullable=True)
    merchant_name = Column(String, index=True, nullable=True)
    merchant_address = Column(Text, nullable=True)
    file_url = Column(String, nullable=True)
    taxable_amount = Column(Float, default=0.0)
    cgst = Column(Float, default=0.0)
    sgst = Column(Float, default=0.0)
    igst = Column(Float, default=0.0)
    total_gst = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    validation_status = Column(String, default="PENDING")  # VALID, INVALID, SUSPICIOUS, PENDING
    validation_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="invoices")
    fields = relationship("InvoiceField", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceField(Base):
    __tablename__ = "invoice_fields"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    field_name = Column(String, nullable=False)
    extracted_value = Column(String, nullable=True)
    confidence = Column(Float, default=0.0)
    bbox = Column(JSON, nullable=True)  # [x1, y1, x2, y2] bounding box coordinates

    invoice = relationship("Invoice", back_populates="fields")

class GSTReport(Base):
    __tablename__ = "gst_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_name = Column(String, nullable=False)
    report_type = Column(String, nullable=False)  # PDF, CSV, EXCEL
    file_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="reports")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)

    user = relationship("User", back_populates="audit_logs")
