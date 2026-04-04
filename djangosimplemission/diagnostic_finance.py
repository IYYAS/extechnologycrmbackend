import os
import django
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import ClientAdvance, ProjectBusinessAddress, Payment, Invoice

def diagnostic():
    try:
        client_id = 47
        invoice_id = 18
        
        print("\n=== CLIENT 47 STATUS ===")
        client = ProjectBusinessAddress.objects.get(id=client_id)
        print(f"Advance Balance Field: {client.advance_balance}")
        
        print("\n=== ADVANCE HISTORY (ClientAdvance Table) ===")
        advances = ClientAdvance.objects.filter(client_id=client_id).order_by('created_at')
        total_adv = Decimal("0.00")
        for a in advances:
            print(f"ID: {a.id} | Amount: {a.amount} | Payment: {a.payment_id} | Date: {a.created_at}")
            total_adv += a.amount
        print(f"Total calculated from records: {total_adv}")
        
        print("\n=== INVOICE 18 STATUS ===")
        invoice = Invoice.objects.get(id=invoice_id)
        print(f"Number: {invoice.invoice_number} | Status: {invoice.status}")
        print(f"Total Amount: {invoice.total_amount} | Total Paid: {invoice.total_paid} | Balance Due: {invoice.balance_due}")
        
        print("\n=== PAYMENTS LINKED TO INVOICE 18 ===")
        payments = Payment.objects.filter(invoice_id=invoice_id).order_by('payment_date')
        total_p = Decimal("0.00")
        for p in payments:
            print(f"ID: {p.id} | Amount: {p.amount} | Transaction ID: {p.transaction_id} | Date: {p.payment_date}")
            total_p += p.amount
        print(f"Grand Total of all payments: {total_p}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    diagnostic()
