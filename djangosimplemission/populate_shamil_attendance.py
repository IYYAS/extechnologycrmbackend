import os
import django
from datetime import date, time, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import User, Attendance, Salary, Employee

def populate_attendance():
    # 1. Get or create shamil
    shamil, created = User.objects.get_or_create(
        username="shamil", 
        defaults={"email": "shamil@example.com"}
    )
    if created:
        shamil.set_password("shamil123")
        shamil.save()
        print("Created user 'shamil'")
    
    # Ensure profile exists for basic salary
    profile, p_created = Employee.objects.get_or_create(
        user=shamil,
        defaults={
            "employee_id": "SHM001",
            "joining_date": date(2025, 1, 1),
            "basic_salary": Decimal('45000.00')
        }
    )
    if p_created:
        print("Created employee profile for 'shamil' with 45k basic")

    # 2. Helper to create 30 days of attendance
    def create_30_days(start_date):
        print(f"Populating attendance for {start_date.strftime('%B %Y')}...")
        for i in range(30):
            current_date = start_date + timedelta(days=i)
            # Skip Sundays for realism (Sunday = 6)
            if current_date.weekday() == 6:
                status = "Absent"
                check_in = None
                check_out = None
            else:
                status = "Present"
                check_in = time(9, 0)
                check_out = time(18, 0)
            
            Attendance.objects.update_or_create(
                employee=shamil,
                date=current_date,
                defaults={
                    "status": status,
                    "check_in": check_in,
                    "check_out": check_out,
                    "overtime_hours": 1.0 if i % 5 == 0 and status == "Present" else 0, # Add some OT
                    "late_minutes": 5 if i % 7 == 0 and status == "Present" else 0 # Add some late
                }
            )

    # March 2026
    create_30_days(date(2026, 3, 1))
    
    # April 2026
    create_30_days(date(2026, 4, 1))

    print("\nVerification:")
    for month in [date(2026, 3, 1), date(2026, 4, 1)]:
        try:
            salary = Salary.objects.get(employee=shamil, month=month)
            print(f"Month: {month.strftime('%B %Y')}")
            print(f" - Basic: {salary.basic}")
            print(f" - Present Days: {salary.present_days}")
            print(f" - Working Days: {salary.working_days}")
            print(f" - Overtime Pay: {salary.overtime_pay}")
            print(f" - Late Deduction: {salary.late_deduction}")
            print(f" - Total Salary: {salary.total_salary}")
        except Salary.DoesNotExist:
            print(f"Salary record for {month.strftime('%B %Y')} not found!")

if __name__ == "__main__":
    populate_attendance()
