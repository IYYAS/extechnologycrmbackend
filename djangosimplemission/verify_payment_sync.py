import os
import django
import sys
from decimal import Decimal

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import (
    Project, ProjectBusinessAddress, ProjectDomain, ProjectServer, 
    Invoice, InvoiceItem, Payment
)
from django.utils import timezone

def reproduce():
    print("--- Reproduction Start ---")
    
    # 1. Setup Data
    project = Project.objects.create(name="Sync Test Project")
    address = ProjectBusinessAddress.objects.create(legal_name="Sync Test Client")
    address.projects.add(project)
    
    domain = ProjectDomain.objects.create(
        project=project,
        client_address=address,
        name="sync-test.com",
        cost=Decimal("1000.00"),
        payment_status="UNPAID"
    )
    
    # 2. Create Invoice
    invoice = Invoice.objects.create(client_company=address)
    item = InvoiceItem.objects.create(
        invoice=invoice,
        project_domain=domain,
        rate=Decimal("1000.00"),
        quantity=1,
        description="Domain Renewal"
    )
    
    # Verify Initial State
    invoice.refresh_from_db()
    print(f"Initial Invoice Status: {invoice.status}")
    print(f"Initial Domain Payment Status: {domain.payment_status}")
    
    # 3. Apply Payment (This triggers process_payment_accounting for NEW payments)
    print("Applying full payment...")
    Payment.objects.create(
        invoice=invoice,
        amount=Decimal("1000.00"),
        payment_method="Cash"
    )
    
    # 4. Check Results
    invoice.refresh_from_db()
    domain.refresh_from_db()
    
    print(f"Final Invoice Status: {invoice.status}")
    print(f"Final Domain Payment Status: {domain.payment_status}")
    
    if invoice.status == "PAID" and domain.payment_status == "UNPAID":
        print("!!! BUG REPRODUCED: Invoice is PAID but Domain is still UNPAID !!!")
    elif invoice.status == "PAID" and domain.payment_status == "PAID":
        print("Fix works: Both are PAID.")
    else:
        print(f"Unexpected state: Invoice {invoice.status}, Domain {domain.payment_status}")

    # Cleanup
    # project.delete()
    # address.delete()

if __name__ == "__main__":
    reproduce()
