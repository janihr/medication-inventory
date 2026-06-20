# File: pdf.py
import io
from datetime import datetime
from xml.sax.saxutils import escape

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

from .models import UserProfile


def generate_order_pdf(order):
    """Generate a PDF for the given order and return an HttpResponse."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # --- Custom Styles ---
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=6 * mm,
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=4 * mm,
        spaceBefore=6 * mm,
    )

    normal_style = styles['Normal']

    cell_style = ParagraphStyle(
        'CellStyle',
        parent=normal_style,
        fontSize=9,
        leading=11,
    )

    # --- Title ---
    elements.append(Paragraph("Order", title_style))
    elements.append(Spacer(1, 4 * mm))

    # --- Ordering Person (From) Section ---
    profile = UserProfile.get_profile()
    has_profile = any([
        profile.name, profile.organization, profile.address_line1,
        profile.city, profile.phone, profile.email
    ])

    if has_profile:
        elements.append(Paragraph("From (Ordering Party)", heading_style))

        from_data = []
        if profile.organization:
            from_data.append(["Organization:", profile.organization])
        if profile.name:
            from_data.append(["Name:", profile.name])
        if profile.address_line1:
            from_data.append(["Address:", profile.address_line1])
        if profile.address_line2:
            from_data.append(["", profile.address_line2])
        if profile.postal_code or profile.city:
            city_line = f"{profile.postal_code} {profile.city}".strip()
            from_data.append(["", city_line])
        if profile.phone:
            from_data.append(["Phone:", profile.phone])
        if profile.email:
            from_data.append(["Email:", profile.email])
        if profile.customer_number:
            from_data.append(["Customer No.:", profile.customer_number])

        if from_data:
            from_table = Table(from_data, colWidths=[3.5 * cm, 10.5 * cm])
            from_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
            ]))
            elements.append(from_table)
            elements.append(Spacer(1, 6 * mm))

    # --- Order Info Table ---
    order_info_data = [
        ["Order ID:", order.order_id],
        ["Date:", order.created_at.strftime("%d.%m.%Y %H:%M")],
        ["Status:", order.get_status_display()],
    ]

    order_info_table = Table(order_info_data, colWidths=[4 * cm, 10 * cm])
    order_info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(order_info_table)
    elements.append(Spacer(1, 6 * mm))

    # --- Supplier Section (To) ---
    elements.append(Paragraph("To (Supplier)", heading_style))

    supplier = order.supplier
    supplier_data = [
        ["Name:", supplier.name],
    ]
    if supplier.phone_number:
        supplier_data.append(["Phone:", supplier.phone_number])
    if supplier.email:
        supplier_data.append(["Email:", supplier.email])

    supplier_table = Table(supplier_data, colWidths=[4 * cm, 10 * cm])
    supplier_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(supplier_table)
    elements.append(Spacer(1, 8 * mm))

    # --- Order Items Section ---
    elements.append(Paragraph("Ordered Items", heading_style))

    items = order.items.select_related('medicine_item').all()

    if items.exists():
        # Table Header using Paragraphs for consistency
        header_style = ParagraphStyle(
            'HeaderCellStyle',
            parent=normal_style,
            fontSize=9,
            leading=11,
            textColor=colors.white,
            fontName='Helvetica-Bold',
        )

        table_data = [
            [
                Paragraph("#", header_style),
                Paragraph("Name", header_style),
                Paragraph("PZN", header_style),
                Paragraph("Package Size", header_style),
                Paragraph("Amount", header_style),
                Paragraph("Note", header_style),
            ]
        ]

        # Table Rows - use Paragraph for Note column to enable text wrapping
        for idx, item in enumerate(items, start=1):
            note_text = escape(item.note) if item.note else "-"
            table_data.append([
                Paragraph(str(idx), cell_style),
                Paragraph(escape(item.medicine_item.name), cell_style),
                Paragraph(escape(item.medicine_item.pzn or "-"), cell_style),
                Paragraph(escape(item.medicine_item.package_size or "-"), cell_style),
                Paragraph(str(item.amount), cell_style),
                Paragraph(note_text, cell_style),
            ])

        # Column widths
        col_widths = [1 * cm, 4.5 * cm, 2.2 * cm, 2.8 * cm, 1.5 * cm, 5 * cm]

        items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        items_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

            # Body
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),

            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(items_table)
    else:
        elements.append(Paragraph("No items in this order.", normal_style))

    # --- Footer ---
    elements.append(Spacer(1, 15 * mm))
    footer_text = f"Generated on {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    footer_style = ParagraphStyle(
        'Footer',
        parent=normal_style,
        fontSize=8,
        textColor=colors.grey,
    )
    elements.append(Paragraph(footer_text, footer_style))

    # --- Build PDF ---
    doc.build(elements)

    # Return as HTTP response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f"order_{order.order_id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response