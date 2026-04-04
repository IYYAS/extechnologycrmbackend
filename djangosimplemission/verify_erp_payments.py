import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Invoice, Payment, ProjectBusinessAddress, ClientLedger
from djangosimplemissionapp.services import recalibrate_ledger

def test_nested_payments():
    # 1. Setup clean state for Client
    try:
        client = ProjectBusinessAddress.objects.get(id=47)
        print(f"Found existing client {client.id}")
    except ProjectBusinessAddress.DoesNotExist:
        client = ProjectBusinessAddress.objects.create(
            id=47,
            legal_name="Test Client ERP",
            city="Test City"
        )
        print(f"Created new test client {client.id}")
    
    Invoice.objects.filter(client_company=client).delete()
    print("Deleted existing invoices for client.")
    Payment.objects.filter(invoice__client_company=client).delete()
    ClientLedger.objects.filter(client=client).delete()
    
    # 2. Create an Invoice
    inv = Invoice.objects.create(
        client_company=client,
        invoice_number="TEST-ERP-001",
        total_amount=Decimal("1000.00"),
        status="UNPAID"
    )
    print(f"Created Invoice: {inv.invoice_number}")
    
    # 3. Add a Payment via logic (simulating the POST endpoint)
    # The endpoint uses PaymentSerializer.save(invoice=invoice)
    p1 = Payment.objects.create(
        invoice=inv,
        amount=Decimal("400.00"),
        payment_method="Bank Transfer",
        transaction_id="TXN123"
    )
    print(f"Added Payment 1: {p1.amount}")
    
    # 4. Add another Payment
    p2 = Payment.objects.create(
        invoice=inv,
        amount=Decimal("600.00"),
        payment_method="Cash",
        transaction_id="TXN456"
    )
    print(f"Added Payment 2: {p2.amount}")
    
    # 5. Verify Ledger (recalibrate_ledger is triggered by signals)
    ledger = ClientLedger.objects.filter(client=client).order_by('created_at')
    print("\n--- LEDGER VERIFICATION ---")
    for entry in ledger:
        print(f"{entry.transaction_type}: Debit={entry.debit}, Credit={entry.credit}, Balance={entry.balance}")

    expected_final_balance = Decimal("0.00") # 1000 - 400 - 600
    actual_final_balance = ledger.last().balance
    
    if actual_final_balance == expected_final_balance:
        print("\n✅ SUCCESS: Ledger is perfectly balanced!")
    else:
        print(f"\n❌ FAILURE: Balance mismatch! Expected {expected_final_balance}, got {actual_final_balance}")

if __name__ == "__main__":
    test_nested_payments()
