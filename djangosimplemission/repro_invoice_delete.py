import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Invoice, Payment, ProjectBusinessAddress

def test_invoice_deletion():
    # 1. Setup
    client = ProjectBusinessAddress.objects.filter(id=47).first()
    if not client:
        client = ProjectBusinessAddress.objects.create(id=47, legal_name="Delete Bug Client")
    
    print("Creating invoice and payments...")
    inv = Invoice.objects.create(
        client_company=client,
        total_amount=Decimal("1000.00"),
        status="UNPAID"
    )
    
    Payment.objects.create(
        invoice=inv,
        amount=Decimal("100.00"),
        payment_method="Cash"
    )

    print(f"Deleting invoice {inv.id}...")
    try:
        inv.delete()
        print("✅ Invoice deleted successfully in script.")
    except Exception as e:
        print(f"❌ Failed to delete invoice: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_invoice_deletion()
