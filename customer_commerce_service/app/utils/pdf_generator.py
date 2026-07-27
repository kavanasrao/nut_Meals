"""GST-compliant invoice PDF builder using ReportLab."""
import io
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from app.core.config import settings


def _currency(value) -> str:
    return f"₹{Decimal(str(value)):,.2f}"


def build_invoice_pdf(invoice) -> bytes:
    """
    Build a GST-compliant invoice PDF.
    Returns raw bytes suitable for upload or streaming.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=16)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12)
    normal = styles["Normal"]
    right = ParagraphStyle("right", parent=normal, alignment=TA_RIGHT)
    small = ParagraphStyle("small", parent=normal, fontSize=8)

    elements = []

    # ── Header ────────────────────────────────────────────────────────────────
    elements.append(Paragraph(settings.COMPANY_NAME, title_style))
    elements.append(Paragraph(settings.COMPANY_ADDRESS, ParagraphStyle("addr", parent=normal, alignment=TA_CENTER)))
    elements.append(Paragraph(f"GSTIN: {settings.COMPANY_GSTIN}", ParagraphStyle("gstin", parent=normal, alignment=TA_CENTER)))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("TAX INVOICE", ParagraphStyle("inv_title", parent=title_style, fontSize=14)))
    elements.append(Spacer(1, 4 * mm))

    # ── Invoice meta ──────────────────────────────────────────────────────────
    meta_data = [
        ["Invoice No.", invoice.invoice_number, "Invoice Date", invoice.created_at.strftime("%d-%m-%Y")],
        ["Order ID", str(invoice.order_id), "", ""],
    ]
    meta_table = Table(meta_data, colWidths=[35 * mm, 65 * mm, 35 * mm, 45 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 4 * mm))

    # ── Bill to ───────────────────────────────────────────────────────────────
    elements.append(Paragraph("<b>Bill To:</b>", h2))
    elements.append(Paragraph(invoice.billing_name, normal))
    elements.append(Paragraph(invoice.billing_address, normal))
    if invoice.billing_gstin:
        elements.append(Paragraph(f"GSTIN: {invoice.billing_gstin}", normal))
    elements.append(Spacer(1, 4 * mm))

    # ── Line items table ──────────────────────────────────────────────────────
    header = ["#", "Product", "Qty", "Unit Price", "Tax Rate", "Total"]
    rows = [header]
    for idx, item in enumerate(invoice.line_items, 1):
        rows.append([
            str(idx),
            item["product_name"],
            str(item["quantity"]),
            _currency(item["unit_price"]),
            f"{item['tax_rate']}%",
            _currency(item["line_total"]),
        ])

    items_table = Table(rows, colWidths=[10 * mm, 75 * mm, 15 * mm, 25 * mm, 20 * mm, 30 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 4 * mm))

    # ── Totals ────────────────────────────────────────────────────────────────
    totals = [
        ["Subtotal", _currency(invoice.subtotal)],
    ]
    if invoice.discount_amount:
        totals.append(["Discount", f"- {_currency(invoice.discount_amount)}"])
    if invoice.cgst_amount:
        totals.append([f"CGST @ {invoice.cgst_rate}%", _currency(invoice.cgst_amount)])
    if invoice.sgst_amount:
        totals.append([f"SGST @ {invoice.sgst_rate}%", _currency(invoice.sgst_amount)])
    if invoice.igst_amount:
        totals.append([f"IGST @ {invoice.igst_rate}%", _currency(invoice.igst_amount)])
    totals.append(["TOTAL", _currency(invoice.total_amount)])

    totals_table = Table(totals, colWidths=[140 * mm, 35 * mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 8 * mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Paragraph(
        "This is a computer-generated invoice and does not require a signature.",
        ParagraphStyle("footer", parent=small, alignment=TA_CENTER, textColor=colors.grey),
    ))

    doc.build(elements)
    return buffer.getvalue()
