from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict
import datetime

from ..database import get_db
from .auth import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compiles key metrics and chart aggregate data for the analytics dashboard"""
    # Fetch all user invoices
    invoices = db.query(models.Invoice).filter(models.Invoice.user_id == current_user.id).all()
    
    total_invoices = len(invoices)
    total_taxable_value = sum(inv.taxable_amount for inv in invoices)
    total_gst_collected = sum(inv.total_gst for inv in invoices)
    cgst_total = sum(inv.cgst for inv in invoices)
    sgst_total = sum(inv.sgst for inv in invoices)
    igst_total = sum(inv.igst for inv in invoices)
    
    pending_validation = sum(1 for inv in invoices if inv.validation_status == "PENDING")
    invalid_invoices = sum(1 for inv in invoices if inv.validation_status in ["INVALID", "SUSPICIOUS"])

    # 1. Compile Monthly Trend
    # Group by 'YYYY-MM'
    monthly_data = defaultdict(float)
    for inv in invoices:
        month_str = inv.created_at.strftime('%Y-%m') # Format YYYY-MM
        monthly_data[month_str] += inv.total_gst
        
    # Sort and format for response
    sorted_months = sorted(monthly_data.keys())
    monthly_trend = []
    for m in sorted_months:
        dt = datetime.datetime.strptime(m, '%Y-%m')
        monthly_trend.append({
            "name": dt.strftime('%b %y'), # e.g. "Jun 26"
            "amount": monthly_data[m]
        })
        
    # Default placeholder if empty
    if not monthly_trend:
        monthly_trend = [{"name": datetime.datetime.utcnow().strftime('%b %y'), "amount": 0.0}]

    # 2. Compile Vendor Distribution
    vendor_data = defaultdict(int)
    for inv in invoices:
        v_name = inv.merchant_name or "Unknown Vendor"
        vendor_data[v_name] += 1
        
    vendor_distribution = []
    for vendor, count in sorted(vendor_data.items(), key=lambda x: x[1], reverse=True)[:5]: # top 5
        vendor_distribution.append({
            "vendor": vendor,
            "count": count
        })
        
    if not vendor_distribution:
        vendor_distribution = [{"vendor": "No Vendors", "count": 0}]

    # 3. Compile Tax Category Breakdown
    # Standard rates: 0%, 5%, 12%, 18%, 28%
    tax_categories = defaultdict(float)
    for inv in invoices:
        if inv.taxable_amount > 0:
            approx_rate = round((inv.total_gst / inv.taxable_amount) * 100)
            # Match to nearest standard bucket
            matched_rate = 18 # default
            if approx_rate < 2: matched_rate = 0
            elif approx_rate < 8: matched_rate = 5
            elif approx_rate < 15: matched_rate = 12
            elif approx_rate < 23: matched_rate = 18
            else: matched_rate = 28
            
            tax_categories[f"{matched_rate}%"] += inv.total_gst
        else:
            tax_categories["0%"] += inv.total_gst
            
    tax_category_breakdown = []
    for cat, amount in tax_categories.items():
        tax_category_breakdown.append({
            "category": cat,
            "amount": amount
        })
        
    if not tax_category_breakdown:
        tax_category_breakdown = [{"category": "18%", "amount": 0.0}]

    return schemas.DashboardSummary(
        total_invoices=total_invoices,
        total_taxable_value=total_taxable_value,
        total_gst_collected=total_gst_collected,
        cgst_total=cgst_total,
        sgst_total=sgst_total,
        igst_total=igst_total,
        pending_validation=pending_validation,
        invalid_invoices=invalid_invoices,
        monthly_trend=monthly_trend,
        vendor_distribution=vendor_distribution,
        tax_category_breakdown=tax_category_breakdown
    )
