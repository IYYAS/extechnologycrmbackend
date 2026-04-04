import os
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import User, Employee, Attendance, Salary, UserSalary, calculate_salary

def verify():
    print("--- Starting UserSalary Verification ---")
    
    # 1. Setup User
    username = "salary_test_user"
    User.objects.filter(username=username).delete()
    user = User.objects.create(username=username, email="salary@test.com")
    
    # 2. Set UserSalary (31200 / 26 days = 1200 per day)
    base_salary = Decimal('31200.00')
    working_days = 26
    UserSalary.objects.create(user=user, base_salary=base_salary, working_days=working_days)
    print(f"Created UserSalary: {base_salary} for {working_days} days")

    # 3. Add Attendance
    test_date = date(2026, 4, 1)
    Attendance.objects.filter(employee=user, date=test_date).delete()
    Attendance.objects.create(employee=user, date=test_date, status="Present")
    print(f"Added Attendance for {test_date}: Present")

    # 4. Verify Salary Record
    salary = Salary.objects.filter(employee=user, month=test_date.replace(day=1)).first()
    if not salary:
        print("FAILURE: Salary record not created!")
        return

    print(f"Generated Salary: Basic={salary.basic}, Working Days={salary.working_days}, Total={salary.total_salary}")
    
    # Expected: 1 day present * (31200 / 26) = 1200
    expected_total = Decimal('1200.00')
    
    if salary.basic == base_salary and salary.working_days == working_days and salary.total_salary == expected_total:
        print("SUCCESS: UserSalary logic is working perfectly!")
    else:
        print(f"FAILURE: Unexpected values. Expected Total: {expected_total}")

    # Cleanup
    # User.objects.filter(username=username).delete()

if __name__ == "__main__":
    verify()
