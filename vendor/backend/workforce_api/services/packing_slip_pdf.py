"""
Packing slip / shipping label PDF.

Built with reportlab (already a dependency, already used the same way for
invoices -- see invoice_pdf.py) rather than a screenshot of the frontend
HTML preview, so the barcode is a real vector Code128 symbol baked into the
PDF and is reliably scannable off a thermal or laser printout.

Format is a compact 4x6 inch shipping label (the common thermal-label size),
not the full-page A4 layout the JSON/HTML packing-slip preview uses -- this
PDF is what actually gets taped to the package, so it leads with the "ship
to" block the way a courier label does, then a barcode encoding the
customer-facing marketplace order number (source_order_id, e.g. MKT00017)
for warehouse/courier scanning -- the same number customer support and the
tracking page already key off of.

One barcode per order is a deliberate simplification: SellerOrder has no
concept of splitting into multiple physical packages (no shipment/package
model), so "one label per order" matches the current data model. If that
ever changes, this function's signature will need an explicit package
argument.
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.graphics.barcode.code128 import Code128

LABEL_WIDTH = 4 * inch
LABEL_HEIGHT = 6 * inch

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#cbd5e1")


def _divider(width):
    return Table(
        [[""]],
        colWidths=[width],
        rowHeights=[0.5],
        style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.75, LINE)]),
    )


def render_packing_slip_pdf(order):
    """Returns the shipping-label PDF (bytes) for a single SellerOrder."""
    buffer = io.BytesIO()
    content_width = LABEL_WIDTH - 20 * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(LABEL_WIDTH, LABEL_HEIGHT),
        leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=8 * mm, bottomMargin=8 * mm,
        title=f"Shipping Label {order.order_number}",
        author="SEVO",
    )

    base = getSampleStyleSheet()
    brand = ParagraphStyle("brand", parent=base["Normal"], fontSize=11, textColor=INK, fontName="Helvetica-Bold")
    small = ParagraphStyle("small", parent=base["Normal"], fontSize=8, textColor=MUTED, leading=11)
    label_hdr = ParagraphStyle("label_hdr", parent=base["Normal"], fontSize=8, textColor=MUTED, leading=10)
    addr_name = ParagraphStyle("addr_name", parent=base["Normal"], fontSize=15, textColor=INK, leading=19, fontName="Helvetica-Bold")
    addr_body = ParagraphStyle("addr_body", parent=base["Normal"], fontSize=11, textColor=INK, leading=15)
    meta = ParagraphStyle("meta", parent=base["Normal"], fontSize=9, textColor=INK, leading=13)

    company = order.company
    seller_name = company.company_name or company.name
    seller_address = getattr(company, "address", "") or ""

    story = []

    # -- Header: from / brand --
    story.append(Paragraph("SEVO GROCERY", brand))
    from_line = f"From: {seller_name}" + (f", {seller_address}" if seller_address else "")
    story.append(Paragraph(from_line, small))
    story.append(Spacer(1, 4 * mm))
    story.append(_divider(content_width))
    story.append(Spacer(1, 4 * mm))

    # -- Ship To block (the part a courier actually reads) --
    story.append(Paragraph("SHIP TO", label_hdr))
    story.append(Paragraph(order.customer_name or "-", addr_name))
    if order.delivery_address:
        story.append(Paragraph(order.delivery_address, addr_body))
    if order.customer_phone:
        story.append(Paragraph(f"Ph: {order.customer_phone}", addr_body))
    story.append(Spacer(1, 5 * mm))

    # -- Order meta --
    # The marketplace order number (e.g. MKT00017) is what customer support
    # and the customer-facing tracking page key off of -- it lives on
    # order.source_order_id here (the "Immutable canonical marketplace order
    # reference from Customer app"). order.order_number is a separate,
    # seller-internal code (e.g. SO-202609-A1B2C3) used for the merchant's
    # own bookkeeping, so it's shown too but only as a secondary reference.
    item_count = order.items.count()
    order_meta_lines = [
        f"Order #{order.source_order_id}",
        f"Seller Ref: {order.order_number}",
        f"Placed: {order.created_at.strftime('%d %b %Y, %I:%M %p')}",
        f"Fulfilment: {order.get_fulfillment_type_display()}" + (f" &middot; {order.delivery_slot}" if order.delivery_slot else ""),
        f"{item_count} item{'s' if item_count != 1 else ''} &middot; {order.currency} {order.total_amount}",
    ]
    story.append(Paragraph("<br/>".join(order_meta_lines), meta))
    story.append(Spacer(1, 6 * mm))
    story.append(_divider(content_width))
    story.append(Spacer(1, 6 * mm))

    # -- Scannable barcode: Code128, encodes the marketplace order number --
    barcode = Code128(
        order.source_order_id,
        barHeight=20 * mm,
        barWidth=0.9,
        humanReadable=True,
        fontSize=10,
        fontName="Courier-Bold",
        quiet=True,
    )
    barcode.hAlign = "CENTER"
    story.append(barcode)

    doc.build(story)
    return buffer.getvalue()
