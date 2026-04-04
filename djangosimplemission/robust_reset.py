import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import ClientAdvance, ClientLedger, ProjectBusinessAddress, Invoice, Payment

def robust_reset():
    print("Starting Robust Reset...")
    
    # 1. Delete all history
    v1 = ClientAdvance.objects.all().delete()
    print(f"Deleted Advances: {v1}")
    
    v2 = ClientLedger.objects.all().delete()
    print(f"Deleted Ledgers: {v2}")
    
    v3 = Payment.objects.all().delete()
    print(f"Deleted Payments: {v3}")
    
    # 2. Reset All Balances
    v4 = ProjectBusinessAddress.objects.all().update(advance_balance=Decimal("0.00"))
    print(f"Reset {v4} Client Balances to 0.00")
    
    # 3. Reset All Invoices
    for inv in Invoice.objects.all():
        inv.total_paid = Decimal("0.00")
        inv.balance_due = inv.total_amount
        inv.status = 'UNPAID'
        inv.save(update_fields=['total_paid', 'balance_due', 'status'])
    print(f"Reset {Invoice.objects.count()} Invoices to UNPAID")
    
    # Verification
    c47 = ProjectBusinessAddress.objects.filter(id=47).first()
    if c47:
        print(f"VERIFICATION: Client 47 Balance is now: {c47.advance_balance}")
    else:
        print("VERIFICATION: Client 47 not found.")

if __name__ == "__main__":
    robust_reset()
