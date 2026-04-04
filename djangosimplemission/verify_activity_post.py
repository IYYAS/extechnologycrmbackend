import os
import django
from datetime import date
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import User, Project, Team, ProjectService, EmployeeDailyActivity
from rest_framework.test import APIRequestFactory, force_authenticate
from djangosimplemissionapp.views import EmployeeDailyActivityListCreateAPIView

def verify_post_api():
    print("Verifying POST API for EmployeeDailyActivity...")
    
    # 1. Setup data
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser(username='testadmin', email='test@example.com', password='password')
    
    project = Project.objects.create(name="Test Project", description="Test Description")
    team = Team.objects.create(name="Test Team")
    service = ProjectService.objects.create(project=project, name="Test Service")
    
    # 2. Prepare POST data
    data = {
        "employee": user.id,
        "team": team.id,
        "project": project.id,
        "project_service": service.id,
        "description": "Completed refactoring models and views.",
        "hours_spent": "5.50",
        "date": str(date.today()),
        "pending_work_percentage": 20,
        "is_timeline_exceeded": False,
        "delay_reason": ""
    }
    
    # 3. Request
    factory = APIRequestFactory()
    view = EmployeeDailyActivityListCreateAPIView.as_view()
    request = factory.post('/api/employee-daily-activities/', data, format='json')
    force_authenticate(request, user=user)
    
    response = view(request)
    
    if response.status_code == 201:
        print("✅ POST request successful (201 Created)")
        print(f"Response data: {response.data}")
        # Verify specific fields in database
        activity = EmployeeDailyActivity.objects.get(id=response.data['id'])
        if activity.hours_spent == Decimal("5.50"):
            print("✅ Field 'hours_spent' saved correctly.")
        else:
            print(f"❌ Field 'hours_spent' mismatch: {activity.hours_spent}")
    else:
        print(f"❌ POST request failed with status {response.status_code}")
        print(f"Response: {response.data}")

    # Cleanup
    project.delete()
    team.delete()

if __name__ == "__main__":
    verify_post_api()
