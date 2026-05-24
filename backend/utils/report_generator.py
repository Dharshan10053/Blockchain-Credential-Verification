"""
Generates a downloadable verification report as PDF.
"""
from __future__ import annotations
import logging
import os
import io
from datetime import datetime

logger = logging.getLogger(__name__)

_REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reports")

def generate_report(result: dict, base_url: str = None) -> str:
    """
    Build a premium dark-themed PDF verification report.
    Returns path to the PDF, or "" on failure.
    """
    if base_url:
        base_url = base_url.rstrip("/")
    else:
        base_url = "https://certauth.network"
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        import qrcode

        os.makedirs(_REPORT_DIR, exist_ok=True)
        cert_hash = result.get("hash", "unknown")
        filename = f"report_{cert_hash[:12]}.pdf"
        filepath = os.path.join(_REPORT_DIR, filename)

        width, height = A4
        c = canvas.Canvas(filepath, pagesize=A4)
        c.setTitle(f"Verification Report - {cert_hash[:12]}")

        # 1. Background (Dark Theme: #0B1120)
        c.setFillColor(colors.HexColor("#0B1120"))
        c.rect(0, 0, width, height, stroke=0, fill=1)

        # 2. Header
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.setFont("Helvetica-Bold", 24)
        c.drawString(2*cm, height - 3*cm, "CertAuth Verification")
        
        c.setFillColor(colors.HexColor("#9CA3AF"))
        c.setFont("Helvetica", 10)
        c.drawString(2*cm, height - 3.7*cm, f"Generated: {datetime.now().strftime('%B %d, %Y - %H:%M UTC')}")

        # Accent Line
        c.setStrokeColor(colors.HexColor("#06B6D4"))
        c.setLineWidth(2)
        c.line(2*cm, height - 4.2*cm, width - 2*cm, height - 4.2*cm)

        # 3. Status Box
        status = result.get("status", "UNKNOWN")
        status_color = {
            "VALID": colors.HexColor("#10B981"),
            "NEWLY_REGISTERED": colors.HexColor("#2563EB"),
            "PARTIALLY_MATCHED": colors.HexColor("#F59E0B"),
            "FAKE": colors.HexColor("#EF4444"),
        }.get(status, colors.HexColor("#6B7280"))

        box_y = height - 7*cm
        c.setFillColor(colors.HexColor("#111827")) # Box background
        c.setStrokeColor(status_color)
        c.setLineWidth(1)
        c.roundRect(2*cm, box_y, width - 4*cm, 2.2*cm, 10, stroke=1, fill=1)
        
        c.setFillColor(status_color)
        c.setFont("Helvetica-Bold", 16)
        label = result.get("label", status).upper()
        c.drawString(2.5*cm, box_y + 1.2*cm, f"STATUS: {label}")
        
        c.setFillColor(colors.HexColor("#9CA3AF"))
        c.setFont("Helvetica", 10)
        c.drawString(2.5*cm, box_y + 0.5*cm, result.get("explanation", "Extraction completeness and hash matching influence this score."))

        # 4. Details Section & QR (Responsive Stacked Layout)
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(2*cm, box_y - 1.5*cm, "Certificate Details")

        import json
        logger.debug(f"FULL PDF GENERATOR PAYLOAD:\n{json.dumps(result, indent=2)}")

        # Centralized normalized fallback resolver exactly as requested
        course_title = result.get("course") or result.get("course_title") or result.get("course_name") or result.get("title") or result.get("certificate_title") or "Not Extracted"
        date_val = result.get("date") or result.get("issue_date") or result.get("year") or result.get("completion_date") or result.get("issued_on") or "Not Mentioned"
        
        # Resolve other fields safely
        candidate_name = result.get("name") or result.get("candidate_name") or result.get("student_name") or result.get("recipient") or "Not Extracted"
        cert_id = result.get("cert_id") or result.get("certificate_id") or result.get("id") or result.get("credential_id") or "Not Extracted"
        issuer = result.get("issuing_authority") or result.get("issuer") or result.get("organization") or result.get("institution") or result.get("issued_by") or "Not Extracted"

        rows = [
            ("Candidate Name", candidate_name),
            ("Course / Title", course_title),
            ("Certificate ID", cert_id),
            ("Issuing Authority", issuer),
            ("Date", date_val),
            ("Confidence", f"{result.get('confidence_score', 0)}%"),
        ]

        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import ParagraphStyle

        value_style = ParagraphStyle(
            'ValueStyle',
            fontName='Helvetica',
            fontSize=11,
            textColor=colors.HexColor("#F8FAFC"),
            leading=14
        )
        
        hash_style = ParagraphStyle(
            'HashStyle',
            fontName='Courier',
            fontSize=10,
            textColor=colors.HexColor("#38BDF8"),
            leading=13,
            wordWrap='CJK'
        )

        # LEFT COLUMN (Details Stacked)
        text_y = box_y - 2.5*cm
        left_col_width = width - 9.5*cm
        
        for lbl, val in rows:
            # Draw Label
            c.setFillColor(colors.HexColor("#9CA3AF"))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2*cm, text_y, lbl.upper())
            
            # Draw Value with wrapping
            p = Paragraph(str(val), value_style)
            w, h = p.wrap(left_col_width, height)
            p.drawOn(c, 2*cm, text_y - h - 0.2*cm)
            
            text_y -= (h + 0.6*cm) # Space after value
            
            # Subtle divider
            c.setStrokeColor(colors.HexColor("#1F2937"))
            c.setLineWidth(0.5)
            c.line(2*cm, text_y, 2*cm + left_col_width, text_y)
            text_y -= 0.6*cm # Space before next label

        # RIGHT COLUMN (QR Code & Seals)
        qr_size = 4.5*cm
        qr_x = width - 2*cm - qr_size
        qr_y = box_y - 1.5*cm - qr_size
        
        # QR Background Box
        c.setFillColor(colors.HexColor("#111827"))
        c.setStrokeColor(colors.HexColor("#374151"))
        c.roundRect(qr_x - 0.5*cm, qr_y - 1*cm, qr_size + 1*cm, qr_size + 2*cm, 5, stroke=1, fill=1)
        
        # Draw white background for QR code
        c.setFillColor(colors.white)
        c.rect(qr_x, qr_y, qr_size, qr_size, stroke=0, fill=1)
        
        token = result.get("token")
        if token:
            qr_url = f"{base_url}/verify_token/{token}"
        else:
            qr_url = f"{base_url}/certificate/{cert_hash}"
            
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        from reportlab.lib.utils import ImageReader
        c.drawImage(ImageReader(img_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

        # Verification Badge text
        c.setFillColor(colors.HexColor("#10B981") if status == "VALID" else colors.HexColor("#EF4444"))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(qr_x + qr_size/2, qr_y - 0.6*cm, "VERIFIED ON LEDGER" if status == "VALID" else "VERIFICATION FAILED")

        # 5. Blockchain Hash (Terminal Style)
        hash_header_y = text_y - 0.5*cm
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(2*cm, hash_header_y, "Blockchain Record")

        hash_text = f"SHA-256: {cert_hash}"
        hash_p = Paragraph(hash_text, hash_style)
        hash_w, hash_h = hash_p.wrap(width - 4.5*cm, height)
        
        box_h = hash_h + 1.2*cm
        hash_y = hash_header_y - 0.5*cm - box_h
        
        c.setFillColor(colors.HexColor("#0f172a")) # Darker terminal background
        c.setStrokeColor(colors.HexColor("#334155"))
        c.roundRect(2*cm, hash_y, width - 4*cm, box_h, 5, stroke=1, fill=1)
        
        # Red/Yellow/Green terminal dots
        dots_y = hash_y + box_h - 0.4*cm
        c.setFillColor(colors.HexColor("#EF4444"))
        c.circle(2.5*cm, dots_y, 0.15*cm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#F59E0B"))
        c.circle(3.0*cm, dots_y, 0.15*cm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#10B981"))
        c.circle(3.5*cm, dots_y, 0.15*cm, stroke=0, fill=1)

        hash_p.drawOn(c, 2.5*cm, hash_y + 0.4*cm)

        c.save()
        logger.info("Premium report saved: %s", filepath)
        return filepath

    except ImportError as e:
        logger.warning(f"Dependency missing for PDF report: {e}")
        return ""
    except Exception as e:
        logger.error("Premium report generation failed: %s", e, exc_info=True)
        return ""
