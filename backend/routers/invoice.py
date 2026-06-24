from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from ..database import get_db
from .auth import get_current_user
from .. import models, schemas, crud
from ..gst_processor.extractor import BackendGSTExtractor
from ..gst_processor.validator import validate_gstin

router = APIRouter(prefix="/invoices", tags=["Invoices"])

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Instantiate Extractor
extractor = BackendGSTExtractor()

@router.post("/upload-invoice")
def upload_invoice(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Uploads an invoice image or PDF and saves it locally"""
    # Validate extension
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "pdf"]:
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, PNG, and PDF files are supported")
        
    # Create unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # Return URL for serving static file
    file_url = f"/static/uploads/{unique_filename}"
    
    crud.log_action(db, current_user.id, "INVOICE_UPLOAD", f"Uploaded file: {file.filename}")
    
    return {
        "filename": file.filename,
        "file_url": file_url,
        "saved_path": file_path
    }

@router.post("/extract-fields", response_model=schemas.InvoiceResponse)
def extract_fields(
    file_url: str = Form(...),
    confidence_threshold: float = Form(0.5),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extracts GST fields from an already uploaded invoice image using YOLO + OCR"""
    # Map static URL back to local path
    filename = file_url.split("/")[-1]
    local_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Uploaded file not found on disk")
        
    # Extract fields
    extraction_results = extractor.extract_gst_information(local_path, confidence_threshold)
    
    if "error" in extraction_results:
        raise HTTPException(status_code=500, detail=extraction_results["error"])
        
    # 1. Parse Metadata
    invoice_number = None
    invoice_date = None
    po_number = None
    total_amount = 0.0
    taxable_amount = 0.0
    cgst_val = 0.0
    sgst_val = 0.0
    igst_val = 0.0
    total_gst_val = 0.0
    merchant_name = None
    merchant_address = None
    
    # Helper parser for currency
    def parse_amount(val_str):
        if not val_str:
            return 0.0
        try:
            # Remove symbols
            cleaned = re.sub(r'[^\d.]', '', val_str.replace(',', ''))
            return float(cleaned)
        except Exception:
            return 0.0

    import re
    # Extract values from metadata list
    if extraction_results['invoice_metadata']['invoice_number']:
        invoice_number = extraction_results['invoice_metadata']['invoice_number'][0]['text_content']
    if extraction_results['invoice_metadata']['invoice_date']:
        invoice_date = extraction_results['invoice_metadata']['invoice_date'][0]['text_content']
    if extraction_results['invoice_metadata']['po_number']:
        po_number = extraction_results['invoice_metadata']['po_number'][0]['text_content']
    if extraction_results['invoice_metadata']['total_amount']:
        total_amount = parse_amount(extraction_results['invoice_metadata']['total_amount'][0]['text_content'])
        
    # Extract business info
    if extraction_results['business_information']['merchant_name']:
        merchant_name = extraction_results['business_information']['merchant_name'][0]['text_content']
    if extraction_results['business_information']['merchant_address']:
        merchant_address = extraction_results['business_information']['merchant_address'][0]['text_content']
        
    # Extract tax info
    if extraction_results['tax_information']['cgst']:
        cgst_val = parse_amount(extraction_results['tax_information']['cgst'][0]['text_content'])
    if extraction_results['tax_information']['sgst']:
        sgst_val = parse_amount(extraction_results['tax_information']['sgst'][0]['text_content'])
    if extraction_results['tax_information']['igst']:
        igst_val = parse_amount(extraction_results['tax_information']['igst'][0]['text_content'])
    if extraction_results['tax_information']['total_gst']:
        total_gst_val = parse_amount(extraction_results['tax_information']['total_gst'][0]['text_content'])
        
    # Re-calculate aggregates if missing
    if total_gst_val == 0.0:
        total_gst_val = cgst_val + sgst_val + igst_val
        
    if taxable_amount == 0.0 and total_amount > 0.0:
        taxable_amount = total_amount - total_gst_val

    # 2. Validate GSTIN
    gstin_val = ""
    validation_status = "PENDING"
    validation_msg = "No GST Number detected on invoice"
    
    if extraction_results['business_information']['gst_numbers']:
        gstin_val = extraction_results['business_information']['gst_numbers'][0]['text_content']
        val_res = validate_gstin(gstin_val)
        validation_status = val_res["status"]
        validation_msg = val_res["message"]

    # 3. Create Invoice database record
    invoice_in = schemas.InvoiceCreate(
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        po_number=po_number,
        merchant_name=merchant_name,
        merchant_address=merchant_address,
        file_url=file_url,
        taxable_amount=taxable_amount,
        cgst=cgst_val,
        sgst=sgst_val,
        igst=igst_val,
        total_gst=total_gst_val,
        total_amount=total_amount,
        validation_status=validation_status,
        validation_details=validation_msg
    )
    
    db_invoice = crud.create_invoice(db, invoice_in, current_user.id)
    
    # 4. Save individual detected fields
    for cat, fields in extraction_results.items():
        if cat == 'summary':
            continue
        for field_type, detections in fields.items():
            for det in detections:
                field_in = schemas.InvoiceFieldBase(
                    field_name=det['field_type'],
                    extracted_value=det['text_content'],
                    confidence=det['confidence'],
                    bbox=det['bbox']
                )
                crud.create_invoice_field(db, db_invoice.id, field_in)
                
    # Refresh to include fields relations
    db.refresh(db_invoice)
    crud.log_action(db, current_user.id, "INVOICE_EXTRACT", f"Extracted fields for Invoice: {db_invoice.id}")
    return db_invoice

@router.get("/invoice-history", response_model=List[schemas.InvoiceResponse])
def get_invoice_history(
    search: Optional[str] = Query(None),
    date_filter: Optional[str] = Query(None), # this_month, last_month
    status: Optional[str] = Query(None), # VALID, INVALID, SUSPICIOUS
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all invoices for current user with search and filtering"""
    return crud.get_invoices(db, current_user.id, search, date_filter, status)

@router.put("/update-invoice/{invoice_id}", response_model=schemas.InvoiceResponse)
def update_invoice_data(
    invoice_id: int,
    invoice_update: schemas.InvoiceUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows manual editing of extracted fields by the user"""
    db_invoice = crud.update_invoice(db, invoice_id, invoice_update, current_user.id)
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    crud.log_action(db, current_user.id, "INVOICE_UPDATE", f"Manually updated Invoice: {invoice_id}")
    return db_invoice

@router.delete("/delete-invoice/{invoice_id}")
def delete_invoice_data(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes an invoice and all its records"""
    success = crud.delete_invoice(db, invoice_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    crud.log_action(db, current_user.id, "INVOICE_DELETE", f"Deleted Invoice: {invoice_id}")
    return {"message": "Invoice successfully deleted"}
