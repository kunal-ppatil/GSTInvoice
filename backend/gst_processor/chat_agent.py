import re
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from ..models import Invoice, InvoiceField
import datetime
from typing import Dict, Any

class BackendChatAgent:
    """Natural Language Assistant that translates GST questions into database queries"""
    
    def __init__(self):
        pass
        
    def process_query(self, db: Session, user_id: int, message: str) -> Dict[str, Any]:
        message_clean = message.lower().strip()
        now = datetime.datetime.utcnow()
        
        # 1. Query: Total GST this month
        if any(k in message_clean for k in ["total gst", "gst collected", "tax collected"]) and any(k in message_clean for k in ["month", "this month", "current month"]):
            total_gst_cgst = db.query(func.sum(Invoice.cgst)).filter(
                Invoice.user_id == user_id,
                extract('year', Invoice.created_at) == now.year,
                extract('month', Invoice.created_at) == now.month
            ).scalar() or 0.0
            total_gst_sgst = db.query(func.sum(Invoice.sgst)).filter(
                Invoice.user_id == user_id,
                extract('year', Invoice.created_at) == now.year,
                extract('month', Invoice.created_at) == now.month
            ).scalar() or 0.0
            total_gst_igst = db.query(func.sum(Invoice.igst)).filter(
                Invoice.user_id == user_id,
                extract('year', Invoice.created_at) == now.year,
                extract('month', Invoice.created_at) == now.month
            ).scalar() or 0.0
            
            total_gst = total_gst_cgst + total_gst_sgst + total_gst_igst
            
            reply = (
                f"📊 **GST Summary for this Month ({now.strftime('%B %Y')}):**\n\n"
                f"- **Total GST Collected:** ₹{total_gst:,.2f}\n"
                f"  - **CGST:** ₹{total_gst_cgst:,.2f}\n"
                f"  - **SGST:** ₹{total_gst_sgst:,.2f}\n"
                f"  - **IGST:** ₹{total_gst_igst:,.2f}\n\n"
                f"This calculation is based on all invoices scanned and saved this month."
            )
            return {"reply": reply, "suggested_actions": ["Show invoices", "Generate GST Report"]}
            
        # 2. Query: Invoices above a threshold (e.g. above 50,000)
        limit_match = re.search(r'(?:above|greater than|over|more than|limit|value)\s*(?:₹|rs\.?)?\s*([\d,]+)', message_clean)
        if limit_match:
            try:
                threshold = float(limit_match.group(1).replace(',', ''))
                invoices = db.query(Invoice).filter(
                    Invoice.user_id == user_id,
                    Invoice.total_amount > threshold
                ).all()
                
                if not invoices:
                    reply = f"🔍 I couldn't find any invoices with total amount exceeding **₹{threshold:,.2f}**."
                else:
                    reply = f"📋 Found **{len(invoices)}** invoices exceeding **₹{threshold:,.2f}**:\n\n"
                    for idx, inv in enumerate(invoices, 1):
                        reply += (
                            f"{idx}. **{inv.merchant_name or 'Unknown Merchant'}** | "
                            f"Inv: `{inv.invoice_number or 'N/A'}` | "
                            f"Date: {inv.invoice_date or 'N/A'} | "
                            f"Amount: **₹{inv.total_amount:,.2f}**\n"
                        )
                return {"reply": reply, "suggested_actions": [f"Export these invoices", "Reset filter"]}
            except Exception:
                pass
                
        # 3. Query: Invalid GSTIN vendors
        if any(k in message_clean for k in ["invalid gstin", "invalid vendors", "invalid gst", "suspicious gst", "suspicious vendors"]):
            invoices = db.query(Invoice).filter(
                Invoice.user_id == user_id,
                Invoice.validation_status.in_(["INVALID", "SUSPICIOUS"])
            ).all()
            
            if not invoices:
                reply = "🟢 Excellent news! All of your scanned vendors have **VALID** GSTINs."
            else:
                reply = f"⚠️ Found **{len(invoices)}** vendors with **Invalid / Suspicious** GSTINs:\n\n"
                for idx, inv in enumerate(invoices, 1):
                    gst_val = "N/A"
                    for f in inv.fields:
                        if f.field_name == 'GST Number':
                            gst_val = f.extracted_value
                            break
                    reply += (
                        f"{idx}. **{inv.merchant_name or 'Unknown'}** | "
                        f"GSTIN: `{gst_val}` | "
                        f"Status: **{inv.validation_status}** | "
                        f"Invoice: `{inv.invoice_number}`\n"
                    )
                reply += "\nI recommend verifying these GSTINs on the official GST portal or contacting the vendors."
                return {"reply": reply, "suggested_actions": ["Download audit report", "Verify manually"]}
                
        # 4. Query: Monthly summary
        if any(k in message_clean for k in ["summary", "monthly summary", "statistics", "stats"]):
            total_invs = db.query(Invoice).filter(Invoice.user_id == user_id).count()
            total_taxable = db.query(func.sum(Invoice.taxable_amount)).filter(Invoice.user_id == user_id).scalar() or 0.0
            total_gst = db.query(func.sum(Invoice.total_gst)).filter(Invoice.user_id == user_id).scalar() or 0.0
            invalid_count = db.query(Invoice).filter(Invoice.user_id == user_id, Invoice.validation_status == "INVALID").count()
            
            reply = (
                f"📈 **InvoiScope Dashboard Executive Summary:**\n\n"
                f"- 📄 **Total Invoices Processed:** {total_invs}\n"
                f"- 💰 **Cumulative Taxable Value:** ₹{total_taxable:,.2f}\n"
                f"- 🛡️ **Total GST Tax Collected:** ₹{total_gst:,.2f}\n"
                f"- ⚠️ **Compliance Warnings:** {invalid_count} invalid GSTIN invoices detected\n\n"
                f"Let me know if you would like me to generate a PDF report of these transactions!"
            )
            return {"reply": reply, "suggested_actions": ["Generate PDF Report", "Show dashboard"]}

        # 5. Default Reply
        reply = (
            f"👋 Hello! I am your **GST SmartScan Assistant**.\n\n"
            f"I can search your database and answer complex compliance questions. You can ask me:\n\n"
            f"- *'What is my total GST collected this month?'*\n"
            f"- *'Show invoices above ₹5,000'* \n"
            f"- *'Which vendors have invalid GSTINs?'*\n"
            f"- *'Show a summary of my database'* \n\n"
            f"How can I help you today?"
        )
        return {"reply": reply, "suggested_actions": ["Total GST this month", "Show invalid GSTINs", "Database summary"]}
