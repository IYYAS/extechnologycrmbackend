import os
import django
from decimal import Decimal
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import User, Employee, Attendance, Salary, UserSalary, calculate_salary

def verify():
    print("--- Starting UserSalary Joining Date Verification ---")
    
    # 1. Setup User
    username = "usersal_date_user"
    User.objects.filter(username=username).delete()
    user = User.objects.create(username=username, email="usersal@test.com")
    
    # 2. Setup Employee Profile (joining: 2026-01-01)
    profile_date = date(2026, 1, 1)
    Employee.objects.create(user=user, employee_id="USAL001", joining_date=profile_date)
    print(f"Profile joining date: {profile_date}")

    # 3. Setup UserSalary (joining: 2026-02-01) - This should OVERRIDE profile
    config_date = date(2026, 2, 1)
    UserSalary.objects.create(user=user, base_salary=Decimal('26000.00'), joining_date=config_date)
    print(f"UserSalary joining date: {config_date} (Should override profile)")

    # 4. Add Attendance for Cycle 1 based on UserSalary (Feb 1st to Feb 26th)
    test_date = date(2026, 2, 5)
    Attendance.objects.create(employee=user, date=test_date, status="Present")
    print(f"Added Attendance for {test_date}")

    # 5. Verify Salary Record
    # Cycle 1 for Feb 1st starts: 2026-02-01
    salary = Salary.objects.filter(employee=user, start_date=config_date).first()
    if not salary:
        print("FAILURE: Salary record NOT found for UserSalary joining date cycle!")
        # Check if it erroneously used profile date
        err_salary = Salary.objects.filter(employee=user, start_date=profile_date).first()
        if err_salary:
            print(f"FAILURE: System used profile date {profile_date} instead of UserSalary date!")
        return

    print(f"SUCCESS: Salary record found for correct cycle: {salary.start_date} to {salary.end_date}")
    print("Verified: UserSalary.joining_date is successfully prioritized over profile!")

if __name__ == "__main__":
    verify()
