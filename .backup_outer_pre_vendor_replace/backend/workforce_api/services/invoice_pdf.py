"""
Invoice PDF.

Built with reportlab (already a dependency) rather than an HTML-to-PDF
round trip, so the document is generated identically on the server whatever the
caller is, and needs no browser.

The PDF is rendered from the invoice's own frozen columns and items, never from
the quote it came from -- a quote can be revised, and a PDF the customer already
holds must keep saying what it said.
"""
import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#e2e8f0")
BAND = colors.HexColor("#f8fafc")


def _rupees(value):
    # "Rs." rather than the rupee sign: the built-in Type 1 fonts have no glyph
    # for U+20B9, and a missing glyph renders as a black box on the customer's
    # copy of a financial document.
    return "Rs. {:,.2f}".format(Decimal(str(value or 0)))


def render_invoice_pdf(invoice):
    """Returns the PDF as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=invoice.invoice_number,
        author="SEVO",
    )

    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Heading1"], fontSize=18, textColor=INK, spaceAfter=2)
    small = ParagraphStyle("small", parent=base["Normal"], fontSize=8.5, textColor=MUTED, leading=12)
    body = ParagraphStyle("body", parent=base["Normal"], fontSize=9.5, textColor=INK, leading=13)
    right = ParagraphStyle("right", parent=body, alignment=TA_RIGHT)

    story = []

    header = Table(
        [[
            Paragraph("<b>SEVO</b><br/>Caldim Engineering", body),
            Paragraph(
                f"<b>TAX INVOICE</b><br/>{invoice.invoice_number}<br/>"
                f"{invoice.issued_at.strftime('%d %b %Y') if invoice.issued_at else ''}",
                right,
            ),
        ]],
        colWidths=[95 * mm, 79 * mm],
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [header, Spacer(1, 10 * mm)]

    bill_to = "<br/>".join(
        x for x in [
            f"<b>{invoice.bill_to_name}</b>" if invoice.bill_to_name else None,
            invoice.bill_to_address or None,
            invoice.bill_to_phone or None,
            invoice.bill_to_email or None,
        ] if x
    ) or "&mdash;"

    meta = "<br/>".join(x for x in [
        f"Service: {invoice.service_name}" if invoice.service_name else None,
        f"Quotation: {invoice.quote.quote_number}" if invoice.quote_id else None,
        f"Booking: #{invoice.job_id}",
        f"Due: {invoice.due_at.strftime('%d %b %Y')}" if invoice.due_at else None,
    ] if x)

    parties = Table(
        [[Paragraph("BILL TO", small), Paragraph("DETAILS", small)],
         [Paragraph(bill_to, body), Paragraph(meta, body)]],
        colWidths=[95 * mm, 79 * mm],
    )
    parties.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
    ]))
    story += [parties, Spacer(1, 8 * mm)]

    rows = [[
        Paragraph("<b>Description</b>", small),
        Paragraph("<b>Qty</b>", small),
        Paragraph("<b>Rate</b>", small),
        Paragraph("<b>Amount</b>", small),
    ]]
    for item in invoice.items.all():
        label = item.name
        if item.description:
            label += f"<br/><font size=8 color='#64748b'>{item.description}</font>"
        rows.append([
            Paragraph(label, body),
            Paragraph(f"{item.quantity:g} {item.unit}", body),
            Paragraph(_rupees(item.unit_price), body),
            Paragraph(_rupees(item.line_total), right),
        ])
    if len(rows) == 1:
        rows.append([Paragraph("No line items recorded.", body), "", "", ""])

    items_table = Table(rows, colWidths=[92 * mm, 24 * mm, 28 * mm, 30 * mm], repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BAND),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [items_table, Spacer(1, 6 * mm)]

    totals = [["Subtotal", _rupees(invoice.subtotal_amount)]]
    if Decimal(invoice.discount_amount or 0) > 0:
        totals.append(["Discount", "- " + _rupees(invoice.discount_amount)])
    totals.append(["GST", _rupees(invoice.tax_amount)])
    if Decimal(invoice.inspection_fee_adjusted or 0) > 0:
        totals.append(["Inspection fee credited", "- " + _rupees(invoice.inspection_fee_adjusted)])
    totals.append(["Total", _rupees(invoice.total_amount)])
    if Decimal(invoice.balance_amount or 0) > 0:
        totals.append([f"Advance ({invoice.advance_percent:g}%)", _rupees(invoice.advance_amount)])
        totals.append(["Balance on completion", _rupees(invoice.balance_amount)])
    if Decimal(invoice.amount_paid or 0) > 0:
        totals.append(["Paid", _rupees(invoice.amount_paid)])
        totals.append(["Outstanding", _rupees(invoice.balance_due)])

    totals_table = Table(
        [[Paragraph(label, body), Paragraph(value, right)] for label, value in totals],
        colWidths=[124 * mm, 50 * mm],
        hAlign="RIGHT",
    )
    total_row = next(i for i, (label, _) in enumerate(totals) if label == "Total")
    totals_table.setStyle(TableStyle([
        ("LINEABOVE", (0, total_row), (-1, total_row), 0.8, INK),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [totals_table, Spacer(1, 10 * mm)]

    story.append(Paragraph(
        f"Status: {invoice.get_status_display()}."
        + (f" {invoice.notes}" if invoice.notes else ""),
        small,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "This is a computer-generated invoice issued through the SEVO platform.",
        small,
    ))

    doc.build(story)
    return buffer.getvalue()
