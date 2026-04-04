import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Project, ProjectBusinessAddress, Invoice
from djangosimplemissionapp.serializers import ProjectSummarySerializer

def test_project_summary():
    print("Testing Project Summary API logic (with M2M)...")
    
    # 1. Create a client address
    addr = ProjectBusinessAddress.objects.create(legal_name="Summary Corp", city="Summary City")
    
    # 2. Create a project and link it
    proj = Project.objects.create(name="Summary Project", description="Test summary")
    addr.projects.add(proj)
    
    # 3. Create an invoice for this client
    # Note: Invoice model might have other required fields
    invoice = Invoice.objects.create(
        client_company=addr,
        total_amount=Decimal("1500.00"),
        total_paid=Decimal("500.00"),
        balance_due=Decimal("1000.00"),
        status="Partial"
    )
    
    # 4. Serialize the project summary
    ser = ProjectSummarySerializer(instance=proj)
    data = ser.data
    
    print("\nSerialized Data:")
    for k, v in data.items():
        print(f" - {k}: {v}")

    # 5. Assertions
    success = True
    if data['legal_name'] != "Summary Corp":
        print(f"❌ Error: Expected legal_name 'Summary Corp', got '{data['legal_name']}'")
        success = False
    
    if data['invoice_count'] != 1:
        print(f"❌ Error: Expected invoice_count 1, got {data['invoice_count']}")
        success = False

    if Decimal(str(data['total_invoiced'])) != Decimal("1500.00"):
        print(f"❌ Error: Expected total_invoiced 1500, got {data['total_invoiced']}")
        success = False

    if success:
        print("\n✅ SUCCESS: Project Summary API logic works as expected with M2M!")
    else:
        print("\n❌ FAILURE: Summary API logic error.")

    # Cleanup (optional)
    # invoice.delete()
    # proj.delete()
    # addr.delete()

if __name__ == "__main__":
    test_project_summary()
