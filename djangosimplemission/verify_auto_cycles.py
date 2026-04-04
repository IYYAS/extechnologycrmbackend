import os
import django
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import User, Employee, Attendance, Salary, UserSalary

def verify():
    print("--- Starting Auto-Generation Verification ---")
    
    # 1. Setup User
    username = "auto_gen_user"
    User.objects.filter(username=username).delete()
    user = User.objects.create(username=username, email="auto@test.com")
    
    # 2. Setup Employee Profile
    Employee.objects.create(user=user, employee_id="AUTO001", joining_date=date(2020, 1, 1))

    # 3. Setup UserSalary with joining date 60 days ago
    today = timezone.now().date()
    joining_date = today - timedelta(days=60)
    
    print(f"Setting joining_date to: {joining_date} (60 days ago)")
    UserSalary.objects.create(user=user, base_salary=Decimal('26000.00'), joining_date=joining_date)
    
    # 4. Check Salary Records
    # Should have 3 records:
    # 1. joining_date to joining_date + 25
    # 2. joining_date + 26 to joining_date + 51
    # 3. joining_date + 52 to joining_date + 77 (Today is day 60, so it's in this cycle)
    
    salaries = Salary.objects.filter(employee=user).order_by('start_date')
    count = salaries.count()
    print(f"Found {count} salary records.")
    
    for s in salaries:
        print(f"- Cycle: {s.start_date} to {s.end_date}")

    if count >= 3:
        print("SUCCESS: Salary cycles were automatically generated from joining date to today!")
    else:
        print(f"FAILURE: Expected at least 3 cycles, found {count}.")

if __name__ == "__main__":
    verify()
