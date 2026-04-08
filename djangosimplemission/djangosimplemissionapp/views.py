from django.contrib.auth.models import Permission
from rest_framework import views, viewsets, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from django.db.models import Q
from .models import (
    User,ProjectClient,ProjectBusinessAddress,DomainOrServerThirdPartyServiceProvider,Role,
    ProjectDomain,ProjectServer,ProjectFinance,Team,ProjectTeam,ProjectNature,
    Project,ProjectBaseInformation,ProjectExcution,ProjectTeamMember,ProjectService,ProjectServiceMember,
    EmployeeDailyActivity,ActivityLog,Invoice,InvoiceItem,Payment,ActivityExceedComment,
    Notification,EmployeeLeave,Company,CompanyProfile,Salary,Attendance,Employee,OtherIncome,OtherExpense,ProjectDocument,
    ClientAdvance, UserSalary
)
  
from .serializers import (
    UserSerializer, ChangePasswordSerializer, AdminChangePasswordSerializer,ProjectClientSerializer,
    ProjectBusinessAddressSerializer,DomainOrServerThirdPartyServiceProviderSerializer,
    ProjectDomainSerializer,ProjectServerSerializer,ProjectFinanceSerializer,TeamSerializer,
    ProjectTeamSerializer,ProjectNatureSerializer,
    ProjectSerializer,ProjectBaseInformationSerializer,ProjectExcutionSerializer,ProjectTeamMemberSerializer,ProjectServiceSerializer,
    EmployeeDailyActivitySerializer,ActivityLogSerializer,InvoiceSerializer,InvoiceItemSerializer,PaymentSerializer,ActivityExceedCommentSerializer,
    NotificationSerializer,EmployeeLeaveSerializer,CompanySerializer,CompanyProfileSerializer,SalarySerializer,AttendanceSerializer,EmployeeSerializer,OtherIncomeSerializer,OtherExpenseSerializer,RoleSerializer, PermissionSerializer,
    ProjectDocumentSerializer, ProjectSummarySerializer, ClientAdvanceSerializer, ClientSummarySerializer, UserSalarySerializer
)


from rest_framework.decorators import action
from .utils import get_date_filter_q
from .pdf_utils import generate_invoice_pdf
from django.contrib.auth import authenticate
from rest_framework import status
from django.http import Http404, JsonResponse, FileResponse
from .permissions import IsSuperAdmin, IsDeveloper, IsAdmin
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserListAPIView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Admins or users with specific permission can see all users
        is_privileged = any(role.upper() in ['SUPERADMIN', 'ADMIN', 'BILLING'] for role in request.user.role_names) or \
                        request.user.has_perm('djangosimplemissionapp.view_all_employee_performance') or \
                        request.user.has_perm('djangosimplemissionapp.view_all_activities') or \
                        request.user.has_perm('djangosimplemissionapp.view_all_team_performance')
        
        if is_privileged:
            users = User.objects.all()
        else:
            # Other users can only see themselves
            users = User.objects.filter(id=request.user.id)
        
        search_query = request.query_params.get('search', None)
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(designation__icontains=search_query) |
                Q(phone_number__icontains=search_query)
            )
            
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Only SuperAdmin can create users
        if not request.user.has_role('SuperAdmin'):
             return Response({'error': 'Permission denied. Only SuperAdmin can create users.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDetailAPIView(views.APIView):
    permission_classes = [IsAuthenticated]  

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        user = self.get_object(pk)
        
        # Privacy check: Only SuperAdmin/Admin or users with specific permission can view other profiles
        is_privileged = any(role.upper() in ['SUPERADMIN', 'ADMIN', 'BILLING'] for role in request.user.role_names) or \
                        request.user.has_perm('djangosimplemissionapp.view_all_employee_performance') or \
                        request.user.has_perm('djangosimplemissionapp.view_all_activities') or \
                        request.user.has_perm('djangosimplemissionapp.view_all_team_performance')
        
        if not is_privileged and request.user.id != user.id:
             return Response({'error': 'Permission denied. You can only view your own profile.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        # Only SuperAdmin can edit users
        if not request.user.has_role('SuperAdmin'):
            return Response({'error': 'Permission denied. Only SuperAdmin can edit users.'}, status=status.HTTP_403_FORBIDDEN)
            
        user = self.get_object(pk)
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        # Only SuperAdmin can delete users
        if not request.user.has_role('SuperAdmin'):
            return Response({'error': 'Permission denied. Only SuperAdmin can delete users.'}, status=status.HTTP_403_FORBIDDEN)

        user = self.get_object(pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        data['is_logged_in'] = True
        data['role'] = user.role.name if user.role else None
        data['permissions'] = list(user.role.permissions.values_list('codename', flat=True)) if user.role else []
        data['is_superuser'] = user.is_superuser

        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
            'designation': user.designation,
            'is_superuser': user.is_superuser,
            'role': user.role.name if user.role else None,
            'roles': [{'name': user.role.name}] if user.role else [],
            'permissions': data['permissions']
        }
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class ChangePasswordView(views.APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.data.get('old_password')):
                user.set_password(serializer.data.get('new_password'))
                user.save()
                return Response({'status': 'password set'}, status=status.HTTP_200_OK)
            return Response({'old_password': ['Wrong password.']}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoleListCreateAPIView(ListCreateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

class RoleDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

class PermissionListAPIView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        perms = Permission.objects.all().order_by('codename')
        serializer = PermissionSerializer(perms, many=True)
        return Response([p['codename'] for p in serializer.data])

class RoleCreateAPIView(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        name = request.data.get('name', '').strip().upper()
        if not name:
            return Response({'error': 'Role name is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        perms_codenames = request.data.get('permissions', [])
        
        role, created = Role.objects.get_or_create(name=name)
        permissions = Permission.objects.filter(codename__in=perms_codenames)
        role.permissions.set(permissions)
        
        return Response({'message': f'Role {"created" if created else "updated"} with {permissions.count()} permissions'}, status=status.HTTP_201_CREATED)


class AdminChangeUserPasswordView(views.APIView):
    permission_classes = [IsSuperAdmin]

    def put(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise Http404

        serializer = AdminChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user.set_password(serializer.data.get('new_password'))
            user.save()
            return Response({'status': 'password set'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ProjectClientListCreateAPIView(ListCreateAPIView):
    queryset = ProjectClient.objects.all()
    serializer_class = ProjectClientSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['company_name', 'contact_person', 'email', 'phone']


class ProjectClientDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectClient.objects.all()
    serializer_class = ProjectClientSerializer
    permission_classes = [IsAuthenticated]



class ProjectBusinessAddressListCreateAPIView(ListCreateAPIView):
    queryset = ProjectBusinessAddress.objects.all()
    serializer_class = ProjectBusinessAddressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['attention_name', 'city', 'district', 'state', 'pin_code','legal_name', 'projects__name']

    def get_queryset(self):
        queryset = ProjectBusinessAddress.objects.all()
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(projects__id=project_id)
        return queryset


class ProjectBusinessAddressDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectBusinessAddress.objects.all()
    serializer_class = ProjectBusinessAddressSerializer
    permission_classes = [IsAuthenticated]

class ClientSummaryListAPIView(ListCreateAPIView):
    queryset = ProjectBusinessAddress.objects.all()
    serializer_class = ClientSummarySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['legal_name', 'city']

    def get_queryset(self):
        # We can add custom filtering here if needed
        return ProjectBusinessAddress.objects.all().order_by('legal_name')



class DomainOrServerThirdPartyServiceProviderListCreateAPIView(ListCreateAPIView):
    queryset = DomainOrServerThirdPartyServiceProvider.objects.all()
    serializer_class = DomainOrServerThirdPartyServiceProviderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['company_name', 'contact_person', 'email', 'phone']


class DomainOrServerThirdPartyServiceProviderDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = DomainOrServerThirdPartyServiceProvider.objects.all()
    serializer_class = DomainOrServerThirdPartyServiceProviderSerializer
    permission_classes = [IsAuthenticated]

class ProjectDomainListCreateAPIView(ListCreateAPIView):
    queryset = ProjectDomain.objects.all()
    serializer_class = ProjectDomainSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'purchased_from', 'status', 'accrued_by']

class ProjectDomainDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectDomain.objects.all()
    serializer_class = ProjectDomainSerializer
    permission_classes = [IsAuthenticated]    

class ProjectServerListCreateAPIView(ListCreateAPIView):
    queryset = ProjectServer.objects.all()
    serializer_class = ProjectServerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'server_type', 'purchased_from', 'status', 'accrued_by']

class ProjectServerDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectServer.objects.all()
    serializer_class = ProjectServerSerializer
    permission_classes = [IsAuthenticated]      

class ProjectFinanceListCreateAPIView(ListCreateAPIView):
    queryset = ProjectFinance.objects.all()
    serializer_class = ProjectFinanceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['id']

class ProjectFinanceDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectFinance.objects.all()
    serializer_class = ProjectFinanceSerializer
    permission_classes = [IsAuthenticated]          

class TeamListCreateAPIView(ListCreateAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'team_lead__username']

class TeamDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]          

class ProjectTeamListCreateAPIView(ListCreateAPIView):
    queryset = ProjectTeam.objects.all()
    serializer_class = ProjectTeamSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['team__name']

class ProjectTeamDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectTeam.objects.all()
    serializer_class = ProjectTeamSerializer
    permission_classes = [IsAuthenticated]              

class ProjectNatureListCreateAPIView(ListCreateAPIView):
    queryset = ProjectNature.objects.all()
    serializer_class = ProjectNatureSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

class ProjectNatureDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectNature.objects.all()
    serializer_class = ProjectNatureSerializer
    permission_classes = [IsAuthenticated]                  

class ProjectListCreateAPIView(ListCreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['description', 'status', 'project_nature__name']

class ProjectSummaryListAPIView(ListCreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSummarySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'status']

class ProjectDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

class ProjectBaseInformationListCreateAPIView(ListCreateAPIView):
    queryset = ProjectBaseInformation.objects.all()
    serializer_class = ProjectBaseInformationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description', 'creator_name']

class ProjectBaseInformationDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectBaseInformation.objects.all()
    serializer_class = ProjectBaseInformationSerializer
    permission_classes = [IsAuthenticated]

class ProjectExcutionListCreateAPIView(ListCreateAPIView):
    queryset = ProjectExcution.objects.all()
    serializer_class = ProjectExcutionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['id']

class ProjectExcutionDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectExcution.objects.all()
    serializer_class = ProjectExcutionSerializer
    permission_classes = [IsAuthenticated]

class ProjectTeamMemberListCreateAPIView(ListCreateAPIView):
    queryset = ProjectTeamMember.objects.all()
    serializer_class = ProjectTeamMemberSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['employee__username', 'role', 'status']

class ProjectTeamMemberDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectTeamMember.objects.all()
    serializer_class = ProjectTeamMemberSerializer
    permission_classes = [IsAuthenticated]

class ProjectServiceListCreateAPIView(ListCreateAPIView):
    queryset = ProjectService.objects.all()
    serializer_class = ProjectServiceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['description', 'status']

class ProjectServiceDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectService.objects.all()
    serializer_class = ProjectServiceSerializer
    permission_classes = [IsAuthenticated]

class EmployeeDailyActivityListCreateAPIView(ListCreateAPIView):
    # queryset = EmployeeDailyActivity.objects.all()  # Removed in favor of dynamic filtering
    serializer_class = EmployeeDailyActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        can_view_all = self.request.user.has_perm('djangosimplemissionapp.view_all_activities')
        can_view_own = self.request.user.has_perm('djangosimplemissionapp.view_own_activities') or can_view_all
        
        if not (can_view_all or can_view_own):
            return EmployeeDailyActivity.objects.none()

        if can_view_all:
            return EmployeeDailyActivity.objects.all()
        return EmployeeDailyActivity.objects.filter(employee=self.request.user)
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['description', 'employee__username', 'project__name', 'project_service__name']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Date filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
            
        # Employee filtering
        employee_id = request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)

        if request.query_params.get('export') == 'pdf':
            from .pdf_utils import generate_activity_pdf
            from django.contrib.auth import get_user_model
            from django.http import FileResponse
            User = get_user_model()
            
            employee_name = 'All Employees'
            e_id = request.query_params.get('employee_id')
            if e_id:
                employee = User.objects.filter(id=e_id).first()
                if employee:
                    employee_name = employee.get_full_name() or employee.username

            context = {
                'title': 'Employee Activity Report',
                'employee_name': employee_name,
                'date_range': f"{start_date} to {end_date}" if start_date and end_date else "All Time"
            }
            buffer = generate_activity_pdf(queryset, context)
            filename = f"Employee_Activity_Report_{timezone.now().strftime('%Y%m%d')}.pdf"
            return FileResponse(buffer, as_attachment=True, filename=filename)

        elif request.query_params.get('export') == 'docx':
            from .docx_utils import generate_activity_docx
            from django.contrib.auth import get_user_model
            from django.http import FileResponse
            User = get_user_model()
            
            employee_name = 'All Employees'
            e_id = request.query_params.get('employee_id')
            if e_id:
                employee = User.objects.filter(id=e_id).first()
                if employee:
                    employee_name = employee.username

            context = {
                'title': 'Employee Activity Report',
                'employee_name': employee_name,
                'date_range': f"{start_date} to {end_date}" if start_date and end_date else "All Time"
            }
            buffer = generate_activity_docx(queryset, context)
            filename = f"Employee_Activity_Report_{timezone.now().strftime('%Y%m%d')}.docx"
            return FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class EmployeeSpecificActivityListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id):
        # 0. Permission check
        can_view_all = request.user.has_perm('djangosimplemissionapp.view_all_activities')
        can_view_own = request.user.has_perm('djangosimplemissionapp.view_own_activities') or can_view_all
        
        if not (can_view_all or (can_view_own and request.user.id == int(employee_id))):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        # 1. Fetch activities for the specified employee
        activities = EmployeeDailyActivity.objects.filter(employee_id=employee_id).order_by('-date', '-created_at')
        
        # 2. Support filtering by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            activities = activities.filter(date__range=[start_date, end_date])

        # 3. Support PDF Export
        if request.query_params.get('export') == 'pdf':
            from .pdf_utils import generate_activity_pdf
            from django.contrib.auth import get_user_model
            User = get_user_model()
            employee = User.objects.filter(id=employee_id).first()
            employee_name = employee.get_full_name() or employee.username if employee else f"User {employee_id}"
            
            context = {
                'title': f'Activity Report for {employee_name}',
                'employee_name': employee_name,
                'date_range': f"{start_date} to {end_date}" if start_date and end_date else "All Time"
            }
            buffer = generate_activity_pdf(activities, context)
            filename = f"Activity_Report_{employee_name}_{timezone.now().strftime('%Y%m%d')}.pdf"
            return FileResponse(buffer, as_attachment=True, filename=filename)

        # 4. Standard Paginated Response
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get('page_size', 10))
        page = paginator.paginate_queryset(activities, request)
        
        serializer = EmployeeDailyActivitySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

class EmployeeWorkDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id):
        # 0. Permission check for viewing work details
        # For simplicity, we leverage the same 'view_all_activities' / 'view_own_activities' or keep it open for self.
        can_view_all = request.user.has_perm('djangosimplemissionapp.view_all_activities') or \
                       request.user.has_perm('djangosimplemissionapp.view_all_employee_performance')
        
        is_self = request.user.id == int(employee_id)
        
        if not (can_view_all or is_self):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        from .models import ProjectTeamMember, ProjectServiceMember, EmployeeDailyActivity
        
        # 1. Projects involved
        project_memberships = ProjectTeamMember.objects.filter(employee_id=employee_id).select_related('project')
        total_projects = project_memberships.values('project').distinct().count()
        
        # 2. Services involved
        service_memberships = ProjectServiceMember.objects.filter(employee_id=employee_id).select_related('service')
        total_services = service_memberships.count()
        active_services = service_memberships.exclude(service__status='Completed').count()
        completed_services = service_memberships.filter(service__status='Completed').count()
        
        # 3. Pending Activities (based on pending_work_percentage > 0)
        pending_activities_count = EmployeeDailyActivity.objects.filter(
            employee_id=employee_id, 
            pending_work_percentage__gt=0
        ).count()

        # 4. List of active projects/services (compact)
        active_items = []
        for pm in project_memberships.exclude(status='Inactive')[:5]:
            days_worked = EmployeeDailyActivity.objects.filter(
                employee_id=employee_id,
                project=pm.project
            ).values('date').distinct().count()
            
            # Fetch project deadline from ProjectExcution
            from .models import ProjectExcution
            deadline = None
            if pm.project:
                exec_info = ProjectExcution.objects.filter(project=pm.project).first()
                if exec_info and exec_info.confirmed_end_date:
                    deadline = exec_info.confirmed_end_date.isoformat()

            active_items.append({
                "type": "Project",
                "name": pm.project.name if pm.project else "Unknown",
                "role": pm.role,
                "days_worked": days_worked,
                "status": pm.status or 'Pending',
                "deadline": deadline
            })
        
        for sm in service_memberships.exclude(status='Inactive')[:5]:
            days_worked = EmployeeDailyActivity.objects.filter(
                employee_id=employee_id,
                project_service=sm.service
            ).values('date').distinct().count()
            
            active_items.append({
                "type": "Service",
                "name": sm.service.name if sm.service else "Unknown",
                "role": sm.role,
                "days_worked": days_worked,
                "status": sm.status or 'Pending',
                "deadline": sm.service.deadline.isoformat() if sm.service and sm.service.deadline else None
            })

        # 5. Recent Activities
        recent_activities = EmployeeDailyActivity.objects.filter(employee_id=employee_id).select_related('project', 'project_service').order_by('-date', '-created_at')[:20]
        activities_data = []
        for act in recent_activities:
            activities_data.append({
                "id": act.id,
                "date": act.date.isoformat() if act.date else None,
                "project_name": act.project.name if act.project else None,
                "service_name": act.project_service.name if act.project_service else None,
                "description": act.description,
                "hours_spent": float(act.hours_spent),
                "target_work_percentage": act.target_work_percentage,
                "pending_work_percentage": act.pending_work_percentage
            })

        data = {
            "total_projects": total_projects,
            "total_services": total_services,
            "active_services": active_services,
            "completed_services": completed_services,
            "pending_activities": pending_activities_count,
            "active_work_list": active_items,
            "recent_activities": activities_data
        }
        
        return Response(data, status=status.HTTP_200_OK)

class EmployeeDailyActivityDetailAPIView(RetrieveUpdateDestroyAPIView):
    # queryset = EmployeeDailyActivity.objects.all()
    serializer_class = EmployeeDailyActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        can_view_all = self.request.user.has_perm('djangosimplemissionapp.view_all_activities')
        if can_view_all:
            return EmployeeDailyActivity.objects.all()
        return EmployeeDailyActivity.objects.filter(employee=self.request.user)

class ActivityLogListCreateAPIView(ListCreateAPIView):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['description']

class ActivityLogDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]


class ClientInvoiceListAPIView(ListCreateAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        return Invoice.objects.filter(client_company_id=client_id)

    def perform_create(self, serializer):
        client_id = self.kwargs.get('client_id')
        serializer.save(client_company_id=client_id)

class InvoiceListCreateAPIView(ListCreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['invoice_number', 'client_company__legal_name']

class InvoiceDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        return Invoice.objects.filter(client_company_id=client_id)

class InvoiceItemListCreateAPIView(ListCreateAPIView):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['service_type', 'description']

class InvoiceItemDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [IsAuthenticated]

class PaymentListCreateAPIView(ListCreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['transaction_id', 'payment_method', 'notes']

class PaymentDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

class InvoicePaymentListCreateAPIView(ListCreateAPIView):
    """
    Nested endpoint: /api/project-business-addresses/<client_id>/invoices/<invoice_id>/payments/
    Handle GET (list payments for this invoice) and POST (add new payment).
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        invoice_id = self.kwargs.get('pk')
        client_id = self.kwargs.get('client_id')
        return Payment.objects.filter(invoice_id=invoice_id, invoice__client_company_id=client_id)

    def perform_create(self, serializer):
        invoice_id = self.kwargs.get('pk')
        client_id = self.kwargs.get('client_id')
        try:
            invoice = Invoice.objects.get(id=invoice_id, client_company_id=client_id)
        except Invoice.DoesNotExist:
            raise Http404("Invoice not found for this client")
        
        serializer.save(invoice=invoice)

class InvoicePaymentDetailAPIView(RetrieveUpdateDestroyAPIView):
    """
    Nested endpoint: /api/project-business-addresses/<client_id>/invoices/<invoice_id>/payments/<payment_id>/
    Handle specific payment management.
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        invoice_id = self.kwargs.get('invoice_pk')
        client_id = self.kwargs.get('client_id')
        return Payment.objects.filter(invoice_id=invoice_id, invoice__client_company_id=client_id)

class ApplyAdvanceCreditView(APIView):
    """
    Manually apply a specific amount of advance credit to an invoice.
    Endpoint: /api/project-business-addresses/<client_id>/invoices/<invoice_id>/apply-advance/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, client_id, pk):
        try:
            invoice = Invoice.objects.get(id=pk, client_company_id=client_id)
        except Invoice.DoesNotExist:
            return Response({"error": "Invoice not found for this client"}, status=status.HTTP_404_NOT_FOUND)

        amount = request.data.get('amount')
        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except:
            return Response({"error": "Invalid amount format"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"error": "Amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)

        if amount > invoice.balance_due:
            return Response({"error": f"Amount exceeds invoice balance ({invoice.balance_due})"}, status=status.HTTP_400_BAD_REQUEST)

        from .services import apply_advances_to_invoice
        
        # Check if they have enough advance total
        from .models import ClientAdvance
        from django.db.models import Sum
        available = ClientAdvance.objects.filter(client=invoice.client_company, remaining_amount__gt=0).aggregate(Sum('remaining_amount'))['remaining_amount__sum'] or 0
        
        if amount > available:
            return Response({"error": f"Insufficient advance credit (Available: {available})"}, status=status.HTTP_400_BAD_REQUEST)

        apply_advances_to_invoice(invoice, limit_amount=amount)
        
        return Response({
            "message": f"Successfully applied {amount} from advance credit.",
            "new_balance": invoice.balance_due
        }, status=status.HTTP_200_OK)

class ActivityExceedCommentListCreateAPIView(ListCreateAPIView):
    queryset = ActivityExceedComment.objects.all()
    serializer_class = ActivityExceedCommentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['comment', 'commented_by__username']

class ActivityExceedCommentDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ActivityExceedComment.objects.all()
    serializer_class = ActivityExceedCommentSerializer
    permission_classes = [IsAuthenticated]

class NotificationListCreateAPIView(ListCreateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['message', 'user__username']

class NotificationDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

class EmployeeLeaveListCreateAPIView(ListCreateAPIView):
    queryset = EmployeeLeave.objects.all()
    serializer_class = EmployeeLeaveSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['employee__username', 'status', 'description']

class EmployeeLeaveDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = EmployeeLeave.objects.all()
    serializer_class = EmployeeLeaveSerializer
    permission_classes = [IsAuthenticated]

class CompanyListCreateAPIView(ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['id']

class CompanyDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

class CompanyProfileListCreateAPIView(ListCreateAPIView):
    queryset = CompanyProfile.objects.all()
    serializer_class = CompanyProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['company_name', 'company_type', 'email', 'phone', 'address']

class CompanyProfileDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = CompanyProfile.objects.all()
    serializer_class = CompanyProfileSerializer
    permission_classes = [IsAuthenticated]

class SalaryListCreateAPIView(ListCreateAPIView):
    queryset = Salary.objects.all()
    serializer_class = SalarySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['employee__user__username', 'status']

    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        employee_id = self.request.query_params.get('employee')
        
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
            
        return queryset

class SalaryDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Salary.objects.all()
    serializer_class = SalarySerializer
    permission_classes = [IsAuthenticated]

class AttendanceListCreateAPIView(ListCreateAPIView):
    queryset = Attendance.objects.all().order_by('-date')
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['employee__user__username', 'status']

class AttendanceDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

class EmployeeListCreateAPIView(ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__username', 'employee_id', 'department']

class EmployeeDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]

class UserSalaryListCreateAPIView(ListCreateAPIView):
    queryset = UserSalary.objects.all()
    serializer_class = UserSalarySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__username',]

class UserSalaryDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = UserSalary.objects.all()
    serializer_class = UserSalarySerializer
    permission_classes = [IsAuthenticated]

class OtherIncomeListCreateAPIView(ListCreateAPIView):

    queryset = OtherIncome.objects.all()
    serializer_class = OtherIncomeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'notes']

class OtherIncomeDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = OtherIncome.objects.all()
    serializer_class = OtherIncomeSerializer
    permission_classes = [IsAuthenticated]

class OtherExpenseListCreateAPIView(ListCreateAPIView):
    queryset = OtherExpense.objects.all()
    serializer_class = OtherExpenseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'notes']

class OtherExpenseDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = OtherExpense.objects.all()
    serializer_class = OtherExpenseSerializer
    permission_classes = [IsAuthenticated]

class ProjectDocumentListCreateAPIView(ListCreateAPIView):
    queryset = ProjectDocument.objects.all()
    serializer_class = ProjectDocumentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

class ProjectDocumentDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectDocument.objects.all()
    serializer_class = ProjectDocumentSerializer
    permission_classes = [IsAuthenticated]



class InvoicePDFView(APIView):  
    permission_classes = [IsAuthenticated]

    def get(self, request, client_id, pk):
        try:
            invoice = Invoice.objects.get(pk=pk, client_company_id=client_id)
        except Invoice.DoesNotExist:
            return Response({"error": "Invoice not found for this client"}, status=status.HTTP_404_NOT_FOUND)

        buffer = generate_invoice_pdf(invoice)
        filename = f"Invoice_{invoice.invoice_number or invoice.id}.pdf"
        
        return FileResponse(buffer, as_attachment=True, filename=filename)


class ClientAdvanceListAPIView(ListCreateAPIView):
    serializer_class = ClientAdvanceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        return ClientAdvance.objects.filter(client_id=client_id).order_by('created_at')

    def perform_create(self, serializer):
        client_id = self.kwargs.get('client_id')
        serializer.save(client_id=client_id)

class ClientAdvanceDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ClientAdvanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        return ClientAdvance.objects.filter(client_id=client_id)


class EmployeePerformanceAPIView(APIView):
    """
    Returns performance analytics for the logged-in employee (or a specific employee
    if employee_id is passed as a query param by an admin).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        can_view_all = request.user.has_perm('djangosimplemissionapp.view_all_employee_performance')
        can_view_own = request.user.has_perm('djangosimplemissionapp.view_own_employee_performance') or can_view_all

        if not (can_view_all or can_view_own):
            return Response({'error': 'You do not have permission to view employee performance.'}, status=status.HTTP_403_FORBIDDEN)

        employee_id = request.query_params.get('employee_id')
        if employee_id:
            if not can_view_all:
                return Response({'error': 'Permission denied to view other employee performance.'}, status=status.HTTP_403_FORBIDDEN)
            try:
                employee = User.objects.get(pk=employee_id)
            except User.DoesNotExist:
                raise Http404
        else:
            employee = request.user

        from .models import ProjectTeamMember, ProjectServiceMember
        
        project_team_memberships = ProjectTeamMember.objects.filter(employee=employee).select_related('project')
        service_team_memberships = ProjectServiceMember.objects.filter(employee=employee).select_related('service', 'service__project')

        from django.utils import timezone
        current_date = timezone.now().date()

        def get_target_score(start, current, allocated):
            if not start or not allocated or allocated <= 0:
                return 0
            days_passed = (current - start).days
            if days_passed < 0:
                return 0
            return round((days_passed / allocated) * 100, 2)

        project_team_data = []
        for m in project_team_memberships:
            t_score = get_target_score(m.start_date, current_date, m.allocated_days)
            project_team_data.append({
                'project_name': m.project.name if m.project else 'Unknown Project',
                'status': m.status,
                'start_date': m.start_date,
                'allocated_days': m.allocated_days,
                'current_date': current_date,
                'end_date': m.end_date,
                'note': m.notes,
                'target_score': t_score,
                'is_over_allocated': t_score > 100,
            })
            
        service_team_data = []
        for m in service_team_memberships:
            t_score = get_target_score(m.start_date, current_date, m.allocated_days)
            p_name = m.service.project.name if m.service and m.service.project else 'Independent Service'
            s_name = m.service.name if m.service else 'Unknown Service'
            service_team_data.append({
                'service_name': f"{p_name} -> {s_name}",
                'status': m.status,
                'start_date': m.start_date,
                'allocated_days': m.allocated_days,
                'current_date': current_date,
                'end_date': m.end_date,
                'note': m.notes,
                'target_score': t_score,
                'is_over_allocated': t_score > 100,
            })

        pending_count = 0
        progressing_count = 0
        completed_count = 0

        for item in project_team_data:
            item_status = item.get('status')
            if item_status == 'Pending':
                pending_count += 1
            elif item_status == 'Progressing':
                progressing_count += 1
            elif item_status == 'Completed':
                completed_count += 1

        for item in service_team_data:
            item_status = item.get('status')
            if item_status == 'Pending':
                pending_count += 1
            elif item_status == 'Progressing':
                progressing_count += 1
            elif item_status == 'Completed':
                completed_count += 1

        data = {
            'employee_id': employee.id,
            'employee_name': employee.get_full_name() or employee.username,
            'pending_total': pending_count,
            'completed_total': completed_count,
            'progressing_total': progressing_count,
            'total_committed_project_count': len(project_team_data),
            'total_committed_project_team': project_team_data,
            'total_committed_service_count': len(service_team_data),
            'total_committed_service_team': service_team_data,
        }

        return Response(data, status=status.HTTP_200_OK)

    def _get_stats(self, employee):
        from django.db.models import Sum

        memberships = ProjectTeamMember.objects.filter(employee=employee).select_related('project')
        service_memberships = ProjectServiceMember.objects.filter(employee=employee).select_related('service', 'service__project')

        total_allocated = memberships.aggregate(s=Sum('allocated_days'))['s'] or 0
        total_actual = memberships.aggregate(s=Sum('actual_days_spent'))['s'] or 0
        svc_allocated = service_memberships.aggregate(s=Sum('allocated_days'))['s'] or 0
        svc_actual = service_memberships.aggregate(s=Sum('actual_days'))['s'] or 0

        total_allocated += svc_allocated
        total_actual += svc_actual

        time_saved = max(0, total_allocated - total_actual)
        time_overrun = max(0, total_actual - total_allocated)

        perf_pct = round((total_actual / total_allocated) * 100, 1) if total_allocated else 0

        # Combine completed counts
        completed_count = memberships.filter(status='Completed').count() + service_memberships.filter(status='Completed').count()
        progress_count = memberships.filter(status__in=['Completed', 'Progressing']).count() + service_memberships.filter(status__in=['Completed', 'Progressing']).count()
        
        reliability = round((completed_count / max(progress_count, 1)) * 100, 1)

        # Productivity score (0–10): lower actual/allocated is better
        productivity = round(max(0, 10 - (time_overrun / max(total_allocated, 1)) * 10), 2)

        if reliability >= 90 and perf_pct <= 110:
            grade = 'A'
        elif reliability >= 75:
            grade = 'B'
        elif reliability >= 60:
            grade = 'C'
        else:
            grade = 'D'

        if productivity >= 7:
            risk = 'Low'
        elif productivity >= 4:
            risk = 'Medium'
        else:
            risk = 'High'

        projects_list = []
        # Add Project Memberships
        for m in memberships[:15]:
            projects_list.append({
                'id': m.project.id if m.project else None,
                'name': m.project.name if m.project else 'Unknown Project',
                'role': m.role,
                'status': m.status,
                'allocated_days': m.allocated_days,
                'actual_days_spent': m.actual_days_spent,
                'type': 'Project'
            })
            
        # Add Service Memberships
        for m in service_memberships[:15]:
            p_name = m.service.project.name if m.service and m.service.project else 'Independent Service'
            s_name = m.service.name if m.service else 'Unknown Service'
            projects_list.append({
                'id': m.service.id if m.service else None,
                'name': f"{p_name} ➔ {s_name}",
                'role': m.role,
                'status': m.status,
                'allocated_days': m.allocated_days,
                'actual_days_spent': m.actual_days,
                'type': 'Service'
            })

        return {
            'employee_id': employee.id,
            'employee_username': employee.username,
            'projects_count': progress_count,  # Total combined active/completed tasks
            'services_count': service_memberships.count(),
            'total_allocated_days': total_allocated,
            'total_actual_days': total_actual,
            'time_saved_days': time_saved,
            'time_overrun_days': time_overrun,
            'overall_performance_percentage': perf_pct,
            'delivery_reliability_percent': reliability,
            'productivity_score': productivity,
            'performance_grade': grade,
            'performance_risk': risk,
            'overall_status': 'On Track' if risk == 'Low' else ('At Risk' if risk == 'Medium' else 'Delayed'),
            'projects': projects_list,
        }


class TeamPerformanceAPIView(APIView):
    """
    Returns aggregated performance analytics for a team.
    Team leads see their own team; admins can specify team_id.
    """
    permission_classes = [IsAuthenticated]

    def _get_team_stats(self, team):
        from .models import ProjectTeam, ProjectServiceTeam, ProjectTeamMember, ProjectServiceMember
        from django.utils import timezone
        current_date = timezone.now().date()
        
        members = team.members.all()
        member_count = members.count()
        
        # 1. Projects assigned specifically to this Team
        team_project_allocations = ProjectTeam.objects.filter(team=team).select_related('project')
        projects_data = []
        project_ids = set()
        
        p_pending = 0
        p_progressing = 0
        p_completed = 0
        
        for allocation in team_project_allocations:
            if allocation.project and allocation.project.id not in project_ids:
                overused = False
                over_days = 0
                remain_days = 0
                check_date = allocation.deadline or allocation.end_date
                
                if check_date:
                    if allocation.status == 'Completed':
                        if allocation.actual_end_date and allocation.actual_end_date > check_date:
                            overused = True
                            over_days = (allocation.actual_end_date - check_date).days
                    else:
                        days_diff = (check_date - current_date).days
                        if days_diff < 0:
                            overused = True
                            over_days = abs(days_diff)
                        else:
                            remain_days = days_diff
                
                projects_data.append({
                    'name': allocation.project.name,
                    'status': allocation.status, # Use the status from ProjectTeam
                    'start_date': allocation.start_date,
                    'end_date': allocation.end_date,
                    'deadline': allocation.deadline,
                    'actual_end_date': allocation.actual_end_date,
                    'current_date': current_date,
                    'overused': overused,
                    'over_days': over_days,
                    'remain_days': remain_days
                })
                project_ids.add(allocation.project.id)
            
            # Status counts from members linked to this team allocation
            for m in allocation.members.all():
                if m.status == 'Pending': p_pending += 1
                elif m.status == 'Progressing': p_progressing += 1
                elif m.status == 'Completed': p_completed += 1

        # 2. Services assigned specifically to this Team
        team_service_allocations = ProjectServiceTeam.objects.filter(team=team).select_related('service', 'service__project')
        services_data = []
        service_ids = set()
        
        s_pending = 0
        s_progressing = 0
        s_completed = 0
        
        for allocation in team_service_allocations:
            svc = allocation.service
            if svc:
                if svc.id not in service_ids:
                    p_name = svc.project.name if svc.project else 'Independent'
                    overused = False
                    over_days = 0
                    remain_days = 0
                    # Use deadline for overuse check if available, otherwise end_date
                    check_date = allocation.deadline or allocation.end_date
                    
                    if check_date:
                        if allocation.status == 'Completed':
                            if allocation.actual_end_date and allocation.actual_end_date > check_date:
                                overused = True
                                over_days = (allocation.actual_end_date - check_date).days
                        else:
                            days_diff = (check_date - current_date).days
                            if days_diff < 0:
                                overused = True
                                over_days = abs(days_diff)
                            else:
                                remain_days = days_diff
                        
                    services_data.append({
                        'name': f"{p_name} ➔ {svc.name}",
                        'status': allocation.status, # Use the status from ProjectServiceTeam
                        'start_date': allocation.start_date,
                        'end_date': allocation.end_date,
                        'deadline': allocation.deadline,
                        'actual_end_date': allocation.actual_end_date,
                        'current_date': current_date,
                        'overused': overused,
                        'over_days': over_days,
                        'remain_days': remain_days
                    })
                    service_ids.add(svc.id)
                
                # For services, we check ProjectServiceMember matching this service and this team's members
                s_mems = ProjectServiceMember.objects.filter(service=svc, employee__in=members)
                s_pending += s_mems.filter(status='Pending').count()
                s_progressing += s_mems.filter(status='Progressing').count()
                s_completed += s_mems.filter(status='Completed').count()

        return {
            'team_id': team.id,
            'team_name': team.name,
            'member_count': member_count,
            'member_names': [m.username for m in members],
            'team_projects_count': len(projects_data),
            'projects': projects_data,
            'team_service_count': len(services_data),
            'services': services_data,
            # Internal fields for aggregation
            '_pending': p_pending + s_pending,
            '_completed': p_completed + s_completed,
            '_progressing': p_progressing + s_progressing,
        }

    def get(self, request):
        # 1. Permission checks
        role_names_upper = [r.upper() for r in request.user.role_names]
        is_admin_flag = any(r in ['SUPERADMIN', 'ADMIN'] for r in role_names_upper)
        
        def check_perm(codename):
            if request.user.is_superuser or is_admin_flag: return True
            if request.user.has_perm(f'djangosimplemissionapp.{codename}'): return True
            if request.user.role and request.user.role.permissions.filter(codename=codename).exists():
                return True
            return False

        can_view_all = check_perm('view_all_team_performance')
        can_view_own = check_perm('view_own_team_performance') or can_view_all

        if not (can_view_all or can_view_own):
            return Response({'error': 'You do not have permission to view team performance.'}, status=status.HTTP_403_FORBIDDEN)

        # 2. Determine base queryset
        if can_view_all:
            queryset = Team.objects.all()
        else:
            # Users with "Own Team" only see teams where they are lead or member
            queryset = Team.objects.filter(
                Q(team_lead=request.user) | Q(members=request.user)
            ).distinct()

        # 3. Handle specific team drill-down if requested
        team_id = request.query_params.get('team_id')
        if team_id:
            queryset = queryset.filter(pk=team_id)
            if not queryset.exists():
                return Response({'error': 'Team not found or access denied.'}, status=status.HTTP_404_NOT_FOUND)

        # 4. Process stats
        all_stats = [self._get_team_stats(t) for t in queryset]
        
        total_pending = sum(s.pop('_pending', 0) for s in all_stats)
        total_completed = sum(s.pop('_completed', 0) for s in all_stats)
        total_inprogress = sum(s.pop('_progressing', 0) for s in all_stats)

        # 5. Handle empty cases for better UX
        if not all_stats and not can_view_all:
            return Response({'error': 'No team found for your account.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'total_teams': len(all_stats),
            'total_pending': total_pending,
            'total_completed': total_completed,
            'total_inprogress': total_inprogress,
            'teams': all_stats,
        }, status=status.HTTP_200_OK)
