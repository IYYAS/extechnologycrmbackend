import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import ProjectClient, ClientAdvance, Invoice
from djangosimplemissionapp.services import apply_advances_to_invoice
from decimal import Decimal

def verify():
    print("--- Starting Backend Logic Verification ---")
    
    # 1. Setup Client
    client = ProjectClient.objects.create(legal_name="Manual Advance Verification Client")
    
    # 2. Add Advance ₹2,000
    adv = ClientAdvance.objects.create(
        client=client,
        amount=Decimal('2000.00'),
        payment_method="Cash",
        notes="Pre-payment for testing"
    )
    print(f"Created Advance: ID={adv.id}, Total=₹{adv.amount}, Remaining=₹{adv.remaining_amount}")

    # 3. Create Invoice ₹3,000
    # Note: Using manual attribute setting as signals handle automatic reconciliation normally.
    # But here we want to test apply_advances_to_invoice directly with limit_amount.
    invoice = Invoice.objects.create(
        client_company=client,
        tax_rate=0,
        discount_amount=0,
        total_amount=Decimal('3000.00'),
        balance_due=Decimal('3000.00'),
        subtotal=Decimal('3000.00')
    )
    print(f"Created Invoice: ID={invoice.id}, Balance=₹{invoice.balance_due}")

    # 4. Apply exactly ₹1,000 from advance credit
    print("\nAction: Manually applying ₹1,000 from advance credit...")
    apply_advances_to_invoice(invoice, limit_amount=Decimal('1000.00'))

    # Refresh items from DB
    invoice.refresh_from_db()
    adv.refresh_from_db()
    
    print(f"Manual Apply Result:")
    print(f"  Invoice Balance Due: ₹{invoice.balance_due} (Expected: ₹2000.00)")
    print(f"  Advance Remaining: ₹{adv.remaining_amount} (Expected: ₹1000.00)")

    # 5. Check if automatic application still works for the rest
    print("\nAction: Automatically applying remaining advances...")
    apply_advances_to_invoice(invoice)
    
    invoice.refresh_from_db()
    adv.refresh_from_db()

    print(f"Automatic Apply Result:")
    print(f"  Invoice Balance Due: ₹{invoice.balance_due} (Expected: ₹1000.00)")
    print(f"  Advance Remaining: ₹{adv.remaining_amount} (Expected: ₹0.00)")

    # 6. Cleanup
    print("\nCleaning up test data...")
    client.delete()
    print("--- Verification Complete ---")

if __name__ == "__main__":
    verify()
