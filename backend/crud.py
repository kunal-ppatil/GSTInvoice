from sqlalchemy.orm import Session
from sqlalchemy import extract
from . import models, schemas
import datetime

# --- User CRUD ---
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        company_name=user.company_name,
        gst_in=user.gst_in
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate, hashed_password: str = None):
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    if user_update.company_name is not None:
        db_user.company_name = user_update.company_name
    if user_update.gst_in is not None:
        db_user.gst_in = user_update.gst_in
    if hashed_password:
        db_user.hashed_password = hashed_password
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Invoice CRUD ---
def create_invoice(db: Session, invoice: schemas.InvoiceCreate, user_id: int):
    db_invoice = models.Invoice(
        user_id=user_id,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        po_number=invoice.po_number,
        merchant_name=invoice.merchant_name,
        merchant_address=invoice.merchant_address,
        file_url=invoice.file_url,
        taxable_amount=invoice.taxable_amount,
        cgst=invoice.cgst,
        sgst=invoice.sgst,
        igst=invoice.igst,
        total_gst=invoice.total_gst,
        total_amount=invoice.total_amount,
        validation_status=invoice.validation_status,
        validation_details=invoice.validation_details
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def get_invoices(db: Session, user_id: int, search: str = None, date_filter: str = None, status: str = None):
    query = db.query(models.Invoice).filter(models.Invoice.user_id == user_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.Invoice.invoice_number.ilike(search_pattern)) |
            (models.Invoice.merchant_name.ilike(search_pattern))
        )
    
    if status:
        query = query.filter(models.Invoice.validation_status == status)

    now = datetime.datetime.utcnow()
    if date_filter == "this_month":
        query = query.filter(
            extract('year', models.Invoice.created_at) == now.year,
            extract('month', models.Invoice.created_at) == now.month
        )
    elif date_filter == "last_month":
        last_month = now.replace(day=1) - datetime.timedelta(days=1)
        query = query.filter(
            extract('year', models.Invoice.created_at) == last_month.year,
            extract('month', models.Invoice.created_at) == last_month.month
        )
    
    return query.order_by(models.Invoice.created_at.desc()).all()

def get_invoice(db: Session, invoice_id: int, user_id: int):
    return db.query(models.Invoice).filter(models.Invoice.id == invoice_id, models.Invoice.user_id == user_id).first()

def update_invoice(db: Session, invoice_id: int, invoice_update: schemas.InvoiceUpdate, user_id: int):
    db_invoice = get_invoice(db, invoice_id, user_id)
    if not db_invoice:
        return None
    
    update_data = invoice_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_invoice, key, value)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def delete_invoice(db: Session, invoice_id: int, user_id: int):
    db_invoice = get_invoice(db, invoice_id, user_id)
    if not db_invoice:
        return False
    db.delete(db_invoice)
    db.commit()
    return True

# --- Invoice Fields CRUD ---
def create_invoice_field(db: Session, invoice_id: int, field: schemas.InvoiceFieldBase):
    db_field = models.InvoiceField(
        invoice_id=invoice_id,
        field_name=field.field_name,
        extracted_value=field.extracted_value,
        confidence=field.confidence,
        bbox=field.bbox
    )
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field

# --- GST Report CRUD ---
def create_gst_report(db: Session, user_id: int, report_name: str, report_type: str, file_url: str):
    db_report = models.GSTReport(
        user_id=user_id,
        report_name=report_name,
        report_type=report_type,
        file_url=file_url
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

def get_gst_reports(db: Session, user_id: int):
    return db.query(models.GSTReport).filter(models.GSTReport.user_id == user_id).order_by(models.GSTReport.created_at.desc()).all()

# --- Audit Logs ---
def log_action(db: Session, user_id: int, action: str, details: str = None):
    db_log = models.AuditLog(
        user_id=user_id,
        action=action,
        details=details
    )
    db.add(db_log)
    db.commit()
    return db_log
