import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import ClientAdvance, ProjectBusinessAddress, Invoice, Payment
from djangosimplemissionapp.services import sync_client_advances

def test_advance_management():
    # 1. Setup Client
    client = ProjectBusinessAddress.objects.filter(id=47).first()
    if not client:
        client = ProjectBusinessAddress.objects.create(id=47, legal_name="Advance Test Client")
    
    import random
    inv_num = f"ADV-TEST-{random.randint(1000, 9999)}"
    
    # 2. Add Invoice
    print(f"Creating invoice {inv_num}...")
    inv = Invoice.objects.create(
        client_company=client,
        invoice_number=inv_num,
        total_amount=Decimal("1000.00"),
        status="UNPAID"
    )

    # 3. Create Manual Advance
    adv_amount = Decimal("500.00")
    adv = ClientAdvance.objects.create(
        client=client,
        amount=adv_amount,
        is_manual=True,
        note="Manual Advance Test"
    )
    print(f"Created manual advance {adv.id} with amount {adv_amount}")

    # 4. Verify Advance Sync
    # handle_client_advance_save calls sync_client_advances
    adv.refresh_from_db()
    if adv.remaining_amount == adv_amount:
        print("✅ Advance correctly initialized with remaining_amount.")
    else:
        print(f"❌ Advance remaining_amount mismatch: {adv.remaining_amount}")

    # 5. Delete Advance
    print(f"Attempting to delete advance {adv.id}...")
    try:
        adv.delete()
        print("✅ Advance deleted successfully (no 500 error).")
    except Exception as e:
        print(f"❌ Failed to delete advance: {e}")
        return

    # 6. Final verification - Ledger model should not exist in DB
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='djangosimplemissionapp_clientledger'")
        if cursor.fetchone()[0] == 0:
            print("✅ ClientLedger table verified DELETED from database.")
        else:
            print("❌ ClientLedger table STILL EXISTS in database!")

    # Cleanup
    inv.delete()

if __name__ == "__main__":
    test_advance_management()
