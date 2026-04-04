from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from django.http import FileResponse
import io

def generate_activity_pdf(activities, context):
    """
    Generates a PDF report for employee daily activities.
    
    Args:
        activities: QuerySet of EmployeeDailyActivity objects
        context: Dictionary containing report metadata (title, employee_name, date_range, etc.)
    
    Returns:
        io.BytesIO buffer containing the PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
        alignment=1  # Center alignment
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor("#7f8c8d"),
        spaceAfter=20,
        alignment=1
    )
    
    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        alignment=1
    )
    
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        leading=12
    )
    
    # Report Header
    title = context.get('title', 'Employee Activity Report')
    subtitle = f"Employee: {context.get('employee_name', 'All Employees')} | {context.get('date_range', '')}"
    
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(subtitle, subtitle_style))
    
    # Performance Summary Table
    total_activities = len(activities)
    if total_activities > 0:
        from .utils import calculate_performance_metrics
        metrics = calculate_performance_metrics(activities)
        
        avg_progress = metrics['avg_progress']
        avg_target = metrics['avg_target']
        efficiency = metrics['efficiency']
        
        summary_data = [
            [Paragraph("<b>Performance Metrics</b>", header_style), ""],
            ["Avg. Actual Progress", f"{avg_progress:.1f}%"],
            ["Avg. Target Progress", f"{avg_target:.1f}%"],
            ["Progress Efficiency", f"{efficiency:.1f}%"]
        ]
        summary_table = Table(summary_data, colWidths=[60*mm, 35*mm])
        summary_table.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#34495e")),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        
        # Pull to right
        elements.append(Spacer(1, 5*mm))
        container = Table([[None, summary_table]], colWidths=[75*mm, 95*mm])
        elements.append(container)
        elements.append(Spacer(1, 5*mm))
    
    # Performance Chart
    if len(activities) > 0:
        drawing = Drawing(170*mm, 60*mm)
        bc = VerticalBarChart()
        bc.x = 20
        bc.y = 20
        bc.height = 120
        bc.width = 440
        
        # Data aggregation
        progress_data = []
        target_data = []
        labels = []
        
        # Limit to last 15 activities for chart to keep it readable
        chart_activities = activities[:15]
        # Copy to list for reversing
        chart_list = list(chart_activities)
        chart_list.reverse() # Chronological order
        
        for act in chart_list:
            # Actual Progress
            progress_data.append(100 - (act.pending_work_percentage or 0))
            
            # Target Progress (from previously added logic or new target field)
            # Using act.target_work_percentage if available, otherwise 0
            target_data.append(getattr(act, 'target_work_percentage', 0))
            labels.append(act.date.strftime('%m-%d'))
            
        bc.data = [target_data, progress_data]
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.labels.angle = 45
        bc.categoryAxis.labels.dx = 0
        bc.categoryAxis.labels.dy = -10
        bc.categoryAxis.labels.fontSize = 8
        
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = 100
        bc.valueAxis.valueStep = 20
        
        bc.bars[0].fillColor = colors.HexColor("#bdc3c7") # Target (Light Grey)
        bc.bars[1].fillColor = colors.HexColor("#3498db") # Actual (Blue)
        
        # Legend
        legend = Legend()
        legend.x = 420
        legend.y = 150
        legend.fontSize = 8
        legend.alignment = 'right'
        legend.colorNamePairs = [(colors.HexColor("#bdc3c7"), 'Target %'), (colors.HexColor("#3498db"), 'Actual %')]
        
        drawing.add(bc)
        drawing.add(legend)
        
        elements.append(drawing)
        elements.append(Spacer(1, 10*mm))
    
    elements.append(Spacer(1, 5*mm))
    
    # Table Data
    # Columns: Date, Employee, Project, Role, Team, Description, Status, Target Achieved, Progress
    data = [['Date', 'Employee', 'Project', 'Role', 'Team', 'Description', 'Status', 'Target', 'Progress']]
    
    from .models import ProjectServiceMember, ProjectTeamMember
    
    for activity in activities:
        # Format date
        date_str = activity.date.strftime('%Y-%m-%d')
        
        # Format project name
        project_obj = activity.project
        project_name = (project_obj.name if project_obj else None) or (getattr(activity, 'project_name', None) or "N/A")
        
        # Format Role and Team
        role = str(getattr(activity, 'role', None) or "N/A")
        team_obj = activity.team
        team_name = (team_obj.name if team_obj else None) or "N/A"
        
        # Format description (truncate if too long for PDF cell)
        desc_text = str(activity.description or "")
        description = desc_text[:100] + "..." if len(desc_text) > 100 else desc_text
        
        # Status
        status = "On Time"
        if activity.is_timeline_exceeded:
            status = "Delayed"
            
        # Target Achieved Percentage
        target_achieved_percentage = getattr(activity, 'target_work_percentage', 0)
        target_achieved = f"{target_achieved_percentage}%"

        # Progress (Completed Percentage)
        pending = activity.pending_work_percentage
        completed_percentage = 100 - pending
        progress = f"{completed_percentage}%"
        
        # Employee Info
        employee_name = activity.employee.username if activity.employee else "N/A"
        
        row = [
            Paragraph(date_str, cell_style),
            Paragraph(employee_name, cell_style),
            Paragraph(project_name, cell_style),
            Paragraph(role, cell_style),
            Paragraph(team_name, cell_style),
            Paragraph(description, cell_style),
            Paragraph(status, cell_style),
            Paragraph(target_achieved, cell_style),
            Paragraph(progress, cell_style)
        ]
        data.append(row)
        
    # Table Styling
    # Total available width = 170mm
    # Date(18), Emp(20), Proj(20), Role(18), Team(18), Desc(32), Status(15), Target(14), Prog(15)
    col_widths = [18*mm, 20*mm, 20*mm, 18*mm, 18*mm, 32*mm, 15*mm, 14*mm, 15*mm]
    table = Table(data, colWidths=col_widths)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#34495e")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9), # Slightly smaller font for headers
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 1), (1, -1), 'CENTER'), # Center Date and Employee
        ('ALIGN', (6, 1), (8, -1), 'CENTER'), # Center Status, Target, Progress
    ]))
    
    elements.append(table)
    
    # 3. Project Distribution Pie Chart (If multiple projects)
    from typing import Dict
    project_hours: Dict[str, float] = {}
    for activity in activities:
        p_obj = activity.project
        p_name = (p_obj.name if p_obj else None) or "Other/Unassigned"
        h = float(activity.hours_spent or 0)
        project_hours[p_name] = project_hours.get(p_name, 0.0) + h
    
    if len(project_hours) > 1:
        elements.append(Spacer(1, 15*mm))
        elements.append(Paragraph("<b>Project Time Distribution (Hours)</b>", styles['Normal']))
        elements.append(Spacer(1, 5*mm))
        
        drawing_pie = Drawing(170*mm, 60*mm)
        pc = Pie()
        pc.x = 150
        pc.y = 10
        pc.width = 100
        pc.height = 100
        pc.data = list(project_hours.values())
        pc.labels = list(project_hours.keys())
        pc.sideLabels = True
        
        # Color palette
        colors_list = [colors.HexColor("#3498db"), colors.HexColor("#2ecc71"), colors.HexColor("#e67e22"), colors.HexColor("#9b59b6"), colors.HexColor("#f1c40f")]
        for i in range(len(pc.data)):
            pc.slices[i].fillColor = colors_list[i % len(colors_list)]
            
        drawing_pie.add(pc)
        elements.append(drawing_pie)

    # Footer / Summary
    elements.append(Spacer(1, 10*mm))
    summary_text = f"Total Activities: {len(activities)}"
    elements.append(Paragraph(summary_text, subtitle_style))
    
    doc.build(elements)
    buffer.seek(0)
    
    return buffer

def generate_invoice_pdf(invoice):
    """
    Generates a PDF for an invoice.
    """
    from .models import CompanyProfile
    from reportlab.platypus import Image
    import os
    from django.conf import settings
    
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
    
    # Custom Styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
        alignment=2 # Right align
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#2c3e50"),
        leading=14
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        leading=12
    )
    
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        leading=12
    )

    company = CompanyProfile.objects.first()
    
    # Header Layout: Logo (Left) and Invoice Title (Right)
    header_data = []
    logo_path = None
    if company and company.logo:
        # Construct absolute path for the logo
        logo_path = os.path.join(settings.MEDIA_ROOT, str(company.logo))
        if os.path.exists(logo_path):
            img = Image(logo_path, width=40*mm, height=15*mm, kind='proportional')
            header_data = [[img, Paragraph("INVOICE", title_style)]]
        else:
            header_data = [["", Paragraph("INVOICE", title_style)]]
    else:
        header_data = [["", Paragraph("INVOICE", title_style)]]

    header_table = Table(header_data, colWidths=[100*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10*mm))
    
    # 2. Information Section (Company Details & Client Details)
    company_name = company.company_name if company else "Extechnology"
    company_type = company.company_type if company else ""
    company_email = company.email if company else ""
    company_phone = company.phone if company else ""
    company_address = company.address if company else ""
    
    company_info_list = [
        [Paragraph(f"<b>{company_name}</b>", value_style)],
        [Paragraph(str(company_address), value_style)] if company_address else [],
        [Paragraph(f"Email: {company_email}", value_style)] if company_email else [],
        [Paragraph(f"Phone: {company_phone}", value_style)] if company_phone else [],
    ]
    # Filter out empty rows
    company_info_list = [row for row in company_info_list if row]
    
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
    
    client_info_list = [
        [Paragraph("<b>BILL TO:</b>", label_style)],
        [Paragraph(str(client_name), value_style)],
    ]
    if client_address:
        client_info_list.append([Paragraph(str(client_address), value_style)])
    
    # Invoice Details Section
    inv_details_list = [
        [Paragraph("Invoice #:", label_style), Paragraph(str(invoice.invoice_number or "N/A"), value_style)],
        [Paragraph("Date:", label_style), Paragraph(invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else "N/A", value_style)],
        [Paragraph("Due Date:", label_style), Paragraph(invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else "N/A", value_style)],
        [Paragraph("Status:", label_style), Paragraph(str(invoice.status or "N/A"), value_style)],
    ]

    info_table_data = [
        [Table(company_info_list, colWidths=[90*mm]), Table(client_info_list, colWidths=[90*mm])]
    ]
    info_table = Table(info_table_data, colWidths=[95*mm, 85*mm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8*mm))
    
    # Smaller Detail Table for Invoice #/Date
    details_table = Table(inv_details_list, colWidths=[30*mm, 50*mm], hAlign='LEFT')
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 15*mm))
    
    # 3. Items Table
    data = [['Service Type', 'Description', 'Purchase Date', 'Expiry Date', 'Rate', 'Qty', 'Total']]
    for item in invoice.items.all():
        data.append([
            Paragraph(str(item.service_type or "N/A"), cell_style),
            Paragraph(str(item.description or ""), cell_style),
            item.purchase_date.strftime('%Y-%m-%d') if item.purchase_date else "N/A",
            item.expairy_date.strftime('%Y-%m-%d') if item.expairy_date else "N/A",
            f"{item.rate:.2f}",
            str(item.quantity),
            f"{item.total_price:.2f}"
        ])
        
    col_widths = [35*mm, 45*mm, 28*mm, 28*mm, 20*mm, 12*mm, 22*mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    header_color = colors.HexColor("#2c3e50")
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10*mm))
    
    # 4. Totals (Right Aligned Table)
    totals_data = [
        [Paragraph("Subtotal:", label_style), f"{invoice.subtotal:.2f}"],
        [Paragraph(f"Tax ({invoice.tax_rate}%):", label_style), f"{invoice.tax_amount:.2f}"],
        [Paragraph("Discount:", label_style), f"-{invoice.discount_amount:.2f}"],
        [Paragraph("Total Amount:", label_style), f"{invoice.total_amount:.2f}"],
        [Paragraph("Total Paid:", label_style), f"{invoice.total_paid:.2f}"],
        [Paragraph("Balance Due:", label_style), f"{invoice.balance_due:.2f}"],
    ]
    
    totals_table = Table(totals_data, colWidths=[40*mm, 30*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (1, 3), (1, 3), 1, colors.black),
        ('FONTNAME', (1, 3), (1, 3), 'Helvetica-Bold'),
        ('LINEABOVE', (1, 5), (1, 5), 1, colors.black),
        ('FONTNAME', (1, 5), (1, 5), 'Helvetica-Bold'),
    ]))
    
    # Use a container table to push totals to the right
    container_data = [[None, totals_table]]
    container_table = Table(container_data, colWidths=[110*mm, 70*mm])
    elements.append(container_table)
    
    # 5. Footer
    elements.append(Spacer(1, 40*mm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor("#7f8c8d"),
        alignment=1 # Center
    )
    elements.append(Paragraph("<b>THANK YOU FOR YOUR BUSINESS!</b>", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def _create_financial_pdf_base(title, data_sections, context, total_text, total_val):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#2c3e50"), spaceAfter=12, alignment=1
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#7f8c8d"), spaceAfter=20, alignment=1
    )
    cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=10, textColor=colors.black, leading=14)
    bold_style = ParagraphStyle('TableBold', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', textColor=colors.black, leading=14)

    elements.append(Paragraph(f"<b>{title}</b>", title_style))
    
    start_date = context.get('start_date')
    end_date = context.get('end_date')
    month = context.get('month')
    year = context.get('year')
    
    date_str = ""
    if start_date and end_date:
        date_str = f"Period: {start_date} to {end_date}"
    elif month and year:
        date_str = f"Period: {year}-{month}"
    elif year:
        date_str = f"Year: {year}"
    elif end_date:
        date_str = f"As of: {end_date}"
    
    if date_str:
        elements.append(Paragraph(date_str, subtitle_style))
        
    table_data = []
    
    for section_title, rows, sec_total_text, sec_total_val in data_sections:
        table_data.append([Paragraph(f"<b>{section_title}</b>", bold_style), ""])
        for label, val in rows:
            formatted_val = f"{float(val):,.2f}" if val is not None else "0.00"
            table_data.append([Paragraph(label, cell_style), formatted_val])
        
        formatted_sec_total = f"{float(sec_total_val):,.2f}" if sec_total_val is not None else "0.00"
        table_data.append([Paragraph(f"<b>{sec_total_text}</b>", bold_style), formatted_sec_total])
        table_data.append(["", ""]) # spacer

    formatted_total = f"{float(total_val):,.2f}" if total_val is not None else "0.00"
    table_data.append([Paragraph(f"<b>{total_text}</b>", bold_style), formatted_total])

    table = Table(table_data, colWidths=[120*mm, 50*mm])
    table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.black), # Line above final total
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_income_statement_pdf(data, context):
    revenue = data['revenue']
    expenses = data['expenses']
    net_income = data['net_income']
    
    sections = [
        ("Revenue", [
            ("Invoices Revenue", revenue['invoices']),
            ("Other Income", revenue['other_income'])
        ], "Total Revenue", revenue['total_revenue']),
        ("Expenses", [
            ("Salaries", expenses['salaries']),
            ("Other Expenses", expenses['other_expenses']),
            ("Domains and Servers", expenses['domains_and_servers'])
        ], "Total Expenses", expenses['total_expenses'])
    ]
    
    return _create_financial_pdf_base("INCOME STATEMENT", sections, context, "Net Income", net_income)

def generate_cash_flow_statement_pdf(data, context):
    cash_in = data['cash_in']
    cash_out = data['cash_out']
    net_flow = data['net_cash_flow']
    
    sections = [
        ("Cash Inflows", [
            ("Invoice Payments Received", cash_in['invoice_payments']),
            ("Other Income Received", cash_in['other_income']),
            ("Client Advances Received", cash_in['client_advances'])
        ], "Total Cash Inflows", cash_in['total_cash_in']),
        ("Cash Outflows", [
            ("Salaries Paid", cash_out['salaries_paid']),
            ("Other Expenses Paid", cash_out['other_expenses']),
            ("Domains & Servers Paid", cash_out['domains_servers_paid'])
        ], "Total Cash Outflows", cash_out['total_cash_out'])
    ]
    
    return _create_financial_pdf_base("CASH FLOW STATEMENT", sections, context, "Net Cash Flow", net_flow)

def generate_balance_sheet_pdf(data, context):
    assets = data['assets']
    liabilities = data['liabilities']
    equity = data['equity']
    
    sections = [
        ("Assets", [
            ("Cash and Equivalents", assets['cash_on_hand']),
            ("Accounts Receivable", assets['accounts_receivable'])
        ], "Total Assets", assets['total_assets']),
        ("Liabilities", [
            ("Accounts Payable", liabilities['accounts_payable']),
            ("Client Advances (Unearned Revenue)", liabilities['client_advances'])
        ], "Total Liabilities", liabilities['total_liabilities']),
        ("Equity", [
            ("Retained Earnings", equity['retained_earnings'])
        ], "Total Equity", equity['total_equity'])
    ]
    
    # Check accounting equation
    return _create_financial_pdf_base("BALANCE SHEET", sections, context, "Total Liabilities & Equity", liabilities['total_liabilities'] + equity['total_equity'])


