import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from djangosimplemissionapp.models import Role, Project, ProjectServer, ProjectDomain, Team, User, EmployeeDailyActivity

def seed_rbac():
    print("Seeding RBAC...")

    project_ct = ContentType.objects.get_for_model(Project)
    server_ct  = ContentType.objects.get_for_model(ProjectServer)
    domain_ct  = ContentType.objects.get_for_model(ProjectDomain)
    role_ct    = ContentType.objects.get_for_model(Role)
    team_ct    = ContentType.objects.get_for_model(Team)
    user_ct    = ContentType.objects.get_for_model(User)
    activity_ct = ContentType.objects.get_for_model(EmployeeDailyActivity)

    # Fetch permissions
    view_project      = Permission.objects.get(codename='view_project',      content_type=project_ct)
    view_projectstats = Permission.objects.get(codename='view_projectstats', content_type=project_ct)
    view_analytics    = Permission.objects.get(codename='view_analytics',    content_type=project_ct)
    view_server_stats = Permission.objects.get(codename='view_server_stats', content_type=server_ct)
    view_domain_stats = Permission.objects.get(codename='view_domain_stats', content_type=domain_ct)
    view_role         = Permission.objects.get(codename='view_role',         content_type=role_ct)
    
    # Team Permissions
    view_teamperformance = Permission.objects.get(codename='view_teamperformance', content_type=team_ct)
    view_all_team_performance = Permission.objects.get(codename='view_all_team_performance', content_type=team_ct)
    view_own_team_performance = Permission.objects.get(codename='view_own_team_performance', content_type=team_ct)
    
    # Employee Performance Permissions
    view_all_employee_performance = Permission.objects.get(codename='view_all_employee_performance', content_type=user_ct)
    view_own_employee_performance = Permission.objects.get(codename='view_own_employee_performance', content_type=user_ct)

    # Activity Permissions
    view_all_activities = Permission.objects.get(codename='view_all_activities', content_type=activity_ct)
    view_own_activities = Permission.objects.get(codename='view_own_activities', content_type=activity_ct)

    # Create/Get Roles and assign permissions
    dev_role,        _ = Role.objects.get_or_create(name='DEVELOPER')
    admin_role,      _ = Role.objects.get_or_create(name='ADMIN')
    superadmin_role, _ = Role.objects.get_or_create(name='SUPERADMIN')
    teamhead_role,   _ = Role.objects.get_or_create(name='TEAMHEAD')

    dev_role.permissions.set([view_project, view_projectstats, view_own_employee_performance, view_own_activities])

    admin_role.permissions.set([
        view_analytics,
        view_project,
        view_projectstats,
        view_server_stats,
        view_domain_stats,
        view_teamperformance,
        view_all_team_performance,
        view_all_employee_performance,
        view_all_activities,
    ])

    teamhead_role.permissions.set([
        view_teamperformance,
        view_own_team_performance,
        view_own_employee_performance,
        view_own_activities,
    ])

    superadmin_role.permissions.set(Permission.objects.all())

    print(f"Roles updated: {Role.objects.count()}")
    print("Done!")

if __name__ == "__main__":
    seed_rbac()
