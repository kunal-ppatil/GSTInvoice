from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os

from ..database import get_db
from .auth import get_current_user
from .. import models, schemas, crud
from ..gst_processor.validator import validate_gstin, calculate_gst_values
from ..gst_processor.report_generator import BackendReportGenerator

router = APIRouter(prefix="/gst", tags=["GST Utilities"])
report_generator = BackendReportGenerator()

@router.post("/validate-gstin", response_model=schemas.GSTINValidationResponse)
def api_validate_gstin(
    request: schemas.GSTINValidationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verifies a GSTIN format and checksum validity"""
    val_res = validate_gstin(request.gstin)
    crud.log_action(db, current_user.id, "GSTIN_VALIDATE", f"Validated GSTIN: {request.gstin} - Status: {val_res['status']}")
    
    return schemas.GSTINValidationResponse(
        gstin=request.gstin,
        status=val_res["status"],
        message=val_res["message"],
        state_code=val_res.get("state_code"),
        state=val_res.get("state"),
        pan=val_res.get("pan")
    )

@router.post("/calculate-gst", response_model=schemas.GSTCalculationResponse)
def api_calculate_gst(
    request: schemas.GSTCalculationRequest,
    current_user: models.User = Depends(get_current_user)
):
    """Calculates CGST, SGST, IGST and total amount from taxable value and tax rate"""
    calc = calculate_gst_values(request.taxable_value, request.gst_rate, request.is_interstate)
    return schemas.GSTCalculationResponse(
        taxable_value=calc["taxable_value"],
        gst_rate=calc["gst_rate"],
        cgst=calc["cgst"],
        sgst=calc["sgst"],
        igst=calc["igst"],
        total_gst=calc["total_gst"],
        grand_total=calc["grand_total"]
    )

@router.post("/generate-report")
def api_generate_report(
    request: schemas.ReportGenerationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates and compiles selected invoices into PDF, CSV or Excel reports"""
    # Fetch invoices
    invoices = []
    for inv_id in request.invoice_ids:
        inv = crud.get_invoice(db, inv_id, current_user.id)
        if not inv:
            raise HTTPException(status_code=404, detail=f"Invoice ID {inv_id} not found")
        invoices.append(inv)
        
    if not invoices:
        raise HTTPException(status_code=400, detail="No invoices selected for report generation")

    fmt = request.format.upper()
    user_info = {
        "company_name": current_user.company_name,
        "gst_in": current_user.gst_in,
        "email": current_user.email
    }
    
    try:
        if fmt == "PDF":
            file_path = report_generator.generate_pdf_report(user_info, invoices)
            report_type = "PDF"
        elif fmt == "CSV":
            file_path = report_generator.generate_csv_report(invoices)
            report_type = "CSV"
        elif fmt == "EXCEL" or fmt == "XLSX":
            file_path = report_generator.generate_excel_report(invoices)
            report_type = "EXCEL"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported report format: {request.format}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

    filename = os.path.basename(file_path)
    file_url = f"/static/results/{filename}"
    
    # Save report log in db
    db_report = crud.create_gst_report(db, current_user.id, filename, report_type, file_url)
    crud.log_action(db, current_user.id, "REPORT_GENERATE", f"Generated {report_type} report: {filename}")
    
    return {
        "report_id": db_report.id,
        "report_name": db_report.report_name,
        "report_type": db_report.report_type,
        "file_url": db_report.file_url,
        "created_at": db_report.created_at
    }

@router.get("/reports", response_model=List[schemas.ReportResponse])
def get_reports_list(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves list of all previously generated reports for downloading"""
    return crud.get_gst_reports(db, current_user.id)
