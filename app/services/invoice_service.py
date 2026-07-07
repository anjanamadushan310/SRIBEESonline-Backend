"""
Invoice Service — professional PDF invoices for orders (Module 5.6).

Uses ReportLab (platypus) to render a branded, itemized invoice to an in-memory
PDF. ReportLab is an optional import so the app still boots without it; the
invoice endpoints surface a clear 503 when it isn't installed.
"""
from datetime import datetime
from io import BytesIO

from loguru import logger

try:
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

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed. PDF invoice generation disabled.")


# Brand palette (matches the SRIBEES magenta used across the apps).
_BRAND = "#D81B60"
_INK = "#1F1B24"
_MUTED = "#6B6B76"
_LINE = "#E2DFE6"
_FILL = "#FBF3F7"


def _money(value) -> str:
    try:
        return f"Rs. {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "Rs. 0.00"


def _pretty_status(status: str) -> str:
    return (status or "").replace("_", " ").title()


class InvoiceService:
    """Renders order invoices to PDF."""

    @staticmethod
    def generate_invoice_pdf(order, customer=None) -> bytes:
        """
        Build a PDF invoice for *order* and return the raw bytes.

        ``order.items`` and ``order.delivery_address`` must be loaded.
        ``customer`` is a User-like object (full_name/email/phone); if omitted,
        ``order.user`` is used when available.
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("PDF generation is unavailable (reportlab not installed).")

        customer = customer or getattr(order, "user", None)

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=f"Invoice {order.order_number}",
        )

        styles = getSampleStyleSheet()
        brand = colors.HexColor(_BRAND)
        ink = colors.HexColor(_INK)
        muted = colors.HexColor(_MUTED)

        h_brand = ParagraphStyle(
            "Brand", parent=styles["Title"], fontSize=22, textColor=brand,
            spaceAfter=0, leading=24,
        )
        h_invoice = ParagraphStyle(
            "InvoiceLabel", parent=styles["Normal"], fontSize=18, textColor=ink,
            alignment=TA_RIGHT, fontName="Helvetica-Bold",
        )
        label = ParagraphStyle(
            "Label", parent=styles["Normal"], fontSize=8, textColor=muted,
            fontName="Helvetica-Bold", spaceAfter=2,
        )
        body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, textColor=ink, leading=13)
        body_right = ParagraphStyle("BodyRight", parent=body, alignment=TA_RIGHT)
        cell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, textColor=ink, leading=12)
        cell_right = ParagraphStyle("CellRight", parent=cell, alignment=TA_RIGHT)

        elements = []

        # ---- Header: brand + INVOICE ------------------------------------
        header = Table(
            [[Paragraph("SRIBEES<font color='%s'>online</font>" % _INK, h_brand),
              Paragraph("INVOICE", h_invoice)]],
            colWidths=[95 * mm, 79 * mm],
        )
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(header)
        elements.append(Paragraph("Fresh groceries, delivered.", ParagraphStyle(
            "Tagline", parent=body, textColor=muted, fontSize=9)))
        elements.append(Spacer(1, 6 * mm))
        elements.append(Table([[""]], colWidths=[174 * mm], style=TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 1.4, brand),
        ])))
        elements.append(Spacer(1, 5 * mm))

        # ---- Order meta -------------------------------------------------
        created = order.created_at
        created_str = (
            created.strftime("%b %d, %Y %H:%M") if isinstance(created, datetime) else "—"
        )
        meta = Table(
            [
                [Paragraph("ORDER", label), Paragraph("DATE", label), Paragraph("STATUS", label)],
                [
                    Paragraph(order.order_number, body),
                    Paragraph(created_str, body),
                    Paragraph(_pretty_status(order.status), body),
                ],
            ],
            colWidths=[58 * mm, 58 * mm, 58 * mm],
        )
        meta.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_FILL)),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(_LINE)),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta)
        elements.append(Spacer(1, 5 * mm))

        # ---- Bill To / Deliver To --------------------------------------
        cust_name = getattr(customer, "full_name", None) or "Customer"
        cust_email = getattr(customer, "email", None) or ""
        cust_phone = getattr(customer, "phone", None) or ""
        bill_lines = [Paragraph("BILL TO", label), Paragraph(cust_name, body)]
        if cust_email:
            bill_lines.append(Paragraph(cust_email, body))
        if cust_phone:
            bill_lines.append(Paragraph(cust_phone, body))

        addr = getattr(order, "delivery_address", None)
        if addr is not None:
            addr_text = ", ".join(
                str(p) for p in [
                    addr.address_line1, addr.address_line2, addr.post_office,
                    addr.district, addr.province, addr.postal_code,
                ] if p
            )
        else:
            addr_text = "—"
        deliver_lines = [Paragraph("DELIVER TO", label), Paragraph(addr_text, body)]

        bill_to = Table([[c] for c in bill_lines], colWidths=[85 * mm])
        deliver_to = Table([[c] for c in deliver_lines], colWidths=[85 * mm])
        for t in (bill_to, deliver_to):
            t.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]))
        parties = Table([[bill_to, deliver_to]], colWidths=[87 * mm, 87 * mm])
        parties.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        elements.append(parties)
        elements.append(Spacer(1, 6 * mm))

        # ---- Items table -----------------------------------------------
        head_style = ParagraphStyle(
            "Th", parent=cell, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8.5)
        head_right = ParagraphStyle("ThR", parent=head_style, alignment=TA_RIGHT)

        rows = [[
            Paragraph("Product", head_style),
            Paragraph("Variant / SKU", head_style),
            Paragraph("Qty", head_right),
            Paragraph("Unit Price", head_right),
            Paragraph("Total", head_right),
        ]]
        for it in (order.items or []):
            rows.append([
                Paragraph(it.product_name or "—", cell),
                Paragraph(it.product_sku or "—", cell),
                Paragraph(str(it.quantity), cell_right),
                Paragraph(_money(it.unit_price), cell_right),
                Paragraph(_money(it.subtotal), cell_right),
            ])
        if len(rows) == 1:
            rows.append([Paragraph("No items on this order", cell), "", "", "", ""])

        items_table = Table(rows, colWidths=[62 * mm, 44 * mm, 14 * mm, 27 * mm, 27 * mm], repeatRows=1)
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), brand),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor(_LINE)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FCFAFB")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 5 * mm))

        # ---- Totals -----------------------------------------------------
        def total_row(name, value, bold=False, color=None):
            name_style = ParagraphStyle(
                "TotN", parent=body_right,
                fontName="Helvetica-Bold" if bold else "Helvetica",
                textColor=color or ink, fontSize=11 if bold else 9.5,
            )
            val_style = ParagraphStyle(
                "TotV", parent=body_right,
                fontName="Helvetica-Bold" if bold else "Helvetica",
                textColor=color or ink, fontSize=11 if bold else 9.5,
            )
            return [Paragraph(name, name_style), Paragraph(value, val_style)]

        totals_data = [
            total_row("Subtotal", _money(order.subtotal)),
            total_row("Delivery Fee", _money(order.shipping_amount)),
        ]
        if float(order.tax_amount or 0) > 0:
            totals_data.append(total_row("Tax", _money(order.tax_amount)))
        if float(order.discount_amount or 0) > 0:
            totals_data.append(total_row("Discount", f"- {_money(order.discount_amount)}",
                                         color=colors.HexColor("#2E7D32")))
        if float(getattr(order, "wallet_deduction", 0) or 0) > 0:
            totals_data.append(total_row("Wallet Applied", f"- {_money(order.wallet_deduction)}",
                                         color=brand))
        totals_data.append(total_row("Total", _money(order.total_amount), bold=True, color=brand))

        totals = Table(totals_data, colWidths=[42 * mm, 32 * mm])
        totals.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor(_LINE)),
        ]))
        # Right-align the totals block.
        totals_wrap = Table([[totals]], colWidths=[174 * mm])
        totals_wrap.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT")]))
        elements.append(totals_wrap)
        elements.append(Spacer(1, 10 * mm))

        # ---- Footer -----------------------------------------------------
        elements.append(Table([[""]], colWidths=[174 * mm], style=TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor(_LINE)),
        ])))
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            "Thank you for shopping with SRIBEESonline. This is a system-generated "
            "invoice and needs no signature.",
            ParagraphStyle("Footer", parent=body, textColor=muted, fontSize=8.5),
        ))

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        logger.info(f"Invoice PDF generated for order {order.order_number} ({len(pdf)} bytes)")
        return pdf

    @staticmethod
    def filename_for(order) -> str:
        return f"invoice_{order.order_number}.pdf"
