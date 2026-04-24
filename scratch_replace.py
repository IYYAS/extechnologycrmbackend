import re
import os

file_path = r"e:\djangosimplemission\djangosimplemission\djangosimplemissionapp\pdf_utils.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

start_idx = content.find("def generate_invoice_pdf(invoice):")
end_idx = content.find("def _create_financial_pdf_base")

if start_idx == -1 or end_idx == -1:
    print("Could not find boundaries.")
    exit(1)

new_func = """def generate_invoice_pdf(invoice):
    \"\"\"
    Generates a PDF for an invoice with a modern SaaS / Premium aesthetic.
    \"\"\"
    from .models import CompanyProfile
    from reportlab.platypus import Image, Spacer, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate
    import os
    from django.conf import settings
    import io
    
    # 1. Accent Colors
    ACCENT_COLOR = colors.HexColor("#4F46E5") # Indigo
    BG_LIGHT = colors.HexColor("#F8FAFC")     # Slate 50
    BG_HOVER = colors.HexColor("#F1F5F9")     # Slate 100
    TEXT_MAIN = colors.HexColor("#1E293B")    # Slate 800
    TEXT_MUTED = colors.HexColor("#64748B")   # Slate 500
    BORDER_COLOR = colors.HexColor("#E2E8F0") # Slate 200

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    company = CompanyProfile.objects.first()

    # --- Header (Accent Strip) ---
    header_data = []
    
    logo_img = ""
    if company and company.logo:
        logo_path = os.path.join(settings.MEDIA_ROOT, str(company.logo))
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=45*mm, height=18*mm, kind='proportional')

    right_header = Paragraph(
        f"<b>INVOICE</b><br/><font size='12' color='#E0E7FF'>#{invoice.invoice_number or 'N/A'}</font>", 
        ParagraphStyle('InvTitle', fontSize=26, textColor=colors.white, alignment=2, leading=28)
    )
    
    header_table = Table([[logo_img, right_header]], colWidths=[90*mm, 90*mm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), ACCENT_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 8*mm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8*mm),
        ('LEFTPADDING', (0,0), (-1,-1), 8*mm),
        ('RIGHTPADDING', (0,0), (-1,-1), 8*mm),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8*mm))
    
    # --- Detail Cards (FROM and BILL TO) ---
    meta_label = ParagraphStyle('MetaLbl', fontSize=8, textColor=TEXT_MUTED, fontName='Helvetica-Bold', spaceAfter=3)
    meta_val = ParagraphStyle('MetaVal', fontSize=9, textColor=TEXT_MAIN, leading=14)
    
    # FROM
    company_name = company.company_name if company else "Extechnology"
    from_lines = [f"<font size='8' color='{TEXT_MUTED}'><b>FROM</b></font>"]
    from_lines.append(f"<font size='11' color='{ACCENT_COLOR}'><b>{company_name}</b></font>")
    if company and company.address: from_lines.append(str(company.address))
    from_html = "<br/>".join(from_lines)
    from_data = [[Paragraph(from_html, meta_val)]]
    
    from_table = Table(from_data, colWidths=[85*mm])
    from_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4*mm),
    ]))

    # TO
    client = invoice.client_company
    client_name = client.legal_name if client else "N/A"
    address_parts = []
    if client:
        parts = [client.unit_or_floor, client.building_name, client.street_name, client.city]
        address_parts = [p.strip() for p in parts if p and p.strip()]
        state_pin = ""
        if client.state and client.state.strip():
            state_pin = client.state.strip()
            if client.pin_code and client.pin_code.strip():
                state_pin += f" - {client.pin_code.strip()}"
        elif client.pin_code and client.pin_code.strip():
            state_pin = client.pin_code.strip()
        if state_pin:
            address_parts.append(state_pin)
    client_address = ", ".join(address_parts)
    
    to_lines = [f"<font size='8' color='{TEXT_MUTED}'><b>BILL TO</b></font>"]
    to_lines.append(f"<font size='11'><b>{client_name}</b></font>")
    if client_address: to_lines.append(str(client_address))
    to_html = "<br/>".join(to_lines)
    to_data = [[Paragraph(to_html, meta_val)]]
    
    to_table = Table(to_data, colWidths=[85*mm])
    to_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4*mm),
    ]))

    cards_table = Table([[from_table, "", to_table]], colWidths=[85*mm, 10*mm, 85*mm])
    cards_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(cards_table)
    elements.append(Spacer(1, 4*mm))
    
    # --- Invoice Dates/Status Strip ---
    inv_date_str = invoice.invoice_date.strftime('%b %d, %Y') if invoice.invoice_date else "N/A"
    due_date_str = invoice.due_date.strftime('%b %d, %Y') if invoice.due_date else "N/A"
    
    dates_table = Table([
        [
            Paragraph("<b>Issue Date:</b>", meta_label), Paragraph(inv_date_str, meta_val),
            Paragraph("<b>Due Date:</b>", meta_label), Paragraph(due_date_str, meta_val),
        ]
    ], colWidths=[20*mm, 40*mm, 20*mm, 40*mm])
    dates_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(dates_table)
    elements.append(Spacer(1, 6*mm))
    
    # --- Items Table ---
    data = [['Service / Item', 'Description', 'Period', 'Rate', 'Qty', 'Total']]
    for item in invoice.items.all():
        period_str = ""
        if item.purchase_date and item.expairy_date:
            period_str = f"{item.purchase_date.strftime('%y/%m/%d')} - {item.expairy_date.strftime('%y/%m/%d')}"
            
        data.append([
            Paragraph(str(item.service_type or "N/A"), meta_val),
            Paragraph(str(item.description or ""), ParagraphStyle('ItemDesc', fontSize=9, textColor=TEXT_MUTED)),
            Paragraph(period_str, ParagraphStyle('ItemPer', fontSize=9, textColor=TEXT_MUTED)),
            f"{item.rate:.2f}",
            str(item.quantity),
            f"{item.total_price:.2f}"
        ])
        
    col_widths = [35*mm, 45*mm, 40*mm, 22*mm, 13*mm, 25*mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), BG_HOVER),
        ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_MAIN),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'), # Aligns Rate, Qty, Total to right
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_MAIN),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
    ]
    
    # Alternating row colors
    for i in range(1, len(data)):
        bg = colors.white if i % 2 == 1 else BG_LIGHT
        ts.append(('BACKGROUND', (0, i), (-1, i), bg))
        ts.append(('LINEBELOW', (0, i), (-1, i), 0.5, BG_HOVER))
        
    table.setStyle(TableStyle(ts))
    elements.append(table)
    elements.append(Spacer(1, 6*mm))
    
    # --- Bottom Area ---
    # 1. Totals Table
    totals_label = ParagraphStyle('TLbl', fontSize=9, textColor=TEXT_MUTED, alignment=0)
    totals_val = ParagraphStyle('TVal', fontSize=9, textColor=TEXT_MAIN, alignment=2, fontName='Helvetica-Bold')

    totals_data = [
        [Paragraph("Subtotal", totals_label), Paragraph(f"{invoice.subtotal:.2f}", totals_val)],
        [Paragraph(f"Tax ({invoice.tax_rate}%)", totals_label), Paragraph(f"{invoice.tax_amount:.2f}", totals_val)],
    ]
    if invoice.discount_amount > 0:
        totals_data.append([Paragraph("Discount", totals_label), Paragraph(f"-{invoice.discount_amount:.2f}", totals_val)])
        
    totals_data.extend([
        [Paragraph("Total Amount", totals_label), Paragraph(f"{invoice.total_amount:.2f}", totals_val)],
        [Paragraph("Total Paid", totals_label), Paragraph(f"{invoice.total_paid:.2f}", totals_val)],
    ])
    
    # Highlighted Balance Due inside the same table
    bal_lbl = Paragraph("<b>Balance Due</b>", ParagraphStyle('BalL', fontSize=10, textColor=colors.white))
    bal_val = Paragraph(f"<b>{invoice.balance_due:.2f}</b>", ParagraphStyle('BalV', fontSize=12, textColor=colors.white, alignment=2))
    totals_data.append([bal_lbl, bal_val])
    
    totals_table = Table(totals_data, colWidths=[40*mm, 40*mm])
    
    tt_style = [
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-2), 2),
        ('TOPPADDING', (0,0), (-1,-2), 2),
        ('LINEBELOW', (0,-3), (-1,-3), 1, BORDER_COLOR), # Line above Total Amount
        ('BACKGROUND', (0,-1), (-1,-1), ACCENT_COLOR),   # Blue background for Balance Due row
        ('TOPPADDING', (0,-1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 4),
    ]
    totals_table.setStyle(TableStyle(tt_style))
    
    # Wrap in container to push totals to right
    bottom_container = Table([["", totals_table]], colWidths=[100*mm, 80*mm])
    bottom_container.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(bottom_container)
    
    elements.append(Spacer(1, 10*mm))
    
    # 2. Payment Details (Full Width Block)
    bank_lines = []
    if company and company.bank_name: bank_lines.append(f"<b>Bank:</b> {company.bank_name}")
    if company and company.account_name: bank_lines.append(f"<b>Name:</b> {company.account_name}")
    if company and company.account_number: bank_lines.append(f"<b>A/C No:</b> {company.account_number}")
    if company and company.ifsc_code: bank_lines.append(f"<b>IFSC:</b> {company.ifsc_code}")
    if company and company.upi_id: bank_lines.append(f"<b>UPI:</b> {company.upi_id}")
    
    bank_html = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(bank_lines)
    
    bank_data = [
        [Paragraph(f"<font size='9' color='{ACCENT_COLOR}'><b>Payment Information</b></font>", meta_val)],
        [Paragraph(bank_html, meta_val)]
    ]

    bank_table = Table(bank_data, colWidths=[180*mm])
    bank_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4*mm),
    ]))
    elements.append(bank_table)
    
    # --- Footer ---
    elements.append(Spacer(1, 10*mm))
    
    line_table = Table([['']], colWidths=[180*mm])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 0.5, ACCENT_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(line_table)
    
    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontSize=11,
        textColor=ACCENT_COLOR,
        fontName='Helvetica-Bold',
        alignment=1 # Center
    )
    elements.append(Paragraph("Thank you for your business!", footer_style))
    
    contact_parts = []
    if company and company.email:
        contact_parts.append(company.email)
    if company and company.phone:
        contact_parts.append(company.phone)
        
    if contact_parts:
        contact_str = " | ".join(contact_parts)
        contact_style = ParagraphStyle(
            'FooterContact',
            parent=styles['Normal'],
            fontSize=9,
            textColor=TEXT_MUTED,
            alignment=1 # Center
        )
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(contact_str, contact_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
"""

final_content = content[:start_idx] + new_func + content[end_idx:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(final_content)

print("Replaced generate_invoice_pdf successfully.")
