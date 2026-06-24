from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    company_name: Optional[str] = None
    gst_in: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    company_name: Optional[str] = None
    gst_in: Optional[str] = None
    password: Optional[str] = None

# --- Invoice Field Schemas ---
class InvoiceFieldBase(BaseModel):
    field_name: str
    extracted_value: Optional[str] = None
    confidence: float
    bbox: Optional[List[int]] = None

class InvoiceFieldResponse(InvoiceFieldBase):
    id: int
    invoice_id: int

    class Config:
        from_attributes = True

# --- Invoice Schemas ---
class InvoiceBase(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    po_number: Optional[str] = None
    merchant_name: Optional[str] = None
    merchant_address: Optional[str] = None
    taxable_amount: Optional[float] = 0.0
    cgst: Optional[float] = 0.0
    sgst: Optional[float] = 0.0
    igst: Optional[float] = 0.0
    total_gst: Optional[float] = 0.0
    total_amount: Optional[float] = 0.0
    validation_status: Optional[str] = "PENDING"
    validation_details: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    file_url: Optional[str] = None

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    po_number: Optional[str] = None
    merchant_name: Optional[str] = None
    merchant_address: Optional[str] = None
    taxable_amount: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total_gst: Optional[float] = None
    total_amount: Optional[float] = None
    validation_status: Optional[str] = None

class InvoiceResponse(InvoiceBase):
    id: int
    user_id: int
    file_url: Optional[str] = None
    created_at: datetime
    fields: List[InvoiceFieldResponse] = []

    class Config:
        from_attributes = True

# --- GST Verification & Calculation ---
class GSTINValidationRequest(BaseModel):
    gstin: str

class GSTINValidationResponse(BaseModel):
    gstin: str
    status: str  # VALID, INVALID, SUSPICIOUS
    message: str
    state_code: Optional[str] = None
    state: Optional[str] = None
    pan: Optional[str] = None

class GSTCalculationRequest(BaseModel):
    taxable_value: float
    gst_rate: float  # 0, 5, 12, 18, 28
    is_interstate: bool  # True for IGST, False for CGST+SGST

class GSTCalculationResponse(BaseModel):
    taxable_value: float
    gst_rate: float
    cgst: float
    sgst: float
    igst: float
    total_gst: float
    grand_total: float

# --- Report Schemas ---
class ReportGenerationRequest(BaseModel):
    invoice_ids: List[int]
    format: str  # PDF, CSV, EXCEL

class ReportResponse(BaseModel):
    report_id: int
    report_name: str
    report_type: str
    file_url: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Dashboard & Analytics Schemas ---
class DashboardSummary(BaseModel):
    total_invoices: int
    total_taxable_value: float
    total_gst_collected: float
    cgst_total: float
    sgst_total: float
    igst_total: float
    pending_validation: int
    invalid_invoices: int
    monthly_trend: List[Dict[str, Any]]
    vendor_distribution: List[Dict[str, Any]]
    tax_category_breakdown: List[Dict[str, Any]]

# --- AI Assistant Chat Schemas ---
class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    reply: str
    suggested_actions: Optional[List[str]] = None
