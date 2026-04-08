from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Sum, Q, Min, Max
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import FileResponse

from .models import (
    Invoice, OtherIncome, Salary, OtherExpense, ProjectDomain, ProjectServer, 
    Payment, ClientAdvance, Project, ProjectService, ProjectServiceTeam, ProjectTeam
)
from .pdf_utils import generate_income_statement_pdf, generate_cash_flow_statement_pdf, generate_balance_sheet_pdf

def get_financial_date_filter(request, date_field='date'):
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    month = request.query_params.get('month')
    year = request.query_params.get('year')
    filter_type = request.query_params.get('filter_type')

    q = Q()
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            q &= Q(**{f"{date_field}__range": [start, end]})
        except ValueError:
            pass
    elif month and year:
        try:
            q &= Q(**{f"{date_field}__year": int(year), f"{date_field}__month": int(month)})
        except ValueError:
            pass
    elif year:
        try:
            q &= Q(**{f"{date_field}__year": int(year)})
        except ValueError:
            pass
    elif filter_type:
        from .utils import get_date_filter_q
        filter_q = get_date_filter_q(filter_type, date_field)
        if isinstance(filter_q, tuple): # some error handling in get_date_filter_q
            q &= filter_q[0] if filter_q[0] else Q()
        else:
            q &= filter_q
            
    return q

class IncomeStatementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Revenue
        invoice_q = get_financial_date_filter(request, 'invoice_date')
        other_income_q = get_financial_date_filter(request, 'date')
        
        invoices = Invoice.objects.filter(invoice_q)
        other_incomes = OtherIncome.objects.filter(other_income_q)
        
        invoice_revenue = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        other_revenue = other_incomes.aggregate(total=Sum('amount'))['total'] or 0
        total_revenue = invoice_revenue + other_revenue

        # Expenses
        salary_q = get_financial_date_filter(request, 'start_date')
        expense_q = get_financial_date_filter(request, 'date')
        domain_q = get_financial_date_filter(request, 'purchase_date')
        
        salaries = Salary.objects.filter(salary_q)
        other_expenses = OtherExpense.objects.filter(expense_q)
        domains = ProjectDomain.objects.filter(domain_q)
        servers = ProjectServer.objects.filter(domain_q)

        salary_expense = sum([(s.basic + s.bonus - s.deductions) for s in salaries])
        other_expense_total = other_expenses.aggregate(total=Sum('amount'))['total'] or 0
        domain_expense = domains.aggregate(total=Sum('cost'))['total'] or 0
        server_expense = servers.aggregate(total=Sum('cost'))['total'] or 0
        
        total_expenses = salary_expense + other_expense_total + domain_expense + server_expense
        
        net_income = total_revenue - total_expenses
        
        data = {
            'revenue': {
                'invoices': invoice_revenue,
                'other_income': other_revenue,
                'total_revenue': total_revenue
            },
            'expenses': {
                'salaries': salary_expense,
                'other_expenses': other_expense_total,
                'domains_and_servers': domain_expense + server_expense,
                'total_expenses': total_expenses
            },
            'net_income': net_income
        }

        if request.query_params.get('export') == 'pdf':
            buffer = generate_income_statement_pdf(data, request.query_params)
            return FileResponse(buffer, as_attachment=True, filename='Income_Statement.pdf')
            
        return Response(data)

class CashFlowStatementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payment_q = get_financial_date_filter(request, 'payment_date')
        income_q = get_financial_date_filter(request, 'date')
        advance_q = get_financial_date_filter(request, 'created_at')

        # Cash In
        payments = Payment.objects.filter(payment_q).aggregate(total=Sum('amount'))['total'] or 0
        other_income = OtherIncome.objects.filter(income_q).aggregate(total=Sum('amount'))['total'] or 0
        advances = ClientAdvance.objects.filter(advance_q).aggregate(total=Sum('amount'))['total'] or 0
        
        total_cash_in = payments + other_income + advances

        # Cash Out
        expense_q = get_financial_date_filter(request, 'date')
        salary_q = get_financial_date_filter(request, 'start_date')
        domain_q = get_financial_date_filter(request, 'purchase_date')

        other_expenses = OtherExpense.objects.filter(expense_q).aggregate(total=Sum('amount'))['total'] or 0
        
        # Only Paid salaries in period
        paid_salaries = Salary.objects.filter(salary_q, status='Paid')
        salary_out = sum([(s.basic + s.bonus - s.deductions) for s in paid_salaries])
        
        domains_paid = ProjectDomain.objects.filter(domain_q, payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
        servers_paid = ProjectServer.objects.filter(domain_q, payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
        
        total_cash_out = other_expenses + salary_out + domains_paid + servers_paid
        
        net_cash_flow = total_cash_in - total_cash_out

        data = {
            'cash_in': {
                'invoice_payments': payments,
                'other_income': other_income,
                'client_advances': advances,
                'total_cash_in': total_cash_in
            },
            'cash_out': {
                'salaries_paid': salary_out,
                'other_expenses': other_expenses,
                'domains_servers_paid': domains_paid + servers_paid,
                'total_cash_out': total_cash_out
            },
            'net_cash_flow': net_cash_flow
        }
        
        if request.query_params.get('export') == 'pdf':
            buffer = generate_cash_flow_statement_pdf(data, request.query_params)
            return FileResponse(buffer, as_attachment=True, filename='Cash_Flow_Statement.pdf')
            
        return Response(data)

class BalanceSheetView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Balance sheet is typically a snapshot at a point in time. 
        # If an end_date is provided, we use it as the "as of" date.
        end_date_str = request.query_params.get('end_date')
        
        # Assets
        # 1. Cash (All-time Cash In - All-time Cash Out, up to end_date)
        # Simplified: Net Cash Flow up to Date
        cash_in_q = Q()
        cash_out_q = Q()

        invoice_q = Q()
        salary_q = Q()
        advance_q = Q()
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                cash_in_q &= Q(payment_date__date__lte=end_date)
                cash_out_q &= Q(date__lte=end_date)
                invoice_q &= Q(invoice_date__lte=end_date)
                salary_q &= Q(start_date__lte=end_date)
                advance_q &= Q(created_at__date__lte=end_date)
            except ValueError:
                pass

        # Cash Calculation (Simplified to use the cash flow logic but all-time/up-to-date)
        payments = Payment.objects.filter(cash_in_q).aggregate(total=Sum('amount'))['total'] or 0
        other_income = OtherIncome.objects.filter(cash_out_q).aggregate(total=Sum('amount'))['total'] or 0
        advances = ClientAdvance.objects.filter(advance_q).aggregate(total=Sum('amount'))['total'] or 0
        total_cash_in = payments + other_income + advances
        
        other_exp = OtherExpense.objects.filter(cash_out_q).aggregate(total=Sum('amount'))['total'] or 0
        # Salaries Paid up to date
        sals_paid = sum([(s.basic + s.bonus - s.deductions) for s in Salary.objects.filter(salary_q, status='Paid')])
        
        domain_cost = ProjectDomain.objects.filter(payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
        if end_date_str:
             domain_cost = ProjectDomain.objects.filter(purchase_date__lte=end_date, payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
             
        server_cost = ProjectServer.objects.filter(payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
        if end_date_str:
             server_cost = ProjectServer.objects.filter(purchase_date__lte=end_date, payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0

        total_cash_out = other_exp + sals_paid + domain_cost + server_cost
        cash_on_hand = total_cash_in - total_cash_out

        # Accounts Receivable (Balances due on Invoices up to date)
        accounts_receivable = Invoice.objects.filter(invoice_q).aggregate(total=Sum('balance_due'))['total'] or 0

        total_assets = cash_on_hand + accounts_receivable

        # Liabilities
        # Accounts Payable (Unpaid Salaries, Unpaid Domains/Servers)
        unpaid_sals = sum([(s.basic + s.bonus - s.deductions) for s in Salary.objects.filter(salary_q).exclude(status='Paid')])
        
        unpaid_domains = ProjectDomain.objects.filter(payment_status='UNPAID').aggregate(total=Sum('cost'))['total'] or 0
        if end_date_str:
            unpaid_domains = ProjectDomain.objects.filter(purchase_date__lte=end_date, payment_status='UNPAID').aggregate(total=Sum('cost'))['total'] or 0
            
        unpaid_servers = ProjectServer.objects.filter(payment_status='UNPAID').aggregate(total=Sum('cost'))['total'] or 0
        if end_date_str:
            unpaid_servers = ProjectServer.objects.filter(purchase_date__lte=end_date, payment_status='UNPAID').aggregate(total=Sum('cost'))['total'] or 0
            
        accounts_payable = unpaid_sals + unpaid_domains + unpaid_servers

        # Unearned Revenue / Advances Remaining
        advances_remaining = ClientAdvance.objects.filter(advance_q).aggregate(total=Sum('remaining_amount'))['total'] or 0

        total_liabilities = accounts_payable + advances_remaining

        # Equity (Retained Earnings = Net Income all time up to date)
        invoice_rev = Invoice.objects.filter(invoice_q).aggregate(total=Sum('total_amount'))['total'] or 0
        total_rev = invoice_rev + other_income
        
        salary_exp = sum([(s.basic + s.bonus - s.deductions) for s in Salary.objects.filter(salary_q)])
        domain_exp = ProjectDomain.objects.filter().aggregate(total=Sum('cost'))['total'] or 0
        server_exp = ProjectServer.objects.filter().aggregate(total=Sum('cost'))['total'] or 0
        
        if end_date_str:
            domain_exp = ProjectDomain.objects.filter(purchase_date__lte=end_date).aggregate(total=Sum('cost'))['total'] or 0
            server_exp = ProjectServer.objects.filter(purchase_date__lte=end_date).aggregate(total=Sum('cost'))['total'] or 0
            
        total_exp = salary_exp + other_exp + domain_exp + server_exp
        
        retained_earnings = total_rev - total_exp
        total_equity = retained_earnings

        data = {
            'assets': {
                'cash_on_hand': cash_on_hand,
                'accounts_receivable': accounts_receivable,
                'total_assets': total_assets
            },
            'liabilities': {
                'accounts_payable': accounts_payable,
                'client_advances': advances_remaining,
                'total_liabilities': total_liabilities
            },
            'equity': {
                'retained_earnings': retained_earnings,
                'total_equity': total_equity
            }
        }
        
        if request.query_params.get('export') == 'pdf':
            buffer = generate_balance_sheet_pdf(data, request.query_params)
            return FileResponse(buffer, as_attachment=True, filename='Balance_Sheet.pdf')

        return Response(data)

class ProjectAnalyticalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import Project, ProjectService, ProjectFinance, ProjectTeam, ProjectServiceTeam
        from rest_framework.pagination import PageNumberPagination
        
        projects = Project.objects.prefetch_related(
            'services', 'project_finances', 'project_teams__team'
        ).order_by('-created_at')
        
        # 1. Search Filter
        search_query = request.query_params.get('search', '')
        if search_query:
            projects = projects.filter(name__icontains=search_query)
            
        # 2. Date Filter
        date_q = get_financial_date_filter(request, 'created_at')
        if date_q:
            projects = projects.filter(date_q)

        # 3. Status Filter (New Interactivity)
        status_filter = request.query_params.get('status', '').lower()
        if status_filter:
            if status_filter == 'pending':
                projects = projects.filter(status__iexact='pending')
            elif status_filter == 'progressing':
                projects = projects.exclude(status__iexact='completed').exclude(status__iexact='done').exclude(status__iexact='pending')
            elif status_filter == 'completed':
                projects = projects.filter(Q(status__iexact='completed') | Q(status__iexact='done'))

        # 4. Payment Status Filter
        payment_status_filter = request.query_params.get('payment_status', '').lower()
        if payment_status_filter:
            unpaid_q = (
                Q(project_finances__total_balance_due__gt=0) |
                Q(project_domains__payment_status='UNPAID') |
                Q(project_servers__payment_status='UNPAID') |
                Q(services__payment_status='UNPAID')
            )
            if payment_status_filter == 'unpaid':
                projects = projects.filter(unpaid_q).distinct()
            elif payment_status_filter == 'paid':
                projects = projects.exclude(unpaid_q).distinct()

        # 5. Team Status Filter
        team_status_filter = request.query_params.get('team_status', '').lower()
        if team_status_filter:
            from .models import ProjectTeam, ProjectServiceTeam
            
            unfinished_pt_project_ids = ProjectTeam.objects.exclude(status__iexact='completed').exclude(status__iexact='done').values_list('project_id', flat=True)
            unfinished_st_project_ids = ProjectServiceTeam.objects.exclude(status__iexact='completed').exclude(status__iexact='done').values_list('service__project_id', flat=True)
            
            has_unfinished_project_ids = set(unfinished_pt_project_ids) | set(unfinished_st_project_ids)
            
            if team_status_filter == 'unfinished':
                projects = projects.filter(id__in=has_unfinished_project_ids).distinct()
            elif team_status_filter == 'finished':
                has_teams_q = Q(project_teams__isnull=False) | Q(services__teams__isnull=False)
                projects = projects.exclude(id__in=has_unfinished_project_ids).filter(has_teams_q).distinct()
            elif team_status_filter == 'overdue':
                # Filter projects that have at least one overdue team (Project or Service)
                overdue_pt = ProjectTeam.objects.exclude(status__iregex=r'^(completed|done)$').filter(deadline__lt=today).values_list('project_id', flat=True)
                overdue_st = ProjectServiceTeam.objects.exclude(status__iregex=r'^(completed|done)$').filter(deadline__lt=today).values_list('service__project_id', flat=True)
                has_overdue_ids = set(overdue_pt) | set(overdue_st)
                projects = projects.filter(id__in=has_overdue_ids).distinct()
                
        today = timezone.now().date()
        
        # --- Overview Aggregation (Before Pagination) ---
        # Note: getattr/getattr-like checks are needed because status can be on base_info or project
        pending_count = 0
        progressing_count = 0
        completed_count = 0
        unpaid_project_count = 0
        unfinished_teams = 0
        overdue_teams_count = 0
        
        # Aggregate before pagination for Pulse stats
        # We perform counts on the projects queryset that only has date/search filters (not status filter yet)
        pulse_projects = projects if not status_filter else projects.all() # simplified
        
        # Let's use a separate loop or better queryset for overview to ensure it doesn't change when we filter BY status
        # Actually, usually Pulse numbers represent the WHOLE filtered set.
        # But if you click 'Pending', should Pulse change? usually NO, it stays as the constant summary.
        # So we use the 'unfiltered-by-status' projects list for Overview.
        
        # Re-apply date/search only for overview
        ov_projects = Project.objects.filter(date_q) if date_q else Project.objects.all()
        if search_query: ov_projects = ov_projects.filter(name__icontains=search_query)

        total_teams = 0
        for p in ov_projects:
            # Status check
            base_info = p.project_base_informations.first()
            p_status = (getattr(base_info, 'status', p.status) if base_info else p.status).lower()
            
            if 'pending' in p_status: pending_count += 1
            elif 'progressing' in p_status or 'active' in p_status or 'in_progress' in p_status: progressing_count += 1
            elif 'completed' in p_status or 'done' in p_status: completed_count += 1
            
            # Comprehensive Payment Status Check
            is_unpaid = p.project_finances.filter(total_balance_due__gt=0).exists() or \
                        p.project_domains.filter(payment_status__iexact='UNPAID').exists() or \
                        p.project_servers.filter(payment_status__iexact='UNPAID').exists() or \
                        p.services.filter(payment_status__iexact='UNPAID').exists() or \
                        p.project_teams.filter(payment_status__iexact='UNPAID').exists()
            
            if is_unpaid: 
                unpaid_project_count += 1
            
            # Work check (Unfinished teams)
            unfinished_teams += p.project_teams.exclude(status__iexact='completed').exclude(status__iexact='done').count()
            unfinished_teams += ProjectServiceTeam.objects.filter(service__project=p).exclude(status__iexact='completed').exclude(status__iexact='done').count()
            
            # Overdue check (Specifically for Critical cards)
            overdue_teams_count += p.project_teams.exclude(status__iregex=r'^(completed|done)$').filter(deadline__lt=today).count()
            overdue_teams_count += ProjectServiceTeam.objects.filter(service__project=p).exclude(status__iregex=r'^(completed|done)$').filter(deadline__lt=today).count()
            
            # Total stats
            total_teams += p.project_teams.count()
            total_teams += ProjectServiceTeam.objects.filter(service__project=p).count()

        total_ov_remaining_amount = 0.0
        for p in ov_projects:
            # Calculate properly for EACH project in overview loop with case-insensitive filters
            t_total = float(p.project_teams.aggregate(t=Sum('cost'))['t'] or 0.0)
            t_paid = float(p.project_teams.filter(payment_status__iexact='PAID').aggregate(t=Sum('cost'))['t'] or 0.0)
            s_total = float(p.services.aggregate(s=Sum('cost'))['s'] or 0.0)
            s_paid = float(p.services.filter(payment_status__iexact='PAID').aggregate(s=Sum('cost'))['s'] or 0.0)
            d_total = float(p.project_domains.aggregate(d=Sum('cost'))['d'] or 0.0)
            d_paid = float(p.project_domains.filter(payment_status__iexact='PAID').aggregate(d=Sum('cost'))['d'] or 0.0)
            srv_total = float(p.project_servers.aggregate(v=Sum('cost'))['v'] or 0.0)
            srv_paid = float(p.project_servers.filter(payment_status__iexact='PAID').aggregate(v=Sum('cost'))['v'] or 0.0)
            
            p_total = t_total + s_total + d_total + srv_total
            p_paid = t_paid + s_paid + d_paid + srv_paid
            total_ov_remaining_amount += (p_total - p_paid)

        overview_data = {
            "projects": {
                "pending": pending_count,
                "progressing": progressing_count,
                "completed": completed_count,
                "total": ov_projects.count()
            },
            "payment": {
                "unpaid_projects": unpaid_project_count,
                "paid_projects": ov_projects.count() - unpaid_project_count,
                "total_remaining_amount": total_ov_remaining_amount
            },
            "work": {
                "unfinished_teams": unfinished_teams,
                "overdue_teams": overdue_teams_count,
                "total_teams": total_teams
            }
        }
        
        # --- Pagination ---
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get('page_size', 10))
        paginated_projects = paginator.paginate_queryset(projects, request)
        
        results = []

        for project in paginated_projects:
            # Base info
            base_info = project.project_base_informations.first()
            project_name = base_info.name if base_info else project.name
            project_status = getattr(base_info, 'status', project.status) if base_info else project.status
            
            # Project teams
            p_teams = list(project.project_teams.all())
            project_team_names = ", ".join(pt.team.name for pt in p_teams if pt.team)
            pt_status = 'No Team'
            if p_teams:
                unfinished_pts = [t.status for t in p_teams if t.status.lower() not in ['completed', 'done']]
                pt_status = unfinished_pts[0] if unfinished_pts else p_teams[0].status
            
            # Domain Payment Status counts
            domains = project.project_domains.all()
            paid_domains = domains.filter(payment_status__iexact='PAID').count()
            unpaid_domains = domains.filter(payment_status__iexact='UNPAID').count()
            total_domains = domains.count()
            domain_payment_str = "No Domain"
            if total_domains > 0:
                domain_payment_str = "Paid" if paid_domains == total_domains else f"Unpaid ({paid_domains}/{total_domains} Paid)"

            # Server Payment Status counts
            servers = project.project_servers.all()
            paid_servers = servers.filter(payment_status__iexact='PAID').count()
            unpaid_servers = servers.filter(payment_status__iexact='UNPAID').count()
            total_servers = servers.count()
            server_payment_str = "No Server"
            if total_servers > 0:
                server_payment_str = "Paid" if paid_servers == total_servers else f"Unpaid ({paid_servers}/{total_servers} Paid)"

            # Finance & Details (DYNAMIC AGGREGATION FROM NEW COST FIELDS)
            # 1. Teams
            teams_total = float(project.project_teams.aggregate(total=Sum('cost'))['total'] or 0.0)
            teams_paid = float(project.project_teams.filter(payment_status__iexact='PAID').aggregate(total=Sum('cost'))['total'] or 0.0)
            
            # 2. Services
            p_srvs = project.services.all()
            services_total = float(p_srvs.aggregate(total=Sum('cost'))['total'] or 0.0)
            services_paid = float(p_srvs.filter(payment_status__iexact='PAID').aggregate(total=Sum('cost'))['total'] or 0.0)
            
            # 3. Domains
            domains_total = float(domains.aggregate(total=Sum('cost'))['total'] or 0.0)
            domains_paid = float(domains.filter(payment_status__iexact='PAID').aggregate(total=Sum('cost'))['total'] or 0.0)
            
            # 4. Servers
            servers_total = float(servers.aggregate(total=Sum('cost'))['total'] or 0.0)
            servers_paid = float(servers.filter(payment_status__iexact='PAID').aggregate(total=Sum('cost'))['total'] or 0.0)
            
            # Final Totals
            total_project_cost = teams_total + services_total + domains_total + servers_total
            total_paid = teams_paid + services_paid + domains_paid + servers_paid
            balance_due = total_project_cost - total_paid
            
            domain_cost = domains_total
            server_cost = servers_total
            service_cost = services_total
            project_cost = teams_total
            
            domain_deadline = domains.aggregate(Min('expiration_date'))['expiration_date__min'] if domains.exists() else None
            server_deadline = servers.aggregate(Min('expiration_date'))['expiration_date__min'] if servers.exists() else None

            category_status = {
                "project": "Paid" if (project_cost > 0 and teams_paid == teams_total) else ("NA" if project_cost == 0 else "Unpaid"),
                "project_total_cost": teams_total,
                "project_paid_cost": teams_paid,
                "project_unpaid_cost": teams_total - teams_paid,
                
                "domain": "NA" if total_domains == 0 else ("Paid" if (domains_total > 0 and domains_paid == domains_total) else "Unpaid"),
                "domain_total_cost": domains_total,
                "domain_paid_cost": domains_paid,
                "domain_unpaid_cost": domains_total - domains_paid,
                "domain_deadline": domain_deadline,
                "domain_items": [
                    {
                        "name": d.name,
                        "cost": float(d.cost or 0.0),
                        "payment_status": d.payment_status,
                        "deadline": d.expiration_date.strftime('%Y-%m-%d') if d.expiration_date else None
                    } for d in domains
                ],
                "server": "NA" if total_servers == 0 else ("Paid" if (servers_total > 0 and servers_paid == servers_total) else "Unpaid"),
                "server_total_cost": servers_total,
                "server_paid_cost": servers_paid,
                "server_unpaid_cost": servers_total - servers_paid,
                "server_deadline": server_deadline,
                "server_items": [
                    {
                        "name": s.name,
                        "cost": float(s.cost or 0.0),
                        "payment_status": s.payment_status,
                        "deadline": s.expiration_date.strftime('%Y-%m-%d') if s.expiration_date else None
                    } for s in servers
                ],
                "service": "NA" if p_srvs.count() == 0 else ("Paid" if (service_cost > 0 and services_paid == services_total) else "Unpaid"),
                "service_total_cost": services_total,
                "service_paid_cost": services_paid,
                "service_unpaid_cost": services_total - services_paid,
            }

            # Granular Team counts for "X/Y Complete"
            project_teams_qs = project.project_teams.all()
            service_teams_qs = ProjectServiceTeam.objects.filter(service__project=project)
            
            p_total = project_teams_qs.count()
            p_done = project_teams_qs.filter(status__iregex=r'^(completed|done)$').count()
            
            s_total = service_teams_qs.count()
            s_done = service_teams_qs.filter(status__iregex=r'^(completed|done)$').count()
            
            total_teams_count = p_total + s_total
            completed_teams_count = p_done + s_done

            # Expiration Counts (Within 30 days) - Only Unpaid
            soon = today + timedelta(days=30)
            server_expiring_soon_count = servers.filter(payment_status__iexact='UNPAID', expiration_date__range=[today, soon]).count()
            domain_expiring_soon_count = domains.filter(payment_status__iexact='UNPAID', expiration_date__range=[today, soon]).count()

            services_data = []
            for service in project.services.all():
                svc_teams = list(service.teams.all())
                st_status = 'No Team'
                if svc_teams:
                    unfinished_sts = [t.status for t in svc_teams if t.status.lower() not in ['completed', 'done']]
                    st_status = unfinished_sts[0] if unfinished_sts else svc_teams[0].status
                    
                services_data.append({
                    "service_team_name": ", ".join(st.team.name for st in svc_teams if st.team) or "No Team",
                    "status": service.status,
                    "service_team_status": st_status,
                    "paid_status": service.payment_status,
                    "service_team_start_date": service.teams.aggregate(Min('start_date'))['start_date__min'],
                    "service_team_deadline": service.teams.aggregate(Max('deadline'))['deadline__max'],
                    "service_cost": float(service.cost or 0.0),
                })

            project_result = {
                "project_id": project.id,
                "project_name": project_name,
                "project_team_name": project_team_names or "No Team",
                "project_team_status": pt_status,
                "status": project_status,
                "total_paid": total_paid,
                "balance_due": balance_due,
                "total_project_cost": total_project_cost,
                "project_cost": project_cost,
                "category_status": category_status,
                "project_payment": category_status["project"], # Legacy
                "domain_payment": domain_payment_str, 
                "server_payment": server_payment_str,
                "project_team_start_date": project.project_teams.aggregate(Min('start_date'))['start_date__min'],
                "project_team_deadline": project.project_teams.aggregate(Max('deadline'))['deadline__max'],
                "serviceteam_count": project.services.count(),
                "server_count": total_servers,
                "paid_server_count": paid_servers,
                "unpaid_server_count": unpaid_servers,
                "domain_count": total_domains,
                "paid_domain_count": paid_domains,
                "unpaid_domain_count": unpaid_domains,
                "server_name": servers.first().name if servers.exists() else "No Server",
                "domain_name": domains.first().name if domains.exists() else "No Domain",
                "total_teams_count": total_teams_count,
                "completed_teams_count": completed_teams_count,
                "server_expiring_soon_count": server_expiring_soon_count,
                "domain_expiring_soon_count": domain_expiring_soon_count,
                "services": services_data
            }
            results.append(project_result)

        # Build final paginated response
        response_data = {
            'overview': overview_data,
            'total_project_count': paginator.page.paginator.count,
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
            'results': results
        }

        return Response(response_data, status=status.HTTP_200_OK)

class ServerAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import ProjectServer
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        next_30_days = today + timedelta(days=30)

        servers = ProjectServer.objects.all()

        total_servers = servers.count()
        paid_servers = servers.filter(payment_status='PAID').count()
        unpaid_servers = servers.filter(payment_status='UNPAID').count()
        total_cost = servers.aggregate(total=Sum('cost'))['total'] or 0

        # Group by server type
        by_server_type_raw = servers.values('server_type').annotate(count=Count('id'))
        by_server_type = [{"server_type": item['server_type'], "count": item['count']} for item in by_server_type_raw]

        # Group by accrued by
        by_accrued_by_raw = servers.values('accrued_by').annotate(count=Count('id'))
        by_accrued_by = [{"accrued_by": item['accrued_by'], "count": item['count']} for item in by_accrued_by_raw]

        # All servers detailed list for drill-down
        servers_list = []
        
        # Overview Tally (Now Status-based for Expired/Active, and Payment-aware for Expiring Soon)
        computed_active = servers.filter(status__iexact='Active').count()
        computed_expired = servers.filter(status__iexact='Expired').count()
        computed_expiring_soon = servers.filter(payment_status__iexact='UNPAID', expiration_date__range=[today, next_30_days]).count()

        for s in servers.select_related('project').order_by('expiration_date'):
            days_until_expiry = None
            if s.expiration_date and s.payment_status != 'PAID':
                days_until_expiry = (s.expiration_date - today).days

            servers_list.append({
                "id": s.id,
                "name": s.name,
                "server_type": s.server_type,
                "expiration_date": s.expiration_date.strftime('%Y-%m-%d') if s.expiration_date else None,
                "purchase_date": s.purchase_date.strftime('%Y-%m-%d') if s.purchase_date else None,
                "project": s.project.name if s.project else None,
                "payment_status": s.payment_status,
                "status": s.status,                        # Raw DB field
                "cost": float(s.cost) if s.cost else 0.0,
                "accrued_by": s.accrued_by,
                "purchased_from": s.purchased_from,
                "days_until_expiry": days_until_expiry,
            })

        # Expiring soon list (subset of servers_list for convenience)
        expiring_soon = [s for s in servers_list if s["days_until_expiry"] is not None and 0 <= s["days_until_expiry"] <= 30]

        data = {
            "overview": {
                "total_servers": total_servers,
                "active_servers": computed_active,
                "expired_servers": computed_expired,
                "expiring_soon_count": computed_expiring_soon,
                "paid_servers": paid_servers,
                "unpaid_servers": unpaid_servers,
                "total_cost": float(total_cost)
            },
            "by_server_type": by_server_type,
            "by_accrued_by": by_accrued_by,
            "expiring_soon": expiring_soon,
            "servers_list": servers_list
        }
        return Response(data, status=status.HTTP_200_OK)

class DomainAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import ProjectDomain
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        next_30_days = today + timedelta(days=30)

        domains = ProjectDomain.objects.all()

        total_domains = domains.count()
        active_domains = domains.filter(status__iexact='Active').count()
        expired_domains = domains.filter(status__iexact='Expired').count()
        paid_domains = domains.filter(payment_status__iexact='PAID').count()
        unpaid_domains = domains.filter(payment_status__iexact='UNPAID').count()
        total_cost = domains.aggregate(total=Sum('cost'))['total'] or 0

        # Group by accrued by
        by_accrued_by_raw = domains.values('accrued_by').annotate(count=Count('id'))
        by_accrued_by = [{"accrued_by": item['accrued_by'], "count": item['count']} for item in by_accrued_by_raw]

        # All domains detailed list for drill-down
        domains_list = []
        
        for d in domains.select_related('project').order_by('expiration_date'):
            days_until_expiry = None
            if d.expiration_date and d.payment_status != 'PAID':
                days_until_expiry = (d.expiration_date - today).days

            domains_list.append({
                "id": d.id,
                "name": d.name,
                "domain": d.name, # kept for backward compatibility with frontend if it expects 'domain' instead of 'name'
                "expiration_date": d.expiration_date.strftime('%Y-%m-%d') if d.expiration_date else None,
                "purchase_date": d.purchase_date.strftime('%Y-%m-%d') if d.purchase_date else None,
                "project": d.project.name if d.project else None,
                "payment_status": d.payment_status,
                "status": d.status,                        # Raw DB field
                "cost": float(d.cost) if d.cost else 0.0,
                "accrued_by": d.accrued_by,
                "purchased_from": d.purchased_from,
                "days_until_expiry": days_until_expiry,
            })

        # Expiring soon list (subset of domains_list for convenience)
        expiring_soon = [d for d in domains_list if d["days_until_expiry"] is not None and 0 <= d["days_until_expiry"] <= 30]

        data = {
            "overview": {
                "total_domains": total_domains,
                "active_domains": active_domains,
                "expired_domains": expired_domains,
                "paid_domains": paid_domains,
                "unpaid_domains": unpaid_domains,
                "total_cost": float(total_cost)
            },
            "by_accrued_by": by_accrued_by,
            "expiring_soon": expiring_soon,
            "domains_list": domains_list
        }

        return Response(data, status=status.HTTP_200_OK)
