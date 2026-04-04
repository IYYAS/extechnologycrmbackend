import os
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import User, Employee, Attendance, Salary, calculate_salary

# 1. Setup
user, _ = User.objects.get_or_create(username="test_erp_user", email="test@erp.com")
profile, _ = Employee.objects.get_or_create(
    user=user, 
    defaults={
        "employee_id": "ERP001", 
        "joining_date": date(2026, 1, 1),
        "basic_salary": Decimal('26000.00')
    }
)

# 2. Create Salary for March 2026
month = date(2026, 3, 1)
Salary.objects.filter(employee=user, month=month).delete()
salary = Salary.objects.create(
    employee=user,
    month=month,
    basic=Decimal('26000.00'),
    working_days=26
)

print(f"Initial Salary: {salary.total_salary}, Present Days: {salary.present_days}")

# 3. Add Attendance
Attendance.objects.filter(employee=user, date__year=2026, date__month=3).delete()

# Day 1: Present
Attendance.objects.create(employee=user, date=date(2026, 3, 1), status="Present")
# Day 2: Half Day
Attendance.objects.create(employee=user, date=date(2026, 3, 2), status="HalfDay")
# Day 3: Present + 2 hours Overtime
Attendance.objects.create(employee=user, date=date(2026, 3, 3), status="Present", overtime_hours=2.0)
# Day 4: Present + 15 mins Late
Attendance.objects.create(employee=user, date=date(2026, 3, 4), status="Present", late_minutes=15)

# Refresh salary
salary.refresh_from_db()
print(f"Updated Salary: {salary.total_salary}")
print(f"Present Days: {salary.present_days} (Expected 3.5)")
print(f"Overtime Pay: {salary.overtime_pay} (Expected 200.00)")
print(f"Late Deduction: {salary.late_deduction} (Expected 30.00)")

# Verify calculations:
# Daily = 26000 / 26 = 1000
# Earned = 3.5 * 1000 = 3500
# Total = 3500 + 200 - 30 = 3670
expected_total = Decimal('3670.00')
if salary.total_salary == expected_total:
    print("SUCCESS: ERP Payroll calculation is accurate!")
else:
    print(f"FAILURE: Expected {expected_total}, got {salary.total_salary}")

# 4. Cleanup (optional, but good for repeatability)
# Attendance.objects.filter(employee=user).delete()
# Salary.objects.filter(employee=user).delete()
