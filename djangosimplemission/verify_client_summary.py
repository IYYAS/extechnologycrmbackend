import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Project, ProjectBusinessAddress, Invoice
from djangosimplemissionapp.serializers import ClientSummarySerializer

def test_client_summary():
    print("Testing Client Summary API logic...")
    
    # 1. Create a client address
    addr = ProjectBusinessAddress.objects.create(legal_name="Client X", city="London")
    addr_id = addr.id
    
    # 2. Link it to TWO projects
    p1 = Project.objects.create(name="Project Alpha", description="...")
    p2 = Project.objects.create(name="Project Beta", description="...")
    addr.projects.add(p1, p2)
    
    # 3. Create THREE invoices for this client
    # Invoice 1
    Invoice.objects.create(client_company=addr, total_amount=Decimal("100.00"), total_paid=Decimal("50.00"), balance_due=Decimal("50.00"))
    # Invoice 2
    Invoice.objects.create(client_company=addr, total_amount=Decimal("200.00"), total_paid=Decimal("0.00"), balance_due=Decimal("200.00"))
    # Invoice 3
    Invoice.objects.create(client_company=addr, total_amount=Decimal("50.00"), total_paid=Decimal("50.00"), balance_due=Decimal("0.00"))

    # 4. Serialize this client
    ser = ClientSummarySerializer(instance=addr)
    data = ser.data
    
    print("\nClient Summary Data:")
    for k, v in data.items():
        print(f" - {k}: {v}")

    # 5. Assertions
    success = True
    if data['invoice_count'] != 3:
        print(f"❌ Error: Expected invoice_count 3, got {data['invoice_count']}")
        success = False
    
    if Decimal(str(data['total_invoiced'])) != Decimal("350.00"):
        print(f"❌ Error: Expected total_invoiced 350.00, got {data['total_invoiced']}")
        success = False

    if success:
        print("\n✅ SUCCESS: Client Summary API correctly counts ALL invoices for a client!")
    else:
        print("\n❌ FAILURE: Client Summary logic error.")

    # Cleanup (optional)
    # Project.objects.filter(id__in=[p1.id, p2.id]).delete()
    # addr.delete()

if __name__ == "__main__":
    test_client_summary()
