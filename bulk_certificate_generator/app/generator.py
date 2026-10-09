from pathlib import Path
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import os
import re

OUTPUT_DIR = Path(os.getenv("CERTIFICATE_DIR", str(Path(__file__).resolve().parent.parent / "generated")))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    return cleaned[:80] or "recipient"

def generate_certificate(name: str, email: str, event_name: str, title: str, job_id: str, certificate_id: int) -> str:
    path = OUTPUT_DIR / f"{job_id}_{certificate_id}_{safe_filename(name)}.pdf"
    page = landscape(A4)
    pdf = canvas.Canvas(str(path), pagesize=page)
    width, height = page
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#1D4ED8"))
    pdf.setLineWidth(4)
    pdf.rect(24, 24, width - 48, height - 48, fill=0, stroke=1)
    pdf.setFillColor(colors.HexColor("#1E3A8A"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, height - 105, title)
    pdf.setFillColor(colors.HexColor("#334155"))
    pdf.setFont("Helvetica", 15)
    pdf.drawCentredString(width / 2, height - 155, "This certificate is proudly presented to")
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 30)
    pdf.drawCentredString(width / 2, height - 205, name)
    pdf.setFillColor(colors.HexColor("#334155"))
    pdf.setFont("Helvetica", 15)
    pdf.drawCentredString(width / 2, height - 245, f"For participation in: {event_name}")
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, 65, f"Certificate ID: {job_id[:8]}-{certificate_id}  |  Recipient: {email}")
    pdf.save()
    return str(path)
